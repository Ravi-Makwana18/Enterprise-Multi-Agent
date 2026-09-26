# Enterprise Multi-Agent Platform

A Python FastAPI + LangGraph-based multi-agent system for handling different enterprise use cases such as blog review, salary processing, security checks, and support ticket generation.

This project is structured as a local prototype first, with a clear path toward AWS Bedrock integration for real LLM-based agent processing.

## Project overview

The application routes incoming user requests to a specific agent based on the message content. The main workflow is managed with LangGraph.

Supported agent categories:
- Blog review / rewrite workflow
- Salary calculation
- Security field verification
- Support ticket generation

## Architecture

### Backend
- FastAPI app entry point: `backend/main.py`
- LangGraph orchestrator: `backend/workflows/langgraph_orchestrator.py`
- Workflow definitions: `backend/workflows/blog_workflow.py`
- Service layer: `backend/services/`
- Agent logic: `backend/agents/`
- Models: `backend/models/`

### Frontend
- React + Vite app in `frontend/`
- Connects to the backend through a local proxy

## Core workflow

The orchestration flow is defined in `backend/workflows/langgraph_orchestrator.py`.

Typical route selection:
- if input contains "blog" -> blog workflow
- if input contains "salary" -> salary agent
- if input contains "security" -> security agent
- otherwise -> support ticket agent

The blog workflow itself uses review and revise steps inside `backend/workflows/blog_workflow.py`.

## Important files

- `backend/main.py` – FastAPI API entry point
- `backend/workflows/langgraph_orchestrator.py` – main routing graph
- `backend/workflows/blog_workflow.py` – blog review/revise graph
- `backend/services/bedrock_service.py` – local/AWS Bedrock abstraction
- `backend/services/ticket_service.py` – in-memory ticket system
- `backend/services/salary_service.py` – salary calculations
- `backend/services/security_service.py` – security validation
- `backend/agents/` – individual agent implementations

## Local setup

### 1. Create virtual environment

```bash
python -m venv .venv
```

### 2. Activate virtual environment

Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Run backend

From project root:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

API endpoints:
- `GET /health`
- `POST /chat`
- `GET /ticket/{ticket_id}`

## Run frontend

From project root:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Then open:
- `http://localhost:5173`

## API example

### Chat request

```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"blog about AI"}'
```

## AWS / Bedrock readiness

The project includes a Bedrock service wrapper in `backend/services/bedrock_service.py`.

Current status:
- Local demo mode is supported
- AWS Bedrock integration is implemented in structure, but real AWS configuration is still required for production use

Required environment variables for AWS usage:

```env
LOCAL_MODE=false
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

This project is intended as a local enterprise agent prototype, and the AWS layer is designed to be extended cleanly when real cloud services are connected.

## Current limitations

- Most workflows are demo-style and use mock/local responses
- The ticket system stores data in memory only
- Security and salary services are sample logic, not production enterprise services
- Blog review depends on local or AWS LLM output depending on configuration
- No database or persistent storage is currently implemented

## Suggested next steps

1. Add persistent storage (Postgres / DynamoDB / S3 depending on use case)
2. Replace mock salary/security logic with real enterprise APIs
3. Add AWS IAM configuration and Bedrock model validation
4. Add authentication and authorization
5. Improve agent orchestration with real LLM intent classification
6. Add tests for each agent workflow and API contract

## Notes

This repository is best understood as a multi-agent demo platform for:
- enterprise orchestration patterns
- LangGraph routing
- Python API service design
- frontend integration with agent workflows
- future AWS Bedrock-based AI orchestration

## License

This project is for learning and internal prototype use unless otherwise specified.
