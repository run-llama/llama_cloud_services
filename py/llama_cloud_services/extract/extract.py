import asyncio
import base64
import os
import time
from io import BufferedIOBase, TextIOWrapper
from pathlib import Path
from typing import List, Optional, Type, Union, Coroutine, Any, TypeVar
import warnings
import httpx
from pydantic import BaseModel
from tenacity import (
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
    AsyncRetrying,
)
from llama_cloud import (
    ExtractAgent as CloudExtractAgent,
    ExtractConfig,
    ExtractJob,
    ExtractRun,
    File,
    FileData,
    ExtractMode,
    StatusEnum,
    ExtractTarget,
    PaginatedExtractRunsResponse,
)
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.core.api_error import ApiError
from llama_cloud_services.extract.utils import (
    JSONObjectType,
    ExperimentalWarning,
)
from llama_cloud_services.utils import augment_async_errors, SourceText, FileInput
from llama_cloud_services.files.client import FileClient
from llama_index.core.schema import BaseComponent
from llama_index.core.async_utils import run_jobs
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.constants import DEFAULT_BASE_URL
from concurrent.futures import ThreadPoolExecutor

T = TypeVar("T")


SchemaInput = Union[JSONObjectType, Type[BaseModel]]

DEFAULT_EXTRACT_CONFIG = ExtractConfig(
    extraction_target=ExtractTarget.PER_DOC,
    extraction_mode=ExtractMode.MULTIMODAL,
)


def _is_retryable_error(exception: BaseException) -> bool:
    """Check if an exception is retryable."""
    if isinstance(exception, ApiError):
        return exception.status_code in (502, 503, 504, 425, 408)
    elif isinstance(
        exception, (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException)
    ):
        return True
    return False


async def _validate_schema(
    client: AsyncLlamaCloud, data_schema: SchemaInput
) -> JSONObjectType:
    """Convert SchemaInput to a validated JSON schema dictionary."""
    processed_schema: JSONObjectType
    if isinstance(data_schema, dict):
        # TODO: if we expose a get_validated JSON schema method, we can use it here
        processed_schema = data_schema  # type: ignore
    elif isinstance(data_schema, type) and issubclass(data_schema, BaseModel):
        processed_schema = data_schema.model_json_schema()
    else:
        raise ValueError("data_schema must be either a dictionary or a Pydantic model")

    # Validate schema via API
    validated_schema = await client.llama_extract.validate_extraction_schema(
        data_schema=processed_schema
    )
    return validated_schema.data_schema


async def _get_job_with_retry(
    client: AsyncLlamaCloud,
    job_id: str,
    max_attempts: int = 5,
    initial_wait: float = 1,
    max_wait: float = 60,
    jitter: float = 5,
) -> ExtractJob:
    """Get extraction job with retry logic."""
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_wait, max=max_wait, jitter=jitter),
        reraise=True,
    ):
        with attempt:
            return await client.llama_extract.get_job(job_id=job_id)


async def _get_run_with_retry(
    client: AsyncLlamaCloud,
    job_id: str,
    project_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    max_attempts: int = 3,
    initial_wait: float = 1,
    max_wait: float = 20,
    jitter: float = 3,
) -> ExtractRun:
    """Get extraction run with retry logic."""
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_wait, max=max_wait, jitter=jitter),
        reraise=True,
    ):
        with attempt:
            return await client.llama_extract.get_run_by_job_id(
                job_id=job_id,
                project_id=project_id,
                organization_id=organization_id,
            )


