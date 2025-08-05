# Prompt Templates

This directory contains JSON templates for structured LLM extraction tasks. Each template defines:

- **system_prompt**: Instructions for the LLM on how to perform the task
- **user_prompt_template**: Template for user input with placeholders for variables
- **response_schema**: JSON schema defining the expected output structure
- **metadata**: Configuration including model, temperature, and description

## Template Structure

```json
{
  "system_prompt": "Instructions for the LLM...",
  "user_prompt_template": "Template with {variables}...",
  "response_schema": {
    "type": "object",
    "properties": {...}
  },
  "metadata": {
    "name": "Template Name",
    "description": "What this template does",
    "version": "1.0",
    "model": "gpt-4o-mini",
    "temperature": 0.1
  }
}
```

## Usage

```python
from lib.llm_extractor import LLMExtractor

extractor = LLMExtractor()

# Using a template
result = extractor.extract_from_template(
    "expert_extraction", 
    {"text": "John Doe worked at Google..."}
)

# Direct extraction
result = extractor.extract_structured_data(
    system_prompt="...",
    user_prompt="...",
    response_schema={...}
)
```

## Available Templates

- **expert_extraction.json**: Extracts professional information from resumes/bios