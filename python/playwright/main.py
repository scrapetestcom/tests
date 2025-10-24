import asyncio
import json
import sys
import os
from datetime import datetime
from playwright.async_api import async_playwright

def parse_args():
    """Parse named arguments (only --key=value format)"""
    args = {
        'url': None,
        'file_prefix': 'capture',
        'ws_browser': None,
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
                elif key == '--ws-browser':
                    args['ws_browser'] = value
                elif key == '--proxy-ip':
                    args['proxy_ip'] = value

    return args

async def main():
    args = parse_args()

    if not args['url']:
        print("Usage: python main.py --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]")
        sys.exit(1)

    url = args['url']
    file_prefix = args['file_prefix']
    ws_browser = args['ws_browser']
    proxy_ip = args['proxy_ip']

    output_dir = './output'

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        if ws_browser:
            # Connect to existing browser via CDP
            browser = await p.chromium.connect_over_cdp(ws_browser)
            context = browser.contexts[0]
            page = context.pages[0]
        else:
            # Launch new browser
            browser = await p.chromium.launch(headless=True)

            context_options = {}
            if proxy_ip:
                context_options['proxy'] = {'server': proxy_ip}

            context = await browser.new_context(**context_options)
            page = await context.new_page()

        # Navigate to site with domcontentloaded (less restrictive than networkidle for slow proxies)
        final_response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)

        # Wait additional time for dynamic content to load
        await asyncio.sleep(5)

        # Get headers from the final response (after redirects)
        final_headers = []
        if final_response:
            final_headers.append({
                'url': final_response.url,
                'status': final_response.status,
                'headers': final_response.headers,
                'timestamp': datetime.now().isoformat()
            })

        # Save data
        with open(os.path.join(output_dir, f'{file_prefix}_headers.json'), 'w') as f:
            json.dump(final_headers, f, indent=2)

        await page.screenshot(path=os.path.join(output_dir, f'{file_prefix}_screenshot.png'), full_page=True)

        html = await page.content()
        with open(os.path.join(output_dir, f'{file_prefix}_page.html'), 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"Completed! Files saved to: {output_dir}")

        await browser.close()

asyncio.run(main())
