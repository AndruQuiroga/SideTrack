FROM python:3.11-slim

# Copy the project sources and install the sidetrack package with
# worker-specific extras.
WORKDIR /src
COPY pyproject.toml ./
COPY sidetrack ./sidetrack
RUN pip install --no-cache-dir .[worker]

# Run the worker from the installed package location.
WORKDIR /usr/local/lib/python3.11/site-packages/sidetrack
CMD ["python", "-m", "sidetrack.worker.run"]

