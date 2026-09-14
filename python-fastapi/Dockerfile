FROM python:3.12-slim

WORKDIR /app

COPY requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements-ai.txt

COPY ai_assistant.py ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "ai_assistant:app", "--host", "0.0.0.0", "--port", "8000"]
