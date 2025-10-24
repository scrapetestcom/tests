import sys
import os
import json
from datetime import datetime
from curl_cffi import requests

def parse_args():
    """Parse named arguments (only --key=value format)"""
    args = {
        'url': None,
        'file_prefix': 'capture',
        'proxy_ip': None
    }

    for arg in sys.argv[1:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            if value:  # Only assign if value is not empty
                if key == '--url':
                    args['url'] = value
                elif key == '--file-prefix':
                    args['file_prefix'] = value
                elif key == '--proxy-ip':
                    args['proxy_ip'] = value

    return args

def main():
    args = parse_args()

    if not args['url']:
        print("Usage: python main.py --url=<url> [--file-prefix=<prefix>] [--proxy-ip=<proxy>]")
        sys.exit(1)

    url = args['url']
    file_prefix = args['file_prefix']
    proxy_ip = args['proxy_ip']

    output_dir = './output'

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Configure request options
    request_options = {
        'impersonate': 'chrome',  # Impersonate Chrome browser
        'timeout': 30,
        'verify': False  # Allow self-signed certificates
    }

    # Add proxy if provided
    if proxy_ip:
        request_options['proxies'] = {
            'http': proxy_ip,
            'https': proxy_ip
        }

    try:
        # Make request using curl_cffi
        response = requests.get(url, **request_options)

        # Get headers from the response
        headers_data = [{
            'url': str(response.url),
            'status': response.status_code,
            'headers': dict(response.headers),
            'timestamp': datetime.now().isoformat()
        }]

        # Save headers
        with open(os.path.join(output_dir, f'{file_prefix}_headers.json'), 'w') as f:
            json.dump(headers_data, f, indent=2)

        # Save HTML
        with open(os.path.join(output_dir, f'{file_prefix}_page.html'), 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"Completed! Files saved to: {output_dir}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
