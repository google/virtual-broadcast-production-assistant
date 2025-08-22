FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg \
      libgl1 \
      libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY ./*.py /app/
COPY src/ /app/src/

RUN useradd -m appuser
USER appuser

EXPOSE 8080

ENTRYPOINT ["python", "/app/main.py"]
