FROM python:3.11-slim
WORKDIR /app

COPY services/api /src/api
RUN pip install --no-cache-dir /src/api

COPY services/worker /src/worker
RUN pip install --no-cache-dir /src/worker

CMD ["python","-m","worker.run"]
