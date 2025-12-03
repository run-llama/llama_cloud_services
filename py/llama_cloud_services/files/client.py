from io import BytesIO
from typing import BinaryIO
import os
from pathlib import Path
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.types import File, FileCreate
from typing import Optional
from llama_cloud_services.utils import SourceText, FileInput


class FileClient:
    """
    Higher-level client for interacting with the LlamaCloud Files API.
    Optionally uses presigned URLs for uploads.

    Args:
        client: The LlamaCloud client to use.
        project_id: The project ID to use.
        organization_id: The organization ID to use.
        use_presigned_url: Whether to use presigned URLs for uploads (set to False when uploading to BYOC deployments).
    """

    def __init__(
        self,
        client: AsyncLlamaCloud,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        use_presigned_url: bool = False,
    ):
        self.client = client
        self.project_id = project_id
        self.organization_id = organization_id
        self.use_presigned_url = use_presigned_url

    async def get_file(self, file_id: str) -> File:
        return await self.client.files.get_file(
            file_id, project_id=self.project_id, organization_id=self.organization_id
        )

    async def read_file_content(self, file_id: str) -> bytes:
        presigned_url = await self.client.files.read_file_content(
            file_id,
            project_id=self.project_id,
            organization_id=self.organization_id,
        )
        httpx_client = self.client._client_wrapper.httpx_client
        response = await httpx_client.get(presigned_url.url)
        response.raise_for_status()
        return response.content

    async def upload_file(
        self, file_path: str, external_file_id: Optional[str] = None
    ) -> File:
        external_file_id = external_file_id or file_path
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as file:
            return await self.upload_buffer(file, external_file_id, file_size)

    async def upload_bytes(self, bytes: bytes, external_file_id: str) -> File:
        return await self.upload_buffer(BytesIO(bytes), external_file_id, len(bytes))

    async def upload_buffer(
        self,
        buffer: BinaryIO,
        external_file_id: str,
        file_size: int,
    ) -> File:
        if self.use_presigned_url:
            if getattr(buffer, "name", None):
                name = os.path.basename(str(getattr(buffer, "name", external_file_id)))
            else:
                name = external_file_id
            presigned_url = await self.client.files.generate_presigned_url(
                project_id=self.project_id,
                organization_id=self.organization_id,
                request=FileCreate(
                    name=name,
                    external_file_id=external_file_id,
                    file_size=file_size,
                ),
            )
            httpx_client = self.client._client_wrapper.httpx_client
            upload_response = await httpx_client.put(
                presigned_url.url,
                data=buffer.read(),
            )
            upload_response.raise_for_status()
            return await self.client.files.get_file(
                presigned_url.file_id,
                project_id=self.project_id,
                organization_id=self.organization_id,
            )
        else:
            # Set buffer.name if not already set, so the upload uses external_file_id
            # for file type detection
            if not getattr(buffer, "name", None):
                setattr(buffer, "name", external_file_id)
            return await self.client.files.upload_file(
                upload_file=buffer,
                external_file_id=external_file_id,
                project_id=self.project_id,
                organization_id=self.organization_id,
            )

    async def upload_content(
        self, file_input: FileInput, external_file_id: Optional[str] = None
    ) -> File:
        """
        Upload content from various input types or fetch an already-uploaded file.

        Args:
            file_input: The content to upload. Can be:
                - File: Already uploaded file (returned as-is)
                - str/Path: Path to a file on disk
                - SourceText: Text content, file, or file_id with explicit filename
                - BufferedIOBase: File-like binary object
            external_file_id: Optional external identifier for the file

        Returns:
            File: The uploaded (or fetched) file object

        Raises:
            ValueError: If the input type is not supported or required info is missing
        """
        # If already a File object, return it
        if isinstance(file_input, File):
            return file_input

        # Handle SourceText
        if isinstance(file_input, SourceText):
            # If file_id is provided, fetch the file object
            if file_input.file_id is not None:
                return await self.get_file(file_input.file_id)
            elif file_input.text_content is not None:
                # Handle direct text content
                text_bytes = file_input.text_content.encode("utf-8")
                return await self.upload_bytes(
                    text_bytes, external_file_id or file_input.filename or "file"
                )
            elif isinstance(file_input.file, (str, Path)):
                # Handle file paths using the existing upload_file method
                return await self.upload_file(
                    str(file_input.file), external_file_id or file_input.filename
                )
            elif isinstance(file_input.file, bytes):
                # Handle bytes
                return await self.upload_bytes(
                    file_input.file, external_file_id or file_input.filename or "file"
                )
            elif hasattr(file_input.file, "read"):
                # Handle any file-like object (TextIOWrapper, BytesIO, BufferedReader, BufferedIOBase, etc.)
                content = file_input.file.read()  # type: ignore
                if isinstance(content, str):
                    content = content.encode("utf-8")
                return await self.upload_bytes(
                    content, external_file_id or file_input.filename or "file"
                )
            else:
                raise ValueError(f"Unsupported file type: {type(file_input.file)}")

        # Handle string/Path directly
        elif isinstance(file_input, (str, Path)):
            return await self.upload_file(str(file_input), external_file_id)

        # Handle raw file-like objects
        elif hasattr(file_input, "read"):
            if hasattr(file_input, "name"):
                filename = os.path.basename(str(file_input.name))
            else:
                filename = external_file_id or "file"

            # Read content to determine size
            content = file_input.read()
            if isinstance(content, str):
                content = content.encode("utf-8")

            return await self.upload_bytes(content, external_file_id or filename)

        else:
            raise ValueError(
                f"Unsupported file input type: {type(file_input)}. "
                f"Supported types: str, Path, SourceText, BufferedIOBase, or File."
            )
