FROM alpine:latest

# Install bash, curl and coreutils (for GNU date)
RUN apk add --no-cache bash curl coreutils

WORKDIR /app

CMD ["bash", "scrape.sh"]
