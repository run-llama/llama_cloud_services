"""Extract namespace fake server implementation."""

from __future__ import annotations

import base64
import hashlib
import json
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional

from llama_cloud import (
    ExtractAgent,
    ExtractConfig,
    ExtractJob,
    ExtractMode,
    ExtractRun,
    ExtractTarget,
    File,
    StatusEnum,
)
from llama_cloud.types import (
    ExtractSchemaValidateResponse,
    FileIdPresignedUrl,
    PaginatedExtractRunsResponse,
)

from llama_cloud_services.testing_utils.llama_cloud.matchers import (
    MatcherContext,
    RequestMatcher,
)
from llama_cloud_services.testing_utils.llama_cloud.server import FakeLlamaCloudServer, FakeRequest

DEFAULT_CONFIG = ExtractConfig(
    extraction_target=ExtractTarget.PER_DOC,
    extraction_mode=ExtractMode.MULTIMODAL,
)

OverrideDataProvider = Callable[[MatcherContext], Mapping[str, Any]]


@dataclass(slots=True)
class _ExtractOverride:
    matcher: RequestMatcher
    provider: OverrideDataProvider
    run_status: StatusEnum
    job_status: StatusEnum


@dataclass(slots=True)
class _FileRecord:
    file: File
    content: bytes
    fingerprint: str
    mime_type: str


@dataclass(slots=True)
class _JobRecord:
    job: ExtractJob
    run_id: str
    polls: int = 0
    target_status: StatusEnum = StatusEnum.SUCCESS
    success_after: int = 1


class ExtractState:
    def __init__(self) -> None:
        self.agents: Dict[str, ExtractAgent] = {}
        self.files: Dict[str, _FileRecord] = {}
        self.jobs: Dict[str, _JobRecord] = {}
        self.runs: Dict[str, ExtractRun] = {}
        self.overrides: List[_ExtractOverride] = []
        self.default_project_id = "00000000-0000-0000-0000-000000000000"

    def next_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4()}"

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    def register_override(self, override: _ExtractOverride) -> None:
        self.overrides.append(override)

    def resolve_override(self, ctx: MatcherContext) -> Optional[_ExtractOverride]:
        for override in reversed(self.overrides):
            if override.matcher.matches(ctx):
                return override
        return None

    def register_file_shell(self, name: str, external_file_id: str, mime_type: str) -> FileIdPresignedUrl:
        file_id = self.next_id("file")
        now = self.now()
        file = File(
            id=file_id,
            name=name,
            external_file_id=external_file_id,
            file_size=0,
            file_type=mime_type,
            created_at=now,
            updated_at=now,
            last_modified_at=now,
            project_id=self.default_project_id,
            data_source_id=self.next_id("ds"),
            permission_info={"access": "private"},
            resource_info={"provider": "fake"},
        )
        self.files[file_id] = _FileRecord(file=file, content=b"", fingerprint="", mime_type=mime_type)
        return FileIdPresignedUrl(
            url="",
            expires_at=now + timedelta(minutes=5),
            form_fields={},
            file_id=file_id,
        )

    def finalize_file(self, file_id: str, data: bytes) -> None:
        record = self.files[file_id]
        record.content = data
        record.fingerprint = hashlib.sha256(data).hexdigest()
        record.file = record.file.copy(
            update={
                "file_size": len(data),
                "updated_at": self.now(),
                "last_modified_at": self.now(),
            }
        )

    def ensure_inline_file(self, name: str, data: bytes, mime_type: str) -> _FileRecord:
        presigned = self.register_file_shell(name=name, external_file_id=name, mime_type=mime_type)
        upload_id = presigned.file_id
        self.finalize_file(upload_id, data)
        return self.files[upload_id]

    def compute_schema_hash(self, schema: Mapping[str, Any]) -> str:
        payload = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def list_runs_for_agent(self, agent_id: str) -> List[ExtractRun]:
        return [run for run in self.runs.values() if run.extraction_agent_id == agent_id]


