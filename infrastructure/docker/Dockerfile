FROM python:3.10-slim

# Install system dependencies including git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/main/ ./src/main/

# Expose port
EXPOSE 8080

# Run the Flask app on port 8080
CMD ["python", "src/main/app.py"]
