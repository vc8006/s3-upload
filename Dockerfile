# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv (fast Python package installer)
RUN pip install --no-cache-dir uv

# Copy project files for dependency installation
COPY pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Copy application code
COPY app.py .
COPY templates/ templates/

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/images.db

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Run the application
CMD ["python", "app.py"]

