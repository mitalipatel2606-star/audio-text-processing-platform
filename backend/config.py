import os
import sys

# Ensure project root is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
SURVEY_CONFIG_PATH = os.path.join(DATA_DIR, "survey_data.json")
RESPONSES_PATH = os.path.join(DATA_DIR, "survey_responses.json")
TEMP_DIR = os.path.join(project_root, "backend", "temp_uploads")
