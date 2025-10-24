FROM python:3.12

# Install curl_cffi
RUN pip install --no-cache-dir curl_cffi

WORKDIR /app

# Default command (will be overridden by docker-compose)
CMD ["python", "main.py"]
