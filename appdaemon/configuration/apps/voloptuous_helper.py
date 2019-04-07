from typing import Any, Sequence, TypeVar, Union

import voluptuous as vol

T = TypeVar('T')


def ensure_list(value: Union[T, Sequence[T]]) -> Sequence[T]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def entity_id(value: Any) -> str:
    value = str(value).lower()
    if '.' in value:
        return value

    raise vol.Invalid(f"Ungültige Entitäts-ID: {value}")