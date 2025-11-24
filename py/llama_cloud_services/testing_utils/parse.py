from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

import httpx

from ._deterministic import generate_text_blob, hash_schema

if TYPE_CHECKING:
    from .server import FakeLlamaCloudServer


@dataclass
class ParseJobRecord:
    job_id: str
    file_name: str
    status: str
    result: Dict[str, Any]
    content: bytes


class FakeParseNamespace:
    def __init__(self, *, server: "FakeLlamaCloudServer") -> None:
        self._server = server
        self._jobs: Dict[str, ParseJobRecord] = {}
        self.routes: Dict[str, Any] = {}

    def register(self) -> None:
        server = self._server
        server.add_route(
            "POST",
            "/api/parsing/upload",
            self._handle_upload,
            namespace="parse",
        )
        server.add_route(
            "GET",
            "/api/parsing/job/{job_id}",
            self._handle_job_status,
            namespace="parse",
        )
        server.add_route(
            "GET",
            "/api/parsing/job/{job_id}/result/{result_type}",
            self._handle_job_result,
            namespace="parse",
        )

    def _handle_upload(self, request: httpx.Request) -> httpx.Response:
        file_bytes, filename, form_data = self._split_multipart(request)
        job_id = self._server.new_id("parse-job")
        seed_hash = hash_schema({"filename": filename, "form": form_data})
        seed = int(seed_hash[:16], 16)
        page_text = generate_text_blob(seed, sentences=3)
        pages: list[Dict[str, Any]] = [
            {
                "page": index + 1,
                "text": f"{page_text} (page {index + 1})",
                "md": f"{page_text} (page {index + 1})",
                "images": [],
                "charts": [],
                "tables": [],
                "layout": [],
                "items": [],
                "status": "SUCCESS",
                "links": [],
                "width": 8.5,
                "height": 11.0,
                "parsingMode": "deterministic",
                "structuredData": {},
                "noStructuredContent": False,
                "noTextContent": False,
                "isAudioTranscript": False,
                "durationInSeconds": None,
                "slideSpeakerNotes": None,
            }
            for index in range(1)
        ]
        result = {
            "job_id": job_id,
            "status": "SUCCESS",
            "file_name": filename,
            "is_done": True,
            "pages": pages,
            "job_metadata": {"job_pages": len(pages)},
            "text": "\n\n".join(str(page["text"]) for page in pages),
            "markdown": "\n\n".join(str(page["md"]) for page in pages),
            "json": {"pages": pages},
        }
        record = ParseJobRecord(
            job_id=job_id,
            file_name=filename,
            status="SUCCESS",
            result=result,
            content=file_bytes,
        )
        self._jobs[job_id] = record
        return self._server.json_response({"id": job_id})

    def _handle_job_status(self, request: httpx.Request) -> httpx.Response:
        job_id = request.url.path.split("/")[-1]
        job = self._jobs.get(job_id)
        if not job:
            return self._server.json_response(
                {"detail": "Job not found"}, status_code=404
            )
        return self._server.json_response({"id": job_id, "status": job.status})

    def _handle_job_result(self, request: httpx.Request) -> httpx.Response:
        job_id = request.url.path.split("/")[-3]
        job = self._jobs.get(job_id)
        if not job:
            return self._server.json_response(
                {"detail": "Result not found"}, status_code=404
            )
        return self._server.json_response(job.result)

    def _split_multipart(
        self, request: httpx.Request
    ) -> tuple[bytes, str, Dict[str, str]]:
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Expected multipart form data for parse upload")
        boundary = content_type.split("boundary=")[-1]
        delimiter = f"--{boundary}".encode()
        closing = f"--{boundary}--".encode()
        parts = []
        body = request.content
        for chunk in body.split(delimiter):
            chunk = chunk.strip()
            if not chunk or chunk == closing:
                continue
            parts.append(chunk)

        file_bytes = b""
        filename = "upload.pdf"
        form_data: Dict[str, str] = {}
        for part in parts:
            header_blob, _, payload = part.partition(b"\r\n\r\n")
            payload = payload.rstrip(b"\r\n")
            header_text = header_blob.decode("utf-8", errors="ignore")
            if "filename=" in header_text:
                filename = (
                    header_text.split("filename=")[-1].strip().strip('"').strip("'")
                )
                file_bytes = payload
            else:
                name = header_text.split('name="')[-1].split('"')[0].strip()
                form_data[name] = payload.decode("utf-8", errors="ignore")
        if not file_bytes:
            raise ValueError("File part missing from multipart payload")
        return file_bytes, filename, form_data
