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
COPY orchestrator/unified_entrypoint.sh /usr/local/bin/doit.sh
COPY worker/run.sh /usr/local/bin/worker_run.sh

# Install dependencies
RUN poetry install --no-interaction --no-ansi

RUN chmod +x /usr/local/bin/doit.sh

# Default role is orchestrator
ENV ROLE=orchestrator

# Default command - will run based on ROLE env var
CMD ["/usr/local/bin/doit.sh"]