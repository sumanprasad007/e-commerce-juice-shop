import os
import unittest
from unittest.mock import AsyncMock, patch

import ai_assistant
from fastapi.testclient import TestClient


class AssistantTests(unittest.TestCase):
    def test_health(self) -> None:
        response = TestClient(ai_assistant.app).get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_chat_uses_catalog_and_fallback(self) -> None:
        products = [
            ai_assistant.Product(name="Apple Juice", description="Crisp apple blend", price=1.99),
            ai_assistant.Product(name="Fruit Press", description="Mixed fruit juice", price=3.49),
        ]
        with patch.object(ai_assistant, "retrieve_products", return_value=products):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("OPEN_AI_KEY", None)
                os.environ.pop("OPENAI_API_KEY", None)
                response = TestClient(ai_assistant.app).post(
                    "/chat", json={"message": "compare apple juice pricing"}
                )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["ai_enabled"])
        self.assertIn("Apple Juice", response.json()["answer"])
        self.assertEqual(response.json()["products"][0]["price"], 1.99)