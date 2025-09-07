FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cuez-rundown-agent/ ./cuez-rundown-agent/

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "cuez-rundown-agent"]