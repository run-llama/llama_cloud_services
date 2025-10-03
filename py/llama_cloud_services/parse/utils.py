import functools
import httpx
import itertools
import logging
import os
from enum import Enum
from pathlib import Path
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)
from typing import Any, Iterable, Iterator, Optional, List, cast

logger = logging.getLogger(__name__)

# Asyncio error messages
nest_asyncio_err = "cannot be called from a running event loop"
nest_asyncio_msg = "The event loop is already running. Add `import nest_asyncio; nest_asyncio.apply()` to your code to fix this issue."


class ResultType(str, Enum):
    """The result type for the parser."""

    TXT = "text"
    MD = "markdown"
    JSON = "json"
    STRUCTURED = "structured"


class ParsingMode(str, Enum):
    """The parsing mode for the parser."""

    parse_page_without_llm = "parse_page_without_llm"
    parse_page_with_llm = "parse_page_with_llm"
    parse_page_with_lvm = "parse_page_with_lvm"
    parse_page_with_agent = "parse_page_with_agent"
    parse_document_with_llm = "parse_document_with_llm"
    parse_document_with_agent = "parse_document_with_agent"


class FailedPageMode(str, Enum):
    """
    Enum for representing the different available page error handling modes
    """

    raw_text = "raw_text"
    blank_page = "blank_page"
    error_message = "error_message"


class Language(str, Enum):
    BAZA = "abq"
    ADYGHE = "ady"
    AFRIKAANS = "af"
    ANGIKA = "ang"
    ARABIC = "ar"
    ASSAMESE = "as"
    AVAR = "ava"
    AZERBAIJANI = "az"
    BELARUSIAN = "be"
    BULGARIAN = "bg"
    BIHARI = "bh"
    BHOJPURI = "bho"
    BENGALI = "bn"
    BOSNIAN = "bs"
    SIMPLIFIED_CHINESE = "ch_sim"
    TRADITIONAL_CHINESE = "ch_tra"
    CHECHEN = "che"
    CZECH = "cs"
    WELSH = "cy"
    DANISH = "da"
    DARGWA = "dar"
    GERMAN = "de"
    ENGLISH = "en"
    SPANISH = "es"
    ESTONIAN = "et"
    PERSIAN_FARSI = "fa"
    FRENCH = "fr"
    IRISH = "ga"
    GOAN_KONKANI = "gom"
    HINDI = "hi"
    CROATIAN = "hr"
    HUNGARIAN = "hu"
    INDONESIAN = "id"
    INGUSH = "inh"
    ICELANDIC = "is"
    ITALIAN = "it"
    JAPANESE = "ja"
    KABARDIAN = "kbd"
    KANNADA = "kn"
    KOREAN = "ko"
    KURDISH = "ku"
    LATIN = "la"
    LAK = "lbe"
    LEZGHIAN = "lez"
    LITHUANIAN = "lt"
    LATVIAN = "lv"
    MAGAHI = "mah"
    MAITHILI = "mai"
    MAORI = "mi"
    MONGOLIAN = "mn"
    MARATHI = "mr"
    MALAY = "ms"
    MALTESE = "mt"
    NEPALI = "ne"
    NEWARI = "new"
    DUTCH = "nl"
    NORWEGIAN = "no"
    OCCITAN = "oc"
    PALI = "pi"
    POLISH = "pl"
    PORTUGUESE = "pt"
    ROMANIAN = "ro"
    RUSSIAN = "ru"
    SERBIAN_CYRILLIC = "rs_cyrillic"
    SERBIAN_LATIN = "rs_latin"
    NAGPURI = "sck"
    SLOVAK = "sk"
    SLOVENIAN = "sl"
    ALBANIAN = "sq"
    SWEDISH = "sv"
    SWAHILI = "sw"
    TAMIL = "ta"
    TABASSARAN = "tab"
    TELUGU = "te"
    THAI = "th"
    TAJIK = "tjk"
    TAGALOG = "tl"
    TURKISH = "tr"
    UYGHUR = "ug"
    UKRAINIAN = "uk"
    URDU = "ur"
    UZBEK = "uz"
    VIETNAMESE = "vi"


