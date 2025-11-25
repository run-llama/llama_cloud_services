from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, MutableMapping


def hash_chunks(chunks: Iterable[bytes]) -> str:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk)
    return digest.hexdigest()


def fingerprint_file(content: bytes, filename: str | None = None) -> str:
    name_bytes = filename.encode("utf-8") if filename else b""
    return hash_chunks((content, name_bytes))


def hash_schema(schema: Any) -> str:
    json_string = json.dumps(
        _to_serializable(schema),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(json_string.encode("utf-8")).hexdigest()


def combined_seed(*parts: str) -> int:
    digest = hash_chunks(tuple(part.encode("utf-8") for part in parts))
    return int(digest[:16], 16)


def generate_data_from_schema(schema: Any, seed: int) -> Any:
    rng = random.Random(seed)
    return _generate_value(schema, rng, depth=0)


def generate_text_blob(seed: int, sentences: int = 3) -> str:
    rng = random.Random(seed)
    words = [
        "aurora",
        "copper",
        "delta",
        "ember",
        "fable",
        "glyph",
        "harbor",
        "iris",
        "juniper",
        "kepler",
        "lumen",
        "monarch",
        "nylon",
        "onyx",
        "paragon",
        "quartz",
        "raptor",
        "solstice",
        "topaz",
        "umbra",
        "verdant",
        "willow",
        "xenon",
        "yonder",
        "zephyr",
    ]
    sentence_pieces = []
    for _ in range(sentences):
        length = rng.randint(6, 12)
        chosen = rng.sample(words, k=length)
        sentence = " ".join(chosen).capitalize() + "."
        sentence_pieces.append(sentence)
    return " ".join(sentence_pieces)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_serializable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    if isinstance(value, Mapping):
        return {key: _to_serializable(val) for key, val in value.items()}
    if isinstance(value, MutableMapping):
        return {key: _to_serializable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_serializable(item) for item in value]
    if hasattr(value, "model_dump_json"):
        return json.loads(value.model_dump_json())
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()  # type: ignore[call-arg]
    if hasattr(value, "model_json_schema"):
        return value.model_json_schema()
    return str(value)


def _generate_value(schema: Any, rng: random.Random, depth: int) -> Any:
    if depth > 8:
        return rng.choice(
            (
                rng.randint(1, 999),
                rng.random(),
                generate_text_blob(rng.randint(0, 1_000_000), sentences=1),
            )
        )

    if schema is None:
        return generate_text_blob(rng.randint(0, 1_000_000), sentences=1)

    if isinstance(schema, list):
        return [_generate_value(item, rng, depth + 1) for item in schema]

    if isinstance(schema, str):
        return f"{schema}-{rng.randint(100, 999)}"

    if isinstance(schema, Mapping):
        if "enum" in schema:
            options = schema["enum"]
            if options:
                index = rng.randint(0, len(options) - 1)
                return options[index]

        schema_type = schema.get("type")

        if schema_type == "object":
            properties = schema.get("properties", {})
            result = {}
            for key, subschema in properties.items():
                result[key] = _generate_value(subschema, rng, depth + 1)
            return result

        if schema_type == "array":
            items_schema = schema.get("items", {})
            min_items = schema.get("minItems", 1)
            max_items = schema.get("maxItems", max(3, min_items))
            length = rng.randint(min_items, min(min_items + 2, max_items))
            return [
                _generate_value(items_schema, rng, depth + 1) for _ in range(length)
            ]

        if schema_type == "integer":
            minimum = schema.get("minimum", 0)
            maximum = schema.get("maximum", minimum + 500)
            return rng.randint(int(minimum), int(maximum))

        if schema_type == "number":
            minimum = schema.get("minimum", 0.0)
            maximum = schema.get("maximum", minimum + 500.0)
            value = rng.uniform(float(minimum), float(maximum))
            return round(value, 2)

        if schema_type == "boolean":
            return rng.choice((True, False))

        if schema_type == "string":
            fmt = schema.get("format")
            if fmt == "date-time":
                timestamp = utcnow().isoformat()
                return timestamp
            if fmt == "email":
                return f"user{rng.randint(1000, 9999)}@example.com"
            if fmt == "uri":
                return f"https://example.com/{rng.randint(1000, 9999)}"
            min_length = schema.get("minLength", 5)
            max_length = schema.get("maxLength", max(10, min_length))
            length = rng.randint(min_length, min(min_length + 5, max_length))
            return generate_text_blob(
                rng.randint(0, 1_000_000), sentences=max(1, length // 5)
            )

        if schema_type == "null":
            return None

        if "oneOf" in schema:
            option = rng.choice(schema["oneOf"])
            return _generate_value(option, rng, depth + 1)

        if "anyOf" in schema:
            option = rng.choice(schema["anyOf"])
            return _generate_value(option, rng, depth + 1)

    return generate_text_blob(rng.randint(0, 1_000_000), sentences=1)
