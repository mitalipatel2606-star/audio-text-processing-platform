import random
import requests

URL = "http://127.0.0.1:8000/api/submit-survey"

names = [
    "Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack",
    "Karen", "Leo", "Mia", "Nathan", "Olivia", "Paul", "Quinn", "Rachel", "Sam", "Tina"
]
ages = ["18-24", "25-34", "35-44", "45-54", "55+"]
noises = ["quiet", "moderate", "noisy"]

voices = ["Amy (Medium)", "Lessac (Medium)", "Joe (Medium)", "Ryan (Medium)", "Danny (Low)"]
audio_files = [
    "LJ001-0001.wav", "LJ001-0002.wav", "LJ001-0003.wav", "LJ001-0004.wav", "LJ001-0005.wav",
    "LJ001-0006.wav", "audio1.wav", "audio2.wav", "audio3.wav", "audio4.wav", "audio5.wav"
]

def generate_responses():
    print(f"Submitting 20 simulated survey responses to {URL}...")
    for i in range(20):
        payload = {
            "userInfo": {
                "name": names[i],
                "age": random.choice(ages),
                "noise": random.choice(noises)
            },
            "ttsResponses": [],
            "sttResponses": [],
            "comments": f"Simulated user response {i+1} for MOS survey round 2."
        }
        
        # Add 5 TTS responses
        for tts_idx in range(1, 6):
            voice = random.choice(voices)
            # Scores randomly chosen between 4 and 5 to simulate positive ratings (MOS > 3.5)
            payload["ttsResponses"].append({
                "id": f"tts_{tts_idx}",
                "voice": voice,
                "naturalness": random.randint(4, 5),
                "pronunciation": random.randint(4, 5),
                "intonation": random.randint(4, 5),
                "overall": random.randint(4, 5)
            })
            
        # Add STT responses
        for stt_idx, filename in enumerate(audio_files):
            payload["sttResponses"].append({
                "id": f"audio_{stt_idx + 1}",
                "filename": filename,
                "clarity": random.randint(4, 5),
                "intelligibility": random.randint(4, 5),
                "noise": random.randint(4, 5),
                "overall": random.randint(4, 5)
            })
            
        try:
            r = requests.post(URL, json=payload)
            r.raise_for_status()
            print(f"[{i+1}/20] Submitted response for {names[i]}: Success (HTTP {r.status_code})")
        except Exception as e:
            print(f"[{i+1}/20] Failed to submit for {names[i]}: {e}")

if __name__ == "__main__":
    generate_responses()
