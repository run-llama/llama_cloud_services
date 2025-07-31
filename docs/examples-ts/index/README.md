# LlamaCloud Index Demo

A TypeScript demo application showcasing the power of **LlamaCloud Index** - a fully automated document ingestion and retrieval serviced offered within [LlamaCloud](https://cloud.llamaindex.ai). This demo allows you to ask questions, retrieve relevant contextual information and generate AI-powered responses using OpenAI's GPT models.

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

- 🤖 **RAG**: Simple-yet-effective Retrieval Augmented Generation pipeline built on top of LlamaCloud Index adn OpenAI
- 🎨 **Beautiful CLI**: Styled console interface with colors and ASCII art
- ⚡ **Fast Development**: Hot reload support with watch mode
- 🛠️ **TypeScript**: Full TypeScript support with strict type checking

## Prerequisites

- Node.js (version 18 or higher)
- pnpm package manager
- OpenAI API key
- LlamaCloud API key
- An existing LlamaCloud Index pipeline

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd llamaparse-demo
```

2. Install dependencies:

```bash
pnpm install
```

3. Set up your environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export LLAMA_CLOUD_API_KEY="your-llamacloud-api-key"
export PIPELINE_NAME="your-pipeline-name"
```

4. Or write them into a `.env` file:

```env
OPENAI_API_KEY="your-openai-api-key"
LLAMA_CLOUD_API_KEY="your-llamacloud-api-key"
PIPELINE_NAME="your-pipeline-name"
```

## Usage

### Start the Demo

```bash
pnpm run start
```

The application will display a welcome screen and prompt you to start chatting!

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

1. **Message Input**: Enter a message
2. **Retrieval**: Several nodes are retrieved from the LlamaCloud index you specified
3. **AI Response Generation**: The retrieved information is passed on to the AI model, along with its relevance score, and a reply to your original message is generated starting from that.
4. **Results**: View the AI-generated summary in your terminal

## Troubleshooting

### Common Issues

1. **Module Resolution Errors**: Ensure you're using Node.js 18+ and have all dependencies installed
2. **API Key Issues**: Verify your OpenAI and LlamaCloud API keys are correctly set

## License

MIT License - see the [LICENSE](../../../LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `pnpm format` and `pnpm lint`
5. Submit a pull request
