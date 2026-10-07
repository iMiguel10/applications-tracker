from copy import deepcopy
from typing import Any

from pydantic import BaseModel


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """El esquema JSON de `model` en la forma que exige la salida estructurada
    estricta de los proveedores (A31): sin referencias (`$ref` se sustituye por su
    definición), todo objeto con `additionalProperties: false` y todos sus campos en
    `required`, y sin `default` (un campo opcional se expresa como admitiendo null).

    Así el mismo esquema sirve a todos los adaptadores, y Pydantic lo valida igual a
    la vuelta (A32, primera capa).
    """
    schema = model.model_json_schema()
    definitions: dict[str, Any] = schema.pop("$defs", {})
    return _strict(schema, definitions, ())


def _strict(node: Any, definitions: dict[str, Any], seen: tuple[str, ...]) -> Any:
    if isinstance(node, list):
        return [_strict(item, definitions, seen) for item in node]
    if not isinstance(node, dict):
        return node

    ref = node.get("$ref")
    if isinstance(ref, str):
        name = ref.removeprefix("#/$defs/")
        if name in seen:
            raise ValueError(f"esquema recursivo no admitido: {name}")
        resolved = deepcopy(definitions[name])
        # Lo que acompaña a la referencia (una descripción) se conserva.
        resolved.update({key: value for key, value in node.items() if key != "$ref"})
        return _strict(resolved, definitions, (*seen, name))

    result = {
        key: _strict(value, definitions, seen)
        for key, value in node.items()
        if key != "default"
    }
    if result.get("type") == "object" and "properties" in result:
        result["additionalProperties"] = False
        result["required"] = list(result["properties"])
    return result
