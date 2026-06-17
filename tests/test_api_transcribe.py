import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app

class TestApiTranscribe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We use FastAPI TestClient
        cls.client = TestClient(app)
        cls.audio_file = "test.wav"
        
        # Verify the test.wav file exists in the directory
        if not os.path.exists(cls.audio_file):
            raise FileNotFoundError(f"Test audio file '{cls.audio_file}' is missing at workspace root.")

    def test_transcribe_default_model(self):
        # Test default transcription without specifying model or language
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/stt",
                files={"file": (self.audio_file, f, "audio/wav")}
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify fields in the JSON response
        self.assertIn("text", data)
        self.assertIn("language", data)
        self.assertIn("duration", data)
        self.assertIn("latency", data)
        
        self.assertGreater(len(data["text"]), 0)
        self.assertEqual(data["language"], "en")
        self.assertGreater(data["duration"], 0.0)
        self.assertGreater(data["latency"], 0.0)
        
        print("\n[Default Model Test]")
        print(f"Text: {data['text']}")
        print(f"Language: {data['language']}")
        print(f"Duration: {data['duration']}s")
        print(f"Latency: {data['latency']}s")

    def test_transcribe_with_params_form(self):
        # Test passing model and language via Form parameters
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/stt",
                files={"file": (self.audio_file, f, "audio/wav")},
                data={"model": "tiny", "language": "en"}
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("text", data)
        self.assertEqual(data["language"], "en")
        self.assertGreater(data["duration"], 0.0)
        self.assertGreater(data["latency"], 0.0)
        
        print("\n[Form Params (tiny, en) Test]")
        print(f"Text: {data['text']}")
        print(f"Language: {data['language']}")
        print(f"Duration: {data['duration']}s")
        print(f"Latency: {data['latency']}s")

    def test_transcribe_with_params_query(self):
        # Test passing model and language via Query parameters
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/stt?model=tiny&language=en",
                files={"file": (self.audio_file, f, "audio/wav")}
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("text", data)
        self.assertEqual(data["language"], "en")
        self.assertGreater(data["duration"], 0.0)
        self.assertGreater(data["latency"], 0.0)
        
        print("\n[Query Params (tiny, en) Test]")
        print(f"Text: {data['text']}")
        print(f"Language: {data['language']}")
        print(f"Duration: {data['duration']}s")
        print(f"Latency: {data['latency']}s")

    def test_transcribe_missing_file(self):
        # Test endpoint error response when no file is uploaded
        response = self.client.post("/api/v1/stt")
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity (ValidationError)

if __name__ == "__main__":
    unittest.main()
