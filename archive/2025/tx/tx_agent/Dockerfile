FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends wget \
      build-essential \
      g++ \
      clang \
      pkg-config \
      libatomic1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY ./*.py /app/
COPY agent/ /app/agent/

RUN useradd -m appuser
USER appuser

EXPOSE 8080

CMD ["python", "/app/__main__.py"]
