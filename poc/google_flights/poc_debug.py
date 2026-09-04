"""
Google Flights POC - Debug Version
Captura HTML e screenshots para analisar estrutura de dados.
"""

import asyncio
import random
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

ORIGINS = ["GRU"]
DESTINATION = "BKK"
DEPARTURE_DATE = "2027-07-28"
RETURN_DATE = "2027-08-05"
PASSENGERS = 2

class GoogleFlightsDebugPOC:
    def __init__(self):
        self.results = []

    async def random_delay(self, min_ms=500, max_ms=3000):
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def human_type(self, page, selector, text):
        try:
            await page.click(selector, timeout=5000)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
        except Exception as e:
            print(f"  [WARN] Typing failed: {e}")

    async def run_debug_search(self, origin):
        """Execute search with extensive debugging."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Use non-headless to see what's happening
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            try:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to Google Flights...")
                await page.goto('https://www.google.com/travel/flights', timeout=60000)

                print("  Waiting 5 seconds for page to fully load...")
                await asyncio.sleep(5)

                # Screenshot before entering data
                await page.screenshot(path=f"poc/reports/debug_1_initial_page.png")
                print("  [DEBUG] Screenshot saved: debug_1_initial_page.png")

                # Enter origin
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Entering origin: {origin}")
                await self.human_type(page, 'input[aria-label*="Where from?"]', origin)
                await asyncio.sleep(2)

                # Screenshot after origin
                await page.screenshot(path=f"poc/reports/debug_2_after_origin.png")
                print("  [DEBUG] Screenshot saved: debug_2_after_origin.png")

                # Enter destination
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Entering destination: {DESTINATION}")
                try:
                    await page.click('input[aria-label*="Where to?"]', timeout=5000)
                    await asyncio.sleep(0.5)
                    await page.keyboard.type(DESTINATION)
                except:
                    print("  [WARN] Using fallback selector for destination...")
                    await page.fill('input[placeholder*="Where to?"]', DESTINATION)

                await asyncio.sleep(2)

                # Screenshot after destination
                await page.screenshot(path=f"poc/reports/debug_3_after_destination.png")
                print("  [DEBUG] Screenshot saved: debug_3_after_destination.png")

                # Submit search
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Submitting search...")
                await page.keyboard.press('Enter')

                print("  Waiting 10 seconds for results...")
                await asyncio.sleep(10)

                # Screenshot after search
                await page.screenshot(path=f"poc/reports/debug_4_after_search.png", full_page=True)
                print("  [DEBUG] Screenshot saved: debug_4_after_search.png")

                # Save HTML for analysis
                html_content = await page.content()
                with open(f"poc/reports/debug_html_{origin}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"  [DEBUG] HTML saved: debug_html_{origin}.html")

                # Try to find price elements with DEBUGGING
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] DEBUGGING: Looking for price elements...")

                # Try MANY possible selectors
                all_selectors = [
                    # Price-related selectors
                    '[data-gs]',
                    '[data-price]',
                    '.YMlIz',
                    '.gStJdb',
                    'span:has-text("R$")',
                    'span:has-text("$")',
                    'div:has-text("R$")',
                    'div:has-text("$")',
                    '[class*="price"]',
                    '[class*="Price"]',
                    '[class*="cost"]',
                    '[class*="Cost"]',
                    # Common Google Flights classes
                    '[jsname*="price"]',
                    '[jsname*="Price"]',
                    '[aria-label*="price"]',
                    '[aria-label*="Price"]',
                    # Generic currency patterns
                    '*:has-text("R$")',
                    '*:has-text("$")',
                ]

                found_prices = []

                for selector in all_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            print(f"\n  ✓ Found {len(elements)} elements with: {selector}")
                            for i, elem in enumerate(elements[:3]):  # First 3 elements
                                try:
                                    text = await elem.text_content()
                                    html = await elem.inner_html()
                                    print(f"    [{i+1}] Text: {text[:100]}")
                                    print(f"        HTML: {html[:100]}")

                                    if text and ('$' in text or 'R$' in text):
                                        found_prices.append({
                                            'selector': selector,
                                            'text': text,
                                            'html': html
                                        })
                                except Exception as e:
                                    print(f"      Error reading element: {e}")
                    except Exception as e:
                        continue

                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] PRICE ELEMENTS FOUND: {len(found_prices)}")

                if found_prices:
                    print("\n=== PRICE DETAILS ===")
                    for price in found_prices:
                        print(f"Selector: {price['selector']}")
                        print(f"Text: {price['text']}")
                        print(f"HTML: {price['html'][:200]}")
                        print("---")
                else:
                    print("\n  [INFO] No price elements found with current selectors")
                    print("  [INFO] HTML saved for manual inspection")

                # Final screenshot
                await page.screenshot(path=f"poc/reports/debug_5_final.png", full_page=True)
                print("  [DEBUG] Final screenshot saved")

                print("\n=== DEBUG COMPLETE ===")
                print("Check the following files:")
                print("  - Screenshots in poc/reports/debug_*.png")
                print("  - HTML in poc/reports/debug_html_GRU.html")
                print("  - This console output for found elements")

            except Exception as e:
                print(f"[ERROR] {str(e)}")
                import traceback
                traceback.print_exc()

            finally:
                await asyncio.sleep(5)  # Time to see the browser
                await context.close()
                await browser.close()

async def main():
    print("=" * 60)
    print("GOOGLE FLIGHTS POC - DEBUG VERSION")
    print("=" * 60)
    print("This version will:")
    print("• Run non-headless (visible browser)")
    print("• Take screenshots at each step")
    print("• Save HTML for analysis")
    print("• Try many price selectors")
    print("• Print detailed element information")
    print("=" * 60)

    await asyncio.sleep(3)  # Time to read the header

    poc = GoogleFlightsDebugPOC()
    await poc.run_debug_search("GRU")

if __name__ == "__main__":
    asyncio.run(main())
