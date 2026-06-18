import os
import sys
import time
import psutil
import unittest
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app

class TestMemoryLeak(unittest.TestCase):
    def test_transcribe_100_runs_leak_check(self):
        print("\n=== Memory Leak Test: Running 100 Sequential Transcription Requests ===")
        
        audio_file = "test.wav"
        self.assertTrue(os.path.exists(audio_file), f"Test audio '{audio_file}' must exist.")
        
        client = TestClient(app)
        
        # Warmup run to trigger model loading and initial allocations
        with open(audio_file, "rb") as f:
            response = client.post(
                "/api/v1/stt?model=tiny",
                files={"file": (audio_file, f, "audio/wav")}
            )
        self.assertEqual(response.status_code, 200)
        
        # Record initial memory (RSS)
        process = psutil.Process(os.getpid())
        initial_mem_bytes = process.memory_info().rss
        initial_mem_mb = initial_mem_bytes / (1024 * 1024)
        print(f"Initial Memory Usage (after warmup): {initial_mem_mb:.2f} MB")
        
        mem_readings = []
        num_runs = 100
        
        # Fire 100 sequential STT requests
        for i in range(1, num_runs + 1):
            t0 = time.time()
            with open(audio_file, "rb") as f:
                response = client.post(
                    "/api/v1/stt?model=tiny",
                    files={"file": (audio_file, f, "audio/wav")}
                )
            self.assertEqual(response.status_code, 200)
            latency = time.time() - t0
            
            if i % 10 == 0 or i == 1:
                current_mem_bytes = process.memory_info().rss
                current_mem_mb = current_mem_bytes / (1024 * 1024)
                growth_mb = current_mem_mb - initial_mem_mb
                mem_readings.append(current_mem_mb)
                print(f"Request {i}/{num_runs} | Latency: {latency:.2f}s | RAM: {current_mem_mb:.2f} MB (Growth: {growth_mb:+.2f} MB)")
                
        # Analyze memory growth
        final_mem_bytes = process.memory_info().rss
        final_mem_mb = final_mem_bytes / (1024 * 1024)
        total_growth_mb = final_mem_mb - initial_mem_mb
        
        print("\n=== Memory Leak Test Summary ===")
        print(f"Initial RAM: {initial_mem_mb:.2f} MB")
        print(f"Final RAM  : {final_mem_mb:.2f} MB")
        print(f"Net Growth : {total_growth_mb:.2f} MB")
        
        # Ensure memory growth is stable.
        # Net growth over 100 runs should be under 150 MB (after weights are loaded)
        self.assertLess(total_growth_mb, 150.0, "Total memory growth is too high, possible leak.")
        
        # Verify RAM stability in the second half of the run (requests 50 to 100)
        # We check the delta between request 50 (middle of readings) and request 100 (final)
        halfway_mem_mb = mem_readings[len(mem_readings) // 2]
        late_growth_mb = final_mem_mb - halfway_mem_mb
        print(f"Late-stage RAM Growth (Requests 50-100): {late_growth_mb:+.2f} MB")
        self.assertLess(abs(late_growth_mb), 15.0, "Late stage memory usage is not stable, indicating a leak.")
        print("Memory usage is STABLE. No leaks detected.")

if __name__ == "__main__":
    unittest.main()
