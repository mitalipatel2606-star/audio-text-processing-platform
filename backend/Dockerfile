FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend files and default data
COPY backend ./backend
COPY data ./data

EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
