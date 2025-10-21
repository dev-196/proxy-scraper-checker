# 🐍 Proxy Scraper and Checker - Python Edition

A single-file Python implementation of the proxy-scraper-checker tool. This is a simplified but fully functional version that scrapes and checks HTTP, SOCKS4, and SOCKS5 proxies.

## ✨ Features

- **Single File** - Everything in one Python file for easy distribution
- **Async/Await** - Fast concurrent scraping and checking using asyncio
- **Multiple Protocols** - Supports HTTP/HTTPS, SOCKS4, and SOCKS5 proxies
- **Flexible Sources** - Scrape from URLs or local files
- **Configurable** - Command-line arguments for all major settings
- **Multiple Outputs** - JSON (with metadata) and plain text formats
- **Fast Checking** - Concurrent proxy validation with configurable limits

## 📋 Requirements

- Python 3.7 or higher
- Dependencies: `aiohttp`, `aiofiles`

## 🚀 Quick Start

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install manually:
   ```bash
   pip install aiohttp aiofiles
   ```

2. **Make the script executable (optional):**
   ```bash
   chmod +x proxy_scraper_checker.py
   ```

### Basic Usage

```bash
# Run with default settings
python3 proxy_scraper_checker.py

# Custom output directory
python3 proxy_scraper_checker.py --output ./my_proxies

# Skip checking (scrape only)
python3 proxy_scraper_checker.py --no-check

# Adjust concurrent checks
python3 proxy_scraper_checker.py --max-concurrent-checks 512

# Custom check URL
python3 proxy_scraper_checker.py --check-url "https://httpbin.org/ip"
```

## ⚙️ Command-Line Options

### Scraping Options
- `--max-proxies-per-source N` - Maximum proxies per source (default: 100000, 0=unlimited)
- `--scraping-timeout SECONDS` - Timeout for fetching sources (default: 60.0)

### Checking Options
- `--check-url URL` - URL for checking proxies (default: https://api.ipify.org)
- `--no-check` - Skip proxy checking (scrape only)
- `--max-concurrent-checks N` - Concurrent checks (default: 1024)
- `--checking-timeout SECONDS` - Proxy response timeout (default: 60.0)

### Output Options
- `--output PATH`, `-o PATH` - Output directory (default: ./out)
- `--sort-by-speed` - Sort by response time (default)
- `--sort-by-address` - Sort by IP address instead
- `--no-txt` - Disable TXT output
- `--no-json` - Disable JSON output

## 📁 Output Structure

The script creates the following output structure:

```
out/
├── proxies.json              # Compact JSON with all proxies
├── proxies_pretty.json       # Pretty-printed JSON
└── proxies/
    ├── all.txt              # All proxies with protocol prefix
    ├── http.txt             # HTTP/HTTPS proxies only
    ├── socks4.txt           # SOCKS4 proxies only
    └── socks5.txt           # SOCKS5 proxies only
```

### JSON Format

Each proxy in the JSON output includes:
```json
{
  "protocol": "http",
  "host": "1.2.3.4",
  "port": 8080,
  "timeout": 1.23,
  "exit_ip": "1.2.3.4"
}
```

Optional fields:
- `username` - Proxy authentication username
- `password` - Proxy authentication password
- `timeout` - Response time in seconds (only if checked)
- `exit_ip` - Detected exit IP address (only if checked)

### TXT Format

Plain text format, one proxy per line:
```
http://1.2.3.4:8080
socks5://5.6.7.8:1080
http://user:pass@9.10.11.12:3128
```

## 🎯 Customizing Proxy Sources

To modify the proxy sources, edit the `ProxyConfig` class in `proxy_scraper_checker.py`:

```python
def __post_init__(self):
    if self.http_sources is None:
        self.http_sources = [
            "https://your-proxy-source.com/http.txt",
            "/path/to/local/http_proxies.txt",
        ]
    # ... similar for socks4_sources and socks5_sources
```

## 🔍 How It Works

1. **Scraping Phase**
   - Fetches proxy lists from configured URLs
   - Supports both remote URLs and local files
   - Parses proxies using regex pattern matching
   - Deduplicates proxies to avoid testing the same proxy twice

2. **Checking Phase** (optional)
   - Tests each proxy by making a request through it
   - Measures response time
   - Extracts exit IP address
   - Validates proxy is working correctly

3. **Output Phase**
   - Sorts proxies (by speed or address)
   - Groups by protocol type
   - Writes to JSON and/or TXT files

## ⚠️ Safety Warning

This tool makes many network requests and can impact your IP reputation. Consider using a VPN for safer operation.

## 🆚 Comparison with Rust Version

| Feature | Rust Version | Python Version |
|---------|--------------|----------------|
| **Performance** | ⚡ Very Fast | 🐢 Moderate |
| **Memory Usage** | 💚 Low | 💛 Moderate |
| **Single File** | ❌ No | ✅ Yes |
| **Dependencies** | Many | 2 (aiohttp, aiofiles) |
| **TUI Interface** | ✅ Yes | ❌ No |
| **ASN/Geo Data** | ✅ Yes | ❌ No |
| **Installation** | Binary Download | pip install |
| **Portability** | Binary per platform | Works anywhere |

The Python version is designed to be:
- ✅ Easier to customize and modify
- ✅ Simpler to understand and maintain
- ✅ More portable (runs anywhere with Python)
- ✅ Single file for easy distribution

## 📝 Examples

### Example 1: Quick Check with Fewer Proxies
```bash
python3 proxy_scraper_checker.py \
  --max-proxies-per-source 1000 \
  --max-concurrent-checks 256 \
  --output ./quick_test
```

### Example 2: Scrape Only (No Checking)
```bash
python3 proxy_scraper_checker.py \
  --no-check \
  --output ./scraped_proxies
```

### Example 3: JSON Output Only
```bash
python3 proxy_scraper_checker.py \
  --no-txt \
  --output ./json_output
```

### Example 4: Use Local Proxy Files
Edit the script to add local files:
```python
self.http_sources = [
    "./my_http_proxies.txt",
    "file:///path/to/more/proxies.txt",
]
```

## 🤝 Contributing

Feel free to modify and improve this script! Since it's a single file, you can easily:
- Add new proxy sources
- Implement additional output formats
- Add filtering options
- Enhance error handling

## 📄 License

MIT License - Same as the main project

---

**Related**: For more advanced features (TUI, geolocation, ASN data), check out the main [Rust version](../README.md).
