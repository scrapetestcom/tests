require 'ferrum'
require 'json'
require 'fileutils'

# Parse named arguments (only --key=value format)
def parse_args
  args = {
    url: nil,
    file_prefix: 'capture',
    ws_url: nil,
    proxy_ip: nil
  }

  ARGV.each do |arg|
    if arg.include?('=')
      key, value = arg.split('=', 2)
      next if value.nil? || value.empty?

      case key
      when '--url'
        args[:url] = value
      when '--file-prefix'
        args[:file_prefix] = value
      when '--ws-browser'
        args[:ws_url] = value
      when '--proxy-ip'
        args[:proxy_ip] = value
      end
    end
  end

  args
end

args = parse_args

if args[:url].nil?
  puts "Usage: ruby script.rb --url=<url> [--file-prefix=<prefix>] [--ws-browser=<ws://browser>] [--proxy-ip=<proxy>]"
  exit 1
end

url = args[:url]
file_prefix = args[:file_prefix]
ws_url = args[:ws_url]
proxy_ip = args[:proxy_ip]

output_dir = './output'

FileUtils.mkdir_p(output_dir)

browser_options = {
  window_size: [1200, 800],
  timeout: 60
}

if ws_url
  # CRUCIAL: desabilita processo local e conecta no WebSocket remoto
  browser_options[:url] = ws_url
  browser_options[:process_timeout] = nil  # Don't start local Chrome
  browser_options[:browser_path] = nil     # Don't look for local Chrome
else
  browser_options[:headless] = true

  if proxy_ip
    browser_options[:browser_options] = {
      'proxy-server' => proxy_ip
    }
  end
end

browser = Ferrum::Browser.new(**browser_options)

begin
  puts "Visiting #{url}..."
  browser.goto(url)
  sleep 3

  final_url = browser.current_url

  browser.screenshot(path: File.join(output_dir, "#{file_prefix}_screenshot.png"))
  File.write(File.join(output_dir, "#{file_prefix}_page.html"), browser.body)

  # Find the response that matches the final URL
  final_traffic = browser.network.traffic.reverse.find do |t|
    t.response && t.response.url == final_url
  end

  # Fallback to last document if no exact match
  if final_traffic.nil?
    puts "Warning: Could not find request matching final URL '#{final_url}'. Falling back to last document."
    final_traffic = browser.network.traffic.reverse.find do |t|
        t.request.resource_type == 'document' && t.response
    end
  end

  headers_data = []
  if final_traffic && final_traffic.response
    final_response = final_traffic.response
    headers_data << {
      url: final_url, # Use the definitive final_url
      status: final_response.status,
      headers: final_response.headers,
      timestamp: final_response.timestamp.iso8601
    }
  else
    puts "Warning: Could not find any document response. Creating a placeholder."
    headers_data << {
        url: final_url,
        status: 0,
        headers: {},
        timestamp: Time.now.iso8601
    }
  end

  File.write(
    File.join(output_dir, "#{file_prefix}_headers.json"),
    JSON.pretty_generate(headers_data)
  )

  puts "Completed! Files saved to: #{output_dir}"
rescue => e
  puts "Error: #{e.message}"
  puts e.backtrace
ensure
  browser.quit
end