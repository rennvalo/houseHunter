FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p templates static /database

# Expose port
EXPOSE 7777

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7777"]
