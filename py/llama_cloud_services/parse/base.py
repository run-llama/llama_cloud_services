import asyncio
import mimetypes
import os
import time
import warnings
from contextlib import asynccontextmanager
from copy import deepcopy
from enum import Enum
from io import BufferedIOBase
from pathlib import Path, PurePath, PurePosixPath
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import httpx
from fsspec import AbstractFileSystem
from llama_index.core.async_utils import asyncio_run, run_jobs
from llama_index.core.bridge.pydantic import (
    Field,
    PrivateAttr,
    model_validator,
)
from llama_index.core.constants import DEFAULT_BASE_URL
from llama_index.core.readers.base import BasePydanticReader
from llama_index.core.readers.file.base import get_default_fs
from llama_index.core.schema import Document

from llama_cloud_services.utils import check_extra_params, check_for_updates
from llama_cloud_services.parse.types import JobResult
from llama_cloud_services.parse.utils import (
    SUPPORTED_FILE_TYPES,
    ResultType,
    ParsingMode,
    FailedPageMode,
    expand_target_pages,
    nest_asyncio_err,
    nest_asyncio_msg,
    make_api_request,
    partition_pages,
    extract_tables_from_json_results,
)

# can put in a path to the file or the file bytes itself
# if passing as bytes or a buffer, must provide the file_name in extra_info
FileInput = Union[str, bytes, BufferedIOBase]

_DEFAULT_SEPARATOR = "\n---\n"


JOB_RESULT_URL = "/api/parsing/job/{job_id}/result/{result_type}"
JOB_STATUS_ROUTE = "/api/parsing/job/{job_id}"
JOB_UPLOAD_ROUTE = "/api/parsing/upload"


def build_url(
    base_url: str, organization_id: Optional[str], project_id: Optional[str]
) -> str:
    query_params = {}
    if organization_id:
        query_params["organization_id"] = organization_id
    if project_id:
        query_params["project_id"] = project_id

    if query_params:
        return base_url + "?" + "&".join([f"{k}={v}" for k, v in query_params.items()])

    return base_url


