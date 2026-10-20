"""Reglas de la exportación completa (issue #4): cada tabla decidida, nombres de
fichero seguros y valores en JSON."""

import uuid
from datetime import UTC, date, datetime

import pytest

import app.models  # noqa: F401  (registra todas las tablas en el metadata)
from app.db.base import Base
from app.domain.account_export import (
    EXCLUDED_TABLES,
    EXPORTED_TABLES,
    document_path,
    table_file,
    to_json_value,
)


def test_every_table_is_exported_or_excluded_with_a_reason() -> None:
    # Una tabla nueva con datos de la cuenta obliga a decidir si se exporta: si no,
    # la portabilidad se quedaría corta sin que nadie lo notara.
    tables = set(Base.metadata.tables)
    decided = set(EXPORTED_TABLES) | set(EXCLUDED_TABLES)

    assert tables - decided == set(), "Tablas sin decidir"
    assert decided - tables == set(), "Tablas que ya no existen"
    assert set(EXPORTED_TABLES).isdisjoint(EXCLUDED_TABLES)
    assert all(reason.strip() for reason in EXCLUDED_TABLES.values())


@pytest.mark.parametrize("table", sorted(EXPORTED_TABLES))
def test_omitted_columns_exist(table: str) -> None:
    # Un nombre mal escrito dejaría salir la columna que se quería omitir.
    columns = set(Base.metadata.tables[table].columns.keys())

    assert EXPORTED_TABLES[table] <= columns


def test_binary_columns_are_always_omitted() -> None:
    # to_json_value no sabe convertir bytes: una columna binaria nueva haría fallar
    # la exportación en lugar de salir codificada sin que nadie lo decidiera.
    for table, omitted in EXPORTED_TABLES.items():
        for column in Base.metadata.tables[table].columns:
            if column.type.python_type is bytes:
                assert column.name in omitted, f"{table}.{column.name}"


def test_account_goes_in_its_own_file() -> None:
    assert table_file("users") == "account.json"
    assert table_file("applications") == "applications.json"


def test_document_path_is_safe_and_unique() -> None:
    document_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    assert (
        document_path(document_id, "CV Ana.pdf")
        == f"documents/{document_id}-CV Ana.pdf"
    )
    assert document_path(document_id, 'a:b/c\\d*?"<>|.pdf') == (
        f"documents/{document_id}-a_b_c_d______.pdf"
    )
    assert document_path(document_id, "carta") == f"documents/{document_id}-carta.pdf"
    assert document_path(document_id, "..") == f"documents/{document_id}-document.pdf"


def test_json_values() -> None:
    some_id = uuid.uuid4()

    assert to_json_value(datetime(2026, 10, 20, 8, 30, tzinfo=UTC)) == (
        "2026-10-20T08:30:00+00:00"
    )
    assert to_json_value(date(2026, 10, 20)) == "2026-10-20"
    assert to_json_value(some_id) == str(some_id)
    assert to_json_value({"a": [1]}) == {"a": [1]}
    with pytest.raises(TypeError):
        to_json_value(b"secreto")
