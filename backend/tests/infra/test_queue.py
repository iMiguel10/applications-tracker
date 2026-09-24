"""`JobQueue`: SAQ contra el Valkey real de pruebas y el doble en memoria."""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from saq import Queue

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
