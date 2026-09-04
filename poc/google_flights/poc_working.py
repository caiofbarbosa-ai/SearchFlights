"""
Google Flights POC - Versão Funcional
CORRIGIDO: Usa Enter para confirmar e aguarda dropdown de sugestões
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

class GoogleFlightsPOC:
    def __init__(self):
        self.results = []

    async def random_delay(self, min_ms=500, max_ms=3000):
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def type_and_confirm(self, page, selector, text, description=""):
        """Digita texto e CONFIRMA com Enter, aguardando o dropdown."""
        try:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {description}")
            await page.click(selector, timeout=5000)
            await asyncio.sleep(0.3)

            # Limpar campo
            await page.keyboard.press('Control+A')
            await asyncio.sleep(0.1)
            await page.keyboard.press('Delete')
            await asyncio.sleep(0.3)

            # Digitar caractere por caractere
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.12))

            # AGUARDAR o dropdown de sugestões aparecer
            await asyncio.sleep(1)

            # CONFIRMAR com Enter (não ESC)
            await page.keyboard.press('Enter')
            await asyncio.sleep(0.5)

            print(f"    ✓ {description}: {text}")
        except Exception as e:
            print(f"    [WARN] Falha em {description}: {e}")

    async def fill_date_via_click(self, page, date_text, description=""):
        """Preenche data clicando no calendário e confirmado."""
        try:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {description}")
            await asyncio.sleep(0.5)

            # Digitar a data diretamente
            for char in date_text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.1))

            await asyncio.sleep(0.3)

            # Confirmar com Enter
            await page.keyboard.press('Enter')
            await asyncio.sleep(0.5)

            print(f"    ✓ {description}: {date_text}")
        except Exception as e:
            print(f"    [WARN] Falha em {description}: {e}")

    async def run_search(self, origin):
        """Execute search com confirmação correta."""
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
                print(f"\n{'='*60}")
                print(f"BUSCA: {origin} → {DESTINATION}")
                print(f"Datas: {DEPARTURE_DATE} - {RETURN_DATE}")
                print(f"{'='*60}\n")

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navegando para Google Flights...")
                await page.goto('https://www.google.com/travel/flights', timeout=60000)
                await asyncio.sleep(5)

                # 1. Preencher ORIGEM com Enter
                await self.type_and_confirm(
                    page,
                    'input[aria-label*="De onde?"]',
                    origin,
                    "Preenchendo ORIGEM"
                )
                await asyncio.sleep(1.5)

                # 2. Preencher DESTINO com Enter
                await self.type_and_confirm(
                    page,
                    'input[aria-label*="Para onde?"]',
                    DESTINATION,
                    "Preenchendo DESTINO"
                )
                await asyncio.sleep(1.5)

                # Screenshot após destino
                await page.screenshot(path=f"poc/reports/working_1_after_dest.png")
                print("  [DEBUG] Screenshot salvo: working_1_after_dest.png")

                # 3. Preencher DATA DE PARTIDA
                date_selectors = [
                    'input[aria-label*="Data de partida"]',
                    'input[placeholder*="Partida"]',
                ]

                for selector in date_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=3000)
                        if elem:
                            await elem.click()
                            await asyncio.sleep(0.5)
                            await self.fill_date_via_click(page, DEPARTURE_DATE, "Preenchendo DATA DE PARTIDA")
                            break
                    except:
                        continue

                await asyncio.sleep(1)

                # 4. Preencher DATA DE VOLTA
                for selector in date_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=3000)
                        if elem:
                            await elem.click()
                            await asyncio.sleep(0.5)
                            await self.fill_date_via_click(page, RETURN_DATE, "Preenchendo DATA DE VOLTA")
                            break
                    except:
                        continue

                await asyncio.sleep(1)

                # Screenshot após datas
                await page.screenshot(path=f"poc/reports/working_2_after_dates.png")
                print("  [DEBUG] Screenshot salvo: working_2_after_dates.png")

                # 5. Submeter busca
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Submetendo BUSCA...")
                await page.keyboard.press('Enter')
                await asyncio.sleep(2)

                # 6. Aguardar resultados
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Aguardando resultados carregarem...")
                await asyncio.sleep(20)

                # Screenshot final
                await page.screenshot(path=f"poc/reports/working_3_results.png", full_page=True)
                print(f"  [DEBUG] Screenshot salvo: working_3_results.png")

                # Salvar HTML
                html_content = await page.content()
                with open(f"poc/reports/working_html_results.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"  [DEBUG] HTML salvo")

                # 7. Analisar resultados
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Analisando resultados...")

                # Verificar se há resultados de voos
                flight_selectors = [
                    '[data-result-id]',
                    '[role="article"]',
                    '.gElC9',
                ]

                flights_found = False
                for selector in flight_selectors:
                    try:
                        flights = await page.query_selector_all(selector)
                        if flights and len(flights) > 2:  # Pelo menos alguns resultados
                            print(f"  ✓ {len(flights)} resultados encontrados!")
                            flights_found = True

                            # Extrair preços dos primeiros voos
                            import re
                            for i, flight in enumerate(flights[:5]):
                                try:
                                    flight_text = await flight.text_content()
                                    prices = re.findall(r'R\$ ?([\d\.]+)', flight_text)
                                    if prices:
                                        print(f"    Voo {i+1}: R$ {prices[0]}")
                                        self.results.append({
                                            'origin': origin,
                                            'destination': DESTINATION,
                                            'price': f"R$ {prices[0]}",
                                            'currency': 'BRL'
                                        })
                                except:
                                    pass
                            break
                    except:
                        continue

                if flights_found:
                    print(f"\n  ✓✓✓ EXTRAÇÃO BEM-SUCEDIDA! ✓✓✓")
                    print(f"  Total de preços extraídos: {len(self.results)}")
                else:
                    print(f"  [INFO] Nenhum resultado de voo encontrado")
                    print(f"  [INFO] Verifique o screenshot para diagnóstico")

                print(f"\n{'='*60}")
                print("EXECUÇÃO COMPLETADA")
                print(f"{'='*60}\n")

                return {'status': 'SUCCESS' if flights_found else 'NO_RESULTS', 'flights_found': flights_found}

            except Exception as e:
                print(f"[ERROR] {str(e)}")
                import traceback
                traceback.print_exc()
                return {'status': 'ERROR', 'error': str(e)}

            finally:
                print("\nAguardando 10 segundos para visualização...")
                await asyncio.sleep(10)
                await context.close()
                await browser.close()

async def main():
    print("=" * 60)
    print("GOOGLE FLIGHTS POC - VERSÃO FUNCIONAL")
    print("=" * 60)
    print("Correções:")
    print("• Usa ENTER para confirmar (não ESC)")
    print("• Aguarda dropdown de sugestões")
    print("• Preenchimento completo de campos")
    print("• Extração de preços com regex")
    print("=" * 60)

    await asyncio.sleep(2)

    poc = GoogleFlightsPOC()
    result = await poc.run_search("GRU")

    print(f"\nResultado final: {result}")

if __name__ == "__main__":
    asyncio.run(main())
