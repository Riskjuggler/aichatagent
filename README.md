# AI Chat Assistant

## Overview
A multi-provider AI chat assistant supporting OpenAI, Anthropic, and Cohere APIs. Provides a command-line interface for interactive conversations with configurable fallback providers and comprehensive logging.

## Features
- Multi-provider support (OpenAI, Anthropic, Cohere)
- Interactive command-line interface
- Conversation history and memory
- Comprehensive debug logging
- Automatic provider fallback
- API key validation
- SSL version checking
- Environment validation

## Installation

### Unix/Linux/MacOS
1. Clone the repository
2. Run setup script:
   ```bash
   ./scripts/phase1_setup.sh
   ```
3. Activate virtual environment:
   ```bash
   source llm_agent_env/bin/activate
   ```

### Windows
1. Clone the repository
2. Run setup script in PowerShell:
   ```powershell
   .\scripts\phase1_setup_windows.ps1
   ```
3. Activate virtual environment:
   ```powershell
   .\llm_agent_env\Scripts\Activate.ps1
   ```

## Configuration
Configure API keys and settings in `.env` file:
```bash
# Required API keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
COHERE_API_KEY=your-cohere-key

# Optional configuration
DEFAULT_PROVIDER=openai
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-opus
COHERE_MODEL=command-r-plus
FALLBACK_ORDER=openai,anthropic,cohere
```

## Usage
Run the chat application:
```bash
python3 src/chat.py
```

Command-line options:
- `--debug`: Enable comprehensive debug logging

Interactive commands:
- `exit` or `quit`: End the session
- `switch`: Change provider

## Documentation
See `project_docs/` for:
- Design documents
- Coding standards
- Implementation details

## Development Standards
Refer to `project_docs/standards/` for:
- AI Engineering Design Standards
- Enterprise Solution Design Standards
- Phase-specific coding standards

## License
MIT License - See [LICENSE](LICENSE) for details