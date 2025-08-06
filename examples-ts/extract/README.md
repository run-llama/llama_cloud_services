# LlamaExtract Demo

A TypeScript demo application showcasing the power of **LlamaExract** - a structured data extraction agentic service from [LlamaCloud](https://cloud.llamaindex.ai). This demo allows you to extract structured information from scientific papers and get them into a nice markdown format.

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

- 📄 **Structured Data Extraction**: Extract data from your files effortlessly, and structure them the way you want!
- 🤖 **Markdown Rendering**: Generate markdown directly from your extracted data
- 🎨 **Beautiful CLI**: Styled console interface with colors and ASCII art
- ⚡ **Fast Development**: Hot reload support with watch mode
- 🛠️ **TypeScript**: Full TypeScript support with strict type checking

## Prerequisites

- Node.js (version 18 or higher)
- pnpm package manager
- LlamaCloud API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/run-llama/llama_cloud_services
cd lama_cloud_services/examples-ts/extract/
```

2. Install dependencies:

```bash
npm install
```

3. Set up your environment variables:

```bash
# Add your API key to your environment
export LLAMA_CLOUD_API_KEY="your-llamacloud-api-key"
```

## Usage

### Start the Demo

```bash
npm run start
```

The application will display a welcome screen and prompt you to enter the path to a document you'd like to process.

### Development Mode

For development with hot reload:

```bash
npm run dev
```

### Build the Project

```bash
npm run build
```

### Code Quality

Format code:

```bash
npm run format
```

Lint code:

```bash
npm run lint
```

## How It Works

1. **Document Input**: Enter the path to your document when prompted
2. **Parsing**: LlamaExtract, based on the schema you can find [here](./src/schema.ts), processes the document and extracts structured data
3. **Markdown Rendering**: The extracted content is rendered into beautiful markdown
4. **Results**: View the results directly in your terminal

## Troubleshooting

### Common Issues

1. **Module Resolution Errors**: Ensure you're using Node.js 18+ and have all dependencies installed
2. **API Key Issues**: Verify your LlamaCloud API key is correctly set
3. **File Path Errors**: Use absolute paths or ensure relative paths are correct from the project root

## License

MIT License - see the [LICENSE](../../LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `npm run format` and `npm run lint`
5. Submit a pull request
