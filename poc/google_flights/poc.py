"""
Google Flights POC - Proof of Concept (v2 - With Lessons Learned)
Validates technical feasibility of scraping Google Flights for cash prices.

LESSONS LEARNED IMPLEMENTED:
1. Modal handler for cookie/consent dialogs
2. Increased timeout to 60s
3. Strategic wait after navigation
4. Better error handling and retries
5. Fallback to direct URL with parameters
"""

import asyncio
import random
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# POC Configuration
ORIGINS = ["GRU", "CGH", "VCP"]  # São Paulo airports
DESTINATION = "BKK"  # Bangkok
DEPARTURE_DATE = "2027-07-28"
RETURN_DATE = "2027-08-05"
PASSENGERS = 2

class GoogleFlightsPOC:
    def __init__(self):
        self.results = []

    async def random_delay(self, min_ms=500, max_ms=3000):
        """Add random delay to simulate human behavior."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def human_type(self, page, selector, text):
        """Type text character-by-character with random intervals."""
        try:
            await page.click(selector, timeout=5000)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
        except Exception as e:
            print(f"  [WARN] Typing failed for {selector}: {e}")

    async def handle_modals(self, page):
        """Handle cookie consent and other modals that might interfere."""
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Checking for modals...")

        # Common cookie consent button selectors
        modal_selectors = [
            'button:has-text("Accept all")',
            'button:has-text("Aceitar tudo")',
            'button:has-text("Accept")',
            'button:has-text("Aceitar")',
            '[aria-label*="Accept"]',
            '[aria-label*="Aceitar"]',
            '.consent-button',
            '#cookie-banner button',
            'button[aria-label="Fechar"]',
            'button[aria-label="Close"]',
        ]

        for selector in modal_selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=2000)
                if button:
                    print(f"  Found modal button: {selector}")
                    await button.click()
                    await asyncio.sleep(1)
                    print(f"  Modal closed/accepted")
                    break
            except:
                continue

    async def wait_for_page_stable(self, page, timeout=10000):
        """Wait for page to be stable after navigation."""
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Waiting for page to stabilize...")

        try:
            # Wait for network to be mostly idle
            await page.wait_for_load_state('domcontentloaded', timeout=timeout)
            await asyncio.sleep(2)  # Extra time for dynamic content
            print(f"  Page stabilized")
        except Exception as e:
            print(f"  [WARN] Stability wait timeout, continuing...")

    async def try_direct_url(self, origin):
        """Fallback: Use direct URL with search parameters."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Trying direct URL approach...")

        # Format URL with search parameters
        url = f"https://www.google.com/travel/flights?tfs={origin}:{DESTINATION}:{DEPARTURE_DATE}:{RETURN_DATE};tt={PASSENGERS}"
        print(f"  URL: {url}")

        async with async_playwright() as p:
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

            try:
                await page.goto(url, timeout=60000)
                await self.wait_for_page_stable(page)

                # Look for results
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Looking for flight results...")

                # Try multiple selectors for results
                result_selectors = [
                    '[data-result-id]',
                    '[role="article"]',
                    '.gElC9',
                    '.Vfpq6'
                ]

                found_results = False
                for selector in result_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        print(f"  Found results with selector: {selector}")
                        found_results = True
                        break
                    except:
                        continue

                if found_results:
                    # Try to extract some data
                    price_selectors = [
                        '[data-gs]',
                        '.YMlIz',
                        '.gStJdb'
                    ]

                    for price_sel in price_selectors:
                        try:
                            prices = await page.query_selector_all(price_sel)
                            for price_elem in prices[:3]:
                                text = await price_elem.text_content()
                                if text and ('$' in text or 'R$' in text or any(c.isdigit() for c in text)):
                                    print(f"  Price found: {text.strip()}")
                                    self.results.append({
                                        'origin': origin,
                                        'price': text.strip(),
                                        'method': 'direct_url',
                                        'timestamp': datetime.now().isoformat()
                                    })
                                    break
                            if self.results:
                                break
                        except:
                            continue

                return {
                    'status': 'SUCCESS',
                    'origin': origin,
                    'method': 'direct_url',
                    'found_results': len(self.results) > 0,
                    'timestamp': datetime.now().isoformat()
                }

            except Exception as e:
                print(f"[ERROR] Direct URL approach failed: {e}")
                return {
                    'status': 'ERROR',
                    'origin': origin,
                    'error': str(e),
                    'method': 'direct_url',
                    'timestamp': datetime.now().isoformat()
                }

            finally:
                await context.close()
                await browser.close()

    async def run_search(self, origin):
        """Execute a single search for given origin."""
        start_time = datetime.now()

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

            try:
                # Navigate to Google Flights with INCREASED TIMEOUT
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to Google Flights...")

                await page.goto('https://www.google.com/travel/flights', timeout=60000)

                # STRATEGIC WAIT after navigation
                await self.wait_for_page_stable(page, timeout=15000)
                await self.random_delay(1000, 2000)

                # HANDLE MODALS before interaction
                await self.handle_modals(page)

                # Input origin with retries
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Entering origin: {origin}")

                origin_selectors = [
                    'input[aria-label*="Where from?"]',
                    'input[placeholder*="Where from?"]',
                    '#origin',
                    '[name="origin"]'
                ]

                origin_entered = False
                for selector in origin_selectors:
                    try:
                        await self.human_type(page, selector, origin)
                        origin_entered = True
                        print(f"  Origin entered using: {selector}")
                        break
                    except Exception as e:
                        print(f"  Failed with {selector}: {e}")
                        continue

                if not origin_entered:
                    raise Exception("Could not enter origin")

                await self.random_delay()

                # Input destination with retries
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Entering destination: {DESTINATION}")

                dest_selectors = [
                    'input[aria-label*="Where to?"]',
                    'input[placeholder*="Where to?"]',
                    '#destination',
                    '[name="destination"]'
                ]

                dest_entered = False
                for selector in dest_selectors:
                    try:
                        await self.human_type(page, selector, DESTINATION)
                        dest_entered = True
                        print(f"  Destination entered using: {selector}")
                        break
                    except Exception as e:
                        print(f"  Failed with {selector}: {e}")
                        continue

                if not dest_entered:
                    raise Exception("Could not enter destination")

                await self.random_delay()

                # Submit search
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Submitting search...")
                await page.keyboard.press('Enter')
                await self.random_delay(2000, 3000)

                # Wait for results with increased timeout
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for results...")

                result_selectors = [
                    '[data-result-id]',
                    '[role="article"]',
                    '.gElC9',
                    '[data-gs]'
                ]

                results_found = False
                for selector in result_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=20000)
                        print(f"  Results found with: {selector}")
                        results_found = True
                        break
                    except:
                        continue

                if results_found:
                    # Extract flight data
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Extracting flight data...")

                    # Look for price elements
                    price_selectors = [
                        '[data-gs]',
                        '.YMlIz',
                        '.gStJdb',
                        'span:has-text("R$")',
                        'span:has-text("$")'
                    ]

                    for price_sel in price_selectors:
                        try:
                            price_elements = await page.query_selector_all(price_sel)
                            if price_elements:
                                for elem in price_elements[:5]:
                                    try:
                                        text = await elem.text_content()
                                        if text and ('$' in text or 'R$' in text or any(c.isdigit() for c in text)):
                                            print(f"  Found: {text.strip()}")
                                            self.results.append({
                                                'origin': origin,
                                                'price': text.strip(),
                                                'timestamp': datetime.now().isoformat()
                                            })
                                            break
                                    except Exception as e:
                                        continue
                                if self.results:
                                    break
                        except Exception as e:
                            continue

                execution_time = (datetime.now() - start_time).total_seconds()

                result = {
                    'status': 'SUCCESS',
                    'origin': origin,
                    'found_results': len(self.results) > 0,
                    'execution_time': f"{execution_time:.1f}s",
                    'timestamp': datetime.now().isoformat()
                }

                print(f"  ✓ Execution completed in {execution_time:.1f}s")

            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                print(f"[ERROR] {str(e)}")
                print(f"  Execution time: {execution_time:.1f}s")

                result = {
                    'status': 'ERROR',
                    'origin': origin,
                    'error': str(e),
                    'execution_time': f"{execution_time:.1f}s",
                    'timestamp': datetime.now().isoformat()
                }

            finally:
                await context.close()
                await browser.close()

            return result

    async def run_poc(self):
        """Execute POC for all origins."""
        print("=" * 60)
        print("GOOGLE FLIGHTS POC v2 - Lessons Learned Applied")
        print("=" * 60)
        print(f"Target: {ORIGINS} → {DESTINATION}")
        print(f"Dates: {DEPARTURE_DATE} - {RETURN_DATE}")
        print(f"Passengers: {PASSENGERS}")
        print("\nIMPROVEMENTS:")
        print("• Modal handler for cookie/consent dialogs")
        print("• Increased timeout to 60s")
        print("• Strategic wait after navigation")
        print("• Better selector fallbacks")
        print("• Direct URL fallback available")
        print("=" * 60)

        all_results = []
        consecutive_errors = 0
        max_consecutive_errors = 2

        for i, origin in enumerate(ORIGINS, 1):
            print(f"\n--- Test {i}/{len(ORIGINS)}: {origin} → {DESTINATION} ---")

            if i > 1:
                # Rate limiting between queries
                print(f"Waiting 7 seconds before next query...")
                await asyncio.sleep(7)

            result = await self.run_search(origin)

            if result['status'] == 'ERROR':
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print(f"\n[PAUSE] {consecutive_errors} consecutive errors. Trying direct URL approach...")
                    direct_result = await self.try_direct_url(origin)
                    all_results.append(direct_result)
                    consecutive_errors = 0
                else:
                    all_results.append(result)
            else:
                consecutive_errors = 0
                all_results.append(result)

        # Summary
        print("\n" + "=" * 60)
        print("POC SUMMARY")
        print("=" * 60)
        for r in all_results:
            status_icon = "✓" if r['status'] == 'SUCCESS' else "✗"
            exec_time = r.get('execution_time', 'N/A')
            method = r.get('method', 'standard')
            print(f"{status_icon} {r['origin']}: {r['status']} ({method}) - {exec_time}")
            if r['status'] == 'ERROR':
                print(f"    Error: {r.get('error', 'Unknown')}")

        print(f"\nTotal results found: {len(self.results)}")

        success_count = sum(1 for r in all_results if r['status'] == 'SUCCESS')
        print(f"Success rate: {success_count}/{len(all_results)} ({success_count/len(all_results)*100:.0f}%)")
        print("=" * 60)

        return all_results


async def main():
    poc = GoogleFlightsPOC()
    results = await poc.run_poc()
    return results


if __name__ == "__main__":
    asyncio.run(main())
