FROM chromedp/headless-shell:latest

# Install Go
RUN apt-get update && \
    apt-get install -y wget dumb-init && \
    wget -q https://go.dev/dl/go1.23.2.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.23.2.linux-amd64.tar.gz && \
    rm go1.23.2.linux-amd64.tar.gz && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/go"

WORKDIR /app

# Remove the original ENTRYPOINT
ENTRYPOINT []
CMD ["/bin/bash"]
