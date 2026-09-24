"""`JobQueue`: SAQ contra el Valkey real de pruebas y el doble en memoria."""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from saq import Queue, Status, Worker
from saq.queue.redis import RedisQueue
from saq.types import Context

from app.core.config import settings
from app.infra.queue import InMemoryJobQueue, QueueUnavailableError, SaqJobQueue


@pytest_asyncio.fixture
async def saq_queue() -> AsyncGenerator[Queue, None]:
    # Una cola con nombre propio por prueba: no ve los trabajos de las demás. Y se
    # crea dentro del loop de la prueba (pytest-asyncio usa uno por prueba).
    queue = Queue.from_url(settings.valkey_url, name=f"test-{uuid.uuid4()}")
    await queue.connect()
    yield queue
    await queue.disconnect()


@pytest.mark.asyncio
async def test_saq_queue_stores_job_with_our_options(saq_queue: Queue) -> None:
    enqueued = await SaqJobQueue(saq_queue).enqueue(
        "generate_document",
        timeout_seconds=60,
        max_attempts=3,
        key="doc-1",
        document_id="d-1",
        user_id="u-1",
    )

    assert enqueued is True
    job = await saq_queue.job("doc-1")
    assert job is not None
    assert job.function == "generate_document"
    assert job.kwargs == {"document_id": "d-1", "user_id": "u-1"}
    assert job.timeout == 60
    # max_attempts se traduce al `retries` de SAQ, que cuenta intentos totales.
    assert job.retries == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("max_attempts", [1, 3])
async def test_failing_job_runs_exactly_max_attempts_times(
    saq_queue: Queue, max_attempts: int
) -> None:
    """La traducción a `retries` se comprueba contra un worker de SAQ real, no
    solo el valor guardado: con max_attempts=1 (emails e IA) un fallo NO se
    repite. Si una versión nueva de SAQ cambiara lo que significa `retries`,
    "nunca dos veces" dependería de esta prueba para enterarse."""
    assert isinstance(saq_queue, RedisQueue)
    calls: list[int] = []
    # Clave única: SAQ guarda la marca de aborto como `saq:abort:<key>`, SIN el
    # nombre de la cola, así que una clave fija se pisaría entre pruebas.
    key = f"falla-{uuid.uuid4()}"

    async def always_fails(ctx: Context) -> None:
        calls.append(1)
        raise RuntimeError("fallo simulado")

    # SAQ registra por __qualname__ (aquí, "…<locals>.always_fails"): nombre
    # explícito.
    worker = Worker(
        saq_queue, functions=[("always_fails", always_fails)], dequeue_timeout=0.5
    )
    worker_task = asyncio.create_task(worker.start())
    try:
        # Al arrancar, el worker barre la lista de activos a la vez que saca el
        # primer trabajo, y puede abortar uno recién sacado (carrera de SAQ). Se
        # encola cuando ese primer barrido ya ha tomado su foto de la lista.
        async with asyncio.timeout(10):
            while not await saq_queue.redis.exists(saq_queue.namespace("sweep")):
                await asyncio.sleep(0.05)

        await SaqJobQueue(saq_queue).enqueue(
            "always_fails", timeout_seconds=10, max_attempts=max_attempts, key=key
        )

        finished = {Status.COMPLETE, Status.FAILED, Status.ABORTED}
        async with asyncio.timeout(20):
            while (job := await saq_queue.job(key)) is None or (
                job.status not in finished
            ):
                await asyncio.sleep(0.05)
    finally:
        await worker.stop()
        await worker_task

    assert (len(calls), job.status) == (max_attempts, Status.FAILED)


@pytest.mark.asyncio
async def test_job_argument_named_like_an_option_stays_an_argument(
    saq_queue: Queue,
) -> None:
    """SAQ mezcla opciones y argumentos en el mismo **kwargs: un argumento que se
    llamara `timeout` acabaría como opción del trabajo si no se separan."""
    await SaqJobQueue(saq_queue).enqueue(
        "some_job", timeout_seconds=10, max_attempts=1, key="k", timeout="arg"
    )

    job = await saq_queue.job("k")
    assert job is not None
    assert job.timeout == 10
    assert job.kwargs == {"timeout": "arg"}


@pytest.mark.asyncio
async def test_saq_queue_skips_a_job_already_queued_with_the_same_key(
    saq_queue: Queue,
) -> None:
    queue = SaqJobQueue(saq_queue)

    first = await queue.enqueue("job", timeout_seconds=10, max_attempts=1, key="same")
    second = await queue.enqueue("job", timeout_seconds=10, max_attempts=1, key="same")

    assert (first, second) == (True, False)


@pytest.mark.asyncio
async def test_unreachable_valkey_raises_our_own_error() -> None:
    """El service decide qué hacer si no se puede encolar; para eso necesita un
    error propio, no uno de redis-py (reglas de capas de infra/)."""
    queue = Queue.from_url("redis://127.0.0.1:1/0")  # nadie escucha en el puerto 1

    with pytest.raises(QueueUnavailableError):
        await SaqJobQueue(queue).enqueue("job", timeout_seconds=10, max_attempts=1)


@pytest.mark.asyncio
async def test_in_memory_queue_records_jobs_and_honours_keys() -> None:
    queue = InMemoryJobQueue()

    await queue.enqueue("job", timeout_seconds=10, max_attempts=1, user_id="u-1")
    await queue.enqueue("job", timeout_seconds=10, max_attempts=1, key="k")
    repeated = await queue.enqueue("job", timeout_seconds=10, max_attempts=1, key="k")

    assert repeated is False
    assert [job.kwargs for job in queue.jobs] == [{"user_id": "u-1"}, {}]
