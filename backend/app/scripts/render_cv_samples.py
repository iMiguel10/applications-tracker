"""Maqueta un perfil de ejemplo con cada diseño de CV, y una carta de ejemplo con
cada uno, para revisarlos a ojo.

    docker compose exec api python -m app.scripts.render_cv_samples /tmp/cv [es|en]

Escribe `<diseño>-<idioma>.pdf` y `<diseño>-carta-<idioma>.pdf` en la carpeta
indicada y el tiempo de cada uno.
Sirve al crear o retocar un diseño (A25): no toca la BD ni el almacén.
"""

import asyncio
import sys
import time
import uuid
from datetime import date
from pathlib import Path

from app.domain.cover_letter import CoverLetterSnapshot
from app.domain.cv import (
    CvSection,
    CvSnapshot,
    SnapshotBullet,
    SnapshotContact,
    SnapshotEntry,
    SnapshotEntrySection,
    SnapshotLanguage,
    SnapshotLink,
    SnapshotSkill,
)
from app.infra.pdf.weasyprint_renderer import WeasyPrintRenderer
from app.services.cv_render_service import CvRenderService


def _entry(
    title: str,
    organization: str,
    start: date,
    end: date | None,
    bullets: list[str],
    *,
    location: str | None = None,
    description: str | None = None,
) -> SnapshotEntry:
    return SnapshotEntry(
        id=uuid.uuid4(),
        title=title,
        organization=organization,
        location=location,
        start_date=start,
        end_date=end,
        is_current=end is None,
        description=description,
        bullets=[SnapshotBullet(id=uuid.uuid4(), text=text) for text in bullets],
    )


def sample_snapshot() -> CvSnapshot:
    """Un perfil verosímil, con tildes, un enlace largo y una sección de cada tipo."""
    return CvSnapshot(
        contact=SnapshotContact(
            full_name="Lucía Fernández Ortega",
            headline="Ingeniera de software backend",
            email="lucia.fernandez@example.com",
            phone="+34 612 345 678",
            location="Valencia, España",
            links=[
                SnapshotLink(
                    label="LinkedIn",
                    url="https://www.linkedin.com/in/lucia-fernandez-ortega/",
                ),
                SnapshotLink(label="GitHub", url="https://github.com/luciafo"),
            ],
        ),
        summary=(
            "Ingeniera backend con ocho años construyendo APIs y sistemas de pagos en "
            "Python y Go. Me muevo bien entre el diseño de datos, la observabilidad y "
            "la mejora de equipos pequeños que tienen que desplegar a menudo sin romper nada."
        ),
        entry_sections=[
            SnapshotEntrySection(
                section=CvSection.EXPERIENCE,
                entries=[
                    _entry(
                        "Ingeniera de software sénior",
                        "Pagora",
                        date(2021, 3, 1),
                        None,
                        [
                            "Migré el cobro con tarjeta a una arquitectura por colas: de 40 a 3 incidencias al trimestre.",
                            "Diseñé la conciliación bancaria diaria que hoy procesa 1,2 millones de movimientos.",
                            "Mentora de tres personas que ahora lideran sus propios servicios.",
                        ],
                        location="Valencia (híbrido)",
                    ),
                    _entry(
                        "Desarrolladora backend",
                        "Viajes Albufera",
                        date(2017, 9, 1),
                        date(2021, 2, 1),
                        [
                            "Reescribí el buscador de disponibilidad: la respuesta media bajó de 1,8 s a 240 ms.",
                            "Introduje pruebas de contrato entre los ocho servicios del área de reservas.",
                        ],
                        location="Valencia",
                        description="Plataforma de reservas de hoteles y paquetes para agencias.",
                    ),
                ],
            ),
            SnapshotEntrySection(
                section=CvSection.EDUCATION,
                entries=[
                    _entry(
                        "Grado en Ingeniería Informática",
                        "Universitat Politècnica de València",
                        date(2012, 9, 1),
                        date(2016, 6, 1),
                        [],
                    )
                ],
            ),
            SnapshotEntrySection(
                section=CvSection.PROJECT,
                entries=[
                    _entry(
                        "Cuaderno de candidaturas",
                        "Proyecto personal",
                        date(2024, 5, 1),
                        None,
                        [
                            "Aplicación web para seguir procesos de selección, con FastAPI y React."
                        ],
                    )
                ],
            ),
            SnapshotEntrySection(
                section=CvSection.CERTIFICATION,
                entries=[
                    _entry(
                        "AWS Certified Solutions Architect – Associate",
                        "Amazon Web Services",
                        date(2022, 11, 1),
                        date(2022, 11, 1),
                        [],
                    )
                ],
            ),
        ],
        skills=[
            SnapshotSkill(id=uuid.uuid4(), name=name, category=category, level=level)
            for name, category, level in [
                ("Python", "Lenguajes", "expert"),
                ("Go", "Lenguajes", "advanced"),
                ("SQL", "Lenguajes", "expert"),
                ("PostgreSQL", "Datos", "expert"),
                ("Kafka", "Datos", "advanced"),
                ("Docker", "Plataforma", "advanced"),
                ("Kubernetes", "Plataforma", "intermediate"),
                ("Terraform", "Plataforma", "intermediate"),
                ("Mentoría", None, None),
            ]
        ],
        languages=[
            SnapshotLanguage(id=uuid.uuid4(), language="Español", level="native"),
            SnapshotLanguage(id=uuid.uuid4(), language="Valenciano", level="c2"),
            SnapshotLanguage(id=uuid.uuid4(), language="Inglés", level="c1"),
        ],
    )


