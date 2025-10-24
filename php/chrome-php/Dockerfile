FROM php:8.4-cli

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install Chromium and dependencies
RUN apt-get update && \
    apt-get install -y \
    chromium \
    chromium-driver \
    git \
    unzip \
    libzip-dev \
    zip && \
    curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install PHP extensions required by chrome-php
RUN docker-php-ext-install sockets zip

WORKDIR /app

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
