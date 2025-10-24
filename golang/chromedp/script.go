package main

import (
    "context"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "log"
    "os"
    "path/filepath"
    "strings"
    "time"

    "github.com/chromedp/cdproto/network"
    "github.com/chromedp/chromedp"
)

type ResponseData struct {
    URL       string            `json:"url"`
    Status    int64             `json:"status"`
    Headers   map[string]string `json:"headers"`
    Timestamp string            `json:"timestamp"`
}

// Parse named arguments (only --key=value format)
func parseArgs() (url, filePrefix, wsURL, proxyIP string) {
    filePrefix = "capture" // default

    for _, arg := range os.Args[1:] {
       if strings.Contains(arg, "=") {
          parts := strings.SplitN(arg, "=", 2)
          if len(parts) == 2 && parts[1] != "" {
             key := parts[0]
             value := parts[1]

             switch key {
             case "--url":
                url = value
             case "--file-prefix":
                filePrefix = value
             case "--ws-browser":
                wsURL = value
             case "--proxy-ip":
                proxyIP = value
             }
          }
       }
    }

    return
}

func main() {
	url, filePrefix, wsURL, proxyIP := parseArgs()

	if url == "" {
		fmt.Println("Usage: go run script.go --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]")
		os.Exit(1)
	}

	outputDir := "./output"

	if err := os.MkdirAll(outputDir, 0755); err != nil {
		log.Fatal(err)
	}

	var allocCtx context.Context
	var cancelAlloc context.CancelFunc
	isRemote := wsURL != ""

	if isRemote {
		allocCtx, cancelAlloc = chromedp.NewRemoteAllocator(context.Background(), wsURL, chromedp.NoModifyURL)
	} else {
		opts := append(chromedp.DefaultExecAllocatorOptions[:],
			chromedp.Flag("headless", true),
			chromedp.Flag("ignore-certificate-errors", true),
		)

		if proxyIP != "" {
			opts = append(opts, chromedp.ProxyServer(proxyIP))
		}

		allocCtx, cancelAlloc = chromedp.NewExecAllocator(context.Background(), opts...)
	}
	defer cancelAlloc()

	var ctx context.Context
	var cancelCtx context.CancelFunc

	if isRemote {
		// For remote: connect to the existing tab without creating a new one
		ctx, cancelCtx = chromedp.NewContext(allocCtx)
	} else {
		// For local: create a new tab
		ctx, cancelCtx = chromedp.NewContext(allocCtx)
	}

	// Use a map to store all document responses, keyed by URL
	responses := make(map[string]*ResponseData)

	chromedp.ListenTarget(ctx, func(ev interface{}) {
		if ev, ok := ev.(*network.EventResponseReceived); ok {
			if ev.Type == network.ResourceTypeDocument {
				headers := make(map[string]string)
				if ev.Response.Headers != nil {
					for k, v := range ev.Response.Headers {
						headers[k] = fmt.Sprintf("%v", v)
					}
				}
				responseData := &ResponseData{
					URL:       ev.Response.URL,
					Status:    ev.Response.Status,
					Headers:   headers,
					Timestamp: time.Now().Format(time.RFC3339),
				}
				// Store response in the map
				responses[ev.Response.URL] = responseData
			}
		}
	})

	var finalURL string
	var htmlContent string
	var screenshotBuf []byte

	// Create context with 60s timeout for navigation
	timeoutCtx, timeoutCancel := context.WithTimeout(ctx, 60*time.Second)
	defer timeoutCancel()

	err := chromedp.Run(timeoutCtx,
		network.Enable(),
		chromedp.Navigate(url),
		chromedp.WaitReady("body"),
		chromedp.Sleep(3*time.Second),
		chromedp.Location(&finalURL), // Get the final URL of the main document
		chromedp.FullScreenshot(&screenshotBuf, 90),
		chromedp.OuterHTML("html", &htmlContent),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Find the correct response from our map using the final URL
	finalDocumentResponse := responses[finalURL]

	// Fallback for cases where the URL might have a trailing slash mismatch
	if finalDocumentResponse == nil {
		if strings.HasSuffix(finalURL, "/") {
			if res, ok := responses[strings.TrimSuffix(finalURL, "/")]; ok {
				finalDocumentResponse = res
			}
		} else {
			if res, ok := responses[finalURL+"/"]; ok {
				finalDocumentResponse = res
			}
		}
	}

	// Save the header of the final document in an array, to maintain the format
	headersToSave := [](*ResponseData){}
	if finalDocumentResponse != nil {
		headersToSave = append(headersToSave, finalDocumentResponse)
	} else {
		// If we couldn't find a matching response, create a placeholder
		log.Printf("Warning: Could not find network response for final URL: %s. Creating a placeholder.", finalURL)
		placeholderResponse := &ResponseData{
			URL:       finalURL,
			Status:    0, // Incomplete data
			Headers:   make(map[string]string),
			Timestamp: time.Now().Format(time.RFC3339),
		}
		headersToSave = append(headersToSave, placeholderResponse)
	}

	headersJSON, _ := json.MarshalIndent(headersToSave, "", "  ")
	ioutil.WriteFile(filepath.Join(outputDir, filePrefix+"_headers.json"), headersJSON, 0644)
	ioutil.WriteFile(filepath.Join(outputDir, filePrefix+"_page.html"), []byte(htmlContent), 0644)
	ioutil.WriteFile(filepath.Join(outputDir, filePrefix+"_screenshot.png"), screenshotBuf, 0644)

	fmt.Printf("Completed! Files saved to: %s\n", outputDir)

	// Only cancel context (close tab) if it's local
	if !isRemote {
		cancelCtx()
	}
}
