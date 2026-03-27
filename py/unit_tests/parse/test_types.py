import pytest
from llama_cloud_services.parse.types import (
    JobResult,
    Page,
    ImageItem,
)


def _make_job_result(pages=None):
    """Helper to create a JobResult with given pages."""
    job_result = {
        "pages": pages or [],
        "job_metadata": {},
    }
    return JobResult(
        job_id="test-job-id",
        file_name="test.pdf",
        job_result=job_result,
    )


def _make_page(page_num, images=None):
    """Helper to create a page dict."""
    return {
        "page": page_num,
        "text": f"Page {page_num} text",
        "md": f"# Page {page_num}",
        "images": images or [],
        "charts": [],
        "tables": [],
        "items": [],
        "layout": [],
        "links": [],
        "parsingMode": "parse_page_without_llm",
    }


def _make_image(name, width=100, height=100, img_type="raster"):
    """Helper to create an image dict."""
    return {
        "name": name,
        "original_width": width,
        "original_height": height,
        "type": img_type,
    }


class TestHasImages:
    def test_no_pages(self):
        result = _make_job_result(pages=[])
        assert result.has_images() is False

    def test_pages_without_images(self):
        result = _make_job_result(pages=[
            _make_page(0),
            _make_page(1),
        ])
        assert result.has_images() is False

    def test_pages_with_images(self):
        result = _make_job_result(pages=[
            _make_page(0, images=[_make_image("img_0.png")]),
            _make_page(1),
        ])
        assert result.has_images() is True

    def test_all_pages_with_images(self):
        result = _make_job_result(pages=[
            _make_page(0, images=[_make_image("img_0.png")]),
            _make_page(1, images=[_make_image("img_1.png"), _make_image("img_2.png")]),
        ])
        assert result.has_images() is True


class TestGetImageExtractionSummary:
    def test_empty_result(self):
        result = _make_job_result(pages=[])
        summary = result.get_image_extraction_summary()
        assert summary["total_images"] == 0
        assert summary["total_pages"] == 0
        assert summary["pages_with_images"] == []
        assert summary["pages_without_images"] == []
        assert summary["image_details"] == []

    def test_no_images(self):
        result = _make_job_result(pages=[
            _make_page(0),
            _make_page(1),
        ])
        summary = result.get_image_extraction_summary()
        assert summary["total_images"] == 0
        assert summary["total_pages"] == 2
        assert summary["pages_with_images"] == []
        assert summary["pages_without_images"] == [0, 1]

    def test_mixed_pages(self):
        result = _make_job_result(pages=[
            _make_page(0, images=[_make_image("img_0.png", 200, 300, "raster")]),
            _make_page(1),
            _make_page(2, images=[
                _make_image("img_1.png", 400, 500),
                _make_image("img_2.png", 600, 700),
            ]),
        ])
        summary = result.get_image_extraction_summary()
        assert summary["total_images"] == 3
        assert summary["total_pages"] == 3
        assert summary["pages_with_images"] == [0, 2]
        assert summary["pages_without_images"] == [1]
        assert len(summary["image_details"]) == 3
        assert summary["image_details"][0]["name"] == "img_0.png"
        assert summary["image_details"][0]["width"] == 200
        assert summary["image_details"][0]["height"] == 300
        assert summary["image_details"][0]["type"] == "raster"


class TestGetImageExtractionTroubleshooting:
    def test_has_images_returns_empty(self):
        result = _make_job_result(pages=[
            _make_page(0, images=[_make_image("img_0.png")]),
        ])
        suggestions = result.get_image_extraction_troubleshooting()
        assert suggestions == []

    def test_no_images_returns_suggestions(self):
        result = _make_job_result(pages=[_make_page(0)])
        suggestions = result.get_image_extraction_troubleshooting()
        assert len(suggestions) > 0
        assert any("premium_mode" in s for s in suggestions)
        assert any("language" in s for s in suggestions)
        assert any("take_screenshot" in s for s in suggestions)
        assert any("inline_images_in_markdown" in s for s in suggestions)


class TestPrintImageExtractionReport:
    def test_report_with_images(self, capsys):
        result = _make_job_result(pages=[
            _make_page(0, images=[_make_image("img_0.png")]),
            _make_page(1),
        ])
        result.print_image_extraction_report()
        captured = capsys.readouterr()
        assert "Image Extraction Report" in captured.out
        assert "Total images extracted: 1" in captured.out
        assert "get_image_documents" in captured.out

    def test_report_without_images(self, capsys):
        result = _make_job_result(pages=[_make_page(0)])
        result.print_image_extraction_report()
        captured = capsys.readouterr()
        assert "No images were extracted!" in captured.out
        assert "premium_mode" in captured.out


class TestGetImageNames:
    def test_returns_all_image_names(self):
        result = _make_job_result(pages=[
            _make_page(0, images=[_make_image("a.png"), _make_image("b.png")]),
            _make_page(1, images=[_make_image("c.png")]),
        ])
        names = result.get_image_names()
        assert names == ["a.png", "b.png", "c.png"]

    def test_empty_when_no_images(self):
        result = _make_job_result(pages=[_make_page(0)])
        assert result.get_image_names() == []


class TestFormatMarkdownForNotebook:
    def test_none_input(self):
        result = _make_job_result()
        assert result._format_markdown_for_notebook(None) is None

    def test_single_dollar_escaped(self):
        result = _make_job_result()
        assert result._format_markdown_for_notebook("$5") == "\\$5"

    def test_double_dollar_preserved(self):
        result = _make_job_result()
        assert (
            result._format_markdown_for_notebook("$$x^2$$") == "$$x^2$$"
        )

    def test_mixed(self):
        result = _make_job_result()
        text = "$5 and $$E=mc^2$$"
        assert result._format_markdown_for_notebook(text) == "\\$5 and $$E=mc^2$$"