SUPPORTED_FILE_TYPES = [
    ".pdf",
    # document and presentations
    ".602",
    ".abw",
    ".cgm",
    ".cwk",
    ".doc",
    ".docx",
    ".docm",
    ".dot",
    ".dotm",
    ".hwp",
    ".key",
    ".lwp",
    ".mw",
    ".mcw",
    ".pages",
    ".pbd",
    ".ppt",
    ".pptm",
    ".pptx",
    ".pot",
    ".potm",
    ".potx",
    ".rtf",
    ".sda",
    ".sdd",
    ".sdp",
    ".sdw",
    ".sgl",
    ".sti",
    ".sxi",
    ".sxw",
    ".stw",
    ".sxg",
    ".txt",
    ".uof",
    ".uop",
    ".uot",
    ".vor",
    ".wpd",
    ".wps",
    ".xml",
    ".zabw",
    ".epub",
    # images
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".svg",
    ".tiff",
    ".webp",
    # web
    ".htm",
    ".html",
    # spreadsheets
    ".xlsx",
    ".xls",
    ".xlsm",
    ".xlsb",
    ".xlw",
    ".csv",
    ".dif",
    ".sylk",
    ".slk",
    ".prn",
    ".numbers",
    ".et",
    ".ods",
    ".fods",
    ".uos1",
    ".uos2",
    ".dbf",
    ".wk1",
    ".wk2",
    ".wk3",
    ".wk4",
    ".wks",
    ".123",
    ".wq1",
    ".wq2",
    ".wb1",
    ".wb2",
    ".wb3",
    ".qpw",
    ".xlr",
    ".eth",
    ".tsv",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".wav",
    ".webm",
]


def should_retry(exception: Exception) -> bool:
    """Check if the exception should be retried.

    Args:
        exception: The exception to check.
    """
    # Retry on connection errors (network issues)
    if isinstance(
        exception,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.RemoteProtocolError,
        ),
    ):
        return True

    # Retry on specific HTTP status codes
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        # Retry on rate limiting or temporary server errors
        return status_code in (429, 500, 502, 503, 504)

    return False


async def make_api_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    timeout: float = 60.0,
    max_retries: int = 5,
    **httpx_kwargs: Any,
) -> httpx.Response:
    """Make an retrying API request to the LlamaParse API.

    Args:
        client: The httpx.AsyncClient to use for the request.
        url: The URL to request.
        headers: The headers to include in the request.
        timeout: The timeout for the request.
        max_retries: The maximum number of retries for the request.
    """

    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=timeout),
        retry=retry_if_exception(should_retry),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _make_request(url: str, **httpx_kwargs: Any) -> httpx.Response:
        if method == "GET":
            response = await client.get(url, **httpx_kwargs)
        elif method == "POST":
            response = await client.post(url, **httpx_kwargs)
        else:
            raise ValueError(f"Invalid method: {method}")
        response.raise_for_status()
        return response

    return await _make_request(url, **httpx_kwargs)


def expand_target_pages(target_pages: str) -> Iterator[int]:
    """Yield all values in target_pages."""
    for target in target_pages.strip().split(","):
        if "-" in target:
            try:
                start, end = map(int, target.strip().split("-"))
                if start > end:
                    raise ValueError
                yield from range(start, end + 1)
            except ValueError as e:
                raise ValueError(f"Invalid page range: {target}") from e
        else:
            try:
                yield int(target)
            except ValueError as e:
                raise ValueError(f"Invalid page number: {target}") from e


def partition_pages(
    pages: Iterable[int], size: int, max_pages: Optional[int] = None
) -> Iterator[str]:
    """Yield partitioned target_pages segments."""
    if size < 1:
        raise ValueError(f"Invalid partition segment size: {size}")
    if max_pages is not None and max_pages < 1:
        raise ValueError("Max pages must be > 0")
    it = iter(pages)
    total = 0
    while max_pages is None or total < max_pages:
        segment = tuple(itertools.islice(it, size))
        if segment:
            targets = []
            for _k, g in itertools.groupby(enumerate(segment), lambda x: x[0] - x[1]):
                group = [item[1] for item in g]
                if len(group) > 1:
                    start, end = group[0], group[-1]
                    group_size = end - start + 1
                    if max_pages is not None and total + group_size > max_pages:
                        end -= total + group_size - max_pages
                        group_size = end - start + 1
                    if group_size > 1:
                        targets.append(f"{start}-{end}")
                    else:
                        targets.append(str(start))
                    total += group_size
                else:
                    targets.append(str(group[0]))
                    total += 1
            yield ",".join(targets)
        else:
            return


@functools.lru_cache(maxsize=1)
def is_jupyter() -> bool:
    """Check if we're running in a Jupyter environment."""
    try:
        from IPython import get_ipython

        return get_ipython().__class__.__name__ == "ZMQInteractiveShell"
    except (ImportError, AttributeError):
        return False


def extract_tables_from_json_results(
    json_results: List[dict], download_path: str
) -> List[str]:
    tables = []
    for json_result in json_results:
        pages = json_result["pages"]
        for page in pages:
            page = cast(dict, page)
            items = page.get("items", [])
            if items:
                for i, item in enumerate(items):
                    item = cast(dict, item)
                    if item.get("type", "") == "table" and item.get("csv", ""):
                        savepath = os.path.join(
                            download_path,
                            f"table_{datetime.now().strftime('%Y_%d_%m_%H_%M_%S_%f')[:-3]}.csv",
                        )
                        if Path(savepath).exists():
                            savepath = (
                                savepath.replace(".csv", "_")[0] + str(i) + ".csv"
                            )
                        with open(savepath, "w") as f:
                            f.write(item["csv"])
                        tables.append(savepath)
    return tables
