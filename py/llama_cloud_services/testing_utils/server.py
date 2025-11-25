from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable, Dict, Optional, Sequence

import httpx
import respx

from .classify import FakeClassifyNamespace
from .extract import FakeExtractNamespace
from .files import FakeFilesNamespace
from .parse import FakeParseNamespace
from .agent_data import FakeAgentDataNamespace

Handler = Callable[[httpx.Request], httpx.Response]


class FakeLlamaCloudServer:
    DEFAULT_BASE_URL = "https://api.cloud.llamaindex.ai"
    DEFAULT_UPLOAD_BASE = "https://uploads.fake-llama.test"
    DEFAULT_DOWNLOAD_BASE = "https://downloads.fake-llama.test"

    def __init__(
        self,
        *,
        base_urls: Optional[Sequence[str]] = None,
        namespaces: Optional[Sequence[str]] = None,
        upload_base_url: Optional[str] = None,
        download_base_url: Optional[str] = None,
        default_project_id: str = "proj-test",
        default_organization_id: str = "org-test",
    ) -> None:
        self.base_urls = tuple(base_urls or (self.DEFAULT_BASE_URL,))
        selected = namespaces or ("files", "extract", "parse", "classify", "agent_data")
        self._namespace_names = {name.lower() for name in selected}
        self._upload_base_url = upload_base_url or self.DEFAULT_UPLOAD_BASE
        self._download_base_url = download_base_url or self.DEFAULT_DOWNLOAD_BASE
        self.default_project_id = default_project_id
        self.default_organization_id = default_organization_id
        self.router = respx.MockRouter(assert_all_called=False)
        self._installed = False
        self._registered = False

        self.files = FakeFilesNamespace(
            server=self,
            upload_base_url=self._upload_base_url,
            download_base_url=self._download_base_url,
        )
        self.extract = FakeExtractNamespace(server=self, files=self.files)
        self.parse = FakeParseNamespace(server=self)
        self.classify = FakeClassifyNamespace(server=self, files=self.files)
        self.agent_data = FakeAgentDataNamespace(server=self)

    # Context management ----------------------------------------------
    def install(self) -> "FakeLlamaCloudServer":
        if not self._registered:
            self._register_namespaces()
        if not self._installed:
            self.router.__enter__()
            self._installed = True
        return self

    def uninstall(self) -> None:
        if self._installed:
            self.router.__exit__(None, None, None)
            self._installed = False

    def __enter__(self) -> "FakeLlamaCloudServer":
        return self.install()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.uninstall()

    # Route utilities -------------------------------------------------
    def add_route(
        self,
        method: str,
        path: str,
        handler: Handler,
        *,
        namespace: str,
        alias: Optional[str] = None,
        base_urls: Optional[Sequence[str]] = None,
    ) -> respx.Route:
        urls = base_urls or self.base_urls
        first_route: Optional[respx.Route] = None
        for base in urls:
            route = self._register_route(method, base, path, handler)
            if first_route is None:
                first_route = route
        if alias and first_route:
            setattr(self, alias, first_route)
        return first_route  # type: ignore[return-value]

    def _register_route(
        self,
        method: str,
        base: str,
        path: str,
        handler: Handler,
    ) -> respx.Route:
        url = self._build_url(base, path)
        if "{" in path:
            regex = self._compile_regex(base, path)
            route = self.router.route(method=method, url__regex=regex)
        else:
            route = self.router.route(method=method, url=url)
        route.mock(side_effect=lambda request, func=handler: func(request))
        return route

    def _build_url(self, base: str, path: str) -> str:
        base = base.rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return f"{base}{path}"

    def _compile_regex(self, base: str, path: str) -> re.Pattern[str]:
        escaped = re.escape(base.rstrip("/"))
        regex_path = re.sub(r"\{[^/]+\}", r"[^/]+", path)
        pattern = f"^{escaped}{regex_path}$"
        return re.compile(pattern)

    # Helpers ---------------------------------------------------------
    def json(self, request: httpx.Request) -> Dict[str, Any]:
        if not request.content:
            return {}
        return json.loads(request.content.decode("utf-8"))

    def encode_json(self, payload: Dict[str, Any]) -> bytes:
        return json.dumps(payload).encode("utf-8")

    def json_response(self, payload: Any, *, status_code: int = 200) -> httpx.Response:
        body = json.dumps(payload, default=self._json_default).encode("utf-8")
        headers = {"content-type": "application/json"}
        return httpx.Response(status_code=status_code, headers=headers, content=body)

    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    # Internal --------------------------------------------------------
    def _json_default(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        if isinstance(value, (set, frozenset)):
            return list(value)
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8")
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()  # datetime/date support
            except Exception:
                pass
        raise TypeError(f"{value!r} is not JSON serializable")

    def _register_namespaces(self) -> None:
        if "files" in self._namespace_names:
            self.files.register()
        if "extract" in self._namespace_names:
            self.extract.register()
        if "parse" in self._namespace_names:
            self.parse.register()
        if "classify" in self._namespace_names:
            self.classify.register()
        if "agent_data" in self._namespace_names:
            self.agent_data.register()
        self._registered = True


__all__ = ["FakeLlamaCloudServer"]
