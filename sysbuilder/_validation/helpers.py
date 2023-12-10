"""
These functions return JSON objects that jsonschema can use to validate JSON
Data.
"""

from typing import Dict, List


def type_bool() -> Dict:
    """Boolean"""
    return {"type": "boolean"}


def type_dict(properties: Dict = None, required: List = None) -> Dict:
    """Object"""

    val = {"type": "object"}

    if properties is not None:
        val["properties"] = properties

    if required is not None:
        val["required"] = required

    return val


def type_int() -> Dict:
    """Integer"""
    return {"type": "integer"}


def type_list(
    items: Dict = None,
    minimum_item_count: int | None = None,
    maximum_item_count: int | None = None,
) -> Dict:
    """Array"""

    val = {"type": "array"}

    if items is not None:
        val["items"] = items

    if minimum_item_count is not None:
        val["minItems"] = minimum_item_count

    if maximum_item_count is not None:
        val["maxItems"] = maximum_item_count

    return val


def type_str(enum: List = None, pattern: str = None) -> Dict:
    """String"""

    val = {"type": "string"}

    if enum is not None:
        val["enum"] = enum

    if pattern is not None:
        val["pattern"] = pattern

    return val
