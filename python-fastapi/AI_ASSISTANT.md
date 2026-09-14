# Juice Shop AI Assistant

This adds a FastAPI RAG service that indexes the live Juice Shop catalog into ChromaDB and answers product, pricing, and comparison questions from the retrieved product information.

## Run it

The complete stack can be started from the repository root with:

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

This starts Juice Shop, the FastAPI assistant, and ChromaDB. The assistant waits for the catalog service and indexes products into the persistent `chroma-data` volume. The frontend's floating drink icon opens the chatbot and sends questions to the assistant at `http://localhost:8000`.

Follow these steps:

1. Install Docker Desktop and make sure Docker is running.
2. Confirm `.env` contains a valid `OPEN_AI_KEY`. Do not commit this file.
3. From the repository root, run `git pull`, then `docker compose -f infrastructure/docker-compose.yml up --build`.

4. Open `http://localhost:8080` and click the floating drink icon. Set `HTTP_PORT=80` if port 80 is available and you prefer `http://localhost`.
5. Ask a product, pricing, or comparison question.
6. Stop the stack with `Ctrl+C`, or run `docker compose -f infrastructure/docker-compose.yml down`.

The first build downloads the assistant dependencies and the first assistant startup creates OpenAI embeddings. Later restarts reuse the persistent Chroma volume. To remove the indexed data as well, run `docker compose -f infrastructure/docker-compose.yml down -v`.

For local development without Docker, with the virtual environment active:

```bash
.venv/bin/python -m pip install -r python-fastapi/requirements-ai.txt
.venv/bin/uvicorn --app-dir python-fastapi ai_assistant:app --reload --port 8000
```

The Juice Shop application must be running at `http://localhost:3000` by default, and ChromaDB must be available at `http://localhost:8001` locally. Set `JUICE_SHOP_URL`, `CHROMA_HOST`, and `CHROMA_PORT` to use other locations. The service reads `OPEN_AI_KEY` from `.env`, uses `text-embedding-3-small` for embeddings, and uses `gpt-4o-mini` for answers by default. Set `OPENAI_MODEL` or `OPENAI_EMBEDDING_MODEL` to change the models.

## Request

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Compare the cheapest apple and fruit juices"}'
```

The response includes the answer, the catalog products used to form it, and an `ai_enabled` flag. A valid OpenAI key is required for embeddings and AI answers.

To manually refresh the vector index after catalog changes:

```bash
curl -X POST http://localhost:8000/ingest
```

## Tests

```bash
.venv/bin/python -m unittest discover -s python-fastapi -p 'test_*.py' -v
```