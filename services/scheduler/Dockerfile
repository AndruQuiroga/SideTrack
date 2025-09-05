FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY scheduler ./scheduler
CMD ["python","-m","scheduler.run"]
