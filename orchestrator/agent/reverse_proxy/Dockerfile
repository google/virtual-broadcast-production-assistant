
# Use an official Python runtime as a parent image.
FROM python:3.11-slim

# Set the working directory in the container.
WORKDIR /app

# Set environment variables for Python.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy just the requirements file to leverage Docker cache.
COPY requirements.txt .

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code.
COPY . .

# Install the application.
RUN pip install .

# Run the application.
CMD ["uvicorn", "reverse_proxy.main:app", "--host", "0.0.0.0", "--port", "8080"]
