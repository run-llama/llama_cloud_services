"""Composable request matcher objects used by the fake server overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(slots=True)
class MatcherContext:
    """Relevant bits of a request needed for matcher evaluation."""

    route: str
    schema_hash: Optional[str]
    file_id: Optional[str]
    file_name: Optional[str]
    file_sha256: Optional[str]
    mime_type: Optional[str]
    text_preview: Optional[str]


@dataclass(slots=True)
class FileMatcher:
    filename: Optional[str] = None
    file_id: Optional[str] = None
    sha256: Optional[str] = None
    mime_type: Optional[str] = None

    def matches(self, ctx: MatcherContext) -> bool:
        if self.file_id is not None and ctx.file_id != self.file_id:
            return False
        if self.filename is not None and ctx.file_name != self.filename:
            return False
        if self.sha256 is not None and ctx.file_sha256 != self.sha256:
            return False
        if self.mime_type is not None and ctx.mime_type != self.mime_type:
            return False
        return True


@dataclass(slots=True)
class SchemaMatcher:
    hash: Optional[str] = None

    def matches(self, ctx: MatcherContext) -> bool:
        if self.hash is None:
            return True
        return ctx.schema_hash == self.hash


@dataclass(slots=True)
class RequestMatcher:
    file: Optional[FileMatcher] = None
    schema: Optional[SchemaMatcher] = None
    predicate: Optional[Callable[[MatcherContext], bool]] = None

    def matches(self, ctx: MatcherContext) -> bool:
        if self.file and not self.file.matches(ctx):
            return False
        if self.schema and not self.schema.matches(ctx):
            return False
        if self.predicate and not self.predicate(ctx):
            return False
        return True
