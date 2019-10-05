"""Define methods to validate configuration for voluptuous."""

import datetime
from typing import Any, Sequence, TypeVar, Union

import voluptuous as vol

T = TypeVar("T")  # pylint: disable=invalid-name


def ensure_list(value: Union[T, Sequence[T]]) -> Sequence[T]:
    """Validate if a given object is a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def entity_id(value: Any) -> str:
    """Validate if a given object is an entity id."""
    value = str(value).lower()
    if "." in value:
        return value

    raise vol.Invalid(f"Invalide Entity-ID: {value}")


def entity_id_list(value: Any) -> str:
    """Validate if a given object is a list of entity ids."""
    value = str(value).lower()
    for item in value.split(","):
        if "." not in item:
            raise vol.Invalid(f"Invalide Entity-Liste: {value}")
    return value


def valid_date(value: Any) -> datetime.date:
    """Validate if a given object is a date."""
    try:
        return datetime.datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        raise vol.Invalid(f"Invalides Datum: {value}")


def valid_time(value: Any) -> datetime.datetime:
    """Validate if a given object is a time."""
    try:
        return datetime.datetime.strptime(value, "%H:%M:%S")
    except ValueError:
        raise vol.Invalid(f"Invalide Uhrzeit: {value}")
