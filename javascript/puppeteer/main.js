import puppeteer from 'puppeteer';
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

let browser;
let page;

if (wsBrowser) {
    // Connect to existing browser via WebSocket
    browser = await puppeteer.connect({
        browserWSEndpoint: wsBrowser,
        defaultViewport: null
    });
    const pages = await browser.pages();
    page = pages[0];
} else {
    // Launch new browser
    const launchOptions = {
        headless: true,
        args: ['--no-sandbox']
    };

    if (proxyIp) {
        launchOptions.args.push(`--proxy-server=${proxyIp}`);
    }


    browser = await puppeteer.launch(launchOptions);
    page = await browser.newPage();
}

const finalResponse = await page.goto(url, {
    waitUntil: 'domcontentloaded',
    timeout: 60000
});

// Get headers from the final response (after redirects)
const finalHeaders = finalResponse ? [{
    url: finalResponse.url(),
    status: finalResponse.status(),
    headers: finalResponse.headers(),
    timestamp: new Date().toISOString()
}] : [];

fs.writeFileSync(path.join(outputDir, `${filePrefix}_headers.json`), JSON.stringify(finalHeaders, null, 2));

await page.screenshot({
    path: path.join(outputDir, `${filePrefix}_screenshot.png`),
    fullPage: true
});

const html = await page.content();

fs.writeFileSync(path.join(outputDir, `${filePrefix}_page.html`), html, 'utf8');

console.log(`Completed! Files saved to: ${outputDir}`);

if (!wsBrowser) {
    await browser.close();
}

process.exit(0);
