# Decision Router Service (`services/decision-router`)

The Decision Router evaluates incoming natural language prompts and determines the fastest, most cost-effective path for execution.

## System One vs. System Two
1. **System One (Fast Path):**
   - Sub-50ms non-autoregressive classifier evaluating intent (`file_management`, `reminder`, `web_research`, `general_query`).
   - If confidence is high and parameters can be extracted directly (e.g. *"Organize downloads"*), it creates the task immediately without invoking heavy generative LLMs.
2. **System Two (LLM Extraction):**
   - If the instruction is complex, ambiguous, or multi-step, the router queries the local LLM (`qwen2.5:7b` via Ollama) to extract structured function call arguments.

## REST Endpoints
- `GET /health` & `GET /ready`: Health check endpoints.
- `POST /api/v1/router/classify`: Classify a prompt and return the `RouteDecision`.
- `POST /api/v1/router/dispatch`: Classify, extract parameters, and automatically create the task in `task-service`.

## Running Locally
```powershell
$env:PYTHONPATH="packages/contracts/src;services/decision-router/src"
.venv\Scripts\uvicorn decision_router.main:app --host 0.0.0.0 --port 8002 --reload
```
Interactive docs at: `http://localhost:8002/docs`
