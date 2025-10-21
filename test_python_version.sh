#!/bin/bash
# Example: Quick test of the Python proxy scraper
# This demonstrates the script with minimal settings for testing

echo "Testing Python Proxy Scraper and Checker..."
echo "============================================"
echo ""

# Test 1: Scrape only (no checking) with limited proxies
echo "Test 1: Scrape-only mode with 10 proxies per source"
python3 proxy_scraper_checker.py \
    --no-check \
    --max-proxies-per-source 10 \
    --output ./test_output \
    --no-json

echo ""
echo "Output saved to ./test_output/"
echo ""
echo "Files created:"
ls -lh ./test_output/proxies/

echo ""
echo "Sample from all.txt:"
head -5 ./test_output/proxies/all.txt

echo ""
echo "Test completed successfully!"
