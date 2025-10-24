FROM python:3.12

# Install minimal system dependencies for Camoufox
RUN apt-get update && \
    apt-get install -y \
        libgtk-3-0 \
        libasound2 \
        libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# Install Camoufox
RUN pip install --no-cache-dir camoufox[geoip]

# Pre-fetch Camoufox browser, fingerprint data and addons
RUN camoufox fetch

WORKDIR /app

# Default command (will be overridden by docker-compose)
CMD ["python", "main.py"]
