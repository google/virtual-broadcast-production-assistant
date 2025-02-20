FROM python:3.12.3

WORKDIR /backend
COPY requirements.txt ./

RUN python -m venv .venv
ENV VIRTUAL_ENV=/backend/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./ ./

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]


