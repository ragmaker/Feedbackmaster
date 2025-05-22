FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for OpenCV - macOS friendly approach
RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgl1-mesa-glx \
        libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY app.py .
COPY templates/ templates/

# Create uploads directory
RUN mkdir -p uploads

# Expose the port the app runs on
EXPOSE 7081

# Command to run the application with Gunicorn
# 4 worker processes, binding to 0.0.0.0:7081
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:7081", "app:app"] 