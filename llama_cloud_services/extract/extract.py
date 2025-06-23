import asyncio
import os
import time
from io import BufferedIOBase, BufferedReader, BytesIO, TextIOWrapper
from pathlib import Path
from typing import List, Optional, Type, Union, Coroutine, Any, TypeVar
import secrets
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
    ExtractJobCreate,
    ExtractRun,
    File,
    ExtractMode,
    StatusEnum,
    ExtractTarget,
    LlamaExtractSettings,
    PaginatedExtractRunsResponse,
)
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.core.api_error import ApiError
from llama_cloud_services.extract.utils import (
    JSONObjectType,
    augment_async_errors,
    ExperimentalWarning,
)
from llama_index.core.schema import BaseComponent
from llama_index.core.async_utils import run_jobs
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.constants import DEFAULT_BASE_URL
from concurrent.futures import ThreadPoolExecutor

T = TypeVar("T")


SchemaInput = Union[JSONObjectType, Type[BaseModel]]

DEFAULT_EXTRACT_CONFIG = ExtractConfig(
    extraction_target=ExtractTarget.PER_DOC,
    extraction_mode=ExtractMode.BALANCED,
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


class SourceText:
    def __init__(
        self,
        *,
        file: Union[bytes, BufferedIOBase, TextIOWrapper, str, Path, None] = None,
        text_content: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        self.file = file
        self.filename = filename
        self.text_content = text_content
        self._validate()

    def _validate(self) -> None:
        """Ensure filename is provided when needed."""
        if not ((self.file is None) ^ (self.text_content is None)):
            raise ValueError("Either file or text_content must be provided.")
        if self.text_content is not None:
            if not self.filename:
                random_hex = secrets.token_hex(4)
                self.filename = f"text_input_{random_hex}.txt"
            return

        if isinstance(self.file, (bytes, BufferedIOBase, TextIOWrapper)):
            if not self.filename and hasattr(self.file, "name"):
                self.filename = os.path.basename(str(self.file.name))
            elif not hasattr(self.file, "name") and self.filename is None:
                raise ValueError(
                    "filename must be provided when file is bytes or a file-like object without a name"
                )
        elif isinstance(self.file, (str, Path)):
            if not self.filename:
                self.filename = os.path.basename(str(self.file))
        else:
            raise ValueError(f"Unsupported file type: {type(self.file)}")


FileInput = Union[str, Path, BufferedIOBase, SourceText]


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
    if config.extraction_mode == ExtractMode.ACCURATE:
        warnings.warn("ACCURATE extraction mode is deprecated. Using BALANCED instead.")
        config.extraction_mode = ExtractMode.BALANCED
    if config.use_reasoning:
        warnings.warn(
            "`use_reasoning` is an experimental feature. Results will be available in "
            "the `extraction_metadata` field for the extraction run.",
            ExperimentalWarning,
        )
    if config.cite_sources:
        warnings.warn(
            "`cite_sources` is an experimental feature. This may greatly increase the "
            "size of the response, and slow down the extraction. Results will be "
            "available in the `extraction_metadata` field for the extraction run.",
            ExperimentalWarning,
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
        processed_schema: JSONObjectType
        if isinstance(data_schema, dict):
            # TODO: if we expose a get_validated JSON schema method, we can use it here
            processed_schema = data_schema  # type: ignore
        elif isinstance(data_schema, type) and issubclass(data_schema, BaseModel):
            processed_schema = data_schema.model_json_schema()
        else:
            raise ValueError(
                "data_schema must be either a dictionary or a Pydantic model"
            )
        validated_schema = self._run_in_thread(
            self._client.llama_extract.validate_extraction_schema(
                data_schema=processed_schema
            )
        )
        self._data_schema = validated_schema.data_schema

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
        file_contents: Optional[Union[BufferedIOBase, BytesIO]] = None
        try:
            if file_input.text_content is not None:
                # Handle direct text content
                file_contents = BytesIO(file_input.text_content.encode("utf-8"))
            elif isinstance(file_input.file, TextIOWrapper):
                # Handle text-based IO objects
                file_contents = BytesIO(file_input.file.read().encode("utf-8"))
            elif isinstance(file_input.file, (str, Path)):
                # Handle file paths
                file_contents = open(file_input.file, "rb")
            elif isinstance(file_input.file, bytes):
                # Handle bytes
                file_contents = BytesIO(file_input.file)
            elif isinstance(file_input.file, BufferedIOBase):
                # Handle binary IO objects
                file_contents = file_input.file
            else:
                raise ValueError(f"Unsupported file type: {type(file_input.file)}")

            # Add name attribute to file object if needed
            if not hasattr(file_contents, "name"):
                file_contents.name = file_input.filename  # type: ignore

            return await self._client.files.upload_file(
                project_id=self._project_id, upload_file=file_contents
            )
        finally:
            if file_contents is not None and isinstance(file_contents, BufferedReader):
                file_contents.close()

    async def _upload_file(self, file_input: FileInput) -> File:
        source_text = None
        if isinstance(file_input, SourceText):
            source_text = file_input
        elif isinstance(file_input, (str, Path)):
            path = Path(file_input)
            source_text = SourceText(file=path, filename=path.name)
        else:
            # Try to get filename from the file object if not provided
            filename = None
            if hasattr(file_input, "name"):
                filename = os.path.basename(str(file_input.name))
            if filename is None:
                raise ValueError(
                    "Use SourceText to provide filename when uploading bytes or file-like objects."
                )

            warnings.warn(
                "Use SourceText instead of bytes or file-like objects",
                DeprecationWarning,
            )
            source_text = SourceText(file=file_input, filename=filename)

        return await self.upload_file(source_text)

    async def _get_job_with_retry(self, job_id: str) -> ExtractJob:
        """Get job with retry logic for transient errors."""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable_error),
            stop=stop_after_attempt(5),
            wait=wait_exponential_jitter(initial=1, max=60, jitter=5),
            reraise=True,
        ):
            with attempt:
                return await self._client.llama_extract.get_job(job_id=job_id)

    async def _get_run_with_retry(self, job_id: str) -> ExtractRun:
        """Get extraction run with retry logic for transient errors."""
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable_error),
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1, max=20, jitter=3),
            reraise=True,
        ):
            with attempt:
                return await self._client.llama_extract.get_run_by_job_id(job_id=job_id)

    async def _wait_for_job_result(self, job_id: str) -> Optional[ExtractRun]:
        """Wait for and return the results of an extraction job."""
        start = time.perf_counter()
        tries = 0

        while True:
            await asyncio.sleep(self.check_interval)
            tries += 1

            try:
                job = await self._get_job_with_retry(job_id)

                if job.status == StatusEnum.SUCCESS:
                    return await self._get_run_with_retry(job_id)
                elif job.status == StatusEnum.PENDING:
                    end = time.perf_counter()
                    if end - start > self.max_timeout:
                        raise Exception(f"Timeout while extracting the file: {job_id}")
                    if self._verbose and tries % 10 == 0:
                        print(".", end="", flush=True)
                    continue
                else:
                    warnings.warn(
                        f"Failure in job: {job_id}, status: {job.status}, error: {job.error}"
                    )
                    return await self._get_run_with_retry(job_id)

            except Exception as e:
                # If we get a non-retryable error or all retries are exhausted, re-raise
                if self._verbose:
                    print(f"\nError in job polling for {job_id}: {e}")
                raise e

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

    async def _run_extraction_test(
        self,
        files: Union[FileInput, List[FileInput]],
        extract_settings: LlamaExtractSettings,
    ) -> Union[ExtractJob, List[ExtractJob]]:
        if not isinstance(files, list):
            files = [files]
            single_file = True
        else:
            single_file = False

        upload_tasks = [self._upload_file(file) for file in files]
        with augment_async_errors():
            uploaded_files = await run_jobs(
                upload_tasks,
                workers=self.num_workers,
                desc="Uploading files",
                show_progress=self.show_progress,
            )

        async def run_job(file: File) -> ExtractRun:
            job_queued = await self._client.llama_extract.run_job_test_user(
                job_create=ExtractJobCreate(
                    extraction_agent_id=self.id,
                    file_id=file.id,
                    data_schema_override=self.data_schema,
                    config_override=self.config,
                ),
                extract_settings=extract_settings,
            )
            return await self._wait_for_job_result(job_queued.id)

        job_tasks = [run_job(file) for file in uploaded_files]
        with augment_async_errors():
            extract_results = await run_jobs(
                job_tasks,
                workers=self.num_workers,
                desc="Running extraction jobs",
                show_progress=self.show_progress,
            )

        if self._verbose:
            for file, job in zip(files, extract_results):
                file_repr = (
                    str(file) if isinstance(file, (str, Path)) else "<bytes/buffer>"
                )
                print(f"Running extraction for file {file_repr} under job_id {job.id}")

        return extract_results[0] if single_file else extract_results

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
            uploaded_files = await run_jobs(
                upload_tasks,
                workers=self.num_workers,
                desc="Uploading files",
                show_progress=self.show_progress,
            )

        job_tasks = [
            self._client.llama_extract.run_job(
                request=ExtractJobCreate(
                    extraction_agent_id=self.id,
                    file_id=file.id,
                    data_schema_override=self.data_schema,
                    config_override=self.config,
                ),
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
            api_key=api_key,
            base_url=base_url,
            check_interval=check_interval,
            max_timeout=max_timeout,
            num_workers=num_workers,
            show_progress=show_progress,
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
            data_schema = data_schema
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
