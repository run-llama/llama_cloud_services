import pytest
import pandas as pd

from llama_cloud_services.parse.utils import (
    expand_target_pages,
    partition_pages,
    MarkdownTextAnalyzer,
    md_table_to_pd_dataframe,
)


@pytest.fixture()
def dataframe_from_tables() -> pd.DataFrame:
    project_data = {
        "Project Name": [
            "User Dashboard",
            "API Integration",
            "Mobile App",
            "Database Migration",
            "Security Audit",
        ],
        "Status": [
            "In Progress",
            "Completed",
            "Planning",
            "In Progress",
            "Not Started",
        ],
        "Completion %": ["75%", "100%", "25%", "60%", "0%"],
        "Assigned Developer": [
            "Alice Johnson",
            "Bob Smith",
            "Carol Davis",
            "David Wilson",
            "Eve Brown",
        ],
        "Due Date": [
            "2025-07-15",
            "2025-06-30",
            "2025-08-20",
            "2025-07-10",
            "2025-08-01",
        ],
    }

    df = pd.DataFrame(project_data)
    return df


@pytest.fixture()
def markdown_file_text() -> str:
    return """
## Team Performance Metrics

The table below shows our team's performance across different projects:

| Project Name       | Status      | Completion % | Assigned Developer | Due Date   |
| ------------------ | ----------- | ------------ | ------------------ | ---------- |
| User Dashboard     | In Progress | 75%          | Alice Johnson      | 2025-07-15 |
| API Integration    | Completed   | 100%         | Bob Smith          | 2025-06-30 |
| Mobile App         | Planning    | 25%          | Carol Davis        | 2025-08-20 |
| Database Migration | In Progress | 60%          | David Wilson       | 2025-07-10 |
| Security Audit     | Not Started | 0%           | Eve Brown          | 2025-08-01 |

| Project Name       | Status      | Completion % | Assigned Developer | Due Date   |
| ------------------ | ----------- | ------------ | ------------------ | ---------- |
| User Dashboard     | In Progress | 75%          | Alice Johnson      | 2025-07-15 |
| API Integration    | Completed   | 100%         | Bob Smith          | 2025-06-30 |
| Mobile App         | Planning    | 25%          | Carol Davis        | 2025-08-20 |
| Database Migration | In Progress | 60%          | David Wilson       | 2025-07-10 |
| Security Audit     | Not Started | 0%           | Eve Brown          | 2025-08-01 |

## Key Observations

Based on the data above, we can see that:

- The API Integration project was completed on schedule
- The User Dashboard is progressing well and should meet its deadline
- The Database Migration needs attention to stay on track
- We need to begin the Security Audit soon to meet the August deadline
"""


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


def test_table_to_dataframe(
    markdown_file_text: str, dataframe_from_tables: pd.DataFrame
) -> None:
    analyzer = MarkdownTextAnalyzer(markdown_file_text)
    md_tables = analyzer.identify_tables()["Table"]
    assert len(md_tables) == 2
    for md_table in md_tables:
        df = md_table_to_pd_dataframe(md_table)
        assert df is not None
        assert df.equals(dataframe_from_tables)
