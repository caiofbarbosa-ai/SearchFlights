"""
Google Flights POC - Debug Version (Português)
Captura HTML e screenshots para analisar estrutura de dados.
CORRIGIDO: Seletores em português para página em português.
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

    async def clear_and_type(self, page, selector, text):
        """Limpa campo e digita novo texto."""
        try:
            await page.click(selector, timeout=5000)
            await asyncio.sleep(0.2)
            # Selecionar todo o texto e deletar
            await page.keyboard.press('Control+A')
            await asyncio.sleep(0.1)
            await page.keyboard.press('Delete')
            await asyncio.sleep(0.2)
            # Digitar novo texto
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
        except Exception as e:
            print(f"  [WARN] Clear and type failed: {e}")

    async def run_debug_search(self, origin):
        """Execute search with extensive debugging - PORTUGUÊS."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR'
            )

            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            try:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navegando para Google Flights...")
                await page.goto('https://www.google.com/travel/flights', timeout=60000)

                print("  Aguardando 5 segundos para página carregar completamente...")
                await asyncio.sleep(5)

                # Screenshot inicial
                await page.screenshot(path=f"poc/reports/debug_pt_1_initial.png")
                print("  [DEBUG] Screenshot salvo: debug_pt_1_initial.png")

                # SALVAR HTML inicial para análise
                html_content = await page.content()
                with open(f"poc/reports/debug_pt_html_initial.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"  [DEBUG] HTML inicial salvo: debug_pt_html_initial.html")

                # Tentar múltiplos seletores para origem (PORTUGUÊS)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tentando encontrar campo de origem...")

                origin_selectors = [
                    'input[aria-label*="De onde?"]',
                    'input[aria-label*="De onde"]',
                    'input[aria-label*="Origem"]',
                    'input[aria-label*="Origem "]',  # com espaço
                    'input[placeholder*="De onde?"]',
                    'input[placeholder*="Para onde?"]',  # campo destino
                    # Fallback inglês
                    'input[aria-label*="Where from?"]',
                    'input[aria-label*="Where from"]',
                ]

                origin_found = False
                for selector in origin_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            print(f"  ✓ Campo de origem encontrado: {selector}")
                            # Verificar estado atual
                            current_value = await elem.get_attribute('value')
                            aria_label = await elem.get_attribute('aria-label')
                            print(f"    Valor atual: '{current_value}'")
                            print(f"    aria-label: '{aria_label}'")
                            origin_found = True
                            origin_selector = selector
                            break
                    except:
                        continue

                if not origin_found:
                    print("  [ERROR] Campo de origem NÃO encontrado com nenhum seletor!")
                    print("  Tentando inspecionar todos os inputs...")
                    all_inputs = await page.query_selector_all('input')
                    print(f"  Total de inputs encontrados: {len(all_inputs)}")
                    for i, inp in enumerate(all_inputs):
                        try:
                            aria = await inp.get_attribute('aria-label')
                            ph = await inp.get_attribute('placeholder')
                            val = await inp.get_attribute('value')
                            print(f"    Input {i}: aria-label='{aria}', placeholder='{ph}', value='{val}'")
                        except:
                            pass
                    raise Exception("Could not find origin input field")

                # Entrar origem
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Inserindo origem: {origin}")

                # Se o campo já tem valor, limpar primeiro
                await self.clear_and_type(page, origin_selector, origin)
                await asyncio.sleep(2)

                # Screenshot após origem
                await page.screenshot(path=f"poc/reports/debug_pt_2_after_origin.png")
                print("  [DEBUG] Screenshot salvo: debug_pt_2_after_origin.png")

                # Tentar múltiplos seletores para destino (PORTUGUÊS)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tentando encontrar campo de destino...")

                dest_selectors = [
                    'input[aria-label*="Para onde?"]',
                    'input[aria-label*="Para onde"]',
                    'input[aria-label*="Destino"]',
                    'input[aria-label*="Destino "]',
                    'input[placeholder*="Para onde?"]',
                    # Fallback inglês
                    'input[aria-label*="Where to?"]',
                    'input[aria-label*="Where to"]',
                ]

                dest_found = False
                for selector in dest_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            print(f"  ✓ Campo de destino encontrado: {selector}")
                            dest_found = True
                            dest_selector = selector
                            break
                    except:
                        continue

                if not dest_found:
                    print("  [ERROR] Campo de destino NÃO encontrado!")
                    raise Exception("Could not find destination input field")

                # Entrar destino
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Inserindo destino: {DESTINATION}")
                await self.human_type(page, dest_selector, DESTINATION)
                await asyncio.sleep(2)

                # Screenshot após destino
                await page.screenshot(path=f"poc/reports/debug_pt_3_after_dest.png")
                print("  [DEBUG] Screenshot salvo: debug_pt_3_after_dest.png")

                # Submit search
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Submetendo busca...")
                await page.keyboard.press('Enter')

                print("  Aguardando 15 segundos para resultados...")
                await asyncio.sleep(15)

                # Screenshot após busca
                await page.screenshot(path=f"poc/reports/debug_pt_4_after_search.png", full_page=True)
                print("  [DEBUG] Screenshot salvo: debug_pt_4_after_search.png")

                # Salvar HTML final
                html_content = await page.content()
                with open(f"poc/reports/debug_pt_html_final.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"  [DEBUG] HTML final salvo: debug_pt_html_final.html")

                # Tentar encontrar preços
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Procurando elementos de preço...")

                # Verificar se há mensagem de "sem voos"
                no_flights_selectors = [
                    'text=/sem voos/i',
                    'text=/no flights/i',
                    'text=/nenhum voo/i',
                ]

                for selector in no_flights_selectors:
                    try:
                        no_flights = await page.query_selector(selector)
                        if no_flights:
                            text = await no_flights.text_content()
                            print(f"  [INFO] Mensagem encontrada: {text}")
                            break
                    except:
                        continue

                # Procurar por elementos que contenham "R$" ou valores monetários
                price_selectors = [
                    # Seletores específicos para preço
                    '[data-gs]',
                    '[data-price]',
                    '[aria-label*="preço"]',
                    '[aria-label*="Preço"]',
                    '[aria-label*="price"]',
                    # Classes comuns (podem mudar)
                    '.YMlIz',
                    '.gStJdb',
                    # Texto contendo R$
                    '*:has-text("R$")',
                    '*:has-text("R$ ")',
                ]

                found_prices = []

                for selector in price_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            print(f"\n  ✓ {len(elements)} elementos com: {selector}")
                            for i, elem in enumerate(elements[:5]):
                                try:
                                    text = await elem.text_content()
                                    if text:
                                        print(f"    [{i+1}] {text[:100]}")
                                        if 'R$' in text or 'USD' in text or '$' in text:
                                            found_prices.append({
                                                'selector': selector,
                                                'text': text.strip()
                                            })
                                except Exception as e:
                                    continue
                    except Exception as e:
                        continue

                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] PREÇOS ENCONTRADOS: {len(found_prices)}")

                if found_prices:
                    print("\n=== DETALHES DOS PREÇOS ===")
                    for price in found_prices[:10]:
                        print(f"Seletor: {price['selector']}")
                        print(f"Texto: {price['text'][:200]}")
                        print("---")
                else:
                    print("\n  [INFO] Nenhum elemento de preço encontrado")
                    print("  [INFO] HTML salvo para inspeção manual")

                print("\n=== DEBUG COMPLETADO ===")
                print("Arquivos gerados:")
                print("  - Screenshots: poc/reports/debug_pt_*.png")
                print("  - HTML: poc/reports/debug_pt_html_*.html")

            except Exception as e:
                print(f"[ERROR] {str(e)}")
                import traceback
                traceback.print_exc()

            finally:
                print("\nAguardando 5 segundos antes de fechar...")
                await asyncio.sleep(5)
                await context.close()
                await browser.close()

async def main():
    print("=" * 60)
    print("GOOGLE FLIGHTS POC - DEBUG (PORTUGUÊS)")
    print("=" * 60)
    print("Este versão:")
    print("• Usa seletores em PORTUGUÊS")
    print("• Executa em modo não-headless (visível)")
    print("• Captura screenshots em cada etapa")
    print("• Salva HTML para análise")
    print("• Tenta múltiplos seletores")
    print("=" * 60)

    await asyncio.sleep(2)

    poc = GoogleFlightsDebugPOC()
    await poc.run_debug_search("GRU")

if __name__ == "__main__":
    asyncio.run(main())
