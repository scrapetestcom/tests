<?php

require 'vendor/autoload.php';

use HeadlessChromium\BrowserFactory;
use HeadlessChromium\Page;

// Parse command line arguments
function parseArgs()
{
    $args = [
        'url' => null,
        'file_prefix' => 'capture',
        'ws_browser' => null,
        'proxy_ip' => null
    ];

    global $argv;
    foreach ($argv as $arg) {
        if (strpos($arg, '=') !== false) {
            list($key, $value) = explode('=', $arg, 2);
            // Remove -- and convert - to _
            $key = str_replace('-', '_', ltrim($key, '-'));
            // Only update if value is not empty and key exists in array
            if (!empty($value) && array_key_exists($key, $args)) {
                $args[$key] = $value;
            }
        }
    }

    return $args;
}

$args = parseArgs();

if (empty($args['url'])) {
    echo "Usage: php script.php --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]\n";
    exit(1);
}

$url = $args['url'];
$filePrefix = $args['file_prefix'];
$wsBrowser = $args['ws_browser'];
$proxyIp = $args['proxy_ip'];

// Create output directory
$outputDir = './output';
if (!is_dir($outputDir)) {
    mkdir($outputDir, 0777, true);
}

// Configure browser options
$browserOptions = [
    'windowSize' => [1200, 800],
    'headless' => true,
    'noSandbox' => true,
    'customFlags' => [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--disable-setuid-sandbox'
    ]
];

// Add proxy if specified
if ($proxyIp) {
    $browserOptions['proxyServer'] = $proxyIp;
} else {
    $browserOptions['noProxyServer'] = true;
}

// Use remote browser if specified
if ($wsBrowser) {
    $browserOptions['debuggerServerTarget'] = $wsBrowser;
    unset($browserOptions['headless']);
    unset($browserOptions['noSandbox']);
}

try {
    // Create browser instance
    $browserFactory = new BrowserFactory('chromium');
    $browser = $browserFactory->createBrowser($browserOptions);

    echo "Visiting {$url}...\n";
    $page = $browser->createPage();

    // Enable Network tracking via DevTools Protocol
    $session = $page->getSession();
    $capturedResponse = null;

    // Enable network monitoring
    $session->sendMessageSync(
        new \HeadlessChromium\Communication\Message('Network.enable')
    );

    // Capture response headers when received
    $session->on('method:Network.responseReceived', function ($params) use (&$capturedResponse) {
        $response = $params['response'];

        // Only capture the first HTML response (main document)
        if (!$capturedResponse &&
            isset($response['mimeType']) &&
            strpos($response['mimeType'], 'text/html') !== false) {
            $capturedResponse = [
                'url' => $response['url'],
                'status' => $response['status'],
                'headers' => $response['headers'],
                'mimeType' => $response['mimeType']
            ];
        }
    });

    // Navigate to URL and wait for page load
    $page->navigate($url)->waitForNavigation(Page::DOM_CONTENT_LOADED, 60000);

    // Get final URL after redirects
    $finalUrl = $page->evaluate('window.location.href')->getReturnValue();

    // Save screenshot
    $page->screenshot([
        'format' => 'png',
        'clip' => $page->getFullPageClip()
    ])->saveToFile($outputDir . '/' . $filePrefix . '_screenshot.png');

    // Save HTML
    file_put_contents(
        $outputDir . '/' . $filePrefix . '_page.html',
        $page->getHtml()
    );

    // Save headers
    if ($capturedResponse) {
        // We captured the response successfully
        $headersData = [
            [
                'url' => $capturedResponse['url'],
                'status' => $capturedResponse['status'],
                'headers' => $capturedResponse['headers'],
                'mimeType' => $capturedResponse['mimeType'],
                'timestamp' => date('c')
            ]
        ];
    } else {
        // No response was captured, create placeholder
        $headersData = [
            [
                'url' => $finalUrl,
                'status' => 0,
                'headers' => [],
                'timestamp' => date('c'),
                'note' => 'No response captured'
            ]
        ];
    }

    file_put_contents(
        $outputDir . '/' . $filePrefix . '_headers.json',
        json_encode($headersData, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)
    );

    echo "Completed! Files saved to: {$outputDir}\n";

} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
    exit(1);
} finally {
    if (!$wsBrowser && isset($browser)) {
        $browser->close();
    }
}