class JobFailedException(Exception):
    """Parse job failed exception."""

    def __init__(
        self,
        job_id: str,
        status: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        exception_str = (
            f"Job ID: {job_id} failed with status: {status}, "
            f'Error code: {error_code or "No error code found"}, '
            f'Error message: {error_message or "No error message found"}'
        )
        super().__init__(exception_str)
        self.job_id = job_id
        self.status = status
        self.error_code = error_code
        self.error_message = error_message

    @classmethod
    def from_result(cls, result_json: Dict[str, Any]) -> "JobFailedException":
        job_id = result_json["id"]
        status = result_json["status"]
        error_code = result_json.get("error_code")
        error_message = result_json.get("error_message")
        return cls(job_id, status, error_code=error_code, error_message=error_message)


class BackoffPattern(str, Enum):
    """Backoff pattern for polling."""

    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


def _get_default_api_key() -> str:
    env_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if env_key is None:
        raise ValueError("The API key is required.")
    return env_key


def _get_default_base_url() -> str:
    env_url = os.getenv("LLAMA_CLOUD_BASE_URL")
    return env_url or DEFAULT_BASE_URL


class LlamaParse(BasePydanticReader):
    """A smart-parser for files."""

    # Library / access specific configurations
    api_key: str = Field(
        default_factory=_get_default_api_key,
        description="The API key for the LlamaParse API.",
        validate_default=True,
    )
    base_url: str = Field(
        default_factory=_get_default_base_url,
        description="The base URL of the Llama Parsing API.",
    )
    organization_id: Optional[str] = Field(
        default=None,
        description="The organization ID for the LlamaParse API.",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="The project ID for the LlamaParse API.",
    )
    check_interval: int = Field(
        default=1,
        description="The interval in seconds to check if the parsing is done.",
    )

    backoff_pattern: BackoffPattern = Field(
        default=BackoffPattern.LINEAR,
        description="Controls the backoff pattern when retrying failed requests: 'constant', 'linear', or 'exponential'.",
    )
    max_check_interval: int = Field(
        default=5,
        description="Maximum interval in seconds between polling attempts when checking job status.",
    )

    custom_client: Optional[httpx.AsyncClient] = Field(
        default=None, description="A custom HTTPX client to use for sending requests."
    )

    ignore_errors: bool = Field(
        default=True,
        description="Whether or not to ignore and skip errors raised during parsing.",
    )
    max_timeout: int = Field(
        default=2000,
        description="The maximum timeout in seconds to wait for the parsing to finish.",
    )
    num_workers: int = Field(
        default=4,
        gt=0,
        lt=20,
        description="The number of workers to use sending API requests for parsing.",
    )
    result_type: ResultType = Field(
        default=ResultType.TXT, description="The result type for the parser."
    )
    show_progress: bool = Field(
        default=True, description="Show progress when parsing multiple files."
    )
    split_by_page: bool = Field(
        default=True,
        description="Whether to split by page using the page separator",
    )
    verbose: bool = Field(
        default=True, description="Whether to print the progress of the parsing."
    )

    # Parsing specific configurations (Alphabetical order)
    adaptive_long_table: Optional[bool] = Field(
        default=False,
        description="If set to true, LlamaParse will try to detect long table and adapt the output.",
    )
    aggressive_table_extraction: Optional[bool] = Field(
        default=False,
        description="If set to true, LlamaParse will try to extract tables aggressively, may lead to false positives.",
    )
    annotate_links: Optional[bool] = Field(
        default=False,
        description="Annotate links found in the document to extract their URL.",
    )
    auto_mode: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will automatically select the best mode to extract text from documents based on the rules provide. Will use the 'accurate' default mode by default and will upgrade page that match the rule to Premium mode.",
    )
    auto_mode_configuration_json: Optional[str] = Field(
        default=None,
        description="A JSON string containing the configuration for the auto mode. If set, the parser will use the provided configuration for the auto mode.",
    )
    auto_mode_trigger_on_image_in_page: Optional[bool] = Field(
        default=False,
        description="If auto_mode is set to true, the parser will upgrade the page that contain an image to Premium mode.",
    )
    auto_mode_trigger_on_table_in_page: Optional[bool] = Field(
        default=False,
        description="If auto_mode is set to true, the parser will upgrade the page that contain a table to Premium mode.",
    )
    auto_mode_trigger_on_text_in_page: Optional[str] = Field(
        default=None,
        description="If auto_mode is set to true, the parser will upgrade the page that contain the text to Premium mode.",
    )
    auto_mode_trigger_on_regexp_in_page: Optional[str] = Field(
        default=None,
        description="If auto_mode is set to true, the parser will upgrade the page that match the regexp to Premium mode.",
    )
    azure_openai_api_version: Optional[str] = Field(
        default=None, description="Azure Openai API Version"
    )
    azure_openai_deployment_name: Optional[str] = Field(
        default=None, description="Azure Openai Deployment Name"
    )
    azure_openai_endpoint: Optional[str] = Field(
        default=None, description="Azure Openai Endpoint"
    )
    azure_openai_key: Optional[str] = Field(
        default=None, description="Azure Openai Key"
    )
    bbox_bottom: Optional[float] = Field(
        default=None,
        description="The bottom margin of the bounding box to use to extract text from documents expressed as a float between 0 and 1 representing the percentage of the page height.",
    )
    bbox_left: Optional[float] = Field(
        default=None,
        description="The left margin of the bounding box to use to extract text from documents expressed as a float between 0 and 1 representing the percentage of the page width.",
    )
    bbox_right: Optional[float] = Field(
        default=None,
        description="The right margin of the bounding box to use to extract text from documents expressed as a float between 0 and 1 representing the percentage of the page width.",
    )
    bbox_top: Optional[float] = Field(
        default=None,
        description="The top margin of the bounding box to use to extract text from documents expressed as a float between 0 and 1 representing the percentage of the page height.",
    )
    compact_markdown_table: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will output compact markdown table (without trailing spaces in cells).",
    )
    continuous_mode: Optional[bool] = Field(
        default=False,
        description="Parse documents continuously, leading to better results on documents where tables span across two pages.",
    )
    disable_ocr: Optional[bool] = Field(
        default=False,
        description="Disable the OCR on the document. LlamaParse will only extract the copyable text from the document.",
    )
    disable_image_extraction: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will not extract images from the document. Make the parser faster.",
    )
    do_not_cache: Optional[bool] = Field(
        default=False,
        description="If set to true, the document will not be cached. This mean that you will be re-charged it you reprocess them as they will not be cached.",
    )
    do_not_unroll_columns: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will keep column in the text according to document layout. Reduce reconstruction accuracy, and LLM's/embedings performances in most case.",
    )
    extract_charts: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will extract/tag charts from the document.",
    )
    extract_layout: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will extract the layout information of the document. Cost 1 credit per page.",
    )
    fast_mode: Optional[bool] = Field(
        default=False,
        description="Note: Non compatible with gpt-4o. If set to true, the parser will use a faster mode to extract text from documents. This mode will skip OCR of images, and table/heading reconstruction.",
    )

    guess_xlsx_sheet_name: Optional[bool] = Field(
        default=False,
        description="Whether to guess the sheet names of the xlsx file.",
    )
    high_res_ocr: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will use high resolution OCR to extract text from images. This will increase the accuracy of the parsing job, but reduce the speed.",
    )
    html_make_all_elements_visible: Optional[bool] = Field(
        default=False,
        description="If set to true, when parsing HTML the parser will consider all elements display not element as display block.",
    )
    html_remove_fixed_elements: Optional[bool] = Field(
        default=False,
        description="If set to true, when parsing HTML the parser will remove fixed elements. Useful to hide cookie banners.",
    )
    html_remove_navigation_elements: Optional[bool] = Field(
        default=False,
        description="If set to true, when parsing HTML the parser will remove navigation elements. Useful to hide menus, header, footer.",
    )
    http_proxy: Optional[str] = Field(
        default=None,
        description="(optional) If set with input_url will use the specified http proxy to download the file.",
    )
    ignore_document_elements_for_layout_detection: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will ignore document elements for layout detection and only rely on a vision model.",
    )
    inline_images_in_markdown: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will inline images in the markdown output.",
    )
    input_s3_region: Optional[str] = Field(
        default=None,
        description="The region of the input S3 bucket if input_s3_path is specified.",
    )
    invalidate_cache: Optional[bool] = Field(
        default=False,
        description="If set to true, the cache will be ignored and the document re-processes. All document are kept in cache for 48hours after the job was completed to avoid processing the same document twice.",
    )
    job_timeout_extra_time_per_page_in_seconds: Optional[float] = Field(
        default=None,
        description="The extra time in seconds to wait for the parsing to finish per page. Get added to job_timeout_in_seconds.",
    )
    job_timeout_in_seconds: Optional[float] = Field(
        default=None,
        description="The maximum timeout in seconds to wait for the parsing to finish. Override default timeout of 30 minutes. Minimum is 120 seconds.",
    )
    keep_page_separator_when_merging_tables: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will keep the page separator when merging tables across pages.",
    )
    language: Optional[str] = Field(
        default="en", description="The language of the text to parse."
    )
    markdown_table_multiline_header_separator: Optional[str] = Field(
        default=None,
        description="The separator to use to split the header of the markdown table into multiple lines. Default is: <br/>",
    )
    max_pages: Optional[int] = Field(
        default=None,
        description="The maximum number of pages to extract text from documents. If set to 0 or not set, all pages will be that should be extracted will be extracted (can work in combination with targetPages).",
    )
    merge_tables_across_pages_in_markdown: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will merge tables across pages in the markdown output. This is useful for documents with tables that span across multiple pages.",
    )
    output_pdf_of_document: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will also output a PDF of the document. (except for spreadsheets)",
    )
    output_s3_path_prefix: Optional[str] = Field(
        default=None,
        description="An S3 path prefix to store the output of the parsing job. If set, the parser will upload the output to S3. The bucket need to be accessible from the LlamaIndex organization.",
    )
    output_s3_region: Optional[str] = Field(
        default=None,
        description="The AWS region of the output S3 bucket defined in output_s3_path_prefix.",
    )
    output_tables_as_HTML: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will output tables as HTML in the markdown.",
    )
    outlined_table_extraction: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will use a dedicated approach to extract tables with outlined cells. This is useful for documents with spreadsheet-like tables where cells are outlined with borders. This could lead to false positives, so use with caution.",
    )
    page_error_tolerance: Optional[float] = Field(
        default=None,
        description="The error tolerance for the number of pages with error in a doc (percentage express as 0-1). If we fail to parse a greater percentage of pages than the tolerance value we fail the job.",
    )
    page_prefix: Optional[str] = Field(
        default=None,
        description="A templated prefix to add to the beginning of each page. If it contain `{page_number}`, it will be replaced by the page number.",
    )
    page_separator: Optional[str] = Field(
        default=None,
        description="A templated  page separator to use to split the text.  If it contain `{page_number}`,it will be replaced by the next page number. If not set will the default separator '\\n---\\n' will be used.",
    )
    page_suffix: Optional[str] = Field(
        default=None,
        description="A templated suffix to add to the beginning of each page. If it contain `{page_number}`, it will be replaced by the page number.",
    )
    parse_mode: Optional[Union[ParsingMode, str]] = Field(
        default=None,
        description="The parsing mode to use, see ParsingMode enum for possible values ",
    )
    premium_mode: Optional[bool] = Field(
        default=False,
        description="Use our best parser mode if set to True.",
    )
    preset: Optional[str] = Field(
        default=None,
        description="The preset to use for the parser. If set, the parser will use the preset configuration. See LlamaParse documentation for available presets. Preset override most other parameters.",
    )
    preserve_layout_alignment_across_pages: Optional[bool] = Field(
        default=False,
        description="Preserve grid alignment across page in text mode.",
    )
    preserve_very_small_text: Optional[bool] = Field(
        default=False,
        description="If set, the parser will try to preserve very small text lines. This can be useful for documents containing vector graphics with very small text lines that may not be recognized by OCR or a vision model (such as in CAD drawings).",
    )
    presentation_out_of_bounds_content: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will include out-of-bounds content in presentation files.",
    )
    precise_bounding_box: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will use a more precise bounding box to extract text from documents. This will increase the accuracy of the parsing job, but reduce the speed.",
    )
    replace_failed_page_mode: Optional[FailedPageMode] = Field(
        default=None,
        description="The mode to use to replace the failed page, see FailedPageMode enum for possible value. If set, the parser will replace the failed page with the specified mode. If not set, the default mode (raw_text) will be used.",
    )
    replace_failed_page_with_error_message_prefix: Optional[str] = Field(
        default=None,
        description="A prefix to add before error message in failed pages. If not set, no prefix will be used.",
    )
    replace_failed_page_with_error_message_suffix: Optional[str] = Field(
        default=None,
        description="A suffix to add after error message in failed pages. If not set, no suffix will be used.",
    )
    remove_hidden_text: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will remove hidden text from the document.",
    )
    save_images: Optional[bool] = Field(
        default=True,
        description="If set to true, the parser will save images extracted from the document.",
    )
    skip_diagonal_text: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will ignore diagonal text (when the text rotation in degrees modulo 90 is not 0).",
    )
    spreadsheet_extract_sub_tables: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will extract sub-tables from the spreadsheet when possible (more than one table per sheet).",
    )
    spreadsheet_force_formula_computation: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will re-compute values for all spreadsheet cells containing formulas.",
    )
    specialized_chart_parsing_agentic: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will use a specialized agentic chart parsing model to extract data from charts. This model is able to understand the chart type and extract the data accordingly.",
    )
    specialized_chart_parsing_efficient: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will use a specialized efficient chart parsing model to extract data from charts. This model is faster and cheaper than the agentic model, but may be less accurate.",
    )
    specialized_chart_parsing_plus: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will use a specialized one-shot chart parsing model to extract data from charts. This model is able to understand the chart type and extract the data accordingly. It is more accurate than the efficient model, but also more expensive.",
    )
    specialized_image_parsing: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will use a specialized image parsing model to extract data from images.",
    )
    strict_mode_buggy_font: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will fail if it can't extract text from a document because of a buggy font.",
    )

    strict_mode_image_extraction: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will fail if it can't extract an image from the document.",
    )

    strict_mode_image_ocr: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will fail if it can't OCR an image from the document.",
    )

    strict_mode_reconstruction: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will fail if it can't reconstruct a table or a heading from the document.",
    )

    structured_output: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will output structured data based on the provided JSON Schema.",
    )
    structured_output_json_schema: Optional[str] = Field(
        default=None,
        description="A JSON Schema to use to structure the output of the parsing job. If set, the parser will output structured data based on the provided JSON Schema.",
    )
    structured_output_json_schema_name: Optional[str] = Field(
        default=None,
        description="The named JSON Schema to use to structure the output of the parsing job. For convenience / testing, LlamaParse provides a few named JSON Schema that can be used directly. Use 'imFeelingLucky' to let llamaParse dream the schema.",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="The system prompt. Replace llamaParse default system prompt, may impact accuracy",
    )
    system_prompt_append: Optional[str] = Field(
        default=None,
        description="String to append to default system prompt.",
    )
    take_screenshot: Optional[bool] = Field(
        default=False,
        description="Whether to take screenshot of each page of the document.",
    )
    target_pages: Optional[str] = Field(
        default=None,
        description="The target pages to extract text from documents. Describe as a comma separated list of page numbers. The first page of the document is page 0",
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="The user prompt. Replace llamaParse default user prompt",
    )
    vendor_multimodal_api_key: Optional[str] = Field(
        default=None,
        description="The API key for the multimodal API.",
    )
    vendor_multimodal_model_name: Optional[str] = Field(
        default=None,
        description="The model name for the vendor multimodal API.",
    )
    model: Optional[str] = Field(
        default=None,
        description="The document model name to be used with `parse_with_agent`.",
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="A URL that needs to be called at the end of the parsing job.",
    )
    partition_pages: Optional[int] = Field(
        default=None,
        description="If set, documents will automatically be partitioned into segments containing the specified number of pages at most. Parsing will be split into separate jobs for each partition segment. Can be used in combination with targetPages and maxPages.",
    )
    hide_headers: Optional[bool] = Field(
        default=False,
        description="Whether to hide page header in output markdown.",
    )
    hide_footers: Optional[bool] = Field(
        default=False,
        description="Whether to hide page footers in output markdown.",
    )
    page_header_suffix: Optional[str] = Field(
        default=None,
        description="A suffix to add to the page header in the output markdown.",
    )
    page_header_prefix: Optional[str] = Field(
        default=None,
        description="A prefix to add to the page header in the output markdown.",
    )
    page_footer_suffix: Optional[str] = Field(
        default=None,
        description="A suffix to add to the page footer in the output markdown.",
    )
    page_footer_prefix: Optional[str] = Field(
        default=None,
        description="A prefix to add to the page footer in the output markdown.",
    )
    extract_printed_page_number: Optional[bool] = Field(
        default=None,
        description="Whether to extract the printed page numbers from pages in the document.",
    )
    line_level_bounding_box: Optional[bool] = Field(
        default=False,
        description="If set to true, the parser will include line-level bounding boxes in the result.",
    )
    tier: Optional[str] = Field(
        default=None, description="The tier to use for the parsing job."
    )
    version: Optional[str] = Field(
        default=None,
        description="The version of the parser to use at the specified tier.",
    )

    # Deprecated
    bounding_box: Optional[str] = Field(
        default=None,
        description="The bounding box to use to extract text from documents describe as a string containing the bounding box margins",
    )
    complemental_formatting_instruction: Optional[str] = Field(
        default=None,
        description="The complemental formatting instruction for the parser. Tell llamaParse how some thing should to be formatted, while retaining the markdown output.",
    )
    content_guideline_instruction: Optional[str] = Field(
        default=None,
        description="The content guideline for the parser. Tell LlamaParse how the content should be changed / transformed.",
    )
    formatting_instruction: Optional[str] = Field(
        default=None,
        description="The Formatting instruction for the parser. Override default llamaParse behavior. In most case you want to use complemental_formatting_instruction instead.",
    )
    gpt4o_mode: Optional[bool] = Field(
        default=False,
        description="Whether to use gpt-4o extract text from documents.",
    )
    gpt4o_api_key: Optional[str] = Field(
        default=None,
        description="The API key for the GPT-4o API. Lowers the cost of parsing.",
    )
    is_formatting_instruction: Optional[bool] = Field(
        default=False,
        description="Allow the parsing instruction to also format the output. Disable to have a cleaner markdown output.",
    )
    parsing_instruction: Optional[str] = Field(
        default="", description="The parsing instruction for the parser."
    )

    use_vendor_multimodal_model: Optional[bool] = Field(
        default=False,
        description="Whether to use the vendor multimodal API.",
    )

    check_for_updates: Optional[bool] = Field(
        default=False,
        description="Automatically check for Python SDK updates.",
    )

    @model_validator(mode="before")
    @classmethod
    def handle_deprecated_params(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        # Handle deprecated guess_xlsx_sheet_names -> guess_xlsx_sheet_name
        if "guess_xlsx_sheet_names" in data:
            warnings.warn(
                "The parameter 'guess_xlsx_sheet_names' is deprecated and will be removed in a future release. "
                "Use 'guess_xlsx_sheet_name' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            # Only set the new parameter if it's not already explicitly set
            if "guess_xlsx_sheet_name" not in data:
                data["guess_xlsx_sheet_name"] = data["guess_xlsx_sheet_names"]
            del data["guess_xlsx_sheet_names"]
        return data

    @model_validator(mode="before")
    @classmethod
    def warn_extra_params(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        extra_params, suggestions = check_extra_params(cls, data)
        if extra_params:
            suggestions = [f"\n - {suggestion}" for suggestion in suggestions]
            suggestions_str = "".join(suggestions)
            warnings.warn(
                "The following parameters are unused: "
                + ", ".join(extra_params)
                + f".\n{suggestions_str}",
            )

        return data

    _aclient: Union[httpx.AsyncClient, None] = PrivateAttr(default=None, init=False)

    @property
    def aclient(self) -> httpx.AsyncClient:
        if not self._aclient:
            self._aclient = self.custom_client or httpx.AsyncClient()

        # need to do this outside instantiation in case user
        # updates base_url, api_key, or max_timeout later
        # ... you wouldn't usually expect that, except
        # if someone does do it and it doesn't reflect on
        # the client they'll end up pretty confused, so
        # for the sake of ergonomics...
        self._aclient.base_url = self.base_url
        self._aclient.headers["Authorization"] = f"Bearer {self.api_key}"
        self._aclient.timeout = self.max_timeout

        return self._aclient

    _update_checked = False

    async def _check_for_updates(self) -> None:
        if self.check_for_updates and not self._update_checked:
            try:
                await check_for_updates(self.aclient, quiet=False)
                self._update_checked = True
            except (ValueError, httpx.HTTPStatusError):
                pass

    @asynccontextmanager
    async def client_context(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        """Create a context for the HTTPX client."""
        if self.custom_client is not None:
            yield self.custom_client
        else:
            async with httpx.AsyncClient(timeout=self.max_timeout) as client:
                yield client

    def _is_input_url(self, file_path: FileInput) -> bool:
        """Check if the input is a valid URL.

        This method checks for:
        - Proper URL scheme (http/https)
        - Valid URL structure
        - Network location (domain)
        """
        if not isinstance(file_path, str):
            return False
        try:
            result = urlparse(file_path)
            return all(
                [
                    result.scheme in ("http", "https"),
                    result.netloc,  # Has domain
                    result.scheme,  # Has scheme
                ]
            )
        except Exception:
            return False

    def _is_s3_url(self, file_path: FileInput) -> bool:
        """Check if the input is a valid URL.

        This method checks for:
        - Proper S3 scheme (s3://)
        """
        if isinstance(file_path, str):
            return file_path.startswith("s3://")
        return False

    # upload a document and get back a job_id
    async def _create_job(
        self,
        file_input: FileInput,
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
        partition_target_pages: Optional[str] = None,
    ) -> str:
        await self._check_for_updates()
        files = None
        file_handle = None
        input_url = file_input if self._is_input_url(file_input) else None
        input_s3_path = file_input if self._is_s3_url(file_input) else None

        if isinstance(file_input, (bytes, BufferedIOBase)):
            if not extra_info or "file_name" not in extra_info:
                raise ValueError(
                    "file_name must be provided in extra_info when passing bytes"
                )
            file_name = extra_info["file_name"]
            mime_type = mimetypes.guess_type(file_name)[0]
            files = {"file": (file_name, file_input, mime_type)}
        elif input_url is not None:
            files = None
        elif input_s3_path is not None:
            files = None
        elif isinstance(file_input, (str, Path, PurePosixPath, PurePath)):
            file_path = str(file_input)
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in SUPPORTED_FILE_TYPES:
                mime_type = "application/octet-stream"
            else:
                mime_type = mimetypes.guess_type(file_path)[0]
            # Open the file here for the duration of the async context
            # load data, set the mime type
            fs = fs or get_default_fs()
            file_handle = fs.open(file_input, "rb")
            files = {"file": (os.path.basename(file_path), file_handle, mime_type)}
        else:
            raise ValueError(
                "file_input must be either a file path string, file bytes, or buffer object"
            )

        data: Dict[str, Any] = {}

        data["from_python_package"] = True

        if self.adaptive_long_table:
            data["adaptive_long_table"] = self.adaptive_long_table

        if self.aggressive_table_extraction:
            data["aggressive_table_extraction"] = self.aggressive_table_extraction

        if self.annotate_links:
            data["annotate_links"] = self.annotate_links

        if self.auto_mode:
            data["auto_mode"] = self.auto_mode

        if self.auto_mode_configuration_json is not None:
            data["auto_mode_configuration_json"] = self.auto_mode_configuration_json

        if self.auto_mode_trigger_on_image_in_page:
            data[
                "auto_mode_trigger_on_image_in_page"
            ] = self.auto_mode_trigger_on_image_in_page

        if self.auto_mode_trigger_on_table_in_page:
            data[
                "auto_mode_trigger_on_table_in_page"
            ] = self.auto_mode_trigger_on_table_in_page

        if self.auto_mode_trigger_on_text_in_page is not None:
            data[
                "auto_mode_trigger_on_text_in_page"
            ] = self.auto_mode_trigger_on_text_in_page

        if self.auto_mode_trigger_on_regexp_in_page is not None:
            data[
                "auto_mode_trigger_on_regexp_in_page"
            ] = self.auto_mode_trigger_on_regexp_in_page

        if self.azure_openai_api_version is not None:
            data["azure_openai_api_version"] = self.azure_openai_api_version

        if self.azure_openai_deployment_name is not None:
            data["azure_openai_deployment_name"] = self.azure_openai_deployment_name

        if self.azure_openai_endpoint is not None:
            data["azure_openai_endpoint"] = self.azure_openai_endpoint

        if self.azure_openai_key is not None:
            data["azure_openai_key"] = self.azure_openai_key

        if self.bbox_bottom is not None:
            data["bbox_bottom"] = self.bbox_bottom

        if self.bbox_left is not None:
            data["bbox_left"] = self.bbox_left

        if self.bbox_right is not None:
            data["bbox_right"] = self.bbox_right

        if self.bbox_top is not None:
            data["bbox_top"] = self.bbox_top

        if self.compact_markdown_table:
            data["compact_markdown_table"] = self.compact_markdown_table

        if self.complemental_formatting_instruction:
            print(
                "WARNING: complemental_formatting_instruction is deprecated and may be remove in a future release. Use system_prompt, system_prompt_append or user_prompt instead."
            )
            data[
                "complemental_formatting_instruction"
            ] = self.complemental_formatting_instruction

        if self.content_guideline_instruction:
            print(
                "WARNING: content_guideline_instruction is deprecated and may be remove in a future release. Use system_prompt, system_prompt_append or user_prompt instead."
            )
            data["content_guideline_instruction"] = self.content_guideline_instruction

        if self.continuous_mode:
            data["continuous_mode"] = self.continuous_mode

        if self.disable_ocr:
            data["disable_ocr"] = self.disable_ocr

        if self.disable_image_extraction:
            data["disable_image_extraction"] = self.disable_image_extraction

        if self.do_not_cache:
            data["do_not_cache"] = self.do_not_cache

        if self.do_not_unroll_columns:
            data["do_not_unroll_columns"] = self.do_not_unroll_columns

        if self.extract_charts:
            data["extract_charts"] = self.extract_charts

        if self.extract_layout:
            data["extract_layout"] = self.extract_layout

        if self.fast_mode:
            data["fast_mode"] = self.fast_mode

        if self.formatting_instruction:
            print(
                "WARNING: formatting_instruction is deprecated and may be remove in a future release. Use system_prompt, system_prompt_append or user_prompt instead."
            )
            data["formatting_instruction"] = self.formatting_instruction

        if self.guess_xlsx_sheet_name:
            data["guess_xlsx_sheet_name"] = self.guess_xlsx_sheet_name

        if self.html_make_all_elements_visible:
            data["html_make_all_elements_visible"] = self.html_make_all_elements_visible

        if self.high_res_ocr:
            data["high_res_ocr"] = self.high_res_ocr

        if self.html_remove_fixed_elements:
            data["html_remove_fixed_elements"] = self.html_remove_fixed_elements

        if self.html_remove_navigation_elements:
            data[
                "html_remove_navigation_elements"
            ] = self.html_remove_navigation_elements

        if self.http_proxy is not None:
            data["http_proxy"] = self.http_proxy

        if self.ignore_document_elements_for_layout_detection:
            data[
                "ignore_document_elements_for_layout_detection"
            ] = self.ignore_document_elements_for_layout_detection

        if self.inline_images_in_markdown:
            data["inline_images_in_markdown"] = self.inline_images_in_markdown

        if input_url is not None:
            files = None
            data["input_url"] = str(input_url)

        if input_s3_path is not None:
            files = None
            data["input_s3_path"] = str(input_s3_path)

        if self.input_s3_region is not None:
            data["input_s3_region"] = self.input_s3_region

        if self.invalidate_cache:
            data["invalidate_cache"] = self.invalidate_cache

        if self.is_formatting_instruction:
            print(
                "WARNING: formatting_instruction is deprecated and may be remove in a future release. Use system_prompt, system_prompt_append or user_prompt instead."
            )
            data["is_formatting_instruction"] = self.is_formatting_instruction

        if self.job_timeout_extra_time_per_page_in_seconds is not None:
            data[
                "job_timeout_extra_time_per_page_in_seconds"
            ] = self.job_timeout_extra_time_per_page_in_seconds

        if self.job_timeout_in_seconds is not None:
            data["job_timeout_in_seconds"] = self.job_timeout_in_seconds

        if self.keep_page_separator_when_merging_tables:
            data[
                "keep_page_separator_when_merging_tables"
            ] = self.keep_page_separator_when_merging_tables

        if self.language:
            data["language"] = self.language

        if self.max_pages is not None:
            data["max_pages"] = self.max_pages

        if self.output_pdf_of_document:
            data["output_pdf_of_document"] = self.output_pdf_of_document

        if self.output_s3_path_prefix is not None:
            data["output_s3_path_prefix"] = self.output_s3_path_prefix

        if self.output_s3_region is not None:
            data["output_s3_region"] = self.output_s3_region

        if self.output_tables_as_HTML:
            data["output_tables_as_HTML"] = self.output_tables_as_HTML

        if self.outlined_table_extraction:
            data["outlined_table_extraction"] = self.outlined_table_extraction

        if self.page_error_tolerance is not None:
            data["page_error_tolerance"] = self.page_error_tolerance

        if self.page_prefix is not None:
            data["page_prefix"] = self.page_prefix

        if self.merge_tables_across_pages_in_markdown:
            data[
                "merge_tables_across_pages_in_markdown"
            ] = self.merge_tables_across_pages_in_markdown

        if self.hide_headers:
            data["hide_headers"] = self.hide_headers

        if self.hide_footers:
            data["hide_footers"] = self.hide_footers

        if self.page_header_suffix is not None:
            data["page_header_suffix"] = self.page_header_suffix

        if self.page_header_prefix is not None:
            data["page_header_prefix"] = self.page_header_prefix

        if self.page_footer_suffix is not None:
            data["page_footer_suffix"] = self.page_footer_suffix

        if self.page_footer_prefix is not None:
            data["page_footer_prefix"] = self.page_footer_prefix

        # only send page separator to server if it is not None
        # as if a null, "" string is sent the server will then ignore the page separator instead of using the default
        if self.page_separator is not None:
            data["page_separator"] = self.page_separator

        if self.page_suffix is not None:
            data["page_suffix"] = self.page_suffix

        if self.parsing_instruction:
            print(
                "WARNING: parsing_instruction is deprecated. Use system_prompt, system_prompt_append or user_prompt instead."
            )
            data["parsing_instruction"] = self.parsing_instruction

        if self.parse_mode:
            data["parse_mode"] = self.parse_mode

        if self.premium_mode:
            data["premium_mode"] = self.premium_mode

        if self.preserve_layout_alignment_across_pages:
            data[
                "preserve_layout_alignment_across_pages"
            ] = self.preserve_layout_alignment_across_pages

        if self.preserve_very_small_text:
            data["preserve_very_small_text"] = self.preserve_very_small_text

        if self.presentation_out_of_bounds_content:
            data[
                "presentation_out_of_bounds_content"
            ] = self.presentation_out_of_bounds_content

        if self.preset is not None:
            data["preset"] = self.preset

        if self.precise_bounding_box:
            data["precise_bounding_box"] = self.precise_bounding_box

        if self.replace_failed_page_mode is not None:
            data["replace_failed_page_mode"] = self.replace_failed_page_mode.value

        if self.replace_failed_page_with_error_message_prefix is not None:
            data[
                "replace_failed_page_with_error_message_prefix"
            ] = self.replace_failed_page_with_error_message_prefix

        if self.replace_failed_page_with_error_message_suffix is not None:
            data[
                "replace_failed_page_with_error_message_suffix"
            ] = self.replace_failed_page_with_error_message_suffix

        if self.remove_hidden_text:
            data["remove_hidden_text"] = self.remove_hidden_text

        data["save_images"] = self.save_images

        if self.skip_diagonal_text:
            data["skip_diagonal_text"] = self.skip_diagonal_text

        if self.spreadsheet_extract_sub_tables:
            data["spreadsheet_extract_sub_tables"] = self.spreadsheet_extract_sub_tables

        if self.spreadsheet_force_formula_computation:
            data[
                "spreadsheet_force_formula_computation"
            ] = self.spreadsheet_force_formula_computation

        if self.specialized_chart_parsing_agentic:
            data[
                "specialized_chart_parsing_agentic"
            ] = self.specialized_chart_parsing_agentic

        if self.specialized_chart_parsing_efficient:
            data[
                "specialized_chart_parsing_efficient"
            ] = self.specialized_chart_parsing_efficient

        if self.specialized_chart_parsing_plus:
            data["specialized_chart_parsing_plus"] = self.specialized_chart_parsing_plus

        if self.specialized_image_parsing:
            data["specialized_image_parsing"] = self.specialized_image_parsing

        if self.strict_mode_buggy_font:
            data["strict_mode_buggy_font"] = self.strict_mode_buggy_font

        if self.strict_mode_image_extraction:
            data["strict_mode_image_extraction"] = self.strict_mode_image_extraction

        if self.strict_mode_image_ocr:
            data["strict_mode_image_ocr"] = self.strict_mode_image_ocr

        if self.strict_mode_reconstruction:
            data["strict_mode_reconstruction"] = self.strict_mode_reconstruction

        if self.structured_output:
            data["structured_output"] = self.structured_output

        if self.structured_output_json_schema is not None:
            data["structured_output_json_schema"] = self.structured_output_json_schema

        if self.structured_output_json_schema_name is not None:
            data[
                "structured_output_json_schema_name"
            ] = self.structured_output_json_schema_name
        if self.system_prompt is not None:
            data["system_prompt"] = self.system_prompt
        if self.system_prompt_append is not None:
            data["system_prompt_append"] = self.system_prompt_append
        if self.take_screenshot:
            data["take_screenshot"] = self.take_screenshot

        if partition_target_pages is not None:
            data["target_pages"] = partition_target_pages
        elif self.target_pages is not None:
            data["target_pages"] = self.target_pages
        if self.user_prompt is not None:
            data["user_prompt"] = self.user_prompt
        if self.use_vendor_multimodal_model:
            data["use_vendor_multimodal_model"] = self.use_vendor_multimodal_model

        if self.vendor_multimodal_api_key is not None:
            data["vendor_multimodal_api_key"] = self.vendor_multimodal_api_key

        if self.vendor_multimodal_model_name is not None:
            data["vendor_multimodal_model_name"] = self.vendor_multimodal_model_name

        if self.model is not None:
            data["model"] = self.model

        if self.webhook_url is not None:
            data["webhook_url"] = self.webhook_url

        if self.markdown_table_multiline_header_separator is not None:
            data[
                "markdown_table_multiline_header_separator"
            ] = self.markdown_table_multiline_header_separator

        if self.extract_printed_page_number is not None:
            data["extract_printed_page_number"] = self.extract_printed_page_number

        if self.line_level_bounding_box is not None:
            data["line_level_bounding_box"] = self.line_level_bounding_box

        if self.tier is not None:
            data["tier"] = self.tier

        if self.version is not None:
            data["version"] = self.version

        # Deprecated
        if self.bounding_box is not None:
            data["bounding_box"] = self.bounding_box

        if self.gpt4o_mode:
            data["gpt4o_mode"] = self.gpt4o_mode

        if self.gpt4o_api_key is not None:
            data["gpt4o_api_key"] = self.gpt4o_api_key

        try:
            url = build_url(JOB_UPLOAD_ROUTE, self.organization_id, self.project_id)
            resp = await make_api_request(self.aclient, "POST", url, timeout=self.max_timeout, files=files, data=data)  # type: ignore
            resp.raise_for_status()  # this raises if status is not 2xx
            return resp.json()["id"]
        except httpx.HTTPStatusError as err:  # this catches it
            msg = f"Failed to parse the file: {err.response.text}"
            raise Exception(msg) from err  # this preserves the exception context
        finally:
            if file_handle is not None:
                file_handle.close()

    def _calculate_backoff(self, current_interval: float) -> float:
        """Calculate the next backoff interval based on the backoff pattern.

        Args:
            current_interval: The current interval in seconds

        Returns:
            The next interval in seconds
        """
        if self.backoff_pattern == BackoffPattern.CONSTANT:
            return current_interval
        elif self.backoff_pattern == BackoffPattern.LINEAR:
            return min(current_interval + 1, float(self.max_check_interval))
        elif self.backoff_pattern == BackoffPattern.EXPONENTIAL:
            return min(current_interval * 2, float(self.max_check_interval))
        return current_interval  # Default fallback

    async def _get_job_result(
        self, job_id: str, result_type: str, verbose: bool = False
    ) -> Dict[str, Any]:
        start = time.time()
        tries = 0
        error_count = 0
        current_interval: float = float(self.check_interval)

        # so we're not re-setting the headers & stuff on each
        # usage... assume that there is not some other
        # coro also modifying base_url and the other client related configs.
        client = self.aclient
        while True:
            try:
                await asyncio.sleep(current_interval)
                tries += 1
                result = await client.get(JOB_STATUS_ROUTE.format(job_id=job_id))
                result.raise_for_status()  # this raises if status is not 2xx
                # Allowed values "PENDING", "SUCCESS", "ERROR", "CANCELED"
                result_json = result.json()
                status = result_json["status"]
                if status == "SUCCESS":
                    parsed_result = await client.get(
                        JOB_RESULT_URL.format(job_id=job_id, result_type=result_type),
                    )
                    return parsed_result.json()
                elif status == "PENDING":
                    end = time.time()
                    if end - start > self.max_timeout:
                        raise Exception(f"Timeout while parsing the file: {job_id}")
                    if verbose and tries % 10 == 0:
                        print(".", end="", flush=True)
                    current_interval = self._calculate_backoff(current_interval)
                else:
                    raise JobFailedException.from_result(result_json)
            except (
                httpx.ConnectError,
                httpx.ReadError,
                httpx.WriteError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.HTTPStatusError,
                httpx.RemoteProtocolError,
            ) as err:
                error_count += 1
                end = time.time()
                if end - start > self.max_timeout:
                    raise Exception(
                        f"Timeout while parsing the file: {job_id}"
                    ) from err
                if verbose and tries % 10 == 0:
                    print(
                        f"HTTP error: {err}...",
                        flush=True,
                    )
                current_interval = self._calculate_backoff(current_interval)

    async def _get_job_result_with_error_handling(
        self, job_id: str, result_type: str, verbose: bool = False
    ) -> Dict[str, Any]:
        """Get job result with error handling based on ignore_errors setting."""
        try:
            return await self._get_job_result(job_id, result_type, verbose=verbose)
        except JobFailedException as e:
            if self.ignore_errors:
                # Return error information when ignore_errors is True
                return {
                    "pages": [],
                    "job_metadata": {},
                    "error": f"{e.status}: {e.error_message or 'No error message'}",
                    "error_code": e.error_code,
                    "status": e.status,
                }
            else:
                raise e

    async def _parse_one(
        self,
        file_path: FileInput,
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
        result_type: Optional[str] = None,
        num_workers: Optional[int] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        if self.partition_pages is None:
            job_results = [
                await self._parse_one_unpartitioned(
                    file_path,
                    extra_info=extra_info,
                    fs=fs,
                    result_type=result_type,
                )
            ]
        else:
            job_results = await self._parse_one_partitioned(
                file_path,
                extra_info,
                fs=fs,
                result_type=result_type,
                num_workers=num_workers,
            )
        return job_results

    async def _parse_one_unpartitioned(
        self,
        file_path: FileInput,
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
        result_type: Optional[str] = None,
        **create_kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """Create one parse job and wait for the result."""
        job_id = await self._create_job(
            file_path, extra_info=extra_info, fs=fs, **create_kwargs
        )
        if self.verbose:
            print("Started parsing the file under job_id %s" % job_id)
        result = await self._get_job_result_with_error_handling(
            job_id, result_type or self.result_type.value, verbose=self.verbose
        )
        return job_id, result

    async def _parse_one_partitioned(
        self,
        file_path: FileInput,
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
        result_type: Optional[str] = None,
        num_workers: Optional[int] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Partition a file and run separate parse jobs per partition segment."""
        assert self.partition_pages is not None

        num_workers = num_workers or self.num_workers
        if num_workers < 1:
            raise ValueError("Invalid number of workers")
        if self.target_pages is not None:
            jobs = [
                self._parse_one_unpartitioned(
                    file_path,
                    extra_info=extra_info,
                    fs=fs,
                    result_type=result_type,
                    partition_target_pages=target_pages,
                )
                for target_pages in partition_pages(
                    expand_target_pages(self.target_pages),
                    self.partition_pages,
                    max_pages=self.max_pages,
                )
            ]
            return await run_jobs(
                jobs,
                workers=num_workers,
                desc="Getting job results",
                show_progress=self.show_progress,
            )

        total = 0
        results: List[Tuple[str, Dict[str, Any]]] = []
        while self.max_pages is None or total < self.max_pages:
            if (
                self.max_pages is not None
                and total + self.partition_pages >= self.max_pages
            ):
                size = self.max_pages - total
            else:
                size = self.partition_pages
            if not size:
                break
            try:
                # Fetch JSON result type first to get accurate pagination data
                # and then fetch the user's desired result type if needed
                job_id, json_result = await self._parse_one_unpartitioned(
                    file_path,
                    extra_info=extra_info,
                    fs=fs,
                    result_type=ResultType.JSON.value,
                    partition_target_pages=f"{total}-{total + size - 1}",
                )
                # Check if the result is an error result (when ignore_errors=True)
                if json_result.get("error_code") == "NO_DATA_FOUND_IN_FILE":
                    raise JobFailedException(
                        job_id=job_id,
                        status=json_result.get("status", "ERROR"),
                        error_code=json_result.get("error_code"),
                        error_message=json_result.get("error"),
                    )

                result_type = result_type or self.result_type.value
                if result_type == ResultType.JSON.value:
                    job_result = json_result
                else:
                    job_result = await self._get_job_result(
                        job_id, result_type, verbose=self.verbose
                    )
            except JobFailedException as e:
                if results and e.error_code == "NO_DATA_FOUND_IN_FILE":
                    # Expected when we try to read past the end of the file
                    return results
                raise
            results.append((job_id, job_result))
            if len(json_result["pages"]) < size:
                break
            total += size
        return results

    async def _aload_data(
        self,
        file_path: FileInput,
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
        verbose: bool = False,
        num_workers: Optional[int] = None,
    ) -> List[Document]:
        """Load data from the input path."""
        try:
            results = [
                job_result
                for _, job_result in await self._parse_one(
                    file_path, extra_info, fs=fs, num_workers=num_workers
                )
            ]
            # Flatten the resulting doc if it was partitioned
            separator = self.page_separator or _DEFAULT_SEPARATOR
            docs = [
                Document(
                    text=separator.join(
                        result[self.result_type.value] for result in results
                    ),
                    metadata=extra_info or {},
                )
            ]
            if self.split_by_page:
                return self._get_sub_docs(docs)
            else:
                return docs

        except Exception as e:
            file_repr = file_path if isinstance(file_path, str) else "<bytes/buffer>"
            print(f"Error while parsing the file '{file_repr}':", e)
            if self.ignore_errors:
                return []
            else:
                raise e

    async def aload_data(
        self,
        file_path: Union[List[FileInput], FileInput],
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """Load data from the input path.

        File(s) which were partitioned before parsing will be loaded as a single
        re-assembled Document.
        """
        if isinstance(file_path, (str, PurePosixPath, Path, bytes, BufferedIOBase)):
            return await self._aload_data(
                file_path, extra_info=extra_info, fs=fs, verbose=self.verbose
            )
        elif isinstance(file_path, list):
            jobs = [
                self._aload_data(
                    f,
                    extra_info=extra_info,
                    fs=fs,
                    verbose=self.verbose and not self.show_progress,
                    num_workers=1,
                )
                for f in file_path
            ]
            try:
                results = await run_jobs(
                    jobs,
                    workers=self.num_workers,
                    desc="Parsing files",
                    show_progress=self.show_progress,
                )

                # return flattened results
                return [item for sublist in results for item in sublist]
            except RuntimeError as e:
                if nest_asyncio_err in str(e):
                    raise RuntimeError(nest_asyncio_msg)
                else:
                    raise e
        else:
            raise ValueError(
                "The input file_path must be a string or a list of strings."
            )

    def load_data(
        self,
        file_path: Union[List[FileInput], FileInput],
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """Load data from the input path."""
        try:
            return asyncio_run(self.aload_data(file_path, extra_info, fs=fs))
        except RuntimeError as e:
            if nest_asyncio_err in str(e):
                raise RuntimeError(nest_asyncio_msg)
            else:
                raise e

    async def _aparse_one(
        self,
        file_path: FileInput,
        file_name: str,
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
        num_workers: Optional[int] = None,
    ) -> List[JobResult]:
        job_results = await self._parse_one(
            file_path,
            extra_info,
            fs=fs,
            result_type=ResultType.JSON.value,
            num_workers=num_workers,
        )
        return [
            JobResult(
                job_id=job_id,
                file_name=file_name,
                job_result=job_result,
                api_key=self.api_key,
                base_url=self.base_url,
                client=self.aclient,
                page_separator=self.page_separator or _DEFAULT_SEPARATOR,
            )
            for job_id, job_result in job_results
        ]

    async def aparse(
        self,
        file_path: Union[List[FileInput], FileInput],
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> Union[List["JobResult"], "JobResult"]:
        """
        Parse the file and return a JobResult object instead of Document objects.

        This method is similar to aload_data but returns JobResult objects that provide
        direct access to the various output formats (text, markdown, json, etc.)

        Args:
            file_path: Path to the file to parse. Can be a string, path, bytes, file-like object, or a list of these.
            extra_info: Additional metadata to include in the result.
            fs: Optional filesystem to use for reading files.

        Returns:
            JobResult object or list of JobResult objects if either multiple files were provided or file(s) were partitioned before parsing.
        """

        if isinstance(file_path, (str, PurePosixPath, Path, bytes, BufferedIOBase)):
            if isinstance(file_path, (bytes, BufferedIOBase)):
                if not extra_info or "file_name" not in extra_info:
                    raise ValueError(
                        "file_name must be provided in extra_info when passing bytes"
                    )
                file_name = extra_info["file_name"]
            else:
                file_name = str(file_path)
            result = await self._aparse_one(
                file_path, file_name, extra_info=extra_info, fs=fs
            )
            return result[0] if len(result) == 1 else result

        elif isinstance(file_path, list):
            file_names = []
            for f in file_path:
                if isinstance(f, (bytes, BufferedIOBase)):
                    if not extra_info or "file_name" not in extra_info:
                        raise ValueError(
                            "file_name must be provided in extra_info when passing bytes"
                        )
                    file_names.append(extra_info["file_name"])
                else:
                    file_names.append(str(f))

            job_results = []
            try:
                for result in await run_jobs(
                    [
                        self._aparse_one(
                            f,
                            file_names[i],
                            extra_info=extra_info,
                            fs=fs,
                            num_workers=1,
                        )
                        for i, f in enumerate(file_path)
                    ],
                    workers=self.num_workers,
                    desc="Getting job results",
                    show_progress=self.show_progress,
                ):
                    job_results.extend(result)
                return job_results

            except RuntimeError as e:
                if nest_asyncio_err in str(e):
                    raise RuntimeError(nest_asyncio_msg)
                else:
                    raise e
        else:
            raise ValueError(
                "The input file_path must be a string or a list of strings."
            )

    def parse(
        self,
        file_path: Union[List[FileInput], FileInput],
        extra_info: Optional[dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> Union[List["JobResult"], "JobResult"]:
        """
        Parse the file and return a JobResult object instead of Document objects.

        This method is similar to load_data but returns JobResult objects that provide
        direct access to the various output formats (text, markdown, json, etc.)

        Args:
            file_path: Path to the file to parse. Can be a string, path, bytes, file-like object, or a list of these.
            extra_info: Additional metadata to include in the result.
            fs: Optional filesystem to use for reading files.

        Returns:
            JobResult object or list of JobResult objects if multiple files were provided
        """
        try:
            return asyncio_run(self.aparse(file_path, extra_info, fs=fs))
        except RuntimeError as e:
            if nest_asyncio_err in str(e):
                raise RuntimeError(nest_asyncio_msg)
            else:
                raise e

    async def _aget_json(
        self,
        file_path: FileInput,
        extra_info: Optional[dict] = None,
        num_workers: Optional[int] = None,
    ) -> List[dict]:
        """Load data from the input path."""
        try:
            job_results = await self._parse_one(
                file_path,
                extra_info=extra_info,
                result_type=ResultType.JSON.value,
                num_workers=num_workers,
            )

            results = []
            for job_id, job_result in job_results:
                job_result["job_id"] = job_id
                if not isinstance(file_path, (bytes, BufferedIOBase)):
                    job_result["file_path"] = str(file_path)
                results.append(job_result)
            return results
        except Exception as e:
            file_repr = file_path if isinstance(file_path, str) else "<bytes/buffer>"
            print(f"Error while parsing the file '{file_repr}':", e)
            if self.ignore_errors:
                return []
            else:
                raise e

    async def aget_json(
        self,
        file_path: Union[List[FileInput], FileInput],
        extra_info: Optional[dict] = None,
    ) -> List[dict]:
        """Load data from the input path."""
        if isinstance(file_path, (str, PurePosixPath, Path, bytes, BufferedIOBase)):
            return await self._aget_json(file_path, extra_info=extra_info)
        elif isinstance(file_path, list):
            jobs = [self._aget_json(f, extra_info=extra_info) for f in file_path]
            try:
                results = await run_jobs(
                    jobs,
                    workers=self.num_workers,
                    desc="Parsing files",
                    show_progress=self.show_progress,
                )

                # return flattened results
                return [item for sublist in results for item in sublist]
            except RuntimeError as e:
                if nest_asyncio_err in str(e):
                    raise RuntimeError(nest_asyncio_msg)
                else:
                    raise e
        else:
            raise ValueError(
                "The input file_path must be a string, Path, bytes, BufferedIOBase, or a list of these types."
            )

    def get_json_result(
        self,
        file_path: Union[List[FileInput], FileInput],
        extra_info: Optional[dict] = None,
    ) -> List[dict]:
        """Parse the input path."""
        try:
            return asyncio_run(self.aget_json(file_path, extra_info))
        except RuntimeError as e:
            if nest_asyncio_err in str(e):
                raise RuntimeError(nest_asyncio_msg)
            else:
                raise e

    def get_json(
        self,
        file_path: Union[List[FileInput], FileInput],
        extra_info: Optional[dict] = None,
    ) -> List[dict]:
        """Load data from the input path."""
        return self.get_json_result(file_path, extra_info)

    async def aget_assets(
        self, json_result: List[dict], download_path: str, asset_key: str
    ) -> List[dict]:
        """Download assets (images or charts) from the parsed result."""
        await self._check_for_updates()
        # Make the download path
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        client = self.aclient
        try:
            assets = []
            for result in json_result:
                job_id = result["job_id"]
                for page in result["pages"]:
                    if self.verbose:
                        print(
                            f"> {asset_key.capitalize()} for page {page['page']}: {page[asset_key]}"
                        )
                    for asset in page[asset_key]:
                        asset_name = asset["name"]

                        # Get the full path
                        asset_path = os.path.join(
                            download_path, f"{job_id}-{asset_name}"
                        )

                        # Get a valid asset path
                        if not asset_path.endswith(".png"):
                            if not asset_path.endswith(".jpg"):
                                asset_path += ".png"

                        asset["path"] = asset_path
                        asset["job_id"] = job_id
                        asset["original_file_path"] = result.get("file_path", None)
                        asset["page_number"] = page["page"]

                        with open(asset_path, "wb") as f:
                            asset_url = f"{self.base_url}/api/parsing/job/{job_id}/result/image/{asset_name}"
                            resp = await make_api_request(
                                client, "GET", asset_url, timeout=self.max_timeout
                            )
                            resp.raise_for_status()
                            f.write(resp.content)
                        assets.append(asset)
            return assets
        except Exception as e:
            print(f"Error while downloading {asset_key} from the parsed result:", e)
            if self.ignore_errors:
                return []
            else:
                raise e

    async def aget_images(
        self, json_result: List[dict], download_path: str
    ) -> List[dict]:
        """Download images from the parsed result."""
        try:
            return await self.aget_assets(json_result, download_path, "images")
        except Exception as e:
            print("Error while downloading images:", e)
            if self.ignore_errors:
                return []
            else:
                raise e

    async def aget_charts(
        self, json_result: List[dict], download_path: str
    ) -> List[dict]:
        """Download charts from the parsed result."""
        try:
            return await self.aget_assets(json_result, download_path, "charts")
        except Exception as e:
            print("Error while downloading charts:", e)
            if self.ignore_errors:
                return []
            else:
                raise e

    def get_images(self, json_result: List[dict], download_path: str) -> List[dict]:
        """Download images from the parsed result."""
        try:
            return asyncio_run(self.aget_images(json_result, download_path))
        except RuntimeError as e:
            if nest_asyncio_err in str(e):
                raise RuntimeError(nest_asyncio_msg)
            else:
                raise e

    def get_charts(self, json_result: List[dict], download_path: str) -> List[dict]:
        """Download charts from the parsed result."""
        try:
            return asyncio_run(self.aget_charts(json_result, download_path))
        except RuntimeError as e:
            if nest_asyncio_err in str(e):
                raise RuntimeError(nest_asyncio_msg)
            else:
                raise e

    def get_tables(self, json_results: List[dict], download_path: str) -> List[str]:
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        return extract_tables_from_json_results(json_results, download_path)

    async def aget_tables(
        self, json_result: List[dict], download_path: str
    ) -> List[str]:
        return await asyncio.to_thread(self.get_tables, json_result, download_path)

    async def aget_xlsx(
        self, json_result: List[dict], download_path: str
    ) -> List[dict]:
        """Download xlsx from the parsed result."""
        await self._check_for_updates()
        # make the download path
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        client = self.aclient
        try:
            xlsx_list = []
            for result in json_result:
                job_id = result["job_id"]
                if self.verbose:
                    print("> XLSX")

                xlsx_path = os.path.join(download_path, f"{job_id}.xlsx")

                xlsx = {}

                xlsx["path"] = xlsx_path
                xlsx["job_id"] = job_id
                xlsx["original_file_path"] = result.get("file_path", None)

                with open(xlsx_path, "wb") as f:
                    xlsx_url = (
                        f"{self.base_url}/api/parsing/job/{job_id}/result/raw/xlsx"
                    )
                    res = await make_api_request(
                        client, "GET", xlsx_url, timeout=self.max_timeout
                    )
                    res.raise_for_status()
                    f.write(res.content)
                xlsx_list.append(xlsx)
            return xlsx_list

        except Exception as e:
            print("Error while downloading xlsx:", e)
            if self.ignore_errors:
                return []
            else:
                raise e

    def get_xlsx(self, json_result: List[dict], download_path: str) -> List[dict]:
        """Download xlsx from the parsed result."""
        try:
            return asyncio_run(self.aget_xlsx(json_result, download_path))
        except RuntimeError as e:
            if nest_asyncio_err in str(e):
                raise RuntimeError(nest_asyncio_msg)
            else:
                raise e

    def _get_sub_docs(self, docs: List[Document]) -> List[Document]:
        """Split docs into pages, by separator."""
        sub_docs = []
        separator = self.page_separator or _DEFAULT_SEPARATOR
        for doc in docs:
            doc_chunks = doc.text.split(separator)
            for doc_chunk in doc_chunks:
                sub_doc = Document(
                    text=doc_chunk,
                    metadata=deepcopy(doc.metadata),
                )
                sub_docs.append(sub_doc)

        return sub_docs

    async def aget_result(
        self, job_id: Union[str, List[str]]
    ) -> Union[JobResult, List[JobResult]]:
        """
        Return JobResult object for previously parsed job(s).

        If the job is still pending, the result will not be returned until it is completed.

        Args:
            job_id: Job ID or list of multiple Job IDs to be retrieved.

        Returns:
            JobResult object or list of JobResult objects if multiple job IDs were provided.
        """
        if isinstance(job_id, str):
            result = await self._get_job_result_with_error_handling(
                job_id, ResultType.JSON.value, verbose=self.verbose
            )
            return JobResult(
                job_id=job_id,
                file_name="",
                job_result=result,
                api_key=self.api_key,
                base_url=self.base_url,
                client=self.aclient,
                page_separator=self.page_separator or _DEFAULT_SEPARATOR,
            )
        elif isinstance(job_id, list):
            results = []
            jobs = [
                self._get_job_result_with_error_handling(
                    id_, ResultType.JSON.value, verbose=self.verbose
                )
                for id_ in job_id
            ]
            results = await run_jobs(
                jobs,
                workers=self.num_workers,
                desc="Getting job results",
                show_progress=self.show_progress,
            )
            return [
                JobResult(
                    job_id=job_id[i],
                    file_name="",
                    job_result=result,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    client=self.aclient,
                    page_separator=self.page_separator or _DEFAULT_SEPARATOR,
                )
                for i, result in enumerate(results)
            ]
        else:
            raise ValueError("The input job_id must be a string or a list of strings.")

    def get_result(
        self, job_id: Union[str, List[str]]
    ) -> Union[JobResult, List[JobResult]]:
        """
        Return JobResult object for previously parsed job(s).

        If the job is still pending, the result will not be returned until it is completed.

        Args:
            job_id: Job ID or list of multiple Job IDs to be retrieved.

        Returns:
            JobResult object or list of JobResult objects if multiple job IDs were provided.
        """
        try:
            return asyncio_run(self.aget_result(job_id))
        except RuntimeError as e:
            if nest_asyncio_err in str(e):
                raise RuntimeError(nest_asyncio_msg)
            else:
                raise e
