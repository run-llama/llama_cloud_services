# LlamaParse Demo

A TypeScript demo application showcasing the power of **LlamaParse** - an intelligent document parsing service from [LlamaCloud](https://cloud.llamaindex.ai). This demo allows you to parse various document formats and generate AI-powered summaries using OpenAI's GPT models.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Start the Demo](#start-the-demo)
  - [Development Mode](#development-mode)
  - [Build the Project](#build-the-project)
  - [Code Quality](#code-quality)
  - [Quick Commands Reference](#quick-commands-reference)
- [How It Works](#how-it-works)
- [API Dependencies](#api-dependencies)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
- [License](#license)
- [Contributing](#contributing)

## Features

- 📄 **Document Parsing**: Parse PDFs, Word docs, and other formats using LlamaParse
- 🤖 **AI Summaries**: Generate intelligent summaries using OpenAI GPT-4
- 🎨 **Beautiful CLI**: Styled console interface with colors and ASCII art
- ⚡ **Fast Development**: Hot reload support with watch mode
- 🛠️ **TypeScript**: Full TypeScript support with strict type checking

## Prerequisites

- Node.js (version 18 or higher)
- pnpm package manager
- OpenAI API key
- LlamaCloud API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/run-llama/llama_cloud_services
cd lama_cloud_services/examples-ts/parse/
```

2. Install dependencies:

```bash
pnpm install
```

3. Set up your environment variables:

```bash
# Add your API keys to your environment
export OPENAI_API_KEY="your-openai-api-key"
export LLAMA_CLOUD_API_KEY="your-llamacloud-api-key"
```

## Usage

### Start the Demo

```bash
pnpm run start
```

The application will display a welcome screen and prompt you to enter the path to a document you'd like to process.

### Development Mode

For development with hot reload:

```bash
pnpm run dev
```

### Build the Project

```bash
pnpm run build
```

### Code Quality

Format code:

```bash
pnpm run format
```

Lint code:

```bash
pnpm run lint
```

## How It Works

1. **Document Input**: Enter the path to your document when prompted
2. **Parsing**: LlamaParse processes the document and extracts structured content
3. **AI Summary**: The extracted content is sent to OpenAI GPT-4 for summarization
4. **Results**: View the AI-generated summary in your terminal

## Troubleshooting

### Common Issues

1. **Module Resolution Errors**: Ensure you're using Node.js 18+ and have all dependencies installed
2. **API Key Issues**: Verify your OpenAI and LlamaCloud API keys are correctly set
3. **File Path Errors**: Use absolute paths or ensure relative paths are correct from the project root

## License

MIT License - see the [LICENSE](../../LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `pnpm run format` and `pnpm run lint`
5. Submit a pull request
