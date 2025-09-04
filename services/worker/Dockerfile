FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir rq==1.16.2 redis==5.0.7
COPY worker ./worker
CMD ["python","-m","worker.run"]

