package main

import (
    "encoding/json"
    "fmt"
    "io/ioutil"
    "log"
    "os"
    "path/filepath"
    "strings"
    "time"

    "github.com/go-rod/rod"
    "github.com/go-rod/rod/lib/launcher"
    "github.com/go-rod/rod/lib/proto"
)

type ResponseData struct {
    URL       string            `json:"url"`
    Status    int               `json:"status"`
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
       log.Fatal("Usage: go run script.go --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]")
    }

    outputDir := "./output"

    if err := os.MkdirAll(outputDir, 0755); err != nil {
       log.Fatal(err)
    }

    var browser *rod.Browser
    var page *rod.Page
    isRemote := wsURL != ""

    if isRemote {
       // Para browser remoto: ignora certificados TLS
       browser = rod.New().ControlURL(wsURL).MustConnect()
       browser.MustIgnoreCertErrors(true)

       pages := browser.MustPages()
       if len(pages) == 0 {
          log.Fatal("No page found")
       }
       page = pages[0]
    } else {
       l := launcher.New().Headless(true).Set("ignore-certificate-errors")

       if proxyIP != "" {
          l = l.Proxy(proxyIP)
       }

       browser = rod.New().ControlURL(l.MustLaunch()).MustConnect()
       page = browser.MustPage()
    }

    // Use a map to store all document responses, keyed by URL
    responses := make(map[string]*ResponseData)
    go page.EachEvent(func(e *proto.NetworkResponseReceived) {
        if e.Type == proto.NetworkResourceTypeDocument {
            headers := make(map[string]string)
            for k, v := range e.Response.Headers {
                headers[k] = v.String()
            }
            responseData := &ResponseData{
                URL:       e.Response.URL,
                Status:    e.Response.Status,
                Headers:   headers,
                Timestamp: time.Now().Format(time.RFC3339),
            }
            responses[e.Response.URL] = responseData
        }
    })()

    page.Timeout(60 * time.Second).MustNavigate(url).MustWaitDOMStable()
    time.Sleep(3 * time.Second)

    finalURL := page.MustInfo().URL
    htmlContent := page.MustHTML()
    screenshotBytes := page.MustScreenshotFullPage()

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
    ioutil.WriteFile(filepath.Join(outputDir, filePrefix+"_screenshot.png"), screenshotBytes, 0644)

    fmt.Printf("Completed! Files saved to: %s\n", outputDir)

    if !isRemote {
       browser.MustClose()
    }
}
