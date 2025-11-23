"""Shared fake HTTP infrastructure for simulating the LlamaCloud REST API."""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional

import httpx
import respx

DEFAULT_SAAS_URL = "https://api.cloud.llamaindex.ai"

try:  # pragma: no cover - exercised indirectly via tests
    from pydantic.v1 import BaseModel as _PydanticBaseModel
except ImportError:  # pragma: no cover
    from pydantic import BaseModel as _PydanticBaseModel  # type: ignore

HandlerReturn = tuple[int, Any] | httpx.Response
Handler = Callable[["FakeRequest"], HandlerReturn | Awaitable[HandlerReturn]]


@dataclass(slots=True)
class FakeRequest:
    """Simplified view of an httpx request for handler consumption."""

    method: str
    url: httpx.URL
    headers: Mapping[str, str]
    query: Dict[str, str]
    json: Any
    body: bytes
    path_params: Dict[str, str] = field(default_factory=dict)

    def get_header(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.headers.get(key.lower(), default)


@dataclass(slots=True)
class _RouteDescriptor:
    method: str
    path_template: str
    handler: Handler

    def parse_path_params(self, path: str) -> Dict[str, str]:
        template_segments = [segment for segment in self.path_template.strip("/").split("/") if segment]
        path_segments = [segment for segment in path.strip("/").split("/") if segment]
        if len(template_segments) != len(path_segments):
            return {}
        params: Dict[str, str] = {}
        for template_segment, path_segment in zip(template_segments, path_segments):
            if template_segment.startswith("{") and template_segment.endswith("}"):
                params[template_segment[1:-1]] = path_segment
            elif template_segment != path_segment:
                return {}
        return params


class FakeLlamaCloudServer:
    """Context-managed respx router populated with fake LlamaCloud routes."""

    def __init__(self, base_urls: Iterable[str] | None = None):
        provided = [self._normalize(url) for url in base_urls or [] if url]
        if not provided:
            provided = [DEFAULT_SAAS_URL]
        ordered: List[str] = []
        for url in [*provided, DEFAULT_SAAS_URL]:
            if url not in ordered:
                ordered.append(url)
        self.primary_base_url: str = ordered[0]
        self.base_urls: tuple[str, ...] = tuple(ordered)
        self.router = respx.MockRouter(assert_all_called=False)
        self._routes: List[_RouteDescriptor] = []
        self.namespaces: Dict[str, Any] = {}

    def __enter__(self) -> "FakeLlamaCloudServer":
        self.router.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.router.__exit__(exc_type, exc, tb)

    def register_namespace(self, name: str, namespace: Any) -> None:
        self.namespaces[name] = namespace

    def add_handler(
        self, method: str, path_template: str, handler: Optional[Handler] = None
    ) -> Callable[[Handler], Handler]:
        """Register a handler for every configured base URL."""

        def decorator(func: Handler) -> Handler:
            descriptor = _RouteDescriptor(method=method.upper(), path_template=path_template, handler=func)
            self._routes.append(descriptor)
            for base in self.base_urls:
                pattern = self._compile_regex(base, path_template)
                self.router.route(method=method.upper(), url__regex=pattern).mock(
                    side_effect=lambda request, desc=descriptor: self._invoke(desc, request)
                )
            return func

        if handler is not None:
            return decorator(handler)
        return decorator

    async def _invoke(self, descriptor: _RouteDescriptor, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        headers = {k.lower(): v for k, v in request.headers.items()}
        fake_request = FakeRequest(
            method=request.method,
            url=request.url,
            headers=headers,
            query={k: v for k, v in request.url.params.multi_items()},
            json=self._maybe_parse_json(body, headers.get("content-type")),
            body=body,
            path_params=descriptor.parse_path_params(request.url.path),
        )
        result = descriptor.handler(fake_request)
        if inspect.isawaitable(result):
            result = await result  # type: ignore[assignment]
        return self._to_response(request, result)

    @staticmethod
    def _maybe_parse_json(body: bytes, content_type: Optional[str]) -> Any:
        if not body:
            return None
        if content_type and "application/json" not in content_type:
            try:
                return json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                return None
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _normalize(url: str) -> str:
        return url.rstrip("/")

    @staticmethod
    def _compile_regex(base: str, template: str) -> re.Pattern[str]:
        base_clean = base.rstrip("/")
        template_segments = [segment for segment in template.strip("/").split("/") if segment]
        regex_segments: List[str] = []
        for segment in template_segments:
            if segment.startswith("{") and segment.endswith("}"):
                regex_segments.append(r"[^/]+")
            else:
                regex_segments.append(re.escape(segment))
        pattern = f"^{re.escape(base_clean)}/" + "/".join(regex_segments) + "$"
        return re.compile(pattern)

    @staticmethod
    def _to_response(request: httpx.Request, result: HandlerReturn) -> httpx.Response:
        if isinstance(result, httpx.Response):
            return result
        status, payload = result
        if isinstance(payload, httpx.Response):
            return payload
        content: bytes
        headers: MutableMapping[str, str] = {}
        if payload is None:
            content = b""
        elif isinstance(payload, bytes):
            content = payload
        elif isinstance(payload, str):
            content = payload.encode("utf-8")
            headers["content-type"] = "text/plain; charset=utf-8"
        else:
            content = json.dumps(payload, default=FakeLlamaCloudServer._json_default).encode("utf-8")
            headers["content-type"] = "application/json"
        return httpx.Response(status_code=status, content=content, headers=headers, request=request)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, _PydanticBaseModel):
            return value.dict()
        if hasattr(value, "value"):
            return getattr(value, "value")
        raise TypeError(f"Object of type {type(value)} is not JSON serializable")
