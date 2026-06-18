import os
import sys
import unittest
import subprocess
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
            
        # Dynamically generate different audio formats from test.wav using ffmpeg
        cls.generated_formats = []
        for ext in [".mp3", ".webm", ".flac", ".ogg"]:
            target_path = f"test{ext}"
            print(f"Generating temporary test audio file: {target_path}")
            command = ["ffmpeg", "-y", "-i", cls.audio_file, target_path]
            try:
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                cls.generated_formats.append(target_path)
            except Exception as e:
                print(f"Warning: Failed to generate {target_path} using FFmpeg: {e}")

    @classmethod
    def tearDownClass(cls):
        # Clean up generated format files
        for path in cls.generated_formats:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Removed temporary test file: {path}")
                except Exception as e:
                    print(f"Failed to remove {path}: {e}")

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

    def test_transcribe_mp3(self):
        target = "test.mp3"
        self.assertTrue(os.path.exists(target), f"Test file {target} should exist.")
        with open(target, "rb") as f:
            response = self.client.post(
                "/api/v1/stt?model=tiny",
                files={"file": (target, f, "audio/mp3")}
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("text", data)
        self.assertGreater(len(data["text"]), 0)
        self.assertEqual(data["language"], "en")
        print(f"\n[MP3 Transcribed Text]: {data['text']}")

    def test_transcribe_webm(self):
        target = "test.webm"
        self.assertTrue(os.path.exists(target), f"Test file {target} should exist.")
        with open(target, "rb") as f:
            response = self.client.post(
                "/api/v1/stt?model=tiny",
                files={"file": (target, f, "audio/webm")}
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("text", data)
        self.assertGreater(len(data["text"]), 0)
        self.assertEqual(data["language"], "en")
        print(f"\n[WebM Transcribed Text]: {data['text']}")

    def test_transcribe_flac(self):
        target = "test.flac"
        self.assertTrue(os.path.exists(target), f"Test file {target} should exist.")
        with open(target, "rb") as f:
            response = self.client.post(
                "/api/v1/stt?model=tiny",
                files={"file": (target, f, "audio/flac")}
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("text", data)
        self.assertGreater(len(data["text"]), 0)
        self.assertEqual(data["language"], "en")
        print(f"\n[FLAC Transcribed Text]: {data['text']}")

    def test_transcribe_ogg(self):
        target = "test.ogg"
        self.assertTrue(os.path.exists(target), f"Test file {target} should exist.")
        with open(target, "rb") as f:
            response = self.client.post(
                "/api/v1/stt?model=tiny",
                files={"file": (target, f, "audio/ogg")}
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("text", data)
        self.assertGreater(len(data["text"]), 0)
        self.assertEqual(data["language"], "en")
        print(f"\n[OGG Transcribed Text]: {data['text']}")

    def test_transcribe_missing_file(self):
        # Test endpoint error response when no file is uploaded
        response = self.client.post("/api/v1/stt")
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity (ValidationError)

if __name__ == "__main__":
    unittest.main()
