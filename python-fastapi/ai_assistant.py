from __future__ import annotations

import os
import asyncio
from typing import Any

import httpx
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

JUICE_SHOP_URL = os.getenv("JUICE_SHOP_URL", "http://localhost:3000").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "juice_shop_products")

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Populate Chroma after the dependent Juice Shop and Chroma services are ready.
    for _ in range(12):
        try:
            products = await get_products()
            index_products(products)
            break
        except Exception:
            await asyncio.sleep(5)
    yield


app = FastAPI(title="Juice Shop AI Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AI_ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class Product(BaseModel):
    id: int | None = None
    name: str
    description: str = ""
    price: float
    deluxePrice: float | None = None
    image: str | None = None


class ChatResponse(BaseModel):
    answer: str
    products: list[Product]
    ai_enabled: bool


def chroma_collection():
    # Use OpenAI embeddings so catalog text and user questions share one vector space.
    api_key = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPEN_AI_KEY is required to create product embeddings")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    embedding_function = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_function,
        metadata={"description": "Juice Shop product information"},
    )


def index_products(products: list[Product]) -> int:
    # Upsert makes re-indexing safe when product descriptions or prices change.
    collection = chroma_collection()
    if not products:
        return 0
    collection.upsert(
        ids=[str(product.id or product.name) for product in products],
        documents=[f"{product.name}\n{product.description}" for product in products],
        metadatas=[product.model_dump(exclude_none=True) for product in products],
    )
    return len(products)


def retrieve_products(message: str, limit: int = 8) -> list[Product]:
    # Retrieve only the catalog records most semantically related to the question.
    collection = chroma_collection()
    result = collection.query(query_texts=[message], n_results=limit)
    metadatas = result.get("metadatas", [[]])[0]
    return [Product.model_validate(metadata) for metadata in metadatas]


async def get_products() -> list[Product]:
    """Read the catalog from the Juice Shop API, keeping prices authoritative."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{JUICE_SHOP_URL}/rest/products/search", params={"q": ""})
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="The Juice Shop catalog is unavailable") from error

    payload: Any = response.json()
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    return [Product.model_validate(row) for row in rows]


def find_relevant_products(message: str, products: list[Product]) -> list[Product]:
    terms = {term.lower() for term in message.split() if len(term) > 2}
    if not terms:
        return products[:8]

    matches = [
        product
        for product in products
        if any(term in f"{product.name} {product.description}".lower() for term in terms)
    ]
    return matches[:8] or sorted(products, key=lambda product: product.price)[:5]


def fallback_answer(message: str, products: list[Product]) -> str:
    if not products:
        return "I could not find any matching juices in the catalog."

    ranked = sorted(products, key=lambda product: product.price)
    if any(word in message.lower() for word in ("compare", "comparison", "best", "cheapest")):
        choices = "; ".join(f"{product.name} (${product.price:.2f})" for product in ranked[:3])
        return f"For value, compare these options: {choices}. The least expensive is {ranked[0].name}."

    details = "; ".join(f"{product.name} costs ${product.price:.2f}" for product in products[:5])
    return f"Here is what I found: {details}. Ask me to compare them if you want a recommendation."


def openai_answer(message: str, products: list[Product]) -> str:
    api_key = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_answer(message, products)

    catalog = "\n".join(
        f"- {product.name}: ${product.price:.2f}. {product.description}" for product in products
    )
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=(
            "You are a concise juice shop assistant. Answer only from the supplied catalog. "
            "Help with product details, pricing, and comparisons. Never invent a product, price, "
            "ingredient, health claim, or availability. If the catalog is insufficient, say so."
        ),
        input=f"Catalog:\n{catalog}\n\nCustomer question: {message}",
    )
    return response.output_text


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest")
async def ingest() -> dict[str, int]:
    # Expose manual refresh for catalog changes made after startup.
    products = await get_products()
    return {"indexed_products": index_products(products)}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Ground the LLM prompt in Chroma results instead of the entire catalog.
    try:
        relevant_products = retrieve_products(request.message)
    except Exception as error:
        raise HTTPException(status_code=503, detail="The product knowledge base is unavailable") from error

    if not relevant_products:
        products = await get_products()
        relevant_products = find_relevant_products(request.message, products)
    try:
        answer = openai_answer(request.message, relevant_products)
    except Exception as error:
        raise HTTPException(status_code=502, detail="The AI provider is unavailable") from error

    return ChatResponse(
        answer=answer,
        products=relevant_products,
        ai_enabled=bool(os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")),
    )