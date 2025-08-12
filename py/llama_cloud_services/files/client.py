from io import BytesIO
from typing import BinaryIO
import os
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.types import File, FileCreate
from typing import Optional


class FileClient:
    """
    Higher-level client for interacting with the LlamaCloud Files API.
    Uses presigned URLs for uploads by default.

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
        use_presigned_url: bool = True,
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
            return await self.client.files.upload_file(
                upload_file=buffer,
                external_file_id=external_file_id,
                project_id=self.project_id,
                organization_id=self.organization_id,
            )
