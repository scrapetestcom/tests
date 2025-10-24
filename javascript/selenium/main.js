import 'chromedriver';
import {Builder} from 'selenium-webdriver';
import chrome from 'selenium-webdriver/chrome.js';
import fs from 'fs';
import path from 'path';

// Parse named arguments (only --key=value format)
function parseArgs() {
    const args = {
        url: null,
        filePrefix: 'capture',
        wsBrowser: null,
        proxyIp: null
    };

    for (let i = 2; i < process.argv.length; i++) {
        const arg = process.argv[i];

        if (arg.includes('=')) {
            const [key, ...valueParts] = arg.split('=');
            const value = valueParts.join('='); // Rejoin in case value contains =

            // Only assign if value is not empty
            if (value !== '') {
                if (key === '--url') {
                    args.url = value;
                } else if (key === '--file-prefix') {
                    args.filePrefix = value;
                } else if (key === '--ws-browser') {
                    args.wsBrowser = value;
                } else if (key === '--proxy-ip') {
                    args.proxyIp = value;
                }
            }
        }
    }

    return args;
}

const args = parseArgs();

if (!args.url) {
    console.log('Usage: node main.js --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]');
    process.exit(1);
}

const url = args.url;
const filePrefix = args.filePrefix;
const wsBrowser = args.wsBrowser;
const proxyIp = args.proxyIp;

const outputDir = './output';

fs.mkdirSync(outputDir, {recursive: true});

const options = new chrome.Options();

if (wsBrowser) {
    const debuggerAddress = wsBrowser
        .replace('wss://', '')
        .replace('ws://', '')
        .split('/')[0];

    console.log('Connecting to:', debuggerAddress);
    options.debuggerAddress(debuggerAddress);
} else {
    options.addArguments('--headless=new');
    options.addArguments('--no-sandbox');
    options.addArguments('--disable-dev-shm-usage');

    if (proxyIp) {
        options.addArguments(`--proxy-server=${proxyIp}`);
    }
}

const driver = await new Builder()
    .forBrowser('chrome')
    .setChromeOptions(options)
    .build();

const cdpSession = await driver.createCDPConnection('page');
await cdpSession.send('Network.enable');

const responses = {}; // Use a map to store responses

cdpSession.on('Network.responseReceived', (params) => {
    if (params.type === 'Document' && params.response) {
        responses[params.response.url] = {
            url: params.response.url,
            status: params.response.status,
            headers: params.response.headers,
            timestamp: new Date().toISOString()
        };
    }
});

await driver.manage().setTimeouts({pageLoad: 60000});
await driver.get(url);
await driver.sleep(3000);

const finalUrl = await driver.getCurrentUrl();

const screenshotData = await driver.takeScreenshot();
fs.writeFileSync(
    path.join(outputDir, `${filePrefix}_screenshot.png`),
    screenshotData,
    'base64'
);

const html = await driver.getPageSource();
fs.writeFileSync(
    path.join(outputDir, `${filePrefix}_page.html`),
    html,
    'utf8'
);

let finalDocumentResponse = responses[finalUrl];

// Fallback for trailing slashes
if (!finalDocumentResponse) {
    if (finalUrl.endsWith('/')) {
        finalDocumentResponse = responses[finalUrl.slice(0, -1)];
    } else {
        finalDocumentResponse = responses[finalUrl + '/'];
    }
}

const headersToSave = [];
if (finalDocumentResponse) {
    headersToSave.push(finalDocumentResponse);
} else {
    console.log(`Warning: Could not find network response for final URL: ${finalUrl}. Creating a placeholder.`);
    headersToSave.push({
        url: finalUrl,
        status: 0, // Incomplete data
        headers: {},
        timestamp: new Date().toISOString()
    });
}

fs.writeFileSync(
    path.join(outputDir, `${filePrefix}_headers.json`),
    JSON.stringify(headersToSave, null, 2)
);
console.log(`Completed! Files saved to: ${outputDir}`);

if (!wsBrowser) {
    await driver.quit();
}

process.exit(0);