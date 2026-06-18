import os
import sys
import unittest
import subprocess
from unittest.mock import patch, MagicMock, mock_open
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

    # --- Authentication Tests ---
    
    @patch.dict(os.environ, {"STT_AUTH_TOKEN": "secret-token"})
    def test_transcribe_unauthorized_missing_token(self):
        # Test 401 when token is missing
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/stt",
                files={"file": (self.audio_file, f, "audio/wav")}
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized: Invalid or missing authentication token")

    @patch.dict(os.environ, {"STT_AUTH_TOKEN": "secret-token"})
    def test_transcribe_unauthorized_invalid_token(self):
        # Test 401 when token is incorrect
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/stt",
                files={"file": (self.audio_file, f, "audio/wav")},
                headers={"Authorization": "Bearer wrong-token"}
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized: Invalid or missing authentication token")

    @patch.dict(os.environ, {"STT_AUTH_TOKEN": "secret-token"})
    def test_transcribe_authorized_success(self):
        # Test 200 when token is correct
        with open(self.audio_file, "rb") as f:
            response = self.client.post(
                "/api/v1/stt",
                files={"file": (self.audio_file, f, "audio/wav")},
                headers={"Authorization": "Bearer secret-token"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text", response.json())

    # --- Transcribe & Audio Formats Tests ---

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
        self.assertEqual(data["language"], "en")

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
        self.assertEqual(data["language"], "en")

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
        self.assertEqual(data["language"], "en")

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
        self.assertEqual(data["language"], "en")

    def test_transcribe_missing_file(self):
        response = self.client.post("/api/v1/stt")
        self.assertEqual(response.status_code, 422)

    # --- Health Check Tests ---

    @patch("backend.main.get_redis_client")
    def test_health_check_redis_connected(self, mock_get_redis):
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_get_redis.return_value = mock_client
        
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redis"], "connected")

    @patch("backend.main.get_redis_client")
    def test_health_check_redis_disconnected(self, mock_get_redis):
        mock_get_redis.return_value = None
        
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redis"], "disconnected")

    @patch("backend.main.get_redis_client")
    def test_health_check_redis_ping_fail(self, mock_get_redis):
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection Refused")
        mock_get_redis.return_value = mock_client
        
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redis"], "connection_failed")

    # --- Survey Configuration Tests ---

    @patch("os.path.exists")
    def test_get_survey_config_success(self, mock_exists):
        mock_exists.return_value = True
        mock_data = '{"survey_name": "Test Survey", "tts": [], "stt": []}'
        
        with patch("builtins.open", mock_open(read_data=mock_data)):
            response = self.client.get("/api/survey-config")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["survey_name"], "Test Survey")

    @patch("os.path.exists")
    def test_get_survey_config_not_found(self, mock_exists):
        mock_exists.return_value = False
        response = self.client.get("/api/survey-config")
        self.assertEqual(response.status_code, 404)

    @patch("os.path.exists")
    def test_get_survey_config_error(self, mock_exists):
        mock_exists.return_value = True
        with patch("builtins.open", side_effect=Exception("Read Error")):
            response = self.client.get("/api/survey-config")
            self.assertEqual(response.status_code, 500)

    # --- Submit Survey Tests ---

    @patch("backend.main.get_redis_client")
    @patch("os.path.exists")
    def test_submit_survey_redis_and_disk_success(self, mock_exists, mock_get_redis):
        mock_exists.return_value = True
        mock_redis_client = MagicMock()
        mock_redis_client.rpush.return_value = 1
        mock_get_redis.return_value = mock_redis_client
        
        survey_payload = {
            "userInfo": {"name": "John", "age": "25-34", "noise": "quiet"},
            "ttsResponses": [{"id": "1", "voice": "amy", "naturalness": 5, "pronunciation": 4, "intonation": 4, "overall": 5}],
            "sttResponses": [{"id": "1", "filename": "audio1.wav", "clarity": 5, "intelligibility": 5, "noise": 4, "overall": 5}],
            "comments": "Great survey"
        }
        
        with patch("builtins.open", mock_open(read_data="[]")) as mocked_file:
            response = self.client.post("/api/submit-survey", json=survey_payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Saved to Redis & Disk", response.json()["message"])
            mock_redis_client.rpush.assert_called_once()

    @patch("backend.main.get_redis_client")
    @patch("os.path.exists")
    def test_submit_survey_disk_only_redis_fail(self, mock_exists, mock_get_redis):
        mock_exists.return_value = False
        mock_redis_client = MagicMock()
        mock_redis_client.rpush.side_effect = Exception("Redis connection lost")
        mock_get_redis.return_value = mock_redis_client
        
        survey_payload = {
            "userInfo": {"name": "Jane", "age": "35-44", "noise": "moderate"},
            "ttsResponses": [],
            "sttResponses": [],
            "comments": ""
        }
        
        with patch("builtins.open", mock_open(read_data="")) as mocked_file:
            response = self.client.post("/api/submit-survey", json=survey_payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Saved to Disk", response.json()["message"])

    def test_submit_survey_validation_fail(self):
        invalid_payload = {"userInfo": {"name": ""}}  # empty name fails min_length constraint
        response = self.client.post("/api/submit-survey", json=invalid_payload)
        self.assertEqual(response.status_code, 422)

    # --- Survey Results Stats Tests ---

    @patch("backend.main.get_redis_client")
    def test_get_survey_results_from_redis(self, mock_get_redis):
        mock_redis_client = MagicMock()
        mock_response_json = '{"userInfo":{"name":"John"}, "ttsResponses":[{"id":"1","voice":"amy","naturalness":5,"pronunciation":4,"intonation":4,"overall":5}], "sttResponses":[{"id":"1","filename":"audio1.wav","clarity":5,"intelligibility":5,"noise":4,"overall":5}], "comments":""}'
        mock_redis_client.lrange.return_value = [mock_response_json]
        mock_get_redis.return_value = mock_redis_client
        
        response = self.client.get("/api/results")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_submissions"], 1)
        self.assertIn("amy", data["summary"]["tts"])
        self.assertEqual(data["summary"]["tts"]["amy"]["overall"]["mean"], 5.0)
        self.assertIn("audio1.wav", data["summary"]["stt"])

    @patch("backend.main.get_redis_client")
    @patch("os.path.exists")
    def test_get_survey_results_fallback_file(self, mock_exists, mock_get_redis):
        mock_get_redis.return_value = None
        mock_exists.return_value = True
        mock_file_data = '[{"userInfo":{"name":"Jane"}, "ttsResponses":[{"id":"1","voice":"ryan","naturalness":4,"pronunciation":3,"intonation":4,"overall":4}], "sttResponses":[{"id":"1","filename":"audio2.wav","clarity":4,"intelligibility":4,"noise":3,"overall":4}], "comments":""}]'
        
        with patch("builtins.open", mock_open(read_data=mock_file_data)):
            response = self.client.get("/api/results")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["total_submissions"], 1)
            self.assertIn("ryan", data["summary"]["tts"])
            self.assertEqual(data["summary"]["tts"]["ryan"]["overall"]["mean"], 4.0)

if __name__ == "__main__":
    unittest.main()
