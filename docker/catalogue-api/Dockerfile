FROM python:3.12-alpine

ARG FASTAPI_COMMON_REF=b11fac39f8db6dc12581bf14d179c67ed5bce672
ARG IAM_SERVICE_REF=49ba8905922ded93e9011f4ea0630a627653939b

RUN apk add --no-cache --virtual .build-deps gcc libc-dev linux-headers make \
    && apk add --no-cache bash git libpq-dev libmagic

WORKDIR /app

RUN pip install --no-cache-dir \
    "git+https://github.com/openg2p/openg2p-fastapi-common@${FASTAPI_COMMON_REF}#subdirectory=openg2p-fastapi-common" \
    "git+https://github.com/openg2p/iam-service@${IAM_SERVICE_REF}#subdirectory=iam-core"

COPY catalogue-api /src/catalogue-api
RUN pip install --no-cache-dir /src/catalogue-api \
    && apk del --no-network .build-deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    CATALOGUE_API_WORKER_TYPE=gunicorn \
    CATALOGUE_API_HOST=0.0.0.0 \
    CATALOGUE_API_PORT=8000 \
    CATALOGUE_API_NO_OF_WORKERS=4

USER 10001:10001

CMD ${CATALOGUE_API_WORKER_TYPE} "openg2p_catalogue_service.main:app" \
    --workers ${CATALOGUE_API_NO_OF_WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind ${CATALOGUE_API_HOST}:${CATALOGUE_API_PORT}
