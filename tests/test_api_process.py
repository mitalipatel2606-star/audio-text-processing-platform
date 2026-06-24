import os
import sys
import unittest
import base64
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app

class TestApiProcess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.audio_file = "test.wav"
        
        # Verify the test.wav file exists in the directory
        if not os.path.exists(cls.audio_file):
            raise FileNotFoundError(f"Test audio file '{cls.audio_file}' is missing at workspace root.")

    def test_process_success(self):
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/process",
                files={"file": (self.audio_file, f, "audio/wav")}
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify JSON keys
        self.assertIn("input_text", data)
        self.assertIn("nlu_data", data)
        self.assertIn("audio_response_base64", data)
        self.assertIn("audio_format", data)
        self.assertIn("latency", data)
        
        self.assertGreater(len(data["input_text"]), 0)
        self.assertEqual(data["audio_format"], "wav")
        self.assertGreater(len(data["audio_response_base64"]), 0)
        
        # Verify nlu_data structure
        self.assertIn("intent", data["nlu_data"])
        self.assertIn("entities", data["nlu_data"])
        self.assertIn("sentiment", data["nlu_data"])
        
        # Verify base64 audio can be decoded and looks like WAV
        audio_bytes = base64.b64decode(data["audio_response_base64"])
        self.assertGreater(len(audio_bytes), 0)
        self.assertEqual(audio_bytes[0:4], b"RIFF")
        self.assertEqual(audio_bytes[8:12], b"WAVE")

    def test_process_with_params(self):
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/process",
                files={"file": (self.audio_file, f, "audio/wav")},
                data={"tts_voice": "ryan", "tts_format": "mp3"}
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["audio_format"], "mp3")
        self.assertGreater(len(data["audio_response_base64"]), 0)
        
        audio_bytes = base64.b64decode(data["audio_response_base64"])
        self.assertGreater(len(audio_bytes), 0)

if __name__ == "__main__":
    unittest.main()
