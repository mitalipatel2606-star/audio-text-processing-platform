FROM python:3.11-slim

# Install system dependencies (ffmpeg is required for audio conversions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy backend files, default data, and services
COPY backend ./backend
COPY data ./data
COPY services ./services

EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
