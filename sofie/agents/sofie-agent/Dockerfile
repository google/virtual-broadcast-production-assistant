FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk update && apk add --no-cache \
    build-base \
    curl \
    rm -rf /var/cache/apk/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project (including .env and agent folder)
COPY . .

# Expose the port your agent listens on
EXPOSE 10004

# Run the agent using your existing entrypoint style
CMD ["python", "."]