def sample_letter(contact: SnapshotContact) -> CoverLetterSnapshot:
    """Una carta de longitud normal (unas 300 palabras), para ver si cabe en una
    página con la cabecera de cada diseño."""
    return CoverLetterSnapshot(
        contact=contact,
        company="Nimbus Data",
        position="Senior Backend Engineer",
        date="7 de octubre de 2026",
        greeting="Estimado equipo de Nimbus Data:",
        paragraphs=[
            (
                "Me presento a la posición de Senior Backend Engineer porque el reto "
                "que describís, escalar una plataforma de datos que ya procesa millones "
                "de eventos al día, es justo el tipo de problema en el que he trabajado "
                "los últimos años."
            ),
            (
                "En Acme Fintech lideré la migración de un monolito en Django a servicios "
                "en Go y Python, reduciendo el tiempo de despliegue de 45 a 8 minutos. "
                "Diseñé además la canalización de eventos con Kafka que hoy procesa "
                "40 millones de mensajes diarios, con métricas y alertas de extremo a "
                "extremo."
            ),
            (
                "Vuestra oferta pide experiencia con PostgreSQL a escala y con "
                "Kubernetes. Optimicé consultas críticas en PostgreSQL hasta bajar la "
                "latencia p95 de 900 a 120 ms, y mantuve los despliegues en Kubernetes "
                "con Terraform para tres equipos de producto."
            ),
            (
                "También me interesa la parte humana del puesto: he acompañado a cuatro "
                "personas en sus primeros meses como desarrolladoras, con revisiones de "
                "código y sesiones de diseño semanales."
            ),
            (
                "Me encantaría contaros con más detalle cómo podría aportar al equipo. "
                "Quedo a vuestra disposición para hablar cuando os venga bien."
            ),
        ],
        closing="Atentamente,",
    )


async def main(output: Path, language: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    service = CvRenderService(WeasyPrintRenderer())
    snapshot = sample_snapshot()
    letter = sample_letter(snapshot.contact)
    for key in service.designs():
        for suffix, render in (
            ("", service.render(snapshot, key, language)),
            ("-carta", service.render_letter(letter, key, language)),
        ):
            started = time.perf_counter()
            pdf = await render
            elapsed = time.perf_counter() - started
            target = output / f"{key}{suffix}-{language}.pdf"
            target.write_bytes(pdf)
            print(f"{target}  {len(pdf) / 1024:.0f} KB  {elapsed * 1000:.0f} ms")


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/cv")
    asyncio.run(main(folder, sys.argv[2] if len(sys.argv) > 2 else "es"))
