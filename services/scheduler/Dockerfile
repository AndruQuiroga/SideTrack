FROM python:3.11-slim
WORKDIR /app

# Copy project files and install scheduler extras
COPY pyproject.toml ./
COPY sidetrack ./sidetrack
RUN pip install --no-cache-dir .[scheduler]

# Run scheduler module from sidetrack package
CMD ["python","-m","sidetrack.scheduler.run"]
