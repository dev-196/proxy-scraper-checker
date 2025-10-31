#!/usr/bin/env python3
"""
Proxy Scraper and Checker - Single File Python Version

A simplified Python implementation of the proxy-scraper-checker tool.
Scrapes proxies from multiple sources and checks their functionality.

Supports:
- HTTP/HTTPS, SOCKS4, and SOCKS5 proxies
- Multiple proxy sources (URLs and local files)
- Concurrent proxy checking
- JSON and TXT output formats
- Response time measurement
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Set, Dict
from urllib.parse import urlparse
import aiohttp
import aiofiles


# Proxy regex pattern - matches protocol://[user:pass@]host:port
PROXY_REGEX = re.compile(
    r"(?:^|[^0-9A-Za-z])(?:(?P<protocol>https?|socks[45])://)?(?:(?P<username>[0-9A-Za-z]{1,64}):(?P<password>[0-9A-Za-z]{1,64})@)?(?P<host>[A-Za-z][\-\.A-Za-z]{0,251}[A-Za-z]|[A-Za-z]|(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(?:\.(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])){3}):(?P<port>[0-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])(?=[^0-9A-Za-z]|$)"
)

# IPv4 regex for parsing check responses
IPV4_REGEX = re.compile(
    r"^\s*(?P<host>(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(?:\.(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])){3})(?::(?:[0-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5]))?\s*$"
)


@dataclass
class ProxyConfig:
    """Configuration for proxy scraper and checker"""
    # Scraping settings
    max_proxies_per_source: int = 100000
    scraping_timeout: float = 60.0
    scraping_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Checking settings
    check_url: str = "https://api.ipify.org"
    max_concurrent_checks: int = 1024
    checking_timeout: float = 60.0
    checking_connect_timeout: float = 5.0
    checking_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Output settings
    output_path: str = "./out"
    sort_by_speed: bool = True
    txt_enabled: bool = True
    json_enabled: bool = True
    
    # Protocol sources
    http_sources: List[str] = None
    socks4_sources: List[str] = None
    socks5_sources: List[str] = None
    
    def __post_init__(self):
        if self.http_sources is None:
            self.http_sources = [
                "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=http",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/http.txt",
            ]
        if self.socks4_sources is None:
            self.socks4_sources = [
                "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks4",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/socks4.txt",
            ]
        if self.socks5_sources is None:
            self.socks5_sources = [
                "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks5",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/refs/heads/master/socks5.txt",
            ]


@dataclass
class Proxy:
    """Represents a proxy server"""
    protocol: str  # http, socks4, or socks5
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: Optional[float] = None
    exit_ip: Optional[str] = None
    
    def to_url(self, include_protocol: bool = True) -> str:
        """Convert proxy to URL format"""
        url = ""
        if include_protocol:
            url += f"{self.protocol}://"
        if self.username and self.password:
            url += f"{self.username}:{self.password}@"
        url += f"{self.host}:{self.port}"
        return url
    
    def __hash__(self):
        return hash((self.protocol, self.host, self.port, self.username, self.password))
    
    def __eq__(self, other):
        if not isinstance(other, Proxy):
            return False
        return (self.protocol == other.protocol and 
                self.host == other.host and 
                self.port == other.port and
                self.username == other.username and
                self.password == other.password)


class ProxyScraper:
    """Scrapes proxies from various sources"""
    
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.scraped_proxies: Set[Proxy] = set()
    
    async def scrape_source(self, url: str, protocol: str, session: aiohttp.ClientSession) -> int:
        """Scrape proxies from a single source"""
        try:
            # Check if it's a local file or URL
            parsed = urlparse(url)
            if parsed.scheme in ('', 'file'):
                # Local file
                file_path = url.replace('file://', '')
                async with aiofiles.open(file_path, 'r') as f:
                    text = await f.read()
            else:
                # Remote URL
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.config.scraping_timeout)) as response:
                    response.raise_for_status()
                    text = await response.text()
            
            # Parse proxies from text
            count = 0
            for match in PROXY_REGEX.finditer(text):
                if self.config.max_proxies_per_source > 0 and count >= self.config.max_proxies_per_source:
                    print(f"Warning: {url}: too many proxies (> {self.config.max_proxies_per_source}) - skipped")
                    break
                
                proxy_protocol = match.group('protocol')
                if proxy_protocol:
                    proxy_protocol = proxy_protocol.lower()
                    if proxy_protocol == 'https':
                        proxy_protocol = 'http'
                else:
                    proxy_protocol = protocol
                
                proxy = Proxy(
                    protocol=proxy_protocol,
                    host=match.group('host'),
                    port=int(match.group('port')),
                    username=match.group('username'),
                    password=match.group('password')
                )
                self.scraped_proxies.add(proxy)
                count += 1
            
            if count == 0:
                print(f"Warning: {url}: no proxies found")
            else:
                print(f"Scraped {count} proxies from {url}")
            
            return count
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return 0
    
    async def scrape_all(self) -> List[Proxy]:
        """Scrape proxies from all configured sources"""
        print("Starting proxy scraping...")
        
        headers = {'User-Agent': self.config.scraping_user_agent}
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            tasks = []
            
            # Add HTTP sources
            for url in self.config.http_sources:
                tasks.append(self.scrape_source(url, 'http', session))
            
            # Add SOCKS4 sources
            for url in self.config.socks4_sources:
                tasks.append(self.scrape_source(url, 'socks4', session))
            
            # Add SOCKS5 sources
            for url in self.config.socks5_sources:
                tasks.append(self.scrape_source(url, 'socks5', session))
            
            # Scrape all sources concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
        
        proxies = list(self.scraped_proxies)
        print(f"Total unique proxies scraped: {len(proxies)}")
        return proxies


class ProxyChecker:
    """Checks if proxies are working"""
    
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.working_proxies: List[Proxy] = []
        self.checked_count = 0
        self.total_count = 0
    
    async def check_proxy(self, proxy: Proxy, session: aiohttp.ClientSession) -> Optional[Proxy]:
        """Check if a single proxy is working"""
        if not self.config.check_url:
            # Skip checking
            return proxy
        
        try:
            proxy_url = proxy.to_url()
            timeout = aiohttp.ClientTimeout(
                total=self.config.checking_timeout,
                connect=self.config.checking_connect_timeout
            )
            
            start_time = time.time()
            async with session.get(
                self.config.check_url,
                proxy=proxy_url,
                timeout=timeout,
                allow_redirects=True
            ) as response:
                response.raise_for_status()
                elapsed = time.time() - start_time
                text = await response.text()
                
                # Parse exit IP from response
                try:
                    data = json.loads(text)
                    exit_ip = data.get('origin', data.get('ip', ''))
                except json.JSONDecodeError:
                    exit_ip = text.strip()
                
                # Extract IPv4 if possible
                match = IPV4_REGEX.match(exit_ip)
                if match:
                    exit_ip = match.group('host')
                
                proxy.timeout = round(elapsed, 2)
                proxy.exit_ip = exit_ip if exit_ip else None
                
                return proxy
        except Exception:
            return None
    
    async def check_all(self, proxies: List[Proxy]) -> List[Proxy]:
        """Check all proxies concurrently"""
        if not self.config.check_url:
            print("Skipping proxy checking (no check URL configured)")
            return proxies
        
        self.total_count = len(proxies)
        print(f"Starting proxy checking ({self.total_count} proxies)...")
        
        headers = {'User-Agent': self.config.checking_user_agent}
        connector = aiohttp.TCPConnector(limit=self.config.max_concurrent_checks)
        
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            # Create semaphore to limit concurrent checks
            semaphore = asyncio.Semaphore(self.config.max_concurrent_checks)
            
            async def check_with_semaphore(proxy):
                async with semaphore:
                    result = await self.check_proxy(proxy, session)
                    self.checked_count += 1
                    if self.checked_count % 100 == 0 or self.checked_count == self.total_count:
                        print(f"Checked {self.checked_count}/{self.total_count} proxies, found {len(self.working_proxies)} working")
                    if result:
                        self.working_proxies.append(result)
                    return result
            
            # Check all proxies
            await asyncio.gather(*[check_with_semaphore(p) for p in proxies], return_exceptions=True)
        
        print(f"Checking complete: {len(self.working_proxies)}/{self.total_count} proxies are working")
        return self.working_proxies


class ProxyOutputWriter:
    """Writes proxies to output files"""
    
    def __init__(self, config: ProxyConfig):
        self.config = config
    
    async def save_proxies(self, proxies: List[Proxy]):
        """Save proxies to output files"""
        if not proxies:
            print("No proxies to save")
            return
        
        # Sort proxies
        if self.config.sort_by_speed:
            proxies.sort(key=lambda p: p.timeout if p.timeout else float('inf'))
        else:
            proxies.sort(key=lambda p: (p.protocol, p.host, p.port))
        
        # Create output directory
        output_path = Path(self.config.output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save JSON output
        if self.config.json_enabled:
            await self.save_json(proxies, output_path)
        
        # Save TXT output
        if self.config.txt_enabled:
            await self.save_txt(proxies, output_path)
        
        print(f"Proxies saved to {output_path.absolute()}")
    
    async def save_json(self, proxies: List[Proxy], output_path: Path):
        """Save proxies in JSON format"""
        proxy_dicts = []
        for proxy in proxies:
            proxy_dict = {
                'protocol': proxy.protocol,
                'host': proxy.host,
                'port': proxy.port,
            }
            if proxy.username:
                proxy_dict['username'] = proxy.username
            if proxy.password:
                proxy_dict['password'] = proxy.password
            if proxy.timeout is not None:
                proxy_dict['timeout'] = proxy.timeout
            if proxy.exit_ip:
                proxy_dict['exit_ip'] = proxy.exit_ip
            proxy_dicts.append(proxy_dict)
        
        # Save compact JSON
        json_path = output_path / 'proxies.json'
        async with aiofiles.open(json_path, 'w') as f:
            await f.write(json.dumps(proxy_dicts, indent=None))
        print(f"Saved {len(proxies)} proxies to {json_path}")
        
        # Save pretty JSON
        json_pretty_path = output_path / 'proxies_pretty.json'
        async with aiofiles.open(json_pretty_path, 'w') as f:
            await f.write(json.dumps(proxy_dicts, indent=2))
    
    async def save_txt(self, proxies: List[Proxy], output_path: Path):
        """Save proxies in TXT format"""
        # Create proxies directory
        txt_dir = output_path / 'proxies'
        txt_dir.mkdir(exist_ok=True)
        
        # Group proxies by protocol
        grouped: Dict[str, List[Proxy]] = {}
        for proxy in proxies:
            if proxy.protocol not in grouped:
                grouped[proxy.protocol] = []
            grouped[proxy.protocol].append(proxy)
        
        # Save all proxies
        all_txt_path = txt_dir / 'all.txt'
        async with aiofiles.open(all_txt_path, 'w') as f:
            for proxy in proxies:
                await f.write(proxy.to_url(include_protocol=True) + '\n')
        print(f"Saved {len(proxies)} proxies to {all_txt_path}")
        
        # Save by protocol
        for protocol, protocol_proxies in grouped.items():
            protocol_path = txt_dir / f'{protocol}.txt'
            async with aiofiles.open(protocol_path, 'w') as f:
                for proxy in protocol_proxies:
                    await f.write(proxy.to_url(include_protocol=False) + '\n')


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Proxy Scraper and Checker - Single File Python Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
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
        """
    )
    
    # Scraping options
    parser.add_argument('--max-proxies-per-source', type=int, default=100000,
                        help='Maximum proxies to collect per source (0=unlimited)')
    parser.add_argument('--scraping-timeout', type=float, default=60.0,
                        help='Request timeout for fetching sources (seconds)')
    
    # Checking options
    parser.add_argument('--check-url', type=str, default='https://api.ipify.org',
                        help='URL for checking proxy functionality')
    parser.add_argument('--no-check', action='store_true',
                        help='Skip proxy checking (scrape only)')
    parser.add_argument('--max-concurrent-checks', type=int, default=1024,
                        help='Number of concurrent proxy checks')
    parser.add_argument('--checking-timeout', type=float, default=60.0,
                        help='Proxy response timeout (seconds)')
    
    # Output options
    parser.add_argument('--output', '-o', type=str, default='./out',
                        help='Output directory')
    parser.add_argument('--sort-by-speed', action='store_true', default=True,
                        help='Sort by response time (default)')
    parser.add_argument('--sort-by-address', dest='sort_by_speed', action='store_false',
                        help='Sort by IP address instead of speed')
    parser.add_argument('--no-txt', action='store_true',
                        help='Disable TXT output')
    parser.add_argument('--no-json', action='store_true',
                        help='Disable JSON output')
    
    args = parser.parse_args()
    
    # Create config
    config = ProxyConfig(
        max_proxies_per_source=args.max_proxies_per_source,
        scraping_timeout=args.scraping_timeout,
        check_url='' if args.no_check else args.check_url,
        max_concurrent_checks=args.max_concurrent_checks,
        checking_timeout=args.checking_timeout,
        output_path=args.output,
        sort_by_speed=args.sort_by_speed,
        txt_enabled=not args.no_txt,
        json_enabled=not args.no_json,
    )
    
    print("="*60)
    print("Proxy Scraper and Checker - Python Edition")
    print("="*60)
    
    try:
        # Scrape proxies
        scraper = ProxyScraper(config)
        proxies = await scraper.scrape_all()
        
        if not proxies:
            print("No proxies found!")
            sys.exit(1)
        
        # Check proxies
        if config.check_url:
            checker = ProxyChecker(config)
            proxies = await checker.check_all(proxies)
            
            if not proxies:
                print("No working proxies found!")
                sys.exit(1)
        
        # Save proxies
        writer = ProxyOutputWriter(config)
        await writer.save_proxies(proxies)
        
        print("\n" + "="*60)
        print("Thank you for using proxy-scraper-checker!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
