import io
import os
import sys
import unittest
import wave

# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.tts.piper_wrapper import load_voice, synthesize, VOICE_MAP


class TestPiperWrapper(unittest.TestCase):

    def test_load_voice_success(self):
        """Test loading a valid voice model successfully."""
        voice = load_voice("amy")
        self.assertIsNotNone(voice)
        # Check that it's cached
        voice_cached = load_voice("amy")
        self.assertIs(voice, voice_cached)

    def test_load_voice_invalid_alias(self):
        """Test that ValueError is raised for an unknown voice alias."""
        with self.assertRaises(ValueError):
            load_voice("invalid_voice_alias_name")

    def test_load_voice_missing_file(self):
        """Test FileNotFoundError is raised if alias is mapped but file does not exist."""
        # Temporarily mock/override the path mapping to a non-existent file
        original_map = VOICE_MAP.copy()
        try:
            VOICE_MAP["missing_voice"] = "non_existent_model_file.onnx"
            with self.assertRaises(FileNotFoundError):
                load_voice("missing_voice")
        finally:
            # Restore original VOICE_MAP
            VOICE_MAP.clear()
            VOICE_MAP.update(original_map)

    def test_synthesize_success(self):
        """Test synthesizing text to WAV bytes and validating the output format."""
        text = "Hello, testing the Piper TTS wrapper integration."
        wav_bytes = synthesize(text, "amy")

        # Verify output is a non-empty bytes sequence
        self.assertIsInstance(wav_bytes, bytes)
        self.assertGreater(len(wav_bytes), 0)

        # Verify standard WAV header magic bytes
        # Bytes 0-4 should be b'RIFF', and bytes 8-12 should be b'WAVE'
        self.assertEqual(wav_bytes[0:4], b"RIFF")
        self.assertEqual(wav_bytes[8:12], b"WAVE")

        # Read as a valid WAV file and verify metadata
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wav_read:
            self.assertEqual(wav_read.getnchannels(), 1)
            # Standard Piper models have a frame rate of 22050Hz (or 16000Hz depending on model)
            self.assertIn(wav_read.getframerate(), [22050, 16000])
            frames = wav_read.getnframes()
            self.assertGreater(frames, 0)
            
            duration = frames / float(wav_read.getframerate())
            print(f"Synthesized WAV duration: {duration:.2f} seconds")
            self.assertGreater(duration, 0.0)

    def test_synthesize_different_voices(self):
        """Test synthesizing using other available voice models to verify loading and runtime caching."""
        for voice_alias in ["danny", "joe"]:
            wav_bytes = synthesize("Short test.", voice_alias)
            self.assertGreater(len(wav_bytes), 0)
            self.assertEqual(wav_bytes[0:4], b"RIFF")
            self.assertEqual(wav_bytes[8:12], b"WAVE")


if __name__ == "__main__":
    unittest.main()
