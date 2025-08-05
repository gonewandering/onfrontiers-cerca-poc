# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- `pipenv install` - Install dependencies from Pipfile
- `pipenv shell` - Activate virtual environment
- Set `OPENAI_API_KEY` environment variable for LLM extraction features

### Running the Application
- `python app.py` - Start the Flask development server

## Architecture Overview

This is a Flask-based expert search application using SQLAlchemy for data modeling.

### Core Components

**Data Models** (`models.py`):
- `Expert`: Main entity with name, summary, and status
- `Experience`: Time-bound work experiences linked to experts
- `Attribute`: Skills/roles with vector embeddings for search (256-dimensional)
- Uses SQLAlchemy relationships with cascade delete

**Route Structure**:
- Main routes defined in `routes.py` (currently imports only)
- Route modules in `routes/` directory:
  - `index.py`: Basic CRUD operations (stub implementation)
  - `Experts.py`: Expert-specific endpoints (placeholder)
  - `search.py`: Search functionality (placeholder)

**Libraries** (`lib/`):
- `embeddings.py`: Vector embedding utilities (placeholder)
- `profiles.py`: Profile management (placeholder)
- `llm_extractor.py`: OpenAI-powered text extraction for converting unstructured text to structured expert data

**Configuration**:
- `settings.py`: Application settings (placeholder)
- `Pipfile`: Python 3.11, Flask, Flask-RESTful, SQLAlchemy, OpenAI, Pydantic dependencies

### Key Architecture Notes

- Database uses Vector columns for semantic search capabilities
- Expert-Experience-Attribute hierarchy supports complex professional profiles
- **LLM Integration**: Expert creation supports both structured JSON and unstructured text input
  - Text input automatically extracts structured data using OpenAI GPT-4 with structured outputs
  - Uses Pydantic models for guaranteed JSON schema compliance
  - Creates complete Expert + Experience + Attribute records from resume/bio text
  - Requires `OPENAI_API_KEY` environment variable
- Many implementation files are currently placeholders/stubs
- No existing test framework or build commands identified

### API Usage Examples

**Creating Expert from structured data:**
```bash
curl -X POST http://localhost:5000/api/experts \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "summary": "Software engineer"}'
```

**Creating Expert from unstructured text:**
```bash
curl -X POST http://localhost:5000/api/experts \
  -H "Content-Type: text/plain" \
  -d "John Doe is a senior software engineer with 10 years experience at Google and Microsoft, specializing in Python, machine learning, and cloud architecture."
```