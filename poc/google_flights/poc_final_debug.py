"""
Google Flights POC - Debug Version Final (Completa)
CORRIGIDO: Seletores em português + Handler para modal + Preenchimento de datas
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

    async def clear_and_type(self, page, selector, text, description=""):
        """Limpa campo, digita texto e fecha modal com ESC."""
        try:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {description}")
            await page.click(selector, timeout=5000)
            await asyncio.sleep(0.3)

            # Selecionar tudo e deletar
            await page.keyboard.press('Control+A')
            await asyncio.sleep(0.1)
            await page.keyboard.press('Delete')
            await asyncio.sleep(0.3)

            # Digitar caractere por caractere
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            # IMPORTANTE: Pressionar ESC para fechar modal de sugestões
            await asyncio.sleep(0.5)
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.3)

            print(f"    ✓ {description}: {text}")
        except Exception as e:
            print(f"    [WARN] Falha em {description}: {e}")

    async def fill_date(self, page, selector, date_value, description=""):
        """Preenche campo de data."""
        try:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {description}")
            await page.click(selector, timeout=5000)
            await asyncio.sleep(0.3)

            # Limpar e digitar data no formato correto
            await page.keyboard.press('Control+A')
            await asyncio.sleep(0.1)
            await page.keyboard.press('Delete')
            await asyncio.sleep(0.2)

            # Digitar data (formato DD/MM/YYYY ou YYYY-MM-DD)
            for char in date_value:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.1))

            await page.keyboard.press('Escape')
            await asyncio.sleep(0.3)

            print(f"    ✓ {description}: {date_value}")
        except Exception as e:
            print(f"    [WARN] Falha em {description}: {e}")

    async def run_debug_search(self, origin):
        """Execute search com todas as correções."""
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

                # 1. Preencher ORIGEM
                await self.clear_and_type(
                    page,
                    'input[aria-label*="De onde?"]',
                    origin,
                    "Preenchendo ORIGEM"
                )
                await asyncio.sleep(1)

                # Screenshot após origem
                await page.screenshot(path=f"poc/reports/final_1_after_origin.png")

                # 2. Preencher DESTINO (com ESC do modal anterior)
                await self.clear_and_type(
                    page,
                    'input[aria-label*="Para onde?"]',
                    DESTINATION,
                    "Preenchendo DESTINO"
                )
                await asyncio.sleep(1)

                # Screenshot após destino
                await page.screenshot(path=f"poc/reports/final_2_after_dest.png")

                # 3. Preencher DATA DE PARTIDA
                # Tentar múltiplos seletores para data
                date_selectors = [
                    'input[aria-label*="Data de partida"]',
                    'input[aria-label*="Partida"]',
                    'input[aria-label*="Ida"]',
                    'input[placeholder*="Partida"]',
                ]

                departure_filled = False
                for selector in date_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            await self.fill_date(page, selector, DEPARTURE_DATE, "Preenchendo DATA DE PARTIDA")
                            departure_filled = True
                            break
                    except:
                        continue

                if not departure_filled:
                    print("  [WARN] Campo de data de partida não encontrado, tentando abordagem alternativa...")
                    # Tentar clicar no campo visual e digitar
                    try:
                        await page.click('text="Partida"')
                        await asyncio.sleep(0.5)
                        for char in DEPARTURE_DATE:
                            await page.keyboard.type(char)
                            await asyncio.sleep(0.05)
                        await page.keyboard.press('Escape')
                        await asyncio.sleep(0.3)
                        print("    ✓ Data de partida preenchida (abordagem alternativa)")
                    except Exception as e:
                        print(f"    [ERROR] Não foi possível preencher data de partida: {e}")

                await asyncio.sleep(1)

                # 4. Preencher DATA DE VOLTA
                return_selectors = [
                    'input[aria-label*="Data de volta"]',
                    'input[aria-label*="Volta"]',
                    'input[aria-label*="Retorno"]',
                    'input[placeholder*="Volta"]',
                ]

                return_filled = False
                for selector in return_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            await self.fill_date(page, selector, RETURN_DATE, "Preenchendo DATA DE VOLTA")
                            return_filled = True
                            break
                    except:
                        continue

                if not return_filled:
                    print("  [WARN] Campo de data de volta não encontrado, tentando abordagem alternativa...")
                    try:
                        await page.click('text="Volta"')
                        await asyncio.sleep(0.5)
                        for char in RETURN_DATE:
                            await page.keyboard.type(char)
                            await asyncio.sleep(0.05)
                        await page.keyboard.press('Escape')
                        await asyncio.sleep(0.3)
                        print("    ✓ Data de volta preenchida (abordagem alternativa)")
                    except Exception as e:
                        print(f"    [ERROR] Não foi possível preencher data de volta: {e}")

                await asyncio.sleep(1)

                # Screenshot após datas
                await page.screenshot(path=f"poc/reports/final_3_after_dates.png")

                # 5. Submeter busca
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Submetendo BUSCA...")
                await page.keyboard.press('Enter')
                await asyncio.sleep(2)

                # 6. Aguardar resultados carregarem
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Aguardando resultados...")
                await asyncio.sleep(15)

                # Screenshot final
                await page.screenshot(path=f"poc/reports/final_4_results.png", full_page=True)
                print(f"  [DEBUG] Screenshot final salvo")

                # Salvar HTML para análise
                html_content = await page.content()
                with open(f"poc/reports/final_html_results.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"  [DEBUG] HTML salvo para análise")

                # 7. Verificar se há resultados
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Analisando resultados...")

                # Verificar mensagens de erro
                error_selectors = [
                    'text=/sem voos/i',
                    'text=/nenhum voo/i',
                    'text=/no flights/i',
                    'text=/não encontrado/i',
                ]

                has_errors = False
                for selector in error_selectors:
                    try:
                        error_elem = await page.query_selector(selector)
                        if error_elem:
                            error_text = await error_elem.text_content()
                            print(f"  [INFO] Mensagem de erro encontrada: {error_text}")
                            has_errors = True
                            break
                    except:
                        continue

                if not has_errors:
                    print("  ✓ Sem mensagens de erro aparentes")

                # 8. Extrair preços (se houver resultados)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tentando extrair preços...")

                # Seletores mais específicos para resultados de voo
                flight_result_selectors = [
                    '[data-result-id]',
                    '[role="article"]',
                    '.gElC9',
                    '[jsname*="flight"]',
                ]

                flights_found = False
                for selector in flight_result_selectors:
                    try:
                        flights = await page.query_selector_all(selector)
                        if flights and len(flights) > 0:
                            print(f"  ✓ {len(flights)} resultados de voo encontrados com: {selector}")
                            flights_found = True

                            # Tentar extrair informações dos primeiros voos
                            for i, flight in enumerate(flights[:3]):
                                try:
                                    flight_html = await flight.inner_html()
                                    flight_text = await flight.text_content()

                                    print(f"\n    Voo {i+1}:")
                                    print(f"    Texto: {flight_text[:200]}...")

                                    # Procurar por preços no HTML
                                    if 'R$' in flight_html:
                                        import re
                                        prices = re.findall(r'R\$ ?[\d\.]+', flight_html)
                                        if prices:
                                            print(f"    Preços encontrados: {prices}")

                                except Exception as e:
                                    print(f"    [WARN] Erro ao extrair voo {i}: {e}")

                            break
                    except Exception as e:
                        continue

                if not flights_found:
                    print("  [INFO] Nenhum resultado de voo encontrado")
                    print("  [INFO] Verifique o screenshot e HTML para diagnóstico")

                print(f"\n{'='*60}")
                print("DEBUG COMPLETADO")
                print(f"{'='*60}")
                print("Arquivos gerados:")
                print("  - Screenshots: poc/reports/final_*.png")
                print("  - HTML: poc/reports/final_html_results.html")
                print(f"{'='*60}\n")

            except Exception as e:
                print(f"[ERROR] {str(e)}")
                import traceback
                traceback.print_exc()

            finally:
                print("\nAguardando 10 segundos antes de fechar (para visualização)...")
                await asyncio.sleep(10)
                await context.close()
                await browser.close()

async def main():
    print("=" * 60)
    print("GOOGLE FLIGHTS POC - DEBUG FINAL")
    print("=" * 60)
    print("Correções implementadas:")
    print("• Seletores em PORTUGUÊS")
    print("• Handler para modal (ESC key)")
    print("• Preenchimento de datas")
    print("• Submissão completa da busca")
    print("• Extração detalhada de resultados")
    print("=" * 60)

    await asyncio.sleep(2)

    poc = GoogleFlightsDebugPOC()
    await poc.run_debug_search("GRU")

if __name__ == "__main__":
    asyncio.run(main())
