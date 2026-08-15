FROM python:3.12-alpine

WORKDIR /app

COPY catalogue-client /src/catalogue-client
RUN pip install --no-cache-dir /src/catalogue-client

COPY docker/consumer-smoke/mock_iam.py /app/mock_iam.py
COPY docker/consumer-smoke/run.py /app/run.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 10001:10001

CMD ["python", "/app/run.py"]
