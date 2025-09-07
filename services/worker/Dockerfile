FROM python:3.11-slim
WORKDIR /app

COPY services /src/services
# Provide the sidetrack package next to API's pyproject
COPY sidetrack /src/services/api/sidetrack
RUN pip install --no-cache-dir /src/services/api
RUN pip install --no-cache-dir /src/services/worker

ENV PYTHONPATH=/src

CMD ["python","-m","worker.run"]
