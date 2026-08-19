# Athena AI

Personal AI Chief of Staff with voice integration, tool calling, and note management.

## Features

- **Voice Input**: Transcribe audio commands using Whisper or Ollama
- **Tool Calling**: Execute system commands, manage Docker, search files
- **Memory System**: Long-term memory with semantic search (Qdrant)
- **Obsidian Integration**: Read, search, create, update notes
- **Joplin Integration**: Connect to your Joplin notebooks
- **Chat Interface**: Web-based UI with microphone support

## Tech Stack

- Backend: FastAPI (Python)
- LLM: Ollama (QwenPaw-Flash-4B-Q4_K_M)
- Vector DB: Qdrant
- Embeddings: nomic-embed-text
- Voice: Whisper / Ollama whisper
- Frontend: Vanilla HTML/CSS/JS

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Services

```bash
# Start Qdrant and PostgreSQL
docker compose up -d

# Pull required Ollama models
ollama pull QwenPaw-Flash-4B-Q4_K_M
ollama pull nomic-embed-text
ollama pull whisper  # for voice transcription
```

### 4. Run Backend

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Open Frontend

Open `frontend/index.html` in your browser, or serve it:

```bash
python -m http.server 8080 --directory frontend
```

## API Endpoints

### Chat
- `POST /ask` - Send a message and get response with tool calls
- `GET /conversation` - Get conversation history
- `DELETE /conversation` - Clear conversation

### Memory
- `POST /memory/save` - Save a memory
- `GET /memory/search` - Search memories
- `GET /memory/count` - Get memory count
- `DELETE /memory` - Clear all memories

### Tools
- `GET /tools` - List all available tools
- `POST /tools/{name}/execute` - Execute a tool

### Obsidian
- `GET /obsidian/notes` - List notes
- `GET /obsidian/search?q=query` - Search notes
- `GET /obsidian/note/{path}` - Get note content
- `POST /obsidian/note` - Create note
- `PUT /obsidian/note/{path}` - Update note
- `DELETE /obsidian/note/{path}` - Delete note

### Joplin
- `GET /joplin/notes` - List recent notes
- `GET /joplin/search?q=query` - Search notes
- `GET /joplin/folders` - List folders
- `POST /joplin/note` - Create note
- `PUT /joplin/note/{id}` - Update note
- `DELETE /joplin/note/{id}` - Delete note

### Voice
- `POST /transcribe` - Upload audio for transcription
- `POST /transcribe/url?url=` - Transcribe from URL

### System
- `GET /health` - Health check
- `GET /config` - Configuration info
- `GET /qdrant` - Qdrant status
- `GET /ollama` - Ollama status

## Available Tools

| Tool | Description |
|------|-------------|
| `get_system_info` | OS, hostname, CPU info |
| `get_disk_usage` | Disk space usage |
| `get_memory_usage` | RAM and swap stats |
| `get_cpu_load` | Load averages |
| `list_processes` | Top processes by memory |
| `search_files` | Find files by pattern |
| `check_service` | Check systemd service status |
| `execute_command` | Run shell commands |
| `install_package` | Install software packages |
| `uninstall_package` | Remove software packages |
| `docker_command` | Docker operations (pull, run, stop, etc.) |
| `start_application` | Start desktop applications |
| `stop_application` | Stop running applications |

## Docker Setup

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./docker/qdrant:/qdrant/storage

  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: athena
      POSTGRES_PASSWORD: athena
      POSTGRES_DB: athena
    ports:
      - "5433:5432"
    volumes:
      - ./docker/postgres:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - ./docker/redis:/data
```

## Voice Configuration

To use voice input:
1. Ensure microphone access is granted in browser
2. Click the microphone button in the chat interface
3. Speak your command
4. Audio is transcribed and sent as text

For better transcription quality, install Whisper:
```bash
pip install whisper
```

## Obsidian Integration

Set the vault path in `.env`:
```
OBSIDIAN_VAULT_PATH=/home/jerry/Obsidian
```

Or configure via API:
```bash
curl -X POST http://localhost:8000/obsidian/config \
  -H "Content-Type: application/json" \
  -d '{"vault_path": "/path/to/vault"}'
```

## Joplin Integration

Joplin must be running with REST API plugin enabled:
1. Open Joplin
2. Go to Tools > Options > Plugins
3. Enable "REST API Plugin"
4. Note the API key from Tools > Options > Plugins > REST API

Configure in `.env`:
```
JOPLIN_API_URL=http://localhost:41184
JOPLIN_API_KEY=your_api_key_here
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Test chat
curl "http://localhost:8000/ask?prompt=What%20tools%20do%20you%20have?"

# List tools
curl http://localhost:8000/tools

# Search memories
curl "http://localhost:8000/memory/search?query=preferred%20editor"
```

## Project Structure

```
athena/
├── backend/
│   ├── api/          # FastAPI routes
│   ├── core/         # Config, constants, logging
│   ├── services/     # Business logic
│   ├── tools/        # Tool implementations
│   └── prompts/      # System prompts
├── frontend/         # Web UI
├── docker/           # Docker volumes
├── tests/            # Test suite
├── logs/             # Application logs
└── config/           # Configuration files
```

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt pytest pytest-asyncio

# Run tests
python -m pytest tests/ -v

# Run with auto-reload
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## License

Private project - Jerry's personal AI assistant
