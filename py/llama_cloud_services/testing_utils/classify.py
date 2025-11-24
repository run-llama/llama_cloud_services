from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List

import httpx
from llama_cloud.types import (
    ClassifierRule,
    ClassifyJob,
    ClassifyJobResults,
    ClassificationResult,
    FileClassification,
    StatusEnum,
)

from ._deterministic import combined_seed, utcnow
from .files import FakeFilesNamespace, StoredFile

if TYPE_CHECKING:
    from .server import FakeLlamaCloudServer


@dataclass
class ClassificationJobRecord:
    job: ClassifyJob
    results: ClassifyJobResults
    files: List[StoredFile]


class FakeClassifyNamespace:
    def __init__(
        self, *, server: "FakeLlamaCloudServer", files: FakeFilesNamespace
    ) -> None:
        self._server = server
        self._files = files
        self._jobs: Dict[str, ClassificationJobRecord] = {}

    def register(self) -> None:
        server = self._server
        server.add_route(
            "POST",
            "/api/v1/classifier/jobs",
            self._handle_create_job,
            namespace="classify",
        )
        server.add_route(
            "GET",
            "/api/v1/classifier/jobs",
            self._handle_list_jobs,
            namespace="classify",
        )
        server.add_route(
            "GET",
            "/api/v1/classifier/jobs/{job_id}",
            self._handle_get_job,
            namespace="classify",
        )
        server.add_route(
            "GET",
            "/api/v1/classifier/jobs/{job_id}/results",
            self._handle_get_results,
            namespace="classify",
        )

    def _handle_create_job(self, request: httpx.Request) -> httpx.Response:
        payload = self._server.json(request)
        file_ids = payload.get("file_ids", [])
        rules_payload = payload.get("rules", [])
        rules = [ClassifierRule.parse_obj(rule) for rule in rules_payload]
        stored_files = []
        for file_id in file_ids:
            stored = self._files.get(file_id)
            if not stored:
                return self._server.json_response(
                    {"detail": f"File {file_id} not found"}, status_code=404
                )
            stored_files.append(stored)

        job_id = self._server.new_id("classify-job")
        job = ClassifyJob(
            id=job_id,
            project_id=request.url.params.get(
                "project_id", self._server.default_project_id
            ),
            user_id="fake-user",
            rules=rules,
            parsing_configuration=None,
            status=StatusEnum.SUCCESS,
            created_at=utcnow(),
            updated_at=utcnow(),
            effective_at=utcnow(),
            error_message=None,
            job_record_id=None,
        )
        results = self._build_results(job_id, stored_files, rules)
        record = ClassificationJobRecord(job=job, results=results, files=stored_files)
        self._jobs[job_id] = record
        return self._server.json_response(job.dict())

    def _handle_list_jobs(self, request: httpx.Request) -> httpx.Response:
        return self._server.json_response(
            [record.job.dict() for record in self._jobs.values()]
        )

    def _handle_get_job(self, request: httpx.Request) -> httpx.Response:
        job_id = request.url.path.split("/")[-1]
        record = self._jobs.get(job_id)
        if not record:
            return self._server.json_response(
                {"detail": "Job not found"}, status_code=404
            )
        return self._server.json_response(record.job.dict())

    def _handle_get_results(self, request: httpx.Request) -> httpx.Response:
        job_id = request.url.path.split("/")[-2]
        record = self._jobs.get(job_id)
        if not record:
            return self._server.json_response(
                {"detail": "Results not found"}, status_code=404
            )
        return self._server.json_response(record.results.dict())

    def _build_results(
        self,
        job_id: str,
        stored_files: List[StoredFile],
        rules: List[ClassifierRule],
    ) -> ClassifyJobResults:
        items: List[FileClassification] = []
        for stored in stored_files:
            seed = combined_seed(stored.sha256, job_id)
            rule_index = seed % len(rules) if rules else 0
            predicted_type = rules[rule_index].type if rules else "unlabeled"
            confidence = 0.55 + (seed % 40) / 100
            reasoning = (
                f"Selected rule '{predicted_type}' using deterministic seed {seed}."
            )
            classification = FileClassification(
                id=self._server.new_id("classification"),
                file_id=stored.file.id,
                classify_job_id=job_id,
                created_at=utcnow(),
                updated_at=utcnow(),
                result=ClassificationResult(
                    type=predicted_type,
                    confidence=min(confidence, 0.95),
                    reasoning=reasoning,
                ),
            )
            items.append(classification)
        return ClassifyJobResults(
            items=items, next_page_token=None, total_size=len(items)
        )
