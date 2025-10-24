from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys
import os
import json
from datetime import datetime

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
            if value:
                if key == '--url':
                    args['url'] = value
                elif key == '--file-prefix':
                    args['file_prefix'] = value
                elif key == '--ws-browser':
                    args['ws_browser'] = value
                elif key == '--proxy-ip':
                    args['proxy_ip'] = value
    return args

def main():
    args = parse_args()

    if not args['url']:
        print("Usage: python main.py --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]")
        sys.exit(1)

    url = args['url']
    file_prefix = args['file_prefix']
    ws_browser = args['ws_browser']
    proxy_ip = args['proxy_ip']

    output_dir = './output'
    os.makedirs(output_dir, exist_ok=True)

    chrome_options = Options()
    seleniumwire_options = {}

    if ws_browser:
        debugger_address = ws_browser.replace('ws://', '').replace('wss://', '').split('/')[0]
        chrome_options.debugger_address = debugger_address
    else:
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        if proxy_ip:
            seleniumwire_options['proxy'] = {
                'http': f'http://{proxy_ip}',
                'https': f'https://{proxy_ip}',
                'no_proxy': 'localhost,127.0.0.1'
            }

    driver = webdriver.Chrome(
        options=chrome_options,
        seleniumwire_options=seleniumwire_options
    )

    try:
        driver.set_page_load_timeout(60)
        driver.get(url)
        time.sleep(3)

        final_url = driver.current_url

        final_response = None
        # Prioritize finding the request that exactly matches the final URL
        for request in reversed(driver.requests):
            if request.response and request.url == final_url:
                final_response = request.response
                break
        
        # Fallback if no exact match is found (e.g., due to fragments or slight variations)
        if not final_response:
            print(f"Warning: Could not find request matching final URL '{final_url}'. Falling back to last document.")
            for request in reversed(driver.requests):
                if request.response and request.response.headers.get('Content-Type') and 'text/html' in request.response.headers.get('Content-Type'):
                    final_response = request.response
                    break

        headers_data = []
        if final_response:
            headers_dict = {k: v for k, v in final_response.headers.items()}
            headers_data.append({
                'url': final_url,
                'status': final_response.status_code,
                'headers': headers_dict,
                'timestamp': datetime.now().isoformat()
            })
        else:
            print(f"Warning: Could not find any document response. Creating a placeholder.")
            headers_data.append({
                'url': final_url,
                'status': 0,
                'headers': {},
                'timestamp': datetime.now().isoformat()
            })

        with open(os.path.join(output_dir, f'{file_prefix}_headers.json'), 'w') as f:
            json.dump(headers_data, f, indent=2)

        driver.save_screenshot(os.path.join(output_dir, f'{file_prefix}_screenshot.png'))

        with open(os.path.join(output_dir, f'{file_prefix}_page.html'), 'w', encoding='utf-8') as f:
            f.write(driver.page_source)

        print(f"Completed! Files saved to: {output_dir}")

    finally:
        # Only quit the driver if we created it. If we connected to a remote one, leave it open.
        if not ws_browser:
            driver.quit()

if __name__ == "__main__":
    main()