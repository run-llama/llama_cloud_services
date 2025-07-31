import pytest

from pathlib import Path
from llama_cloud_services.parse.utils import (
    expand_target_pages,
    partition_pages,
    extract_tables_from_json_results,
)
from typing import List


@pytest.fixture()
def pseudo_json_results() -> List[dict]:
    return [
        {
            "pages": [
                {
                    "items": [
                        {
                            "type": "table",
                            "csv": "Name,Age,Height (cm)\nAnna,12,140\nBob,22,175\nClaire,33,173\nDenis,44,185\n",
                        }
                    ]
                }
            ]
        }
    ]


def test_expand_target_pages() -> None:
    with pytest.raises(ValueError):
        list(expand_target_pages("x"))
    with pytest.raises(ValueError):
        list(expand_target_pages("1-2-3"))
    with pytest.raises(ValueError):
        list(expand_target_pages("2-1"))
    result = list(expand_target_pages("0,2-3,5,8-10"))
    assert result == [0, 2, 3, 5, 8, 9, 10]


def test_partion_pages() -> None:
    pages = [0, 2, 3, 5, 8, 9, 10]
    with pytest.raises(ValueError):
        list(partition_pages(pages, 0))
    result = list(partition_pages(pages, 3))
    assert result == ["0,2-3", "5,8-9", "10"]

    with pytest.raises(ValueError):
        list(partition_pages(pages, 3, 0))
    result = list(partition_pages(pages, 3, max_pages=5))
    assert result == ["0,2-3", "5,8"]
    result = list(partition_pages(pages, 3, max_pages=10))
    assert result == ["0,2-3", "5,8-9", "10"]


def test_table_extraction(pseudo_json_results: List[dict], tmpdir: Path) -> None:
    tables = extract_tables_from_json_results(pseudo_json_results, tmpdir)
    assert len(tables) == 1
    for table in tables:
        assert Path(table).exists()
        with open(table) as t:
            assert t.read() == pseudo_json_results[0]["pages"][0]["items"][0]["csv"]
