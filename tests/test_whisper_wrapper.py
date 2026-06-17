import unittest
import os
import sys

# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.stt.whisper_wrapper import load_model, transcribe

class TestWhisperWrapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Emulate loading model on startup
        print("=== Test SetUp: Preloading Whisper model ===")
        load_model(model_size="base", device="cpu", compute_type="int8")

    def test_transcribe_success(self):
        audio_file = "test.wav"
        self.assertTrue(os.path.exists(audio_file), f"Test audio file '{audio_file}' is missing.")

        print(f"Running transcription on '{audio_file}'...")
        result = transcribe(audio_file)

        # Verify correct return keys
        self.assertIn("text", result)
        self.assertIn("metadata", result)

        text = result["text"]
        metadata = result["metadata"]

        print(f"Transcribed Text: '{text}'")
        print(f"Metadata: {metadata}")

        # Assertions on text content
        self.assertGreater(len(text), 0, "Transcribed text should not be empty.")
        self.assertIn("hello", text.lower(), "Transcribed text should contain the word 'hello'.")

        # Assertions on metadata structure
        self.assertEqual(metadata["language"], "en")
        self.assertGreater(metadata["duration"], 0.0)
        self.assertIn("segments", metadata)
        self.assertGreater(len(metadata["segments"]), 0)

        # Assertions on segment details
        first_segment = metadata["segments"][0]
        self.assertIn("start", first_segment)
        self.assertIn("end", first_segment)
        self.assertIn("text", first_segment)
        self.assertIn("avg_logprob", first_segment)
        self.assertIn("no_speech_prob", first_segment)

    def test_file_not_found(self):
        # Expect FileNotFoundError for non-existent file
        with self.assertRaises(FileNotFoundError):
            transcribe("non_existent_file.wav")

if __name__ == "__main__":
    unittest.main()
