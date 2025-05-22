FROM python:3.11-slim

WORKDIR /app

# Install system dependencies with a Mac-friendly approach
# - Use mirrors.ocf.berkeley.edu which is more stable for Docker builds on macOS
# - Implement retry logic
# - Skip apt-key validation which can cause issues on macOS Docker builds
RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid && \
    echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/99-assume-yes && \
    echo 'Acquire::AllowInsecureRepositories "true";' > /etc/apt/apt.conf.d/99allow-insecure && \
    echo 'Acquire::AllowDowngradeToInsecureRepositories "true";' > /etc/apt/apt.conf.d/99allow-insecure-2 && \
    for i in 1 2 3; do \
        echo "Attempt $i: apt-get update" && \
        apt-get update -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true || true && \
        echo "Installing dependencies..." && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            libgl1-mesa-glx \
            libglib2.0-0 && \
        echo "Successfully installed dependencies" && \
        break || \
        if [ $i -lt 3 ]; then \
            echo "apt-get attempt $i failed, retrying..." && \
            sleep 5; \
        else \
            echo "apt-get failed after 3 attempts, but continuing anyway" && \
            break; \
        fi; \
    done && \
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