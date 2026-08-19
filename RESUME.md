# Athena AI - Resume Point

## Current Status (2026-08-12)
- **Backend**: http://localhost:8000 (healthy)
- **Frontend**: http://localhost:8080 (serving)
- **Model**: llama3.2:3b-instruct-q5_K_M
- **Tests**: 2/2 passed

## Recent Changes
1. Switched from QwenPaw-Flash-4B to llama3.2:3b (10-20x faster)
2. Fixed /ask endpoint (was GET, now POST)
3. Fixed Joplin API pagination (handles has_more + offset)
4. Implemented single-pass tool calling workaround
5. Simplified system prompt (~40 lines → ~20 lines)
6. Added search/execute distinction in prompt

## Files Modified
- `.env` - LLM_MODEL=llama3.2:3b-instruct-q5_K_M
- `backend/core/config.py` - Same model update
- `backend/prompts/system.md` - Simplified prompt
- `backend/services/ollama_service.py` - Single-pass tool calling
- `backend/services/joplin_service.py` - Client-side filtering + pagination
- `backend/tools/knowledge_tools.py` - Fixed obsidian output format

## Known Issues
1. LLM sometimes calls docker_command instead of obsidian_search_notes
2. Responses still verbose (30-60s per query)
3. Joplin Clipper API doesn't return note bodies (only titles)
4. Some queries timeout at 60s

## Next Steps (when you resume)
1. Test the app with llama3.2 model
2. Try better prompts for direct responses
3. Consider Pydantic AI hybrid approach (validation only, no full migration)
4. Evaluate switching to mistral-nemo or qwen2.5:7b for better quality

## Testing Commands
```bash
# Health check
curl http://localhost:8000/health

# Run tests
source .venv/bin/activate && python -m pytest tests/unit/ -q

# Test chat
curl -X POST "http://localhost:8000/ask" -H "Content-Type: application/json" -d '{"prompt": "check disk"}'
```

## User's Open WebUI Note Location
Obsidian: `/home/jerry/obsidian/Joplin/Techs/AI/open-webui.md`
Contains the exact docker command needed.