class ExtractTestingApi:
    """Entry point for configuring and registering the fake extract endpoints."""

    def __init__(self, server: FakeLlamaCloudServer):
        self.server = server
        self.state = ExtractState()
        self.server.register_namespace("extract", self)
        self._register_routes()

    def stub_run(
        self,
        *,
        matcher: Optional[RequestMatcher] = None,
        data: Mapping[str, Any] | OverrideDataProvider,
        run_status: StatusEnum = StatusEnum.SUCCESS,
        job_status: StatusEnum = StatusEnum.SUCCESS,
    ) -> None:
        def _provider(ctx: MatcherContext) -> Mapping[str, Any]:
            return data(ctx) if callable(data) else data

        self.state.register_override(
            _ExtractOverride(
                matcher=matcher or RequestMatcher(),
                provider=_provider,
                run_status=run_status,
                job_status=job_status,
            )
        )

    def _register_routes(self) -> None:
        self.server.add_handler("PUT", "/api/v1/files")(self._handle_generate_presigned_url)
        self.server.add_handler("PUT", "/_fake/uploads/{file_id}")(self._handle_file_upload)
        self.server.add_handler("GET", "/api/v1/files/{file_id}")(self._handle_get_file)

        self.server.add_handler("POST", "/api/v1/extraction/extraction-agents")(self._handle_create_agent)
        self.server.add_handler("GET", "/api/v1/extraction/extraction-agents")(self._handle_list_agents)
        self.server.add_handler(
            "GET", "/api/v1/extraction/extraction-agents/{extraction_agent_id}"
        )(self._handle_get_agent)
        self.server.add_handler(
            "DELETE", "/api/v1/extraction/extraction-agents/{extraction_agent_id}"
        )(self._handle_delete_agent)
        self.server.add_handler(
            "PUT", "/api/v1/extraction/extraction-agents/{extraction_agent_id}"
        )(self._handle_update_agent)
        self.server.add_handler(
            "GET", "/api/v1/extraction/extraction-agents/by-name/{name}"
        )(self._handle_get_agent_by_name)
        self.server.add_handler(
            "POST", "/api/v1/extraction/extraction-agents/schema/validation"
        )(self._handle_validate_schema)

        self.server.add_handler("POST", "/api/v1/extraction/jobs")(self._handle_run_job)
        self.server.add_handler("GET", "/api/v1/extraction/jobs/{job_id}")(self._handle_get_job)
        self.server.add_handler(
            "GET", "/api/v1/extraction/runs/by-job/{job_id}"
        )(self._handle_get_run_by_job_id)
        self.server.add_handler("GET", "/api/v1/extraction/runs")(self._handle_list_runs)
        self.server.add_handler("DELETE", "/api/v1/extraction/runs/{run_id}")(self._handle_delete_run)
        self.server.add_handler("POST", "/api/v1/extraction/run")(self._handle_stateless_run)

    def _handle_generate_presigned_url(self, request: FakeRequest) -> tuple[int, Any]:
        payload = request.json or {}
        name = payload.get("name") or payload.get("external_file_id") or "file"
        mime = self._guess_mime_type(name)
        presigned = self.state.register_file_shell(
            name=name,
            external_file_id=payload.get("external_file_id", name),
            mime_type=mime,
        )
        upload_url = request.url.copy_with(path=f"/_fake/uploads/{presigned.file_id}", query=None)
        presigned = presigned.copy(update={"url": str(upload_url)})
        return 200, presigned

    def _handle_file_upload(self, request: FakeRequest) -> tuple[int, Any]:
        file_id = request.path_params["file_id"]
        self.state.finalize_file(file_id, request.body)
        return 200, {"uploaded": True}

    def _handle_get_file(self, request: FakeRequest) -> tuple[int, Any]:
        file_id = request.path_params["file_id"]
        record = self.state.files[file_id]
        return 200, record.file

    def _handle_create_agent(self, request: FakeRequest) -> tuple[int, Any]:
        payload = request.json or {}
        config = self._parse_config(payload.get("config"))
        schema = payload.get("data_schema") or {}
        agent_id = self.state.next_id("agent")
        now = self.state.now()
        agent = ExtractAgent(
            id=agent_id,
            name=payload["name"],
            data_schema=schema,
            config=config,
            project_id=request.query.get("project_id") or self.state.default_project_id,
            custom_configuration=None,
            created_at=now,
            updated_at=now,
        )
        self.state.agents[agent_id] = agent
        return 200, agent

    def _handle_list_agents(self, request: FakeRequest) -> tuple[int, Any]:
        return 200, list(self.state.agents.values())

    def _handle_get_agent(self, request: FakeRequest) -> tuple[int, Any]:
        agent = self.state.agents[request.path_params["extraction_agent_id"]]
        return 200, agent

    def _handle_get_agent_by_name(self, request: FakeRequest) -> tuple[int, Any]:
        name = request.path_params["name"]
        for agent in self.state.agents.values():
            if agent.name == name:
                return 200, agent
        return 404, {"detail": "Agent not found"}

    def _handle_delete_agent(self, request: FakeRequest) -> tuple[int, Any]:
        self.state.agents.pop(request.path_params["extraction_agent_id"], None)
        return 200, {}

    def _handle_update_agent(self, request: FakeRequest) -> tuple[int, Any]:
        agent_id = request.path_params["extraction_agent_id"]
        payload = request.json or {}
        agent = self.state.agents[agent_id]
        updated = agent.copy(
            update={
                "data_schema": payload.get("data_schema") or agent.data_schema,
                "config": self._parse_config(payload.get("config")) or agent.config,
                "updated_at": self.state.now(),
            }
        )
        self.state.agents[agent_id] = updated
        return 200, updated

    def _handle_validate_schema(self, request: FakeRequest) -> tuple[int, Any]:
        payload = request.json or {}
        schema = payload.get("data_schema") or {}
        return 200, ExtractSchemaValidateResponse(data_schema=schema)

    def _handle_run_job(self, request: FakeRequest) -> tuple[int, Any]:
        payload = request.json or {}
        agent_id = payload["extraction_agent_id"]
        file_id = payload["file_id"]
        agent = self.state.agents[agent_id]
        file_record = self.state.files[file_id]
        schema = payload.get("data_schema_override") or agent.data_schema
        config = self._parse_config(payload.get("config_override")) or agent.config
        context = self._build_context(route="/api/v1/extraction/jobs", schema=schema, file=file_record)
        job, _ = self._create_job_and_run(agent, file_record, schema, config, context)
        return 200, job

    def _handle_get_job(self, request: FakeRequest) -> tuple[int, Any]:
        job_id = request.path_params["job_id"]
        record = self.state.jobs[job_id]
        if record.job.status != record.target_status:
            record.polls += 1
            if record.polls >= record.success_after:
                record.job = record.job.copy(update={"status": record.target_status, "error": None})
        return 200, record.job

    def _handle_get_run_by_job_id(self, request: FakeRequest) -> tuple[int, Any]:
        job_id = request.path_params["job_id"]
        record = self.state.jobs[job_id]
        run = self.state.runs[record.run_id]
        return 200, run

    def _handle_list_runs(self, request: FakeRequest) -> tuple[int, Any]:
        agent_id = request.query.get("extraction_agent_id")
        skip = int(request.query.get("skip", 0))
        limit = int(request.query.get("limit", 50))
        runs = self.state.list_runs_for_agent(agent_id) if agent_id else list(self.state.runs.values())
        sliced = runs[skip : skip + limit]
        response = PaginatedExtractRunsResponse(items=sliced, skip=skip, limit=limit, total=len(runs))
        return 200, response

    def _handle_delete_run(self, request: FakeRequest) -> tuple[int, Any]:
        run_id = request.path_params["run_id"]
        self.state.runs.pop(run_id, None)
        return 200, {}

    def _handle_stateless_run(self, request: FakeRequest) -> tuple[int, Any]:
        payload = request.json or {}
        schema = payload.get("data_schema") or {}
        config = self._parse_config(payload.get("config")) or DEFAULT_CONFIG
        text = payload.get("text")
        file_record: _FileRecord
        if "file_id" in payload:
            file_record = self.state.files[payload["file_id"]]
        elif "file" in payload:
            file_payload = payload["file"]
            data = base64.b64decode(file_payload["data"])
            mime = file_payload.get("mime_type", "application/octet-stream")
            file_record = self.state.ensure_inline_file(name="stateless-upload", data=data, mime_type=mime)
        elif text is not None:
            file_record = self.state.ensure_inline_file(
                name="stateless-text",
                data=text.encode("utf-8"),
                mime_type="text/plain",
            )
        else:
            raise ValueError("stateless run requires file_id, file, or text")
        context = self._build_context(
            route="/api/v1/extraction/run", schema=schema, file=file_record, text=text
        )
        agent = self._ensure_stateless_agent(schema, config)
        job, _ = self._create_job_and_run(agent, file_record, schema, config, context)
        return 200, job

    def _create_job_and_run(
        self,
        agent: ExtractAgent,
        file_record: _FileRecord,
        schema: Mapping[str, Any],
        config: ExtractConfig,
        context: MatcherContext,
    ) -> tuple[ExtractJob, ExtractRun]:
        job_id = self.state.next_id("job")
        now = self.state.now()
        override = self.state.resolve_override(context)
        data = override.provider(context) if override else self._generate_data(schema, file_record, context)
        run_status = override.run_status if override else StatusEnum.SUCCESS
        target_status = override.job_status if override else StatusEnum.SUCCESS
        run_id = self.state.next_id("run")
        run = ExtractRun(
            id=run_id,
            job_id=job_id,
            extraction_agent_id=agent.id,
            data=data,
            data_schema=schema,
            config=config,
            status=run_status,
            file=file_record.file,
            extraction_metadata={"source": "fake"},
            project_id=agent.project_id,
            created_at=now,
            updated_at=now,
            error=None,
            from_ui=False,
        )
        job = ExtractJob(
            id=job_id,
            status=StatusEnum.PENDING,
            file=file_record.file,
            extraction_agent=agent,
            error=None,
        )
        self.state.runs[run_id] = run
        self.state.jobs[job_id] = _JobRecord(
            job=job,
            run_id=run_id,
            target_status=target_status,
            success_after=1 if target_status == StatusEnum.SUCCESS else 2,
        )
        return job, run

    def _build_context(
        self,
        *,
        route: str,
        schema: Mapping[str, Any],
        file: _FileRecord,
        text: Optional[str] = None,
    ) -> MatcherContext:
        return MatcherContext(
            route=route,
            schema_hash=self.state.compute_schema_hash(schema),
            file_id=file.file.id,
            file_name=file.file.name,
            file_sha256=file.fingerprint or hashlib.sha256(file.content).hexdigest(),
            mime_type=file.mime_type,
            text_preview=(text or "")[:64] if text else None,
        )

    def _parse_config(self, config: Optional[Mapping[str, Any]]) -> ExtractConfig:
        if config is None:
            return DEFAULT_CONFIG
        if isinstance(config, ExtractConfig):
            return config
        return ExtractConfig.parse_obj(config)

    def _ensure_stateless_agent(self, schema: Mapping[str, Any], config: ExtractConfig) -> ExtractAgent:
        key = self.state.compute_schema_hash(schema)
        existing = next((agent for agent in self.state.agents.values() if agent.name == f"stateless-{key}"), None)
        if existing:
            return existing
        now = self.state.now()
        agent = ExtractAgent(
            id=self.state.next_id("agent"),
            name=f"stateless-{key}",
            data_schema=schema,
            config=config,
            project_id=self.state.default_project_id,
            custom_configuration=None,
            created_at=now,
            updated_at=now,
        )
        self.state.agents[agent.id] = agent
        return agent

    def _generate_data(
        self, schema: Mapping[str, Any], file_record: _FileRecord, context: MatcherContext
    ) -> Mapping[str, Any]:
        fingerprint = context.file_sha256 or hashlib.sha256(file_record.content).hexdigest()
        seed = int(
            hashlib.sha256(f"{context.schema_hash}:{fingerprint}".encode("utf-8")).hexdigest()[:16],
            16,
        )
        rng = random.Random(seed)
        return self._render_schema(schema, rng)

    def _render_schema(self, schema: Mapping[str, Any], rng: random.Random) -> Any:
        if "enum" in schema:
            return schema["enum"][rng.randint(0, len(schema["enum"]) - 1)]
        schema_type = schema.get("type")
        if schema_type == "object":
            properties = schema.get("properties", {})
            return {key: self._render_schema(value, rng) for key, value in properties.items()}
        if schema_type == "array":
            items = schema.get("items", {"type": "string"})
            length = max(1, min(3, schema.get("minItems", 1)))
            return [self._render_schema(items, rng) for _ in range(length)]
        if schema_type == "number":
            return round(rng.uniform(-100, 100), 2)
        if schema_type == "integer":
            return rng.randint(0, 100)
        if schema_type == "boolean":
            return rng.choice([True, False])
        return self._render_string(rng)

    @staticmethod
    def _render_string(rng: random.Random) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        size = rng.randint(5, 10)
        return "".join(rng.choice(letters) for _ in range(size))

    @staticmethod
    def _guess_mime_type(name: str) -> str:
        extension = name.lower().split(".")[-1] if "." in name else ""
        return {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "json": "application/json",
            "html": "text/html",
            "png": "image/png",
            "jpg": "image/jpeg",
        }.get(extension, "application/octet-stream")


def attach_extract_api(server: FakeLlamaCloudServer) -> ExtractTestingApi:
    """Register extract routes on the provided fake server."""

    return ExtractTestingApi(server)
