# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install ODBC dependencies first to avoid conflicts
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    odbcinst \
    unixodbc-common \
    libodbcinst2 \
    libodbc2 \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 18 for SQL Server using direct download method
RUN curl -o msodbcsql18.deb -L "https://packages.microsoft.com/debian/11/prod/pool/main/m/msodbcsql18/msodbcsql18_18.3.2.1-1_amd64.deb" \
    && DEBIAN_FRONTEND=noninteractive ACCEPT_EULA=Y dpkg -i msodbcsql18.deb || true \
    && apt-get update \
    && apt-get install -f -y \
    && rm msodbcsql18.deb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from pyproject.toml
COPY pyproject.toml .

# Install pip and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir toml && \
    python -c "import toml; deps = toml.load('pyproject.toml')['project']['dependencies']; print('\n'.join(deps))" > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Debug: Check what was copied and create knowledge base directory
RUN echo "=== Debugging Docker Copy ===" && \
    echo "Contents of /app:" && \
    ls -la /app/ && \
    echo "Contents of /app/app:" && \
    ls -la /app/app/ && \
    echo "Contents of /app/app/advisor_agent:" && \
    ls -la /app/app/advisor_agent/ && \
    echo "Creating knowledge base directory..." && \
    mkdir -p /app/app/advisor_agent/knowledge_base && \
    echo "Knowledge base directory created"

# Expose port for FastAPI
EXPOSE 8000

# Create a startup script with proper shebang and error handling
RUN echo '#!/bin/bash\n\
# Start the FastAPI application\n\
echo "Starting FastAPI application..."\n\
uvicorn app.main:app --host 0.0.0.0 --port 8000' > /app/start.sh && \
    chmod +x /app/start.sh

# Command to run the application
CMD ["/bin/bash", "/app/start.sh"]
