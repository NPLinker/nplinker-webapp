FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r npuser && useradd -r -g npuser npuser

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

# Change ownership of the application files
RUN chown -R npuser:npuser /app

# Switch to non-root user
USER npuser

# Expose the port the app runs on
EXPOSE 8050

# Command to run the application
CMD ["python", "app/main.py"]