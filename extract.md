# LlamaExtract

LlamaExtract provides a simple API for extracting structured data from unstructured documents like PDFs, text files and images.

## Quick Start

The simplest way to get started is to use the stateless API with the extraction configuration and the file/text to extract from:

```python
from llama_cloud_services import LlamaExtract
from llama_cloud import ExtractConfig, ExtractMode
from pydantic import BaseModel, Field

# Initialize client
extractor = LlamaExtract()


# Define schema using Pydantic
class Resume(BaseModel):
    name: str = Field(description="Full name of candidate")
    email: str = Field(description="Email address")
    skills: list[str] = Field(description="Technical skills and technologies")


# Configure extraction settings
config = ExtractConfig(extraction_mode=ExtractMode.FAST)

# Extract data directly from document - no agent needed!
result = extractor.extract(Resume, config, "resume.pdf")
print(result.data)
```

### Supported File Types

LlamaExtract supports the following file formats:

- **Documents**: PDF (.pdf), Word (.docx)
- **Text files**: Plain text (.txt), CSV (.csv), JSON (.json), HTML (.html, .htm), Markdown (.md)
- **Images**: PNG (.png), JPEG (.jpg, .jpeg)

### Different Input Types

```python
# From file path (string or Path)
result = extractor.extract(Resume, config, "resume.pdf")

# From file handle
with open("resume.pdf", "rb") as f:
    result = extractor.extract(Resume, config, f)

# From bytes with filename
with open("resume.pdf", "rb") as f:
    file_bytes = f.read()
from llama_cloud_services.extract import SourceText

result = extractor.extract(
    Resume, config, SourceText(file=file_bytes, filename="resume.pdf")
)

# From text content
text = "Name: John Doe\nEmail: john@example.com\nSkills: Python, AI"
result = extractor.extract(Resume, config, SourceText(text_content=text))
```

### Async Extraction

For better performance with multiple files or when integrating with async applications:

```python
import asyncio


async def extract_resumes():
    # Async extraction
    result = await extractor.aextract(Resume, config, "resume.pdf")
    print(result.data)

    # Queue extraction jobs (returns immediately)
    jobs = await extractor.queue_extraction(
        Resume, config, ["resume1.pdf", "resume2.pdf"]
    )
    print(f"Queued {len(jobs)} extraction jobs")


# Run async function
asyncio.run(extract_resumes())
```

## Core Concepts

- **Data Schema**: Structure definition for the data you want to extract in the form of a JSON schema or a Pydantic model.
- **Extraction Config**: Settings that control how extraction is performed (e.g., speed vs accuracy trade-offs).
- **Extraction Jobs**: Asynchronous extraction tasks that can be monitored.
- **Extraction Agents** (Advanced): Reusable extractors configured with a specific schema and extraction settings.

## Defining Schemas

Schemas define the structure of data you want to extract. You can use either Pydantic models or JSON Schema:

### Using Pydantic (Recommended)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from llama_cloud import ExtractConfig, ExtractMode


class Experience(BaseModel):
    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    start_date: Optional[str] = Field(description="Start date of employment")
    end_date: Optional[str] = Field(description="End date of employment")


class Resume(BaseModel):
    name: str = Field(description="Candidate name")
    experience: List[Experience] = Field(description="Work history")


# Use the schema for extraction
config = ExtractConfig(extraction_mode=ExtractMode.FAST)
result = extractor.extract(Resume, config, "resume.pdf")
```

### Using JSON Schema

```python
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Candidate name"},
        "experience": {
            "type": "array",
            "description": "Work history",
            "items": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Company name",
                    },
                    "title": {"type": "string", "description": "Job title"},
                    "start_date": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "description": "Start date of employment",
                    },
                    "end_date": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "description": "End date of employment",
                    },
                },
            },
        },
    },
}

# Use the schema for extraction
config = ExtractConfig(extraction_mode=ExtractMode.FAST)
result = extractor.extract(schema, config, "resume.pdf")
```

## Extraction Configuration

Configure how extraction is performed using `ExtractConfig`:

```python
from llama_cloud import ExtractConfig, ExtractMode

# Fast extraction (lower accuracy, faster processing)
fast_config = ExtractConfig(extraction_mode=ExtractMode.FAST)

# Balanced extraction (good balance of speed and accuracy)
balanced_config = ExtractConfig(extraction_mode=ExtractMode.BALANCED)

