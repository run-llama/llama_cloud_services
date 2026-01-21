import httpx
import os
import re
from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny, model_validator
from typing import Dict, Any, List, Optional, get_origin, get_args

from llama_cloud_services.parse.utils import (
    make_api_request,
    is_jupyter,
)
from llama_index.core.async_utils import asyncio_run
from llama_index.core.schema import Document, ImageDocument, ImageNode, TextNode

PAGE_REGEX = r"page[-_](\d+)\.jpg$"

SAFE_MODEL_CONFIGS = ConfigDict(
    extra="allow",
    validate_assignment=False,
    arbitrary_types_allowed=True,
    validate_default=False,
)


class SafeBaseModel(BaseModel):
    """Base model that gracefully handles None values from unstable backend responses."""

    model_config = SAFE_MODEL_CONFIGS

    @model_validator(mode="before")
    @classmethod
    def coerce_none_to_defaults(cls, data: Any) -> Any:
        """
        Replace None values with appropriate defaults based on field type annotations.
        This prevents validation errors when the backend returns None for non-optional fields.
        """
        if not isinstance(data, dict):
            return data

        # Process each field that has a None value
        result = {}
        for key, value in data.items():
            if value is not None or key not in cls.model_fields:
                result[key] = value
                continue

            # Value is None and field exists in model
            field_info = cls.model_fields[key]

            # If field has a default or default_factory, let Pydantic handle it
            from pydantic_core import PydanticUndefined

            if (
                field_info.default is not PydanticUndefined
                or field_info.default_factory is not None
            ):
                continue

            # Otherwise, provide a sensible default based on the type annotation
            annotation = field_info.annotation
            origin = get_origin(annotation)

            # Handle List types
            if origin is list:
                result[key] = []
            # Handle Dict types
            elif origin is dict:
                result[key] = {}
            # Handle basic types
            elif annotation == str or (origin and str in get_args(annotation)):
                result[key] = ""
            elif annotation == int or (origin and int in get_args(annotation)):
                result[key] = 0
            elif annotation == float or (origin and float in get_args(annotation)):
                result[key] = 0.0
            elif annotation == bool or (origin and bool in get_args(annotation)):
                result[key] = False
            # If we can't determine a safe default, skip (let Pydantic try)
            else:
                result[key] = value

        return result


class JobMetadata(SafeBaseModel):
    """Metadata about the job."""

    job_pages: int = Field(default=0, description="The number of pages in the job.")
    job_auto_mode_triggered_pages: Optional[int] = Field(
        default=None,
        description="The number of pages that triggered auto mode (thus increasing the cost).",
    )
    job_is_cache_hit: bool = Field(
        default=False, description="Whether the job was a cache hit."
    )


class BBox(SafeBaseModel):
    """A bounding box."""

    x: Optional[float] = Field(
        default=None,
        description="The x-coordinate of the bounding box.",
    )
    y: Optional[float] = Field(
        default=None,
        description="The y-coordinate of the bounding box.",
    )
    w: Optional[float] = Field(
        default=None,
        description="The width of the bounding box.",
    )
    h: Optional[float] = Field(
        default=None,
        description="The height of the bounding box.",
    )


class LineLevelBboxItem(SafeBaseModel):
    """A line-level bounding box item."""

    md: Optional[str] = Field(
        default=None, description="The markdown-formatted content of the line."
    )
    text: Optional[str] = Field(
        default=None, description="The text content of the line."
    )
    bBox: Optional[BBox] = Field(
        default=None, description="The bounding box of the line."
    )
    startIndex: Optional[int] = Field(
        default=None, description="The start index of the line in the page text."
    )
    endIndex: Optional[int] = Field(
        default=None, description="The end index of the line in the page text."
    )


