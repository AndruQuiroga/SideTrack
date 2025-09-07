FROM python:3.11-slim
WORKDIR /app
# Install deps
COPY services/scheduler/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# Copy monorepo package source and expose for imports
COPY sidetrack /srv/sidetrack
ENV PYTHONPATH=/srv
# Run scheduler module from sidetrack package
CMD ["python","-m","sidetrack.scheduler.run"]
