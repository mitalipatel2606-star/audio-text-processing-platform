import os
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app


class TestApiSynthesize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We use FastAPI TestClient
        cls.client = TestClient(app)

    # --- Success Synthesis and Format Tests ---

    def test_synthesize_default_wav(self):
        # Test basic success case: WAV format using JSON body payload
        payload = {
            "text": "Hello from the FastAPI TTS service.",
            "voice": "amy",
            "format": "wav"
        }
        response = self.client.post("/api/v1/tts", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        
        data = response.content
        self.assertGreater(len(data), 0)
        # Check standard WAV magic bytes
        self.assertEqual(data[0:4], b"RIFF")
        self.assertEqual(data[8:12], b"WAVE")

    def test_synthesize_mp3(self):
        # Test synthesis converting to MP3
        payload = {
            "text": "Converting synthesized speech to mp3 format.",
            "voice": "danny",
            "format": "mp3"
        }
        response = self.client.post("/api/v1/tts", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/mpeg")
        
        data = response.content
        self.assertGreater(len(data), 0)
        # MP3 files usually start with ID3 (b"ID3") or frame sync (0xFF)
        self.assertTrue(data.startswith(b"ID3") or (len(data) > 0 and data[0] == 0xFF))

    def test_synthesize_ogg(self):
        # Test synthesis converting to OGG
        payload = {
            "text": "Testing Ogg format conversion using ffmpeg.",
            "voice": "joe",
            "format": "ogg"
        }
        response = self.client.post("/api/v1/tts", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/ogg")
        
        data = response.content
        self.assertGreater(len(data), 0)
        # OGG container files always start with "OggS"
        self.assertTrue(data.startswith(b"OggS"))

    # --- Parameter Passing Methods Tests ---

    def test_parameter_parsing_form(self):
        # Test passing parameters via Form data
        response = self.client.post(
            "/api/v1/tts",
            data={"text": "Form data synthesis test.", "voice": "ryan", "format": "wav"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content[0:4], b"RIFF")

    def test_parameter_parsing_query(self):
        # Test passing parameters via Query parameters
        response = self.client.post(
            "/api/v1/tts?text=Query+string+synthesis+test&voice=lessac&format=wav"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content[0:4], b"RIFF")

    # --- Validation Error Tests ---

    def test_validation_missing_text(self):
        # Missing text parameter
        payload = {"voice": "amy", "format": "wav"}
        response = self.client.post("/api/v1/tts", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json()["detail"])

    def test_validation_empty_text(self):
        # Empty text parameter
        payload = {"text": "   ", "voice": "amy", "format": "wav"}
        response = self.client.post("/api/v1/tts", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json()["detail"])

    def test_validation_text_too_long(self):
        # Text exceeding 5000 characters limit
        long_text = "a" * 5001
        payload = {"text": long_text, "voice": "amy", "format": "wav"}
        response = self.client.post("/api/v1/tts", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("exceeds maximum length", response.json()["detail"])

    def test_validation_missing_voice(self):
        # Missing voice parameter
        payload = {"text": "Hello world", "format": "wav"}
        response = self.client.post("/api/v1/tts", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("voice", response.json()["detail"])

    def test_validation_invalid_voice(self):
        # Invalid/Unknown voice alias
        payload = {"text": "Hello world", "voice": "invalid_voice", "format": "wav"}
        response = self.client.post("/api/v1/tts", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown voice alias", response.json()["detail"])

    def test_validation_unsupported_format(self):
        # Unsupported format choice
        payload = {"text": "Hello world", "voice": "amy", "format": "mp4"}
        response = self.client.post("/api/v1/tts", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported format", response.json()["detail"])

    # --- Authentication Tests ---

    @patch.dict(os.environ, {"TTS_AUTH_TOKEN": "tts-secret-token"})
    def test_tts_unauthorized_missing_token(self):
        # Returns 401 when token is required but missing from request headers
        payload = {"text": "Authentication check.", "voice": "amy", "format": "wav"}
        response = self.client.post("/api/v1/tts", json=payload)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized: Invalid or missing authentication token")

    @patch.dict(os.environ, {"TTS_AUTH_TOKEN": "tts-secret-token"})
    def test_tts_unauthorized_invalid_token(self):
        # Returns 401 when token is incorrect
        payload = {"text": "Authentication check.", "voice": "amy", "format": "wav"}
        response = self.client.post(
            "/api/v1/tts",
            json=payload,
            headers={"Authorization": "Bearer bad-token"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized: Invalid or missing authentication token")

    @patch.dict(os.environ, {"TTS_AUTH_TOKEN": "tts-secret-token"})
    def test_tts_authorized_success(self):
        # Returns 200 when valid token is supplied
        payload = {"text": "Authentication check with valid token.", "voice": "amy", "format": "wav"}
        response = self.client.post(
            "/api/v1/tts",
            json=payload,
            headers={"Authorization": "Bearer tts-secret-token"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content[0:4], b"RIFF")


if __name__ == "__main__":
    unittest.main()
