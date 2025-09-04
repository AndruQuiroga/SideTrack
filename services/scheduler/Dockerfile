FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir requests==2.32.3 schedule==1.2.2
COPY scheduler ./scheduler
CMD ["python","-m","scheduler.run"]

