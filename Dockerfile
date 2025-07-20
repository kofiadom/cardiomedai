# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including ODBC driver for SQL Server
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    unixodbc-dev \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 18 for SQL Server
# Try repository method first, fallback to direct download if needed
RUN (curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18) \
    || (echo "Repository method failed, trying direct download..." \
    && curl -o msodbcsql18.deb -L "https://packages.microsoft.com/debian/11/prod/pool/main/m/msodbcsql18/msodbcsql18_18.3.2.1-1_amd64.deb" \
    && ACCEPT_EULA=Y dpkg -i msodbcsql18.deb \
    && apt-get install -f -y \
    && rm msodbcsql18.deb) \
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