class PageItem(SafeBaseModel):
    """An item in a page."""

    type: str = Field(default="", description="The type of the item.")
    lvl: Optional[int] = Field(
        default=None, description="The level of indentation of the item."
    )
    value: Optional[str] = Field(
        default=None, description="The text content of the item."
    )
    md: Optional[str] = Field(
        default=None, description="The markdown-formatted content of the item."
    )
    rows: Optional[List[List[Any]]] = Field(
        default=None, description="The rows of the item."
    )
    bBox: Optional[BBox] = Field(
        default=None, description="The bounding box of the item."
    )
    html: Optional[str] = Field(
        default=None,
        description="The HTML-formatted content of the item. Only applicable for table items when output_tables_as_HTML=True.",
    )
    lines: Optional[List[LineLevelBboxItem]] = Field(
        default=None, description="The line-level bounding box items of the item."
    )


class ImageItem(SafeBaseModel):
    """An image in a page."""

    name: str = Field(default="", description="The name of the image.")
    height: Optional[float] = Field(
        default=None, description="The height of the image."
    )
    width: Optional[float] = Field(default=None, description="The width of the image.")
    x: Optional[float] = Field(
        default=None, description="The x-coordinate of the image."
    )
    y: Optional[float] = Field(
        default=None, description="The y-coordinate of the image."
    )
    original_width: Optional[int] = Field(
        default=None, description="The original width of the image."
    )
    original_height: Optional[int] = Field(
        default=None, description="The original height of the image."
    )
    type: Optional[str] = Field(default=None, description="The type of the image.")


class LayoutItem(SafeBaseModel):
    """The layout of a page."""

    image: str = Field(
        default="", description="The name of the image containing the layout item"
    )
    confidence: float = Field(
        default=0.0, description="The confidence of the layout item."
    )
    label: str = Field(default="", description="The label of the layout item.")
    bbox: Optional[BBox] = Field(
        default=None, description="The bounding box of the layout item."
    )
    isLikelyNoise: bool = Field(
        default=False, description="Whether the layout item is likely noise."
    )


class ChartItem(SafeBaseModel):
    """A chart in a page."""

    name: str = Field(default="", description="The name of the chart.")
    x: Optional[float] = Field(
        default=None, description="The x-coordinate of the chart."
    )
    y: Optional[float] = Field(
        default=None, description="The y-coordinate of the chart."
    )
    width: Optional[float] = Field(default=None, description="The width of the chart.")
    height: Optional[float] = Field(
        default=None, description="The height of the chart."
    )


class Page(SafeBaseModel):
    """A page of the document."""

    page: int = Field(default=0, description="The page number.")
    text: Optional[str] = Field(default=None, description="The text of the page.")
    md: Optional[str] = Field(default=None, description="The markdown of the page.")
    images: List[ImageItem] = Field(
        default_factory=list,
        description="The names of the image IDs in the page, including both objects and page screenshots.",
    )
    charts: List[ChartItem] = Field(
        default_factory=list, description="The charts in the page."
    )
    tables: List[str] = Field(
        default_factory=list, description="The names of the table IDs in the page."
    )
    layout: List[LayoutItem] = Field(
        default_factory=list, description="The layout of the page."
    )
    items: List[PageItem] = Field(
        default_factory=list, description="The items in the page."
    )
    status: Optional[str] = Field(default=None, description="The status of the page.")
    links: List[SerializeAsAny[Any]] = Field(
        default_factory=list, description="The links in the page."
    )
    width: Optional[float] = Field(default=None, description="The width of the page.")
    height: Optional[float] = Field(default=None, description="The height of the page.")
    triggeredAutoMode: Optional[bool] = Field(
        default=False,
        description="Whether the page triggered auto mode (thus increasing the cost).",
    )
    parsingMode: str = Field(
        default="", description="The parsing mode used for the page."
    )
    structuredData: Optional[Dict[str, Any]] = Field(
        default=None, description="The structured data of the page."
    )
    noStructuredContent: bool = Field(
        default=True, description="Whether the page has no structured data."
    )
    noTextContent: bool = Field(
        default=False, description="Whether the page has no text content."
    )
    isAudioTranscript: bool = Field(
        default=False, description="Whether the page is an audio transcript."
    )
    durationInSeconds: Optional[float] = Field(
        default=None, description="The duration of the audio transcript in seconds."
    )
    slideSpeakerNotes: Optional[str] = Field(
        default=None, description="The speaker notes for the slide."
    )
    confidence: Optional[float] = Field(
        default=None, description="The confidence of the page parsing."
    )
    printedPageNumber: Optional[str] = Field(
        default=None,
        description="The printed page number on the page, if found and extractPrintedPageNumber is set to true.",
    )
    pageHeaderMarkdown: Optional[str] = Field(
        default=None, description="The page header in markdown format."
    )
    pageFooterMarkdown: Optional[str] = Field(
        default=None, description="The page footer in markdown format."
    )


class JobResult(SafeBaseModel):
    """The raw JSON result from the LlamaParse API."""

    pages: List[Page] = Field(
        default_factory=list, description="The pages of the document."
    )
    job_metadata: JobMetadata = Field(
        default_factory=JobMetadata, description="The metadata of the job."
    )
    file_name: str = Field(
        default="", description="The path to the file that was parsed."
    )
    job_id: str = Field(default="", description="The ID of the job.")
    is_done: bool = Field(default=False, description="Whether the job is done.")
    error: Optional[str] = Field(
        default=None, description="The error message if the job failed."
    )
    error_code: Optional[str] = Field(
        default=None, description="The error code if the job failed."
    )
    status: Optional[str] = Field(
        default=None,
        description="The job status (e.g., PENDING, SUCCESS, ERROR, CANCELED).",
    )

    def __init__(
        self,
        job_id: str,
        file_name: str,
        job_result: Dict[str, Any],
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        page_separator: str = "\n\n",
    ):
        """
        Initialize JobResult with job_id and job_result.

        Args:
            job_id: The job ID of the parsing task
            job_result: The JSON response from the parsing job or a JobResult instance (optional)
            api_key: The API key for the LlamaParse API
            base_url: The base URL of the Llama Parsing API
            page_separator: The separator that was used to define page splits in the result
        """
        super().__init__(job_id=job_id, file_name=file_name, **job_result)

        self._api_key = api_key or os.environ.get("LLAMA_CLOUD_API_KEY", "")
        self._base_url = base_url or os.environ.get(
            "LLAMA_CLOUD_BASE_URL", "https://api.llama-parse.ai"
        )
        self._client = client or httpx.AsyncClient()
        self._client.base_url = self._base_url
        self._client.headers["Authorization"] = f"Bearer {self._api_key}"
        self._page_separator = page_separator

    def get_text_documents(self, split_by_page: bool = False) -> List[Document]:
        """
        Get the documents from the job.

        Args:
            split_by_page: Whether to split the pages into separate documents
        """
        if split_by_page:
            return [
                Document(
                    text=page.text,
                    metadata={"page_number": page.page, "file_name": self.file_name},
                )
                for page in self.pages
            ]
        else:
            text = self._page_separator.join(
                [page.text if page.text is not None else "" for page in self.pages]
            )
            return [Document(text=text, metadata={"file_name": self.file_name})]

    async def aget_text_documents(self, split_by_page: bool = False) -> List[Document]:
        """
        Get the documents from the job.

        Args:
            split_by_page: Whether to split the pages into separate documents
        """
        # No async needed, but here for consistency
        return self.get_text_documents(split_by_page)

    def get_text_nodes(self, split_by_page: bool = False) -> List[TextNode]:
        """
        Get the text nodes from the job.
        """
        documents = self.get_text_documents(split_by_page)
        return [TextNode(text=doc.text, metadata=doc.metadata) for doc in documents]

    async def aget_text_nodes(self, split_by_page: bool = False) -> List[TextNode]:
        """
        Get the text nodes from the job.
        """
        documents = await self.aget_text_documents(split_by_page)
        return [TextNode(text=doc.text, metadata=doc.metadata) for doc in documents]

    def _format_markdown_for_notebook(self, text: Optional[str]) -> Optional[str]:
        """Format markdown text for Jupyter notebook display by escaping dollar signs."""
        if text is None:
            return None

        def escape_single_dollar_signs(text: str) -> str:
            """Escape single dollar signs in text to prevent Jupyter from interpreting them as LaTeX.

            Preserves all strings of dollar signs greater than length 1,
            especially preserving double dollar signs ($$) which denote LaTeX equations.

            Args:
                text: The text to escape

            Returns:
                Text with single dollar signs escaped
            """
            # Replace single $ with \$, but preserve $$
            # Use negative lookahead and lookbehind to match $ not preceded or followed by $
            return re.sub(r"(?<!\$)\$(?!\$)", r"\$", text)

        return escape_single_dollar_signs(text)

    def get_markdown_documents(self, split_by_page: bool = False) -> List[Document]:
        """
        Get the markdown documents from the job.

        Args:
            split_by_page: Whether to split the pages into separate documents
        """
        if split_by_page:
            return [
                Document(
                    text=self._format_markdown_for_notebook(page.md)
                    if is_jupyter()
                    else page.md,
                    metadata={"page_number": page.page, "file_name": self.file_name},
                )
                for page in self.pages
            ]
        else:
            text = self._page_separator.join(
                [page.md if page.md is not None else "" for page in self.pages]
            )
            return [
                Document(
                    text=self._format_markdown_for_notebook(text)
                    if is_jupyter()
                    else text,
                    metadata={"file_name": self.file_name},
                )
            ]

    async def aget_markdown_documents(
        self, split_by_page: bool = False
    ) -> List[Document]:
        """
        Get the markdown documents from the job.

        Args:
            split_by_page: Whether to split the pages into separate documents
        """
        # No async needed, but here for consistency
        return self.get_markdown_documents(split_by_page)

    def get_markdown_nodes(self, split_by_page: bool = False) -> List[TextNode]:
        """
        Get the markdown nodes from the job.

        Args:
            split_by_page: Whether to split the pages into separate documents
        """
        documents = self.get_markdown_documents(split_by_page)
        return [TextNode(text=doc.text, metadata=doc.metadata) for doc in documents]

    async def aget_markdown_nodes(self, split_by_page: bool = False) -> List[TextNode]:
        """
        Get the markdown nodes from the job.
        Args:
            split_by_page: Whether to split the pages into separate documents
        """
        documents = await self.aget_markdown_documents(split_by_page)
        return [TextNode(text=doc.text, metadata=doc.metadata) for doc in documents]

    def get_markdown(self) -> str:
        """
        Get the raw parsed markdown from the job, distinct from the markdown documents.
        This does not include page separators, e.g. if merge_tables_across_pages_in_markdown is True
        """
        return asyncio_run(self.aget_markdown())

    async def aget_markdown(self) -> str:
        """
        Get the raw parsed markdown from the job, distinct from the markdown documents.
        This does not include page separators, e.g. if merge_tables_across_pages_in_markdown is True
        """
        url = f"{self._base_url}/api/v1/parsing/job/{self.job_id}/result/raw/markdown"
        response = await make_api_request(self._client, "GET", url)
        markdown = response.content.decode("utf-8")
        return (
            self._format_markdown_for_notebook(markdown) if is_jupyter() else markdown
        )

    def get_text(self) -> str:
        """
        Get the raw parsed text from the job.
        """
        return asyncio_run(self.aget_text())

    async def aget_text(self) -> str:
        """
        Get the raw parsed text from the job.
        """
        url = f"{self._base_url}/api/v1/parsing/job/{self.job_id}/result/raw/text"
        response = await make_api_request(self._client, "GET", url)
        return response.content.decode("utf-8")

    def get_json(self) -> Dict[str, Any]:
        """
        Get the full parsed JSON result from the job.

        Note:
            This is not the same as JobResult.json(), which is a
            JSON serialized version of the JobResult Page Documents.
        """
        return asyncio_run(self.aget_json())

    async def aget_json(self) -> Dict[str, Any]:
        """
        Get the full parsed JSON result from the job.

        Note:
            This is not the same as JobResult.json(), which is a
            JSON serialized version of the JobResult Page Documents.
        """
        url = f"{self._base_url}/api/v1/parsing/job/{self.job_id}/result/json"
        response = await make_api_request(self._client, "GET", url)
        return response.json()

    async def _get_image_document_with_bytes(
        self, image: ImageItem, page: Page
    ) -> ImageDocument:
        image_data = await self.aget_image_data(image.name)

        return ImageDocument(
            image=image_data,
            metadata={
                "page_number": page.page,
                "file_name": self.file_name,
                "width": image.original_width,
                "height": image.original_height,
                "x": image.x,
                "y": image.y,
            },
            excluded_embed_metadata_keys=["width", "height", "x", "y"],
            excluded_llm_metadata_keys=["width", "height", "x", "y"],
        )

    async def _get_image_document_with_path(
        self, image: ImageItem, page: Page, image_download_dir: str
    ) -> ImageDocument:
        image_path = await self.asave_image(image.name, image_download_dir)

        return ImageDocument(
            image_path=image_path,
            metadata={
                "page_number": page.page,
                "file_name": self.file_name,
                "width": image.original_width,
                "height": image.original_height,
                "x": image.x,
                "y": image.y,
            },
            excluded_embed_metadata_keys=["width", "height", "x", "y"],
            excluded_llm_metadata_keys=["width", "height", "x", "y"],
        )

    def get_image_documents(
        self,
        include_screenshot_images: bool = True,
        include_object_images: bool = True,
        image_download_dir: Optional[str] = None,
    ) -> List[ImageDocument]:
        """
        Get the image documents from the job.

        Args:
            include_screenshot_images (bool):
                Whether to include screenshot images. Default is True.
            include_object_images (bool):
                Whether to include object images. Default is True.
            image_download_dir (Optional[str]):
                The directory to save the images to. If not provided, the images will be loaded into memory.
                Default is None.
        """
        return asyncio_run(
            self.aget_image_documents(
                include_screenshot_images, include_object_images, image_download_dir
            )
        )

    async def aget_image_documents(
        self,
        include_screenshot_images: bool = True,
        include_object_images: bool = True,
        image_download_dir: Optional[str] = None,
    ) -> List[ImageDocument]:
        """
        Get the image documents from the job.

        Args:
            include_screenshot_images (bool):
                Whether to include screenshot images. Default is True.
            include_object_images (bool):
                Whether to include object images. Default is True.
            image_download_dir (Optional[str]):
                The directory to save the images to. If not provided, the images will be loaded into memory.
                Default is None.
        """
        documents = []
        for page in self.pages:
            for image in page.images:
                is_screenshot = re.search(PAGE_REGEX, image.name) is not None

                # Skip images that don't match the inclusion criteria
                if (is_screenshot and not include_screenshot_images) or (
                    not is_screenshot and not include_object_images
                ):
                    continue

                # Get image document using appropriate method based on download_dir
                get_document = (
                    self._get_image_document_with_path
                    if image_download_dir
                    else self._get_image_document_with_bytes
                )

                documents.append(
                    await get_document(image, page, image_download_dir)  # type: ignore
                    if image_download_dir
                    else await get_document(image, page)  # type: ignore
                )

        return documents

    def get_image_nodes(
        self,
        include_screenshot_images: bool = True,
        include_object_images: bool = True,
        image_download_dir: Optional[str] = None,
    ) -> List[ImageNode]:
        """
        Get the image nodes from the job.

        Args:
            include_screenshot_images (bool):
                Whether to include screenshot images. Default is True.
            include_object_images (bool):
                Whether to include object images. Default is True.
            image_download_dir (Optional[str]):
                The directory to save the images to. If not provided, the images will be loaded into memory.
                Default is None.
        """
        documents = self.get_image_documents(
            include_screenshot_images, include_object_images, image_download_dir
        )
        return [
            ImageNode(
                image=doc.image,
                image_path=doc.image_path,
                image_url=doc.image_url,
                metadata=doc.metadata,
            )
            for doc in documents
        ]

    async def aget_image_nodes(
        self,
        include_screenshot_images: bool = True,
        include_object_images: bool = True,
        image_download_dir: Optional[str] = None,
    ) -> List[ImageNode]:
        """
        Get the image nodes from the job.

        Args:
            include_screenshot_images (bool):
                Whether to include screenshot images. Default is True.
            include_object_images (bool):
                Whether to include object images. Default is True.
            image_download_dir (Optional[str]):
                The directory to save the images to. If not provided, the images will be loaded into memory.
                Default is None.
        """
        documents = await self.aget_image_documents(
            include_screenshot_images, include_object_images, image_download_dir
        )
        return [
            ImageNode(
                image=doc.image,
                image_path=doc.image_path,
                image_url=doc.image_url,
                metadata=doc.metadata,
            )
            for doc in documents
        ]

    async def aget_image_data(self, image_name: str) -> bytes:
        """
        Get image data by name using the job ID.

        Args:
            image_name: The name of the image to fetch

        Returns:
            The image data as bytes
        """
        url = f"{self._base_url}/api/v1/parsing/job/{self.job_id}/result/image/{image_name}"
        response = await make_api_request(self._client, "GET", url)
        return response.content

    def get_image_data(self, image_name: str) -> bytes:
        """
        Get image data by name using the job ID (synchronous version).

        Args:
            image_name: The name of the image to fetch

        Returns:
            The image data as bytes
        """
        return asyncio_run(self.aget_image_data(image_name))

    async def aget_xlsx_data(self) -> bytes:
        """
        Get the XLSX data for the job.

        Returns:
            The XLSX data as bytes
        """
        url = f"{self._base_url}/api/v1/parsing/job/{self.job_id}/result/xlsx"
        response = await make_api_request(self._client, "GET", url)
        return response.content

    def get_xlsx_data(self) -> bytes:
        """
        Get the XLSX data for the job (synchronous version).

        Returns:
            The XLSX data as bytes
        """
        return asyncio_run(self.aget_xlsx_data())

    async def asave_image(self, image_name: str, output_dir: str) -> str:
        """
        Save an image to a file.

        Args:
            image_name: The name of the image to fetch
            output_dir: The directory to save the image to

        Returns:
            The path to the saved image
        """
        image_data = await self.aget_image_data(image_name)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Save image to file
        output_path = os.path.join(output_dir, image_name)
        with open(output_path, "wb") as f:
            f.write(image_data)

        return output_path

    def save_image(self, image_name: str, output_dir: str) -> str:
        """
        Save an image to a file (synchronous version).

        Args:
            image_name: The name of the image to fetch
            output_dir: The directory to save the image to

        Returns:
            The path to the saved image
        """
        return asyncio_run(self.asave_image(image_name, output_dir))

    def get_image_names(self) -> List[str]:
        """
        Get the names of all images in the job.

        Returns:
            A list of image names
        """
        return [image.name for page in self.pages for image in page.images]

    async def asave_all_images(self, output_dir: str) -> List[str]:
        """
        Save all images to files.

        Args:
            output_dir: The directory to save the images to

        Returns:
            A list of paths to the saved images
        """
        image_names = self.get_image_names()
        saved_paths = []

        for name in image_names:
            path = await self.asave_image(name, output_dir)
            saved_paths.append(path)

        return saved_paths

    def save_all_images(self, output_dir: str) -> List[str]:
        """
        Save all images to files (synchronous version).

        Args:
            output_dir: The directory to save the images to

        Returns:
            A list of paths to the saved images
        """
        return asyncio_run(self.asave_all_images(output_dir))
