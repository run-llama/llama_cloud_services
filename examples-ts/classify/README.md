# LlamaClassify Demo

A TypeScript demo application showcasing the power of **LlamaClassify** - an agentic documents classification service from [LlamaCloud](https://cloud.llamaindex.ai). This demo allows you to classify financial documents among three different types (Cash flow statement, Income Statement and Balance Sheet).

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Start the Demo](#start-the-demo)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
- [License](#license)
- [Contributing](#contributing)

## Features

- 📄 **Documemt Classification**: Classify files based on well-defined rules you can customized and play around with.
- 🤖 **Reasoning-based Actionable Insights**: Get in-depth, reasoning based insights on the document classification, accompanied by confidence scores.
- 🎨 **Beautiful UI**: [DaisyUI](https://daisyui.com)-based interface powered by [TanStack](https://tanstack.com)
- ⚡ **Fast Development**: Hot reload support with development mode
- 🛠️ **TypeScript**: Full TypeScript support with strict type checking

## Prerequisites

- Node.js (version 22 or higher)
- pnpm package manager
- LlamaCloud API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/run-llama/llama_cloud_services
cd lama_cloud_services/examples-ts/classify/
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
npm run dev
```

The application will be up and running on http://localhost:3000

## How It Works

1. **Document Input**: Enter the path to your document when prompted
2. **Parsing**: LlamaClassify, based on the rules you can find [here](./src/utils/classifier.ts), processes the document and classifies it
3. **Results**: The classification outcome, as well as the reasoning behind it and the confidence score, are displayed in the UI.

## Troubleshooting

### Common Issues

1. **Module Resolution Errors**: Ensure you're using Node.js 22+ and have all dependencies installed
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
