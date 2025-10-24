import asyncio
import json
import sys
import os
from datetime import datetime
from camoufox.async_api import AsyncCamoufox

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

async def main():
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

    # Configure Camoufox options
    browser_config = {
        'headless': True,
    }

    # Add proxy if provided
    if proxy_ip:
        browser_config['proxy'] = {
            'server': proxy_ip
        }
        browser_config['geoip'] = True

    async with AsyncCamoufox(**browser_config) as browser:
        page = await browser.new_page()

        # Navigate to site
        try:
            response = await page.goto(url, timeout=60000, wait_until='domcontentloaded')

            # Wait additional time for dynamic content to load
            await asyncio.sleep(5)

            # Get headers from the response
            headers_data = []
            if response:
                headers_data.append({
                    'url': response.url,
                    'status': response.status,
                    'headers': dict(response.headers),
                    'timestamp': datetime.now().isoformat()
                })

            # Save headers
            with open(os.path.join(output_dir, f'{file_prefix}_headers.json'), 'w') as f:
                json.dump(headers_data, f, indent=2)

            # Take screenshot
            await page.screenshot(path=os.path.join(output_dir, f'{file_prefix}_screenshot.png'), full_page=True)

            # Save HTML
            html = await page.content()
            with open(os.path.join(output_dir, f'{file_prefix}_page.html'), 'w', encoding='utf-8') as f:
                f.write(html)

            print(f"Completed! Files saved to: {output_dir}")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
