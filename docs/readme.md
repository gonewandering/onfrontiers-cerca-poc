Local development quick start

- macOS note: AirPlay Receiver often uses port 5000. This app defaults to port 5001 to avoid conflicts. If you want a different port, export PORT accordingly.

Steps

1) Copy the example env and customize it (auto-loaded via python-dotenv):
   - cp .env.example .env
   - Edit .env with your DB credentials and OpenAI key

2) Install deps (pipenv or pip):
   - pip install -r requirements.txt  (or pipenv install)

3) Run:
   - python app.py

4) Verify:
   - curl http://127.0.0.1:5001/health
   - Open http://127.0.0.1:5001/ui/search

Troubleshooting

- If you get a 403 on http://localhost:5000, you're likely hitting macOS AirPlay. Use http://localhost:5001 instead or change PORT.
- The search endpoint requires:
  - A reachable Postgres with pgvector and populated tables (attribute, experience, expert, experience_attribute).
  - A valid OpenAI API key for LLM extraction and embeddings.