async def _wait_for_job_result(
    client: AsyncLlamaCloud,
    job_id: str,
    check_interval: int = 1,
    max_timeout: int = 2000,
    verbose: bool = False,
    project_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    job_retry_attempts: int = 5,
    job_max_wait: float = 60,
    job_jitter: float = 5,
    run_retry_attempts: int = 3,
    run_max_wait: float = 20,
    run_jitter: float = 3,
) -> Optional[ExtractRun]:
    """Wait for and return the results of an extraction job."""
    start = time.perf_counter()
    poll_count = 0

    while True:
        await asyncio.sleep(check_interval)
        poll_count += 1
        job = await _get_job_with_retry(
            client,
            job_id,
            max_attempts=job_retry_attempts,
            max_wait=job_max_wait,
            jitter=job_jitter,
        )

        if job.status == StatusEnum.SUCCESS:
            return await _get_run_with_retry(
                client,
                job_id,
                project_id,
                organization_id,
                max_attempts=run_retry_attempts,
                max_wait=run_max_wait,
                jitter=run_jitter,
            )
        elif job.status == StatusEnum.PENDING:
            end = time.perf_counter()
            if end - start > max_timeout:
                raise Exception(f"Timeout while extracting the file: {job_id}")
            if verbose and poll_count % 10 == 0:
                print(".", end="", flush=True)
            continue
        else:
            warnings.warn(
                f"Failure in job: {job_id}, status: {job.status}, error: {job.error}"
            )
            return await _get_run_with_retry(
                client,
                job_id,
                project_id,
                organization_id,
                max_attempts=run_retry_attempts,
                max_wait=run_max_wait,
                jitter=run_jitter,
            )


def run_in_thread(
    coro: Coroutine[Any, Any, T],
    thread_pool: ThreadPoolExecutor,
    verify: bool,
    httpx_timeout: float,
    client_wrapper: Any,
) -> T:
    """Run coroutine in a thread with proper client management."""

    async def wrapped_coro() -> T:
        client = httpx.AsyncClient(
            verify=verify,
            timeout=httpx_timeout,
            limits=httpx.Limits(max_keepalive_connections=100, max_connections=100),
        )
        original_client = client_wrapper.httpx_client
        try:
            client_wrapper.httpx_client = client
            return await coro
        finally:
            client_wrapper.httpx_client = original_client
            await client.aclose()

    def run_coro() -> T:
        try:
            return asyncio.run(wrapped_coro())
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {str(e)}") from e
        except httpx.NetworkError as e:
            raise ConnectionError(f"Network error: {str(e)}") from e

    return thread_pool.submit(run_coro).result()


def _extraction_config_warning(config: ExtractConfig) -> None:
    if config.cite_sources or config.confidence_scores:
        warnings.warn(
            "`cite_sources`/`confidence_scores` could greatly increase the "
            "size of the response, and slow down the extraction. Results will be "
            "available in the `extraction_metadata` field for the extraction run.",
            ExperimentalWarning,
        )
    if config.use_reasoning:
        if config.extraction_mode == ExtractMode.FAST:
            raise ValueError(
                "`reasoning` is only supported with BALANCED, MULTIMODAL, or PREMIUM extraction modes."
            )
    if config.cite_sources:
        if config.extraction_mode in (ExtractMode.FAST, ExtractMode.BALANCED):
            raise ValueError(
                "`cite_sources` is only supported with MULTIMODAL or PREMIUM extraction modes."
            )


class ExtractionAgent:
    """Class representing a single extraction agent with methods for extraction operations."""

    def __init__(
        self,
        client: AsyncLlamaCloud,
        agent: CloudExtractAgent,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        check_interval: int = 1,
        max_timeout: int = 2000,
        num_workers: int = 4,
        show_progress: bool = True,
        verbose: bool = False,
        verify: Optional[bool] = True,
        httpx_timeout: Optional[float] = 60,
    ):
        self._client = client
        self._agent = agent
        self._project_id = project_id
        self._organization_id = organization_id
        self.check_interval = check_interval
        self.max_timeout = max_timeout
        self.num_workers = num_workers
        self.show_progress = show_progress
        self.verify = verify
        self.httpx_timeout = httpx_timeout
        self._verbose = verbose
        self._data_schema: Union[JSONObjectType, None] = None
        self._config: Union[ExtractConfig, None] = None
        self._thread_pool = ThreadPoolExecutor(
            max_workers=min(10, (os.cpu_count() or 1) + 4)
        )
        self._file_client = FileClient(client, project_id, organization_id)

    @property
    def id(self) -> str:
        return self._agent.id

    @property
    def name(self) -> str:
        return self._agent.name

    @property
    def data_schema(self) -> dict:
        return self._agent.data_schema if not self._data_schema else self._data_schema

    @data_schema.setter
    def data_schema(self, data_schema: SchemaInput) -> None:
        # Use the shared schema processing and validation function
        self._data_schema = self._run_in_thread(
            _validate_schema(self._client, data_schema)
        )

    @property
    def config(self) -> ExtractConfig:
        return self._agent.config if not self._config else self._config

    @config.setter
    def config(self, config: ExtractConfig) -> None:
        _extraction_config_warning(config)
        self._config = config

    def _run_in_thread(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run coroutine in a separate thread to avoid event loop issues"""
        return run_in_thread(
            coro,
            self._thread_pool,
            self.verify,  # type: ignore
            self.httpx_timeout,  # type: ignore
            self._client._client_wrapper,
        )

    async def upload_file(self, file_input: SourceText) -> File:
        """Upload a file for extraction.

        Args:
            file_input: The file to upload (path, bytes, or file-like object)

        Raises:
            ValueError: If filename is not provided for bytes input or for file-like objects
                       without a name attribute.
        """
        return await self._file_client.upload_content(file_input)

    async def _upload_file(self, file_input: FileInput) -> File:
        """Upload a file from various input types using FileClient."""
        return await self._file_client.upload_content(file_input)

    async def _wait_for_job_result(self, job_id: str) -> Optional[ExtractRun]:
        """Wait for and return the results of an extraction job."""
        return await _wait_for_job_result(
            client=self._client,
            job_id=job_id,
            check_interval=self.check_interval,
            max_timeout=self.max_timeout,
            verbose=self._verbose,
            project_id=self._project_id,
            organization_id=self._organization_id,
            job_retry_attempts=5,
            job_max_wait=60,
            job_jitter=5,
            run_retry_attempts=3,
            run_max_wait=20,
            run_jitter=3,
        )

    def save(self) -> None:
        """Persist the extraction agent's schema and config to the database.

        Returns:
            ExtractionAgent: The updated extraction agent
        """
        self._agent = self._run_in_thread(
            self._client.llama_extract.update_extraction_agent(
                extraction_agent_id=self.id,
                data_schema=self.data_schema,
                config=self.config,
            )
        )

    async def queue_extraction(
        self,
        files: Union[FileInput, List[FileInput]],
    ) -> Union[ExtractJob, List[ExtractJob]]:
        """
        Queue multiple files for extraction.

        Args:
            files (Union[FileInput, List[FileInput]]): The files to extract

        Returns:
            Union[ExtractJob, List[ExtractJob]]: The queued extraction jobs
        """
        """Queue one or more files for extraction concurrently."""
        if not isinstance(files, list):
            files = [files]
            single_file = True
        else:
            single_file = False

        upload_tasks = [self._upload_file(file) for file in files]
        with augment_async_errors():
            uploaded_files: List[File] = await run_jobs(
                upload_tasks,
                workers=self.num_workers,
                desc="Uploading files",
                show_progress=self.show_progress,
            )

        job_tasks = [
            self._client.llama_extract.run_job(
                extraction_agent_id=self.id,
                file_id=file.id,
                data_schema_override=self.data_schema,
                config_override=self.config,
            )
            for file in uploaded_files
        ]
        with augment_async_errors():
            extract_jobs = await run_jobs(
                job_tasks,
                workers=self.num_workers,
                desc="Creating extraction jobs",
                show_progress=self.show_progress,
            )

        if self._verbose:
            for file, job in zip(files, extract_jobs):
                file_repr = (
                    str(file) if isinstance(file, (str, Path)) else "<bytes/buffer>"
                )
                print(
                    f"Queued file extraction for file {file_repr} under job_id {job.id}"
                )

        return extract_jobs[0] if single_file else extract_jobs

    async def aextract(
        self, files: Union[FileInput, List[FileInput]]
    ) -> Union[ExtractRun, List[ExtractRun]]:
        """Asynchronously extract data from one or more files using this agent.

        Args:
            files (Union[FileInput, List[FileInput]]): The files to extract

        Returns:
            Union[ExtractRun, List[ExtractRun]]: The extraction results
        """
        if not isinstance(files, list):
            files = [files]
            single_file = True
        else:
            single_file = False

        # Queue all files for extraction
        jobs = await self.queue_extraction(files)
        # Wait for all results concurrently
        result_tasks = [self._wait_for_job_result(job.id) for job in jobs]
        with augment_async_errors():
            results = await run_jobs(
                result_tasks,
                workers=self.num_workers,
                desc="Extracting files",
                show_progress=self.show_progress,
            )

        return results[0] if single_file else results

    def extract(
        self, files: Union[FileInput, List[FileInput]]
    ) -> Union[ExtractRun, List[ExtractRun]]:
        """Synchronously extract data from one or more files using this agent.

        Args:
            files (Union[FileInput, List[FileInput]]): The files to extract

        Returns:
            Union[ExtractRun, List[ExtractRun]]: The extraction results
        """
        return self._run_in_thread(self.aextract(files))

    def get_extraction_job(self, job_id: str) -> ExtractJob:
        """
        Get the extraction job for a given job_id.

        Args:
            job_id (str): The job_id to get the extraction job for

        Returns:
            ExtractJob: The extraction job
        """
        return self._run_in_thread(self._client.llama_extract.get_job(job_id=job_id))

    def get_extraction_run_for_job(self, job_id: str) -> ExtractRun:
        """
        Get the extraction run for a given job_id.

        Args:
            job_id (str): The job_id to get the extraction run for

        Returns:
            ExtractRun: The extraction run
        """
        return self._run_in_thread(
            self._client.llama_extract.get_run_by_job_id(
                job_id=job_id,
            )
        )

    def delete_extraction_run(self, run_id: str) -> None:
        """Delete an extraction run by ID.

        Args:
            run_id (str): The ID of the extraction run to delete
        """
        self._run_in_thread(
            self._client.llama_extract.delete_extraction_run(run_id=run_id)
        )

    def list_extraction_runs(
        self, page: int = 0, limit: int = 100
    ) -> PaginatedExtractRunsResponse:
        """List extraction runs for the extraction agent.

        Returns:
            PaginatedExtractRunsResponse: Paginated list of extraction runs
        """
        return self._run_in_thread(
            self._client.llama_extract.list_extract_runs(
                extraction_agent_id=self.id,
                skip=page * limit,
                limit=limit,
            )
        )

    def __repr__(self) -> str:
        return f"ExtractionAgent(id={self.id}, name={self.name})"

    def __del__(self) -> None:
        """Cleanup resources properly."""
        try:
            if hasattr(self, "_thread_pool"):
                self._thread_pool.shutdown(wait=True)
        except Exception:
            pass  # Suppress exceptions during cleanup


class LlamaExtract(BaseComponent):
    """Factory class for creating and managing extraction agents."""

    api_key: str = Field(description="The API key for the LlamaExtract API.")
    base_url: str = Field(description="The base URL of the LlamaExtract API.")
    check_interval: int = Field(
        default=1,
        description="The interval in seconds to check if the extraction is done.",
    )
    max_timeout: int = Field(
        default=2000,
        description="The maximum timeout in seconds to wait for the extraction to finish.",
    )
    num_workers: int = Field(
        default=4,
        gt=0,
        lt=10,
        description="The number of workers to use sending API requests for extraction.",
    )
    show_progress: bool = Field(
        default=True, description="Show progress when extracting multiple files."
    )
    verbose: bool = Field(
        default=False, description="Show verbose output when extracting files."
    )
    verify: Optional[bool] = Field(
        default=True, description="Simple SSL verification option."
    )
    httpx_timeout: Optional[float] = Field(
        default=60, description="Timeout for the httpx client."
    )
    _async_client: AsyncLlamaCloud = PrivateAttr()
    _thread_pool: ThreadPoolExecutor = PrivateAttr()
    _project_id: Optional[str] = PrivateAttr()
    _organization_id: Optional[str] = PrivateAttr()

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        check_interval: int = 1,
        max_timeout: int = 2000,
        num_workers: int = 4,
        show_progress: bool = True,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        verify: Optional[bool] = True,
        httpx_timeout: Optional[float] = 60,
        verbose: bool = False,
    ):
        if not api_key:
            api_key = os.getenv("LLAMA_CLOUD_API_KEY", None)
            if api_key is None:
                raise ValueError("The API key is required.")

        if not base_url:
            base_url = os.getenv("LLAMA_CLOUD_BASE_URL", None) or DEFAULT_BASE_URL

        super().__init__(
            api_key=api_key,  # type: ignore
            base_url=base_url,  # type: ignore
            check_interval=check_interval,
            max_timeout=max_timeout,
            num_workers=num_workers,
            show_progress=show_progress,
            project_id=project_id,
            organization_id=organization_id,
            verify=verify,
            httpx_timeout=httpx_timeout,
            verbose=verbose,
        )
        self._httpx_client = httpx.AsyncClient(verify=verify, timeout=httpx_timeout)  # type: ignore
        self.verify = verify
        self.httpx_timeout = httpx_timeout

        self._async_client = AsyncLlamaCloud(
            token=self.api_key,
            base_url=self.base_url,
            httpx_client=self._httpx_client,
        )
        self._thread_pool = ThreadPoolExecutor(
            max_workers=min(10, (os.cpu_count() or 1) + 4)
        )
        if not project_id:
            project_id = os.getenv("LLAMA_CLOUD_PROJECT_ID", None)
        self._project_id = project_id
        self._organization_id = organization_id

    def _run_in_thread(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run coroutine in a separate thread to avoid event loop issues"""
        return run_in_thread(
            coro,
            self._thread_pool,
            self.verify,  # type: ignore
            self.httpx_timeout,  # type: ignore
            self._async_client._client_wrapper,
        )

    def create_agent(
        self,
        name: str,
        data_schema: SchemaInput,
        config: Optional[ExtractConfig] = None,
    ) -> ExtractionAgent:
        """Create a new extraction agent.

        Args:
            name (str): The name of the extraction agent
            data_schema (SchemaInput): The data schema for the extraction agent
            config (Optional[ExtractConfig]): The extraction config for the agent

        Returns:
            ExtractionAgent: The created extraction agent
        """
        if config is not None:
            _extraction_config_warning(config)
        else:
            config = DEFAULT_EXTRACT_CONFIG

        if isinstance(data_schema, dict):
            pass
        elif issubclass(data_schema, BaseModel):
            data_schema = data_schema.model_json_schema()
        else:
            raise ValueError(
                "data_schema must be either a dictionary or a Pydantic model"
            )

        agent = self._run_in_thread(
            self._async_client.llama_extract.create_extraction_agent(
                project_id=self._project_id,
                organization_id=self._organization_id,
                name=name,
                data_schema=data_schema,
                config=config,
            )
        )

        return ExtractionAgent(
            client=self._async_client,
            agent=agent,
            project_id=self._project_id,
            organization_id=self._organization_id,
            check_interval=self.check_interval,
            max_timeout=self.max_timeout,
            num_workers=self.num_workers,
            show_progress=self.show_progress,
            verbose=self.verbose,
            verify=self.verify,
            httpx_timeout=self.httpx_timeout,
        )

    def get_agent(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
    ) -> ExtractionAgent:
        """Get extraction agents by name or extraction agent ID.

        Args:
            name (Optional[str]): Filter by name
            extraction_agent_id (Optional[str]): Filter by extraction agent ID

        Returns:
            ExtractionAgent: The extraction agent
        """
        if id is not None and name is not None:
            warnings.warn(
                "Both name and extraction_agent_id are provided. Using extraction_agent_id."
            )

        if id:
            agent = self._run_in_thread(
                self._async_client.llama_extract.get_extraction_agent(
                    extraction_agent_id=id,
                )
            )

        elif name:
            agent = self._run_in_thread(
                self._async_client.llama_extract.get_extraction_agent_by_name(
                    name=name,
                    project_id=self._project_id,
                )
            )
        else:
            raise ValueError("Either name or extraction_agent_id must be provided.")

        return ExtractionAgent(
            client=self._async_client,
            agent=agent,
            project_id=self._project_id,
            organization_id=self._organization_id,
            check_interval=self.check_interval,
            max_timeout=self.max_timeout,
            num_workers=self.num_workers,
            show_progress=self.show_progress,
            verbose=self.verbose,
            verify=self.verify,
            httpx_timeout=self.httpx_timeout,
        )

    def list_agents(self) -> List[ExtractionAgent]:
        """List all available extraction agents."""
        agents = self._run_in_thread(
            self._async_client.llama_extract.list_extraction_agents(
                project_id=self._project_id,
            )
        )

        return [
            ExtractionAgent(
                client=self._async_client,
                agent=agent,
                project_id=self._project_id,
                organization_id=self._organization_id,
                check_interval=self.check_interval,
                max_timeout=self.max_timeout,
                num_workers=self.num_workers,
                show_progress=self.show_progress,
                verbose=self.verbose,
                verify=self.verify,
                httpx_timeout=self.httpx_timeout,
            )
            for agent in agents
        ]

    def delete_agent(self, agent_id: str) -> None:
        """Delete an extraction agent by ID.

        Args:
            agent_id (str): ID of the extraction agent to delete
        """
        self._run_in_thread(
            self._async_client.llama_extract.delete_extraction_agent(
                extraction_agent_id=agent_id
            )
        )

    async def _wait_for_job_result(self, job_id: str) -> Optional[ExtractRun]:
        """Wait for and return the results of an extraction job."""
        return await _wait_for_job_result(
            client=self._async_client,
            job_id=job_id,
            check_interval=self.check_interval,
            max_timeout=self.max_timeout,
            verbose=self.verbose,
            project_id=self._project_id,
            organization_id=self._organization_id,
            job_retry_attempts=3,
            job_max_wait=4,
            job_jitter=5,
            run_retry_attempts=3,
            run_max_wait=4,
            run_jitter=3,
        )

    def _get_mime_type(
        self,
        filename: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Determine MIME type for a file based on filename or path."""
        # MIME type mappings for supported formats
        MIME_TYPE_MAP = {
            # Text files
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
            ".html": "text/html",
            ".htm": "text/html",
            ".md": "text/markdown",
            # Document files
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            # Image files
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }

        # Try to get extension from filename or file_path
        extension = None
        if filename:
            extension = Path(filename).suffix.lower()
        elif file_path:
            extension = Path(file_path).suffix.lower()

        # Check if the extension is supported
        if extension and extension in MIME_TYPE_MAP:
            return MIME_TYPE_MAP[extension]

        # If we don't have a supported extension, provide helpful error message
        supported_extensions = [ext[1:] for ext in MIME_TYPE_MAP.keys()]  # Remove dots
        supported_list = ", ".join(sorted(supported_extensions))

        if extension:
            ext_without_dot = extension[1:]  # Remove the leading dot
            raise ValueError(
                f"Unsupported file type: '{ext_without_dot}'. "
                f"Supported formats are: {supported_list}"
            )
        else:
            raise ValueError(
                f"Could not determine file type. Please provide a filename with one of these supported extensions: {supported_list}"
            )

    def _convert_file_to_file_data(
        self, file_input: FileInput
    ) -> Union[FileData, str, File]:
        """Convert FileInput to FileData or text string for stateless extraction."""
        if isinstance(file_input, File):
            return file_input

        if isinstance(file_input, SourceText):
            if file_input.text_content is not None:
                return file_input.text_content
            elif file_input.file is not None:
                if isinstance(file_input.file, bytes):
                    data = file_input.file
                    filename = file_input.filename
                elif isinstance(file_input.file, (str, Path)):
                    with open(file_input.file, "rb") as f:
                        data = f.read()
                    filename = file_input.filename or str(file_input.file)
                elif isinstance(file_input.file, (BufferedIOBase, TextIOWrapper)):
                    if hasattr(file_input.file, "read"):
                        content = file_input.file.read()
                        if isinstance(content, str):
                            data = content.encode("utf-8")
                        else:
                            data = content
                    else:
                        raise ValueError("File object must have a read method")
                    filename = file_input.filename or getattr(
                        file_input.file, "name", None
                    )
                else:
                    raise ValueError(f"Unsupported file type: {type(file_input.file)}")

                # Encode as base64
                encoded_data = base64.b64encode(data).decode("utf-8")

                # Determine mime type
                mime_type = self._get_mime_type(filename=filename)

                return FileData(data=encoded_data, mime_type=mime_type)
            else:
                raise ValueError("SourceText must have either text_content or file")

        elif isinstance(file_input, (str, Path)):
            with open(file_input, "rb") as f:
                data = f.read()
            encoded_data = base64.b64encode(data).decode("utf-8")
            mime_type = self._get_mime_type(file_path=file_input)
            return FileData(data=encoded_data, mime_type=mime_type)

        elif isinstance(file_input, bytes):
            # For raw bytes, we can't determine the file type, so we need to raise an error
            raise ValueError(
                "Cannot determine file type from raw bytes. Please use SourceText with a filename, or provide a file path."
            )

        elif isinstance(file_input, (BufferedIOBase, TextIOWrapper)):
            if hasattr(file_input, "read"):
                content = file_input.read()
                if isinstance(content, str):
                    data = content.encode("utf-8")
                else:
                    data = content
                encoded_data = base64.b64encode(data).decode("utf-8")

                # Try to get filename from the file object
                filename = getattr(file_input, "name", None)
                mime_type = self._get_mime_type(filename=filename)

                return FileData(data=encoded_data, mime_type=mime_type)
            else:
                raise ValueError("File object must have a read method")

        else:
            raise ValueError(f"Unsupported file input type: {type(file_input)}")

    async def queue_extraction(
        self,
        data_schema: SchemaInput,
        config: ExtractConfig,
        files: Union[FileInput, List[FileInput]],
    ) -> Union[ExtractJob, List[ExtractJob]]:
        """Queue extraction jobs using stateless extraction (no agent required).

        Args:
            data_schema: The schema defining what data to extract
            config: The extraction configuration
            files: File(s) to extract from

        Returns:
            ExtractJob or list of ExtractJobs
        """
        _extraction_config_warning(config)
        processed_schema = await _validate_schema(self._async_client, data_schema)

        if not isinstance(files, list):
            files = [files]

        jobs = []
        for file_input in files:
            file_data_or_text = self._convert_file_to_file_data(file_input)

            if isinstance(file_data_or_text, File):
                file_args = {"file_id": file_data_or_text.id}

            elif isinstance(file_data_or_text, str):
                # It's text content
                file_args = {"text": file_data_or_text}
            else:
                # It's FileData
                file_args = {"file": file_data_or_text}

            job = await self._async_client.llama_extract.extract_stateless(
                project_id=self._project_id,
                organization_id=self._organization_id,
                data_schema=processed_schema,
                config=config,
                **file_args,
            )
            jobs.append(job)

        return jobs[0] if len(jobs) == 1 else jobs

    async def aextract(
        self,
        data_schema: SchemaInput,
        config: ExtractConfig,
        files: Union[FileInput, List[FileInput]],
    ) -> Union[ExtractRun, List[ExtractRun]]:
        """Run stateless extraction and wait for results.

        Args:
            data_schema: The schema defining what data to extract
            config: The extraction configuration
            files: File(s) to extract from

        Returns:
            ExtractRun or list of ExtractRuns with the extraction results
        """
        jobs = await self.queue_extraction(data_schema, config, files)

        if isinstance(jobs, list):
            runs = []
            for job in jobs:
                run = await self._wait_for_job_result(job.id)
                if run is None:
                    raise RuntimeError(
                        f"Failed to get extraction result for job {job.id}"
                    )
                runs.append(run)
            return runs
        else:
            run = await self._wait_for_job_result(jobs.id)
            if run is None:
                raise RuntimeError(f"Failed to get extraction result for job {jobs.id}")
            return run

    def extract(
        self,
        data_schema: SchemaInput,
        config: ExtractConfig,
        files: Union[FileInput, List[FileInput]],
    ) -> Union[ExtractRun, List[ExtractRun]]:
        """Run stateless extraction and wait for results (synchronous version).

        Args:
            data_schema: The schema defining what data to extract
            config: The extraction configuration
            files: File(s) to extract from

        Returns:
            ExtractRun or list of ExtractRuns with the extraction results
        """
        return self._run_in_thread(self.aextract(data_schema, config, files))

    def __del__(self) -> None:
        """Cleanup resources properly."""
        try:
            if hasattr(self, "_thread_pool"):
                self._thread_pool.shutdown(wait=True)
        except Exception:
            pass  # Suppress exceptions during cleanup


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Example usage:
    #
    # # Basic usage with stateless extraction (no agent required)
    # extractor = LlamaExtract()
    # schema = {"name": {"type": "string"}, "email": {"type": "string"}}
    # config = ExtractConfig(extraction_mode=ExtractMode.FAST)
    # files = ["path/to/document.pdf"]
    #
    # # Queue extraction jobs
    # jobs = extractor.queue_extraction(schema, config, files)
    #
    # # Or run extraction and wait for results
    # results = extractor.extract(schema, config, files)

    data_dir = Path(__file__).parent.parent / "tests" / "data"
    extractor = LlamaExtract()
    try:
        agent = extractor.get_agent(name="test-agent")
    except Exception:
        agent = extractor.create_agent(
            "test-agent",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                },
            },
        )
    results = agent.extract(data_dir / "slide" / "conocophilips.pdf")
    extractor.delete_agent(agent.id)
    print(results)
