FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for building numpy/pandas
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend directory to maintain module structure
# This preserves the backend/ package structure needed for absolute imports
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Run the application from parent directory so backend module is resolvable
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