# Use different configs for different needs
result = extractor.extract(schema, fast_config, "simple_document.pdf")
result = extractor.extract(schema, balanced_config, "complex_document.pdf")
```

### Important restrictions on JSON/Pydantic Schema

_LlamaExtract only supports a subset of the JSON Schema specification._ While limited, it should
be sufficient for a wide variety of use-cases.

- All fields are required by default. Nullable fields must be explicitly marked as such,
  using `anyOf` with a `null` type. See `"start_date"` field above.
- Root node must be of type `object`.
- Schema nesting must be limited to within 5 levels.
- The important fields are key names/titles, type and description. Fields for
  formatting, default values, etc. are **not supported**. If you need these, you can add the
  restrictions to your field description and/or use a post-processing step. e.g. default values can be supported by making a field optional and then setting `"null"` values from the extraction result to the default value.
- There are other restrictions on number of keys, size of the schema, etc. that you may
  hit for complex extraction use cases. In such cases, it is worth thinking how to restructure
  your extraction workflow to fit within these constraints, e.g. by extracting subset of fields
  and later merging them together.

## Extraction Agents (Advanced)

For reusable extraction workflows, you can create extraction agents that encapsulate both schema and configuration:

### Creating Agents

```python
from llama_cloud_services import LlamaExtract
from llama_cloud import ExtractConfig, ExtractMode
from pydantic import BaseModel, Field

# Initialize client
extractor = LlamaExtract()


# Define schema
class Resume(BaseModel):
    name: str = Field(description="Full name of candidate")
    email: str = Field(description="Email address")
    skills: list[str] = Field(description="Technical skills and technologies")


# Configure extraction settings
config = ExtractConfig(extraction_mode=ExtractMode.FAST)

# Create extraction agent
agent = extractor.create_agent(
    name="resume-parser", data_schema=Resume, config=config
)

# Use the agent
result = agent.extract("resume.pdf")
print(result.data)
```

### Agent Batch Processing

Process multiple files with an agent:

```python
# Queue multiple files for extraction
jobs = await agent.queue_extraction(["resume1.pdf", "resume2.pdf"])

# Check job status
for job in jobs:
    status = agent.get_extraction_job(job.id).status
    print(f"Job {job.id}: {status}")

# Get results when complete
results = [agent.get_extraction_run_for_job(job.id) for job in jobs]
```

### Updating Agent Schemas

Schemas can be modified and updated after creation:

```python
# Update schema
agent.data_schema = new_schema

# Save changes
agent.save()
```

### Managing Agents

```python
# List all agents
agents = extractor.list_agents()

# Get specific agent
agent = extractor.get_agent(name="resume-parser")

# Delete agent
extractor.delete_agent(agent.id)
```

### When to Use Agents vs Direct Extraction

**Use Direct Extraction When:**

- One-off extractions
- Different schemas for different documents
- Simple workflows
- Getting started quickly

**Use Extraction Agents When:**

- Repeated extractions with the same schema
- Team collaboration (shared, named extractors)
- Complex workflows requiring state management
- Production systems with consistent extraction patterns

## Installation

```bash
pip install llama-cloud-services
```

## Tips & Best Practices

At the core of LlamaExtract is the schema, which defines the structure of the data you want to extract from your documents.

1. **Schema Design**:

   - Try to limit schema nesting to 3-4 levels.
   - Make fields optional when data might not always be present. Having required fields may force the model
     to hallucinate when these fields are not present in the documents.
   - When you want to extract a variable number of entities, use an `array` type. However, note that you cannot use
     an `array` type for the root node.
   - Use descriptive field names and detailed descriptions. Use descriptions to pass formatting
     instructions or few-shot examples.
   - Above all, start simple and iteratively build your schema to incorporate requirements.

2. **Running Extractions**:
   - Note that resetting `agent.schema` will not save the schema to the database,
     until you call `agent.save`, but it will be used for running extractions.
   - Check extraction results for any errors. Error information is available in the `result.error` field for debugging.
   - Consider async operations (`aextract` or `queue_extraction`) for large-scale extraction or when processing multiple files.
   - For repeated extractions with the same schema, consider creating an extraction agent to avoid redefining the schema each time.

### Hitting "The response was too long to be processed" Error

This implies that the extraction response is hitting output token limits of the LLM. In such cases, it is worth rethinking the design of your schema to enable a more efficient/scalable extraction. e.g.

- Instead of one field that extracts a complex object, you can use multiple fields to distribute the extraction logic.
- You can also use multiple schemas to extract different subsets of fields from the same document and merge them later.

Another option (orthogonal to the above) is to break the document into smaller sections and extract from each section individually, when possible. LlamaExtract will in most cases be able to handle both document and schema chunking automatically, but there are cases where you may need to do this manually.

## Additional Resources

- [Example Notebook](docs/examples-py/extract/resume_screening.ipynb) - Detailed walkthrough of resume parsing
- [Example Application with TypeScript](./examples-ts/extract/) - End-to-end examples using LlamaExtract TypeScript client.
- [Discord Community](https://discord.com/invite/eN6D2HQ4aX) - Get help and share feedback
