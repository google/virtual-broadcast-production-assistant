FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ /app/src/

# Cloud Run dynamic port mapping default
EXPOSE 8080

# Default command launches FOH Proxy (can be overridden during deployment)
CMD ["python", "src/foh_proxy.py"]
