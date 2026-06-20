import os
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app


class TestApiNlu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # --- Intent Classification Tests ---

    def test_intent_matching_all_classes(self):
        # Maps query inputs to their expected intent class
        test_cases = {
            "Hello there, good morning!": "greet",
            "Please close the application and exit": "goodbye",
            "Where can I find instructions and help?": "help",
            "Please transcribe this voice recording": "transcribe_audio",
            "Synthesize this text to audio": "synthesize_speech",
            "Show me the MOS scores and survey analytics": "get_survey_results",
            "Check if the backend system is healthy": "check_health",
            "Analyze this sentence and extract POS tags": "nlp_analyze",
            "Clear all database records and survey data": "clear_data",
            "What is the weather forecast for today?": "get_weather",
        }

        for text, expected_intent in test_cases.items():
            response = self.client.post("/api/v1/nlu", json={"text": text})
            self.assertEqual(response.status_code, 200, f"Failed on text: {text}")
            data = response.json()
            self.assertEqual(data["intent"], expected_intent, f"Failed for text '{text}': expected {expected_intent}, got {data['intent']}")
            self.assertGreaterEqual(data["confidence"], 0.85)

    def test_intent_fallback_below_threshold(self):
        # A completely random query should classify as "unknown" with 0.0 confidence
        query = "purple flying elephants eating space dust in a simulation"
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["intent"], "unknown")
        self.assertEqual(data["confidence"], 0.0)

    # --- NLP Structures Tests (NER & POS) ---

    def test_entity_extraction(self):
        # "Google" is recognized as an ORG (Organization) and "California" as a GPE (Geopolitical Entity)
        query = "Google is an organization based in California."
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        entities = data["entities"]
        self.assertGreaterEqual(len(entities), 1)
        
        # Verify entity schema structure
        for ent in entities:
            self.assertIn("text", ent)
            self.assertIn("label", ent)
            self.assertIn("start", ent)
            self.assertIn("end", ent)
            self.assertIsInstance(ent["start"], int)
            self.assertIsInstance(ent["end"], int)

        texts = [e["text"] for e in entities]
        labels = [e["label"] for e in entities]
        
        # Check standard extraction labels or existence
        self.assertTrue(any(t in ["Google", "California"] for t in texts))

    def test_pos_tagging_structure(self):
        query = "Verify pos tagging structure."
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        pos_tags = data["pos_tags"]
        self.assertGreater(len(pos_tags), 0)
        
        for token in pos_tags:
            self.assertIn("text", token)
            self.assertIn("pos", token)
            self.assertIn("tag", token)
            self.assertIn("dep", token)

    # --- Sentiment Analysis Tests ---

    def test_sentiment_positive(self):
        query = "This is a great and wonderful day, I enjoy it."
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        sentiment = data["sentiment"]
        self.assertEqual(sentiment["label"], "positive")
        self.assertGreater(sentiment["score"], 0.1)

    def test_sentiment_negative(self):
        query = "We had a terrible slow error and awful failure."
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        sentiment = data["sentiment"]
        self.assertEqual(sentiment["label"], "negative")
        self.assertLess(sentiment["score"], -0.1)

    def test_sentiment_neutral(self):
        query = "The table is wooden."
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        sentiment = data["sentiment"]
        self.assertEqual(sentiment["label"], "neutral")
        self.assertEqual(sentiment["score"], 0.0)

    def test_sentiment_negation_positive_word(self):
        # "not good" should resolve as negative sentiment due to negation check
        query = "The service was not good."
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        sentiment = data["sentiment"]
        self.assertEqual(sentiment["label"], "negative")
        self.assertLess(sentiment["score"], 0.0)

    def test_sentiment_negation_negative_word(self):
        # "no slow error" should resolve as positive due to negation of negative
        query = "There was no error."
        response = self.client.post("/api/v1/nlu", json={"text": query})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        sentiment = data["sentiment"]
        self.assertEqual(sentiment["label"], "positive")
        self.assertGreater(sentiment["score"], 0.0)

    # --- Parameter Passing Methods Tests ---

    def test_parameter_parsing_form(self):
        response = self.client.post("/api/v1/nlu", data={"text": "Hello form parameters"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "greet")

    def test_parameter_parsing_query(self):
        response = self.client.post("/api/v1/nlu?text=Help+me+please")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "help")

    def test_validation_missing_text(self):
        response = self.client.post("/api/v1/nlu", json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.json()["detail"])

    # --- Authentication Tests ---

    @patch.dict(os.environ, {"NLU_AUTH_TOKEN": "nlu-secret-token"})
    def test_nlu_unauthorized_missing_token(self):
        response = self.client.post("/api/v1/nlu", json={"text": "hello"})
        self.assertEqual(response.status_code, 401)

    @patch.dict(os.environ, {"NLU_AUTH_TOKEN": "nlu-secret-token"})
    def test_nlu_authorized_success(self):
        response = self.client.post(
            "/api/v1/nlu",
            json={"text": "hello"},
            headers={"Authorization": "Bearer nlu-secret-token"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "greet")


if __name__ == "__main__":
    unittest.main()
