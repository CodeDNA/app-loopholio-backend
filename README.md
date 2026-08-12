# Loopholio

**AI-powered Terms of Service analyzer built with LangGraph, FastAPI, Next.js, and IBM Docling.**

🌐 **Live:** https://loopholio.codedna.io

Loopholio analyzes Terms of Service documents and converts dense legal text into structured, traceable risk reports. It uses a multi-agent AI pipeline to extract important clauses, identify potential risks, explain them in plain English, and generate an evidence-backed report.

## Features

- Upload and analyze Terms of Service documents
- Analyze pasted Terms of Service text
- Structure-aware document parsing and chunking with IBM Docling
- Multi-agent analysis pipeline built with LangGraph
- Parallel processing of document chunks
- Structured LLM outputs using LangChain and Pydantic
- Clause-level risk detection and legal reasoning
- Plain-English explanations and recommendations
- Source-text traceability for identified risks
- Streaming analysis results to the frontend
- Redis-based IP rate limiting
- Concurrent-analysis protection
- Request and document-size limits
- Production deployment using Vercel and Google Cloud Run
- Secure secret management using Google Secret Manager
- LangSmith tracing and observability

---

## Architecture

```text
                         User
                          │
                          ▼
               ┌─────────────────────┐
               │   Next.js Frontend  │
               │       Vercel        │
               └──────────┬──────────┘
                          │
                   /api/analyze-tos
                          │
                          ▼
               ┌─────────────────────┐
               │  Next.js API Route  │
               │   Server-side Proxy │
               └──────────┬──────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │   Google Cloud Run  │
               │       FastAPI       │
               └──────────┬──────────┘
                          │
                 Validation & Limits
                          │
                          ▼
               ┌─────────────────────┐
               │   Upstash Redis     │
               │    Rate Limiting    │
               └──────────┬──────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │     IBM Docling     │
               │    HybridChunker    │
               └──────────┬──────────┘
                          │
                          ▼
                  LangGraph Pipeline
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
   Document Chunk 1                Document Chunk N
          │                               │
          ▼                               ▼
   Clause Extraction               Clause Extraction
          │                               │
          ▼                               ▼
    Risk Detection                  Risk Detection
          │                               │
          └───────────────┬───────────────┘
                          ▼
                     Explainer
                          │
                          ▼
                 Report Generation
                          │
                          ▼
                  Structured Report
                          │
                          ▼
                       User
```

---

## AI Pipeline

Loopholio uses a specialized multi-agent workflow instead of sending an entire document through a single LLM prompt.

### 1. Document Parsing

Uploaded documents are processed using **IBM Docling**.

`HybridChunker` creates structure-aware chunks while preserving document context required by downstream agents.

### 2. Clause Extraction

Each document chunk is independently analyzed to identify important legal clauses, obligations, restrictions, and other risk-prone sections.

Clause extraction is executed in parallel across document chunks using LangGraph fan-out.

### 3. Risk Detection

Extracted clauses are passed to the risk-detection agent.

The agent determines whether a clause represents a potential risk and produces structured information including:

- Risk category
- Confidence
- Legal reasoning
- Supporting evidence
- Original source text

### 4. Plain-English Explanation

Detected risks are transformed into user-friendly explanations describing:

- Risk level
- Why the clause matters
- Potential impact on the user
- Recommended action

### 5. Report Generation

The final stage combines the analyzed risks into a structured report while preserving the original clause/source text for traceability.

---

## Structured AI Outputs

LLM responses are constrained using **LangChain structured outputs and Pydantic models**.

This provides predictable contracts between agents instead of relying on arbitrary free-form LLM responses.

Conceptually:

```text
Document Chunk
      │
      ▼
ExtractedClause
      │
      ▼
DetectedRisk
      │
      ▼
ExplainedRisk
      │
      ▼
RiskReportItem
```

This makes the pipeline easier to validate, debug, and extend.

---

## Parallel Processing

Loopholio uses LangGraph fan-out to process independent chunks concurrently.

Instead of:

```text
Chunk 1 → Chunk 2 → Chunk 3 → Chunk 4
```

the pipeline can execute:

```text
             ┌─ Chunk 1 ─→ Agents
             │
Document ────├─ Chunk 2 ─→ Agents
             │
             ├─ Chunk 3 ─→ Agents
             │
             └─ Chunk 4 ─→ Agents
```

This reduces the amount of unnecessary sequential processing for large documents.

---

## Abuse & Cost Protection

Because every analysis can generate external LLM usage, the production backend implements multiple protection layers.

### Input Limits

The backend enforces:

| Limit                   |             Value |
| ----------------------- | ----------------: |
| Maximum file size       |              5 MB |
| Minimum text length     |    100 characters |
| Maximum text length     | 50,000 characters |
| Maximum document chunks |                25 |

Equivalent validation is also performed in the frontend where appropriate for faster user feedback.

### IP Rate Limiting

Rate-limit state is stored in **Upstash Redis**.

Current production limits:

| Limit               |    Value |
| ------------------- | -------: |
| Analyses per hour   | 2 per IP |
| Analyses per day    | 5 per IP |
| Concurrent analyses | 1 per IP |

Redis TTL-based keys automatically expire after their corresponding rate-limit windows.

A distributed lock prevents the same client from starting multiple expensive analyses simultaneously.

The lock is released in a `finally` block so unexpected pipeline failures do not permanently lock a client out.

### LLM Cost Protection

The OpenAI project also has a configured monthly spending limit as an additional protection against unexpected API usage.

---

## Proxy Security

The browser communicates with the Next.js API route rather than directly with Cloud Run:

```text
Browser
   ↓
Next.js /api/analyze-tos
   ↓
Cloud Run /analyze-document
```

The server-side proxy forwards the client IP to the backend for rate limiting.

Communication between the proxy and backend is protected using a server-side proxy secret.

The secret is never exposed through a `NEXT_PUBLIC_*` environment variable.

---

## Tech Stack

### Frontend

- Next.js
- React
- TypeScript
- Vercel

### Backend

- Python 3.12
- FastAPI
- Pydantic
- Uvicorn

### AI / Document Processing

- LangGraph
- LangChain
- IBM Docling
- Docling HybridChunker
- OpenAI
- LangSmith

### Infrastructure

- Docker
- Docker Buildx
- Google Cloud Run
- Google Artifact Registry
- Google Secret Manager
- Upstash Redis
- Vercel
- Google Cloud DNS

---

## API

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Analyze Document

```http
POST /analyze-document
```

Processes a Terms of Service document or supported analysis input through the Loopholio pipeline.

The production frontend accesses this endpoint through the Next.js server-side API proxy rather than calling Cloud Run directly from the browser.

---

## Environment Variables

The backend uses environment variables for external services and model configuration.

Examples include:

```env
OPENAI_API_KEY=
TAVILY_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=Loopholio
LANGSMITH_ENDPOINT=

DEFAULT_LLM_PROVIDER=
DEFAULT_OPENAI_MODEL=

LOOPHOLIO_PROXY_SECRET=
```

Production secrets should **never** be committed to the repository.

Sensitive backend values are stored using **Google Secret Manager** and injected into Cloud Run at deployment/runtime.

The frontend/server proxy stores its corresponding secrets using Vercel environment variables.

---

## Local Development

### Backend

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install the project:

```bash
pip install .
```

Configure the required environment variables and start FastAPI:

```bash
uvicorn app.main:app --reload
```

The backend will normally be available at:

```text
http://localhost:8000
```

### Frontend

Install dependencies:

```bash
npm install
```

Start the Next.js development server:

```bash
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

## Docker

The backend is containerized using Python 3.12.

The Dockerfile is structured so dependency installation is cached independently from application source code.

Conceptually:

```dockerfile
COPY pyproject.toml ./
COPY app/__init__.py ./app/__init__.py

RUN python -m pip install \
    --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    .

COPY app ./app
```

This means changing normal application code does not require reinstalling large dependencies such as Docling and PyTorch on every build.

The initial dependency build can take several minutes, while subsequent code-only builds can reuse the cached dependency layer.

### Build Production Image

The production Cloud Run image targets `linux/amd64`:

```bash
docker buildx build \
  --platform linux/amd64 \
  -t <ARTIFACT_REGISTRY_IMAGE>:<VERSION> \
  --push \
  .
```

Versioned container tags are used so deployments can be identified and rolled back independently.

---

## Production Deployment

### Frontend

The Next.js application is deployed on **Vercel**.

Production domain:

**https://loopholio.codedna.io**

The subdomain is configured through DNS and secured with HTTPS.

### Backend

The FastAPI backend runs as a Docker container on **Google Cloud Run**.

Container images are stored in **Google Artifact Registry**.

Deployment flow:

```text
Backend source
     ↓
Docker Buildx
     ↓
Artifact Registry
     ↓
Cloud Run revision
```

Application secrets are stored separately in Google Secret Manager and made available to the Cloud Run service through IAM-controlled secret access.

---

## Observability

Loopholio integrates with **LangSmith** for tracing the agent pipeline.

Tracing helps inspect:

- Agent execution
- LLM calls
- Structured outputs
- Pipeline failures
- Token usage
- Execution flow across LangGraph nodes

Cloud Run logs provide additional backend application and infrastructure visibility.

---

## Design Goals

Loopholio was designed around several principles:

**Traceability**
Risk findings retain their relationship to the original Terms of Service text.

**Structured communication**
Agents exchange validated structured data rather than loosely formatted text.

**Specialization**
Clause extraction, risk detection, explanation, and report generation are handled as separate responsibilities.

**Parallelism**
Independent document chunks can move through portions of the workflow concurrently.

**Cost awareness**
Input limits, rate limiting, concurrency controls, and external API spending limits reduce the risk of uncontrolled LLM usage.

**Production readiness**
The system is containerized, deployed behind HTTPS, uses managed secrets, distributed Redis state, health checks, and production observability.

---

## Disclaimer

Loopholio provides AI-generated analysis intended to help users understand Terms of Service documents.

It is **not a substitute for professional legal advice**. AI-generated results may be incomplete or inaccurate, and users should consult a qualified legal professional when making decisions with legal consequences.

---

## Future Improvements

- User authentication and account-based quotas
- More robust Vercel-to-Cloud Run authentication
- Risk consolidation and deduplication across document sections
- CI/CD deployment pipeline
- Expanded document-format support
- Additional model/provider evaluation
- Improved production monitoring and alerting

---

## Author

**Prabhakar Punj Lal**

Software Engineer

Built as an end-to-end exploration of production AI engineering, multi-agent orchestration, structured LLM workflows, document processing, distributed rate limiting, and cloud deployment.
