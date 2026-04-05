FROM python:3.12-slim

# Install Docker CLI and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Create working directory
WORKDIR /app

# Copy project files (build context should be the project root)
COPY pyproject.toml ./
COPY src ./src
COPY worker ./worker
COPY orchestrator/test_entrypoint.sh /usr/local/bin/test_entrypoint.sh

# Install dependencies
RUN poetry install --no-interaction --no-ansi

RUN chmod +x /usr/local/bin/test_entrypoint.sh

# Default command runs test
ENTRYPOINT ["/usr/local/bin/test_entrypoint.sh"]