from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import httpx


MatcherPredicate = Callable[[httpx.Request], bool]


@dataclass
class FileMatcher:
    filename: Optional[str] = None
    sha256: Optional[str] = None
    file_id: Optional[str] = None


@dataclass
class SchemaMatcher:
    model: Optional[type] = None
    schema_hash: Optional[str] = None


@dataclass
class RequestMatcher:
    file: Optional[FileMatcher | MatcherPredicate] = None
    schema: Optional[SchemaMatcher] = None
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    organization_id: Optional[str] = None
    predicate: Optional[MatcherPredicate] = None


@dataclass
class RequestContext:
    request: httpx.Request
    json: Optional[dict[str, Any]]
    file_id: Optional[str] = None
    filename: Optional[str] = None
    file_sha256: Optional[str] = None
    schema_hash: Optional[str] = None
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    organization_id: Optional[str] = None

    def matches(self, matcher: Optional[RequestMatcher]) -> bool:
        if matcher is None:
            return True

        if matcher.project_id and matcher.project_id != self.project_id:
            return False

        if matcher.organization_id and matcher.organization_id != self.organization_id:
            return False

        if matcher.agent_id and matcher.agent_id != self.agent_id:
            return False

        if matcher.file:
            if isinstance(matcher.file, FileMatcher):
                if matcher.file.filename and matcher.file.filename != self.filename:
                    return False
                if matcher.file.file_id and matcher.file.file_id != self.file_id:
                    return False
                if matcher.file.sha256 and matcher.file.sha256 != self.file_sha256:
                    return False
            else:
                if not matcher.file(self.request):
                    return False

        if matcher.schema:
            if (
                matcher.schema.schema_hash
                and matcher.schema.schema_hash != self.schema_hash
            ):
                return False
            if matcher.schema.model and matcher.schema.schema_hash:
                return matcher.schema.schema_hash == self.schema_hash
            if matcher.schema.model and matcher.schema.schema_hash is None:
                expected = _schema_hash_from_model(matcher.schema.model)
                return expected == self.schema_hash

        if matcher.predicate and not matcher.predicate(self.request):
            return False

        return True


def _schema_hash_from_model(model: type) -> Optional[str]:
    if hasattr(model, "model_json_schema"):
        schema = model.model_json_schema()
    elif hasattr(model, "schema"):
        schema = model.schema()  # type: ignore[attr-defined]
    else:
        return None

    from ._deterministic import hash_schema

    return hash_schema(schema)
