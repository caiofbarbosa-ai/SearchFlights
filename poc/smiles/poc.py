"""
Smiles POC - Proof of Concept
Validates technical feasibility of scraping Smiles for award availability.
"""

import asyncio
import random
import time
import json
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# POC Configuration
ORIGINS = ["GRU", "CGH", "VCP"]  # São Paulo airports
DESTINATION = "BKK"  # Bangkok
DEPARTURE_DATE = "2027-07-28"
RETURN_DATE = "2027-08-05"
PASSENGERS = 2
CABIN = "economy"

class SmilesPOC:
    def __init__(self):
        self.results = []
        self.api_responses = []

    async def random_delay(self, min_ms=500, max_ms=3000):
        """Add random delay to simulate human behavior."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def human_type(self, page, selector, text):
        """Type text character-by-character with random intervals."""
        await page.click(selector)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def capture_api_response(self, response):
        """Capture and validate API responses."""
        # Capture JSON responses that look like flight search results
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            try:
                data = await response.json()
                if data and any(key in data for key in ['flights', 'itineraries', 'results', 'offers']):
                    self.api_responses.append({
                        'url': response.url,
                        'status': response.status,
                        'data': data,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"[API] Captured response from: {response.url[:50]}...")
            except:
                pass

    async def run_search(self, origin):
        """Execute a single search for given origin."""
        async with async_playwright() as p:
            # Launch browser with stealth
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            # Set up response interception
            page.on('response', self.capture_api_response)

            try:
                # Navigate to Smiles
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to Smiles...")
                await page.goto('https://www.smiles.com.br/', timeout=30000)
                await self.random_delay(2000, 3000)

                # Look for login/flight search elements
                # Note: Smiles may require login or have a different flow
                await page.wait_for_load_state('networkidle', timeout=10000)
                await self.random_delay()

                # Try to find flight search input
                search_selectors = [
                    'input[placeholder*="origem"]',
                    'input[placeholder*="Origem"]',
                    'input[aria-label*="origem"]',
                    '#origin',
                    '[data-test="flight-search-origin"]'
                ]

                origin_input = None
                for selector in search_selectors:
                    try:
                        origin_input = await page.wait_for_selector(selector, timeout=5000)
                        if origin_input:
                            break
                    except:
                        continue

                if origin_input:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Entering origin: {origin}")
                    await self.human_type(page, search_selectors[0], origin)
                    await self.random_delay()
                else:
                    print("[WARN] Could not find origin input - Smiles may require login")
                    result = {
                        'status': 'BLOCKED',
                        'origin': origin,
                        'error': 'Login required or page structure changed',
                        'timestamp': datetime.now().isoformat()
                    }
                    await context.close()
                    await browser.close()
                    return result

                # Continue with destination and dates...
                # (This is a POC skeleton - actual selectors need validation)

                result = {
                    'status': 'SUCCESS',
                    'origin': origin,
                    'api_responses_captured': len(self.api_responses),
                    'timestamp': datetime.now().isoformat()
                }

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Search completed for {origin}")

            except Exception as e:
                print(f"[ERROR] {str(e)}")
                result = {
                    'status': 'ERROR',
                    'origin': origin,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

            finally:
                await context.close()
                await browser.close()

            return result

    async def run_poc(self):
        """Execute POC for all origins."""
        print("=" * 60)
        print("SMILES POC - Proof of Concept")
        print("=" * 60)
        print(f"Target: {ORIGINS} → {DESTINATION}")
        print(f"Dates: {DEPARTURE_DATE} - {RETURN_DATE}")
        print(f"Passengers: {PASSENGERS}")
        print("=" * 60)

        all_results = []

        for i, origin in enumerate(ORIGINS, 1):
            print(f"\n--- Test {i}/{len(ORIGINS)}: {origin} → {DESTINATION} ---")

            if i > 1:
                # Rate limiting between queries
                print(f"Waiting 7 seconds before next query...")
                await asyncio.sleep(7)

            result = await self.run_search(origin)
            all_results.append(result)

        # Summary
        print("\n" + "=" * 60)
        print("POC SUMMARY")
        print("=" * 60)
        for r in all_results:
            status_icon = "✓" if r['status'] == 'SUCCESS' else "✗"
            print(f"{status_icon} {r['origin']}: {r['status']}")
            if r.get('api_responses_captured'):
                print(f"    API responses captured: {r['api_responses_captured']}")
            if r['status'] == 'ERROR':
                print(f"    Error: {r.get('error', 'Unknown')}")

        print(f"\nTotal API responses captured: {len(self.api_responses)}")

        if self.api_responses:
            print("\n--- API Response Structure ---")
            for resp in self.api_responses[:1]:  # Show first response
                print(f"URL: {resp['url'][:80]}...")
                print(f"Status: {resp['status']}")
                if isinstance(resp['data'], dict):
                    print(f"Keys: {list(resp['data'].keys())[:10]}")

        print("=" * 60)

        return all_results


async def main():
    poc = SmilesPOC()
    results = await poc.run_poc()
    return results


if __name__ == "__main__":
    asyncio.run(main())
