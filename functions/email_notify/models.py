"""Pydantic models for email_notify Firestore CloudEvent."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, model_validator

type FirestoreScalar = str | int | float | bool | None
type FirestoreRecursiveValue = (
    FirestoreScalar
    | Mapping[str, FirestoreRecursiveValue]
    | list[FirestoreRecursiveValue]
)


class MapValue(BaseModel):
    """Firestore MapValue: fields mapping string -> Value."""

    fields: dict[str, "FirestoreValue"] = {}

    model_config = ConfigDict(extra="ignore")


class ArrayValue(BaseModel):
    """Firestore ArrayValue: list of Value."""

    values: list["FirestoreValue"] = []

    model_config = ConfigDict(extra="ignore")


class FirestoreValue(BaseModel):
    """Firestore Value proto: union of stringValue, integerValue, doubleValue, etc.

    Handles mapValue and arrayValue recursively for nested documents.
    """

    string_value: str | None = None
    integer_value: str | None = None
    double_value: float | None = None
    boolean_value: bool | None = None
    null_value: str | None = None
    bytes_value: str | None = None
    reference_value: str | None = None
    map_value: MapValue | None = None
    array_value: ArrayValue | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _from_proto_keys(cls, data: dict[str, object]) -> dict[str, object]:
        """Convert Firestore proto keys (camelCase) to model fields."""
        key_map = {
            "stringValue": "string_value",
            "integerValue": "integer_value",
            "doubleValue": "double_value",
            "booleanValue": "boolean_value",
            "nullValue": "null_value",
            "bytesValue": "bytes_value",
            "referenceValue": "reference_value",
            "mapValue": "map_value",
            "arrayValue": "array_value",
        }
        return {key_map.get(k, k): v for k, v in data.items() if k in key_map}


def parse_firestore_value(value: FirestoreValue) -> FirestoreRecursiveValue:
    """Extract scalar or nested structure from FirestoreValue."""
    if value.null_value is not None:
        return None
    if value.string_value is not None:
        return value.string_value
    if value.integer_value is not None:
        return int(value.integer_value)
    if value.double_value is not None:
        return value.double_value
    if value.boolean_value is not None:
        return value.boolean_value
    if value.map_value is not None:
        return {k: parse_firestore_value(v) for k, v in value.map_value.fields.items()}
    if value.array_value is not None:
        return [parse_firestore_value(v) for v in value.array_value.values]
    return None


class DocumentEventData(BaseModel):
    """Firestore DocumentEventData: value with name and fields."""

    name: str | None = None
    fields: dict[str, FirestoreValue] = {}

    model_config = ConfigDict(extra="ignore")


class FirestoreCloudEventData(BaseModel):
    """CloudEvent data for Firestore document events."""

    value: DocumentEventData = DocumentEventData()

    model_config = ConfigDict(extra="ignore")


class ParsedUserDocument(BaseModel):
    """Parsed user document fields for email_notify."""

    status: str | None = None
    github_login: str | None = None
    email: str | None = None
