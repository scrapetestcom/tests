#!/bin/bash

set -e

echo "Starting scrape script..."

# Parse named arguments (only --key=value format)
URL=""
FILE_PREFIX="capture"
WS_BROWSER=""
PROXY_IP=""

for arg in "$@"; do
    if [[ "$arg" == *"="* ]]; then
        KEY="${arg%%=*}"
        VALUE="${arg#*=}"

        if [[ -n "$VALUE" ]]; then
            case "$KEY" in
                --url)
                    URL="$VALUE"
                    ;;
                --file-prefix)
                    FILE_PREFIX="$VALUE"
                    ;;
                --ws-browser)
                    WS_BROWSER="$VALUE"
                    ;;
                --proxy-ip)
                    PROXY_IP="$VALUE"
                    ;;
            esac
        fi
    fi
done

if [[ -z "$URL" ]]; then
    echo "Usage: bash scrape.sh --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]"
    exit 1
fi

echo "URL: $URL"
echo "FILE_PREFIX: $FILE_PREFIX"
echo "PROXY_IP: $PROXY_IP"

OUTPUT_DIR="./output"
mkdir -p "$OUTPUT_DIR"

echo "Output directory created: $OUTPUT_DIR"

TEMP_HEADERS="${OUTPUT_DIR}/.temp_headers_$$"
TEMP_BODY="${OUTPUT_DIR}/.temp_body_$$"

# Build curl command
CURL_CMD=(curl -s -k -L --max-time 60 --connect-timeout 10 -w '\n%{json}' -D "$TEMP_HEADERS" -o "$TEMP_BODY")

if [[ -n "$PROXY_IP" ]]; then
    CURL_CMD+=(-x "$PROXY_IP")
fi

CURL_CMD+=("$URL")

# Execute curl
echo "Executing curl command..."
set +e  # Temporarily disable exit on error
CURL_STATS=$("${CURL_CMD[@]}" 2>&1)
CURL_EXIT_CODE=$?
set -e  # Re-enable exit on error

if [[ $CURL_EXIT_CODE -ne 0 ]]; then
    echo "Error: curl failed with exit code $CURL_EXIT_CODE"
    echo "Output: $CURL_STATS"
    exit 1
fi

echo "Curl completed successfully"

# Read response body
BODY_CONTENT=$(cat "$TEMP_BODY")

# Read headers
HEADERS_RAW=$(cat "$TEMP_HEADERS")

# Extract only the LAST set of headers (after all redirects)
# Find the last HTTP response line and get everything after it
LAST_HTTP_LINE=$(echo "$HEADERS_RAW" | grep -n "^HTTP/" | tail -n 1 | cut -d: -f1)
FINAL_HEADERS=$(echo "$HEADERS_RAW" | tail -n +$LAST_HTTP_LINE)

# Extract status code from LAST HTTP response
HTTP_STATUS=$(echo "$FINAL_HEADERS" | head -n 1 | awk '{print $2}')

# Parse headers into JSON object
HEADERS_JSON="{"
FIRST=true
while IFS=': ' read -r key value; do
    # Skip empty lines, status line, and lines without proper key
    # Trim whitespace from key and check if it's not empty
    key_trimmed=$(echo "$key" | xargs)
    if [[ -n "$key_trimmed" && "$key_trimmed" != HTTP* ]]; then
        value=$(echo "$value" | tr -d '\r\n')
        if [[ "$FIRST" == true ]]; then
            FIRST=false
        else
            HEADERS_JSON+=","
        fi
        # Escape quotes in value
        value_escaped=$(echo "$value" | sed 's/"/\\"/g')
        HEADERS_JSON+="\"$key_trimmed\":\"$value_escaped\""
    fi
done < <(echo "$FINAL_HEADERS" | tail -n +2)
HEADERS_JSON+="}"

# Get timestamp (use GNU date format)
TIMESTAMP=$(date -Iseconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S+00:00")

# Get final URL from curl stats
FINAL_URL=$(echo "$CURL_STATS" | grep -o '"url_effective":"[^"]*"' | cut -d'"' -f4)
if [[ -z "$FINAL_URL" ]]; then
    FINAL_URL="$URL"
fi

# Create headers JSON file
cat > "${OUTPUT_DIR}/${FILE_PREFIX}_headers.json" << EOF
[
  {
    "url": "$FINAL_URL",
    "status": $HTTP_STATUS,
    "headers": $HEADERS_JSON,
    "timestamp": "$TIMESTAMP"
  }
]
EOF

# Save page content
echo "$BODY_CONTENT" > "${OUTPUT_DIR}/${FILE_PREFIX}_page.html"

# Clean up temp files
rm -f "$TEMP_HEADERS" "$TEMP_BODY"

echo "Completed! Files saved to: $OUTPUT_DIR"
