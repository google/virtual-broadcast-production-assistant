# Use an official Python runtime as a parent image.
# Using python 3.11-slim for a smaller image size.
FROM python:3.11-slim

# Set the working directory in the container.
WORKDIR /app

# Set environment variables for Python.
# Prevents Python from writing .pyc files to disc.
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr.
ENV PYTHONUNBUFFERED 1

# Copy just the requirements file to leverage Docker cache.
COPY requirements.txt .

# Install dependencies.
# gunicorn is a production-grade WSGI server.
# We install it here directly to keep production-specific dependencies
# out of your local requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn

# Copy the rest of the application's code.
COPY . .

# Cloud Run automatically sets the PORT environment variable.
# Gunicorn will listen on the port specified by the PORT variable.
# We use uvicorn.workers.UvicornWorker as the worker class for Gunicorn to run an ASGI application.
# The `exec` command ensures that your application is the main process (PID 1).
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker main:app"]
