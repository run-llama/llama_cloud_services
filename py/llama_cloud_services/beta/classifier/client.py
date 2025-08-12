import asyncio
import time
from typing import Optional
from pydantic import BaseModel
from llama_cloud.client import AsyncLlamaCloud
from llama_cloud.types import (
    ClassifierRule,
    ClassifyJobResults,
    ClassifyParsingConfiguration,
    StatusEnum,
    ClassifyJobWithStatus,
    File,
)
from llama_cloud.resources.classifier.client import OMIT
from llama_cloud_services.files.client import FileClient
from llama_cloud_services.constants import POLLING_TIMEOUT_SECONDS
from llama_cloud_services.utils import is_terminal_status, augment_async_errors
from llama_index.core.async_utils import DEFAULT_NUM_WORKERS, run_jobs


class ClassificationOutput(BaseModel):
    file_id: str
    classification: str


class ClassifyClient:
    """
    Experimental - Client for interacting with the LlamaCloud Classifier API.
    The Classification API is currently in beta and may change in the future without notice.

    Args:
        client: The LlamaCloud client to use.
        project_id: The project ID to use.
        organization_id: The organization ID to use.
        polling_interval: The interval to poll for job completion in seconds.
        polling_timeout: The timeout for the job to complete in seconds.
    """

    def __init__(
        self,
        client: AsyncLlamaCloud,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        polling_interval: float = 1.0,
        polling_timeout: float = POLLING_TIMEOUT_SECONDS,
    ):
        self.client = client
        self.project_id = project_id
        self.organization_id = organization_id
        self.polling_interval = polling_interval
        self.file_client = FileClient(client, project_id, organization_id)
        self.polling_timeout = polling_timeout

    async def aclassify_file_ids(
        self,
        rules: list[ClassifierRule],
        file_ids: list[str],
        parsing_configuration: Optional[ClassifyParsingConfiguration] = None,
        raise_on_error: bool = True,
    ) -> ClassifyJobResults:
        """
        Classify a list of files by their IDs.
        Note that even if a job fails, some of the files may have been classified successfully.
        In this case, you may want to set raise_on_error to False and check the results for successful classifications.

        Args:
            rules: The rules to use for classification.
            file_ids: The IDs of the files to classify.
            parsing_configuration: The parsing configuration to use for classification.
            raise_on_error: Whether to raise an error if the classification job fails.

        Returns:
            The results of the classification job.
        """
        classify_job = await self.client.classifier.create_classify_job(
            rules=rules,
            file_ids=file_ids,
            parsing_configuration=parsing_configuration or OMIT,
            project_id=self.project_id,
            organization_id=self.organization_id,
        )

        classify_job_with_status = await self._wait_for_job_completion(classify_job.id)

        if raise_on_error and classify_job_with_status.status == StatusEnum.ERROR:
            raise ValueError(
                f"Error classifying files under job ID {classify_job_with_status.id}"
            )

        results = await self.client.classifier.get_classification_job_results(
            classify_job_with_status.id,
            project_id=self.project_id,
            organization_id=self.organization_id,
        )

        return results

    def classify_file_ids(
        self,
        rules: list[ClassifierRule],
        file_ids: list[str],
        parsing_configuration: Optional[ClassifyParsingConfiguration] = None,
        raise_on_error: bool = True,
    ) -> ClassifyJobResults:
        with augment_async_errors():
            return asyncio.run(
                self.aclassify_file_ids(
                    rules, file_ids, parsing_configuration, raise_on_error
                )
            )

    async def aclassify_file_path(
        self,
        rules: list[ClassifierRule],
        file_input_path: str,
        parsing_configuration: Optional[ClassifyParsingConfiguration] = None,
        raise_on_error: bool = True,
    ) -> ClassifyJobResults:
        file = await self.file_client.upload_file(file_input_path)
        return await self.aclassify_file_ids(
            rules, [file.id], parsing_configuration, raise_on_error
        )

    def classify_file_path(
        self,
        rules: list[ClassifierRule],
        file_input_path: str,
        parsing_configuration: Optional[ClassifyParsingConfiguration] = None,
        raise_on_error: bool = True,
    ) -> ClassifyJobResults:
        with augment_async_errors():
            return asyncio.run(
                self.aclassify_file_path(
                    rules, file_input_path, parsing_configuration, raise_on_error
                )
            )

    async def aclassify_file_paths(
        self,
        rules: list[ClassifierRule],
        file_input_paths: list[str],
        parsing_configuration: Optional[ClassifyParsingConfiguration] = None,
        raise_on_error: bool = True,
        workers: int = DEFAULT_NUM_WORKERS,
        show_progress: bool = False,
    ) -> ClassifyJobResults:
        coroutines = [self.file_client.upload_file(path) for path in file_input_paths]
        files: list[File] = await run_jobs(
            coroutines,
            show_progress=show_progress,
            workers=workers,
            desc="Uploading files for classification",
        )
        return await self.aclassify_file_ids(
            rules, [file.id for file in files], parsing_configuration, raise_on_error
        )

    def classify_file_paths(
        self,
        rules: list[ClassifierRule],
        file_input_paths: list[str],
        parsing_configuration: Optional[ClassifyParsingConfiguration] = None,
        raise_on_error: bool = True,
    ) -> ClassifyJobResults:
        with augment_async_errors():
            return asyncio.run(
                self.aclassify_file_paths(
                    rules, file_input_paths, parsing_configuration, raise_on_error
                )
            )

    async def _wait_for_job_completion(self, job_id: str) -> ClassifyJobWithStatus:
        job = await self.client.classifier.get_classify_job(
            job_id, project_id=self.project_id, organization_id=self.organization_id
        )
        start_time = time.time()
        while not is_terminal_status(job.status):
            polling_duration = time.time() - start_time
            if polling_duration > self.polling_timeout:
                raise TimeoutError(
                    f"Job {job_id} timed out after {polling_duration} seconds"
                )
            await asyncio.sleep(self.polling_interval)
            job = await self.client.classifier.get_classify_job(
                job_id, project_id=self.project_id, organization_id=self.organization_id
            )
        return job
