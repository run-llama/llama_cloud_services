import asyncio
import io
import os
import time
from typing import Any, Dict, TYPE_CHECKING

import httpx
from llama_cloud.client import AsyncLlamaCloud
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from llama_cloud_services.beta.sheets.types import (
    FileUploadResponse,
    JobStatus,
    PresignedUrlResponse,
    SpreadsheetJob,
    SpreadsheetJobResult,
    SpreadsheetParsingConfig,
    SpreadsheetResultType,
)
from llama_cloud_services.constants import BASE_URL
from llama_cloud_services.files.client import FileClient
from llama_cloud_services.utils import (
    augment_async_errors,
    FileInput,
)

if TYPE_CHECKING:
    import pandas as pd


def _should_retry_exception(exception: BaseException) -> bool:
    """Determine if an exception should be retried."""
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in (429, 500, 502, 503, 504)
    return False


class SpreadsheetAPIError(Exception):
    """Base exception for spreadsheet API errors"""

    pass


class SpreadsheetJobError(SpreadsheetAPIError):
    """Exception raised when a spreadsheet job fails"""

    pass


class SpreadsheetTimeoutError(SpreadsheetAPIError):
    """Exception raised when a job times out"""

    pass


class LlamaSheets:
    """Client for the LlamaCloud Spreadsheet API"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_timeout: int = 300,
        poll_interval: int = 5,
        max_retries: int = 3,
        project_id: str | None = None,
        organization_id: str | None = None,
        async_httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the LlamaSheets client.

        Args:
            api_key: API key for authentication. If not provided, will use LLAMA_CLOUD_API_KEY env var
            base_url: Base URL for the API
            max_timeout: Maximum time to wait for job completion in seconds
            poll_interval: Interval between status checks in seconds
            max_retries: Maximum number of retries for failed requests
            project_id: Project ID for file operations. If not provided, will use LLAMA_CLOUD_PROJECT_ID env var
            organization_id: Organization ID for file operations. If not provided, will use LLAMA_CLOUD_ORGANIZATION_ID env var
            async_httpx_client: Optional custom async httpx client
        """
        self.api_key = api_key or os.environ.get("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            raise ValueError(
                "An API key must be provided either as an argument or via the LLAMA_CLOUD_API_KEY environment variable."
            )

        base_url = base_url or os.environ.get("LLAMA_CLOUD_BASE_URL", BASE_URL)
        self.base_url = str(base_url).rstrip("/")

        self.max_timeout = max_timeout
        self.poll_interval = poll_interval
        self.max_retries = max_retries

        self.project_id = project_id or os.environ.get("LLAMA_CLOUD_PROJECT_ID")
        self.organization_id = organization_id or os.environ.get(
            "LLAMA_CLOUD_ORGANIZATION_ID"
        )

        self._async_client: httpx.AsyncClient | None = async_httpx_client
        self._files_client = FileClient(
            AsyncLlamaCloud(
                token=self.api_key,
                base_url=self.base_url,
                httpx_client=async_httpx_client,
            ),
            project_id=self.project_id,
            organization_id=self.organization_id,
        )

    def _get_default_params(self) -> dict[str, str]:
        """Get default query parameters for API requests"""
        params = {}
        if self.project_id is not None:
            params["project_id"] = self.project_id
        if self.organization_id is not None:
            params["organization_id"] = self.organization_id

        return params

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create the async httpx client"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                follow_redirects=True,
            )
        return self._async_client

    def _get_headers(self) -> dict[str, str]:
        """Get common headers for API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # Sync methods

    def upload_file(
        self, file_obj: FileInput, file_name: str | None = None
    ) -> FileUploadResponse:
        """Upload a file to the Files API.

        Args:
            file_obj: File to upload (path, bytes, or file-like object)
            file_name: Optional name for the uploaded filename

        Returns:
            FileUploadResponse with the uploaded file ID
        """
        with augment_async_errors():
            return asyncio.run(self.aupload_file(file_obj))

    def create_job(
        self,
        file_id: str,
        config: dict | SpreadsheetParsingConfig | None = None,
    ) -> SpreadsheetJob:
        """Create a new spreadsheet parsing job.

        Args:
            file_id: ID of the uploaded file
            config: Parsing configuration

        Returns:
            SpreadsheetJob with job details
        """
        with augment_async_errors():
            return asyncio.run(self.acreate_job(file_id, config))

    def get_job(
        self, job_id: str, include_results_metadata: bool = True
    ) -> SpreadsheetJobResult:
        """Get the status of a spreadsheet parsing job.

        Args:
            job_id: ID of the job
            include_results_metadata: Whether to include results metadata in the response

        Returns:
            SpreadsheetJobResult with job status and optionally results
        """
        with augment_async_errors():
            return asyncio.run(self.aget_job(job_id, include_results_metadata))

    def wait_for_completion(self, job_id: str) -> SpreadsheetJobResult:
        """Wait for a job to complete by polling.

        Args:
            job_id: ID of the job to wait for

        Returns:
            SpreadsheetJobResult when job is complete

        Raises:
            SpreadsheetTimeoutError: If job doesn't complete within max_timeout
            SpreadsheetJobError: If job fails
        """
        with augment_async_errors():
            return asyncio.run(self.await_for_completion(job_id))

    def download_region_result(
        self,
        job_id: str,
        region_id: str,
        result_type: SpreadsheetResultType = SpreadsheetResultType.TABLE,
    ) -> bytes:
        """Download a region result (either region data or cell metadata).

        Args:
            job_id: ID of the job
            region_id: ID of the region
            result_type: Type of result to download (region or cell_metadata)

        Returns:
            Raw bytes of the parquet file
        """
        with augment_async_errors():
            return asyncio.run(
                self.adownload_region_result(job_id, region_id, result_type)
            )

    def download_region_as_dataframe(
        self,
        job_id: str,
        region_id: str,
        result_type: SpreadsheetResultType = SpreadsheetResultType.TABLE,
    ) -> "pd.DataFrame":
        """Download a region result as a pandas DataFrame.

        Args:
            job_id: ID of the job
            region_id: ID of the region
            result_type: Type of result to download (region or cell_metadata)

        Returns:
            pandas DataFrame
        """
        with augment_async_errors():
            return asyncio.run(
                self.adownload_region_as_dataframe(job_id, region_id, result_type)
            )

    def extract_regions(
        self,
        file_obj: FileInput,
        config: dict | SpreadsheetParsingConfig | None = None,
    ) -> SpreadsheetJobResult:
        """High-level method to parse a spreadsheet file.

        This method handles the entire workflow:
        1. Upload the file
        2. Create a parsing job
        3. Wait for completion
        4. Return results

        Args:
            file_obj: File to parse (path, bytes, or file-like object)
            config: Parsing configuration

        Returns:
            SpreadsheetJobResult with parsing results
        """
        with augment_async_errors():
            return asyncio.run(self.aextract_regions(file_obj, config))

    # Async methods

    async def aupload_file(
        self, file_obj: FileInput, file_name: str | None = None
    ) -> FileUploadResponse:
        """Upload a file to the Files API.

        Args:
            file_obj: File to upload (path, bytes, or file-like object)
            file_name: Optional name for the uploaded filename

        Returns:
            FileUploadResponse with the uploaded file ID
        """
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=32),
                retry=retry_if_exception(_should_retry_exception),
                reraise=True,
            ):
                with attempt:
                    return await self._files_client.upload_content(
                        file_obj, external_file_id=file_name
                    )
        except Exception as e:
            raise SpreadsheetAPIError(f"Failed to upload file: {e}") from e
        raise RuntimeError("Tenacity did not execute")

    async def acreate_job(
        self,
        file_id: str,
        config: dict | SpreadsheetParsingConfig | None = None,
    ) -> SpreadsheetJob:
        """Create a new spreadsheet parsing job.

        Args:
            file_id: ID of the uploaded file
            config: Parsing configuration

        Returns:
            SpreadsheetJob with job details
        """
        if config is None:
            config = SpreadsheetParsingConfig()
        elif isinstance(config, dict):
            config = SpreadsheetParsingConfig.model_validate(config)

        if not isinstance(config, SpreadsheetParsingConfig):
            raise ValueError(
                "config must be a dict or SpreadsheetParsingConfig instance"
            )

        payload = {
            "file_id": file_id,
            "config": config.model_dump(mode="json", exclude_none=True),
        }

        params = self._get_default_params()

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=32),
                retry=retry_if_exception(_should_retry_exception),
                reraise=True,
            ):
                with attempt:
                    client = self._get_async_client()
                    response = await client.post(
                        f"{self.base_url}/api/v1/beta/sheets/jobs",
                        headers=self._get_headers(),
                        params=params,
                        json=payload,
                    )
                    response.raise_for_status()
                    return SpreadsheetJob.model_validate(response.json())
        except Exception as e:
            raise SpreadsheetAPIError(f"Failed to create job: {e}") from e
        raise RuntimeError("Tenacity did not execute")

    async def aget_job(
        self, job_id: str, include_results_metadata: bool = True
    ) -> SpreadsheetJobResult:
        """Get the status of a spreadsheet parsing job.

        Args:
            job_id: ID of the job
            include_results_metadata: Whether to include results in the response

        Returns:
            SpreadsheetJobResult with job status and optionally results
        """
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=32),
                retry=retry_if_exception(_should_retry_exception),
                reraise=True,
            ):
                with attempt:
                    client = self._get_async_client()
                    params: Dict[str, Any] = {
                        "include_results": include_results_metadata,
                        **self._get_default_params(),
                    }
                    response = await client.get(
                        f"{self.base_url}/api/v1/beta/sheets/jobs/{job_id}",
                        headers=self._get_headers(),
                        params=params,
                    )
                    response.raise_for_status()

                    return SpreadsheetJobResult.model_validate(response.json())
        except Exception as e:
            raise SpreadsheetAPIError(f"Failed to get job status: {e}") from e
        raise RuntimeError("Tenacity did not execute")

    async def await_for_completion(self, job_id: str) -> SpreadsheetJobResult:
        """Wait for a job to complete by polling.

        Args:
            job_id: ID of the job to wait for

        Returns:
            SpreadsheetJobResult when job is complete

        Raises:
            SpreadsheetTimeoutError: If job doesn't complete within max_timeout
            SpreadsheetJobError: If job fails
        """
        start_time = time.time()

        while (time.time() - start_time) < self.max_timeout:
            job_result = await self.aget_job(job_id, include_results_metadata=True)

            if job_result.status in (
                JobStatus.SUCCESS,
                JobStatus.PARTIAL_SUCCESS,
                JobStatus.ERROR,
                JobStatus.FAILURE,
            ):
                if job_result.status in (JobStatus.SUCCESS, JobStatus.PARTIAL_SUCCESS):
                    return job_result
                else:
                    error_msg = f"Job failed with status: {job_result.status}"
                    if job_result.errors:
                        error_msg += f"\nErrors: {', '.join(job_result.errors)}"
                    raise SpreadsheetJobError(error_msg)

            await asyncio.sleep(self.poll_interval)

        raise SpreadsheetTimeoutError(
            f"Job did not complete within {self.max_timeout} seconds"
        )

    async def adownload_region_result(
        self,
        job_id: str,
        region_id: str,
        result_type: SpreadsheetResultType = SpreadsheetResultType.TABLE,
    ) -> bytes:
        """Download a region result (either region data or cell metadata).

        Args:
            job_id: ID of the job
            region_id: ID of the region
            result_type: Type of result to download (region or cell_metadata)

        Returns:
            Raw bytes of the parquet file
        """
        # Get presigned URL
        presigned_response = None
        result_type_str = str(result_type)
        params = self._get_default_params()

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=32),
                retry=retry_if_exception(_should_retry_exception),
                reraise=True,
            ):
                with attempt:
                    client = self._get_async_client()
                    response = await client.get(
                        f"{self.base_url}/api/v1/beta/sheets/jobs/{job_id}/regions/{region_id}/result/{result_type_str}",
                        headers=self._get_headers(),
                        params=params,
                    )
                    response.raise_for_status()
                    presigned_response = PresignedUrlResponse.model_validate(
                        response.json()
                    )
        except Exception as e:
            raise SpreadsheetAPIError(f"Failed to get presigned URL: {e}") from e

        # Download using presigned URL
        if presigned_response is None:
            raise SpreadsheetAPIError("Failed to obtain presigned URL.")

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=32),
                retry=retry_if_exception(_should_retry_exception),
                reraise=True,
            ):
                with attempt:
                    download_response = await client.get(presigned_response.url)
                    download_response.raise_for_status()
                    return download_response.content
        except Exception as e:
            raise SpreadsheetAPIError(f"Failed to download result: {e}") from e
        raise RuntimeError("Tenacity did not execute")

    async def adownload_region_as_dataframe(
        self,
        job_id: str,
        region_id: str,
        result_type: SpreadsheetResultType = SpreadsheetResultType.TABLE,
    ) -> "pd.DataFrame":
        """Download a region result as a pandas DataFrame.

        Args:
            job_id: ID of the job
            region_id: ID of the region
            result_type: Type of result to download (region or cell_metadata)

        Returns:
            pandas DataFrame
        """
        import pandas as pd

        parquet_bytes = await self.adownload_region_result(
            job_id, region_id, result_type
        )
        return pd.read_parquet(io.BytesIO(parquet_bytes))

    async def aextract_regions(
        self,
        file_obj: FileInput,
        config: dict | SpreadsheetParsingConfig | None = None,
    ) -> SpreadsheetJobResult:
        """High-level method to parse a spreadsheet file.

        This method handles the entire workflow:
        1. Upload the file
        2. Create a parsing job
        3. Wait for completion
        4. Return results

        Args:
            file_obj: File to parse (path, bytes, or file-like object)
            config: Parsing configuration

        Returns:
            SpreadsheetJobResult with parsing results
        """
        # Upload file
        file_response = await self.aupload_file(file_obj)

        # Create job
        job = await self.acreate_job(file_response.id, config)

        # Wait for completion
        return await self.await_for_completion(job.id)

    async def aclose(self) -> None:
        """Close all HTTP clients (async)"""
        if self._async_client:
            await self._async_client.aclose()

    async def __aenter__(self) -> "LlamaSheets":
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:  # type: ignore
        await self.aclose()
