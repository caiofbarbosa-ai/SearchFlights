"""
Google Flights POC - Versão Completa com Seleção Visual de Datas
CORRIGIDO: Clica nas datas no calendário e clica em "Concluído"
"""

import asyncio
import random
from datetime import datetime, timedelta
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
        """Digita texto e confirma com Enter."""
        try:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {description}")
            await page.click(selector, timeout=5000)
            await asyncio.sleep(0.3)

            await page.keyboard.press('Control+A')
            await asyncio.sleep(0.1)
            await page.keyboard.press('Delete')
            await asyncio.sleep(0.3)

            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.12))

            await asyncio.sleep(0.8)

            await page.keyboard.press('Enter')
            await asyncio.sleep(0.5)

            print(f"    ✓ {description}: {text}")
        except Exception as e:
            print(f"    [WARN] Falha em {description}: {e}")

    async def select_dates_in_calendar(self, page, departure_str, return_str):
        """Abre calendário e seleciona as datas visualmente."""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Selecionando datas no calendário...")

            # Parse das datas
            dep_date = datetime.strptime(departure_str, "%Y-%m-%d")
            ret_date = datetime.strptime(return_str, "%Y-%m-%d")

            dep_day = dep_date.day
            dep_month_name = self._get_portuguese_month(dep_date.month)
            ret_day = ret_date.day
            ret_month_name = self._get_portuguese_month(ret_date.month)

            print(f"  Selecionando: {dep_day} de {dep_month_name} (ida) e {ret_day} de {ret_month_name} (volta)")

            # 1. Clicar no campo de data para abrir calendário
            date_selectors = [
                'input[aria-label*="Data de partida"]',
                'input[placeholder*="Partida"]',
                'input[aria-label*="Partida"]',
            ]

            calendar_opened = False
            for selector in date_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await asyncio.sleep(1)
                    calendar_opened = True
                    print("  ✓ Calendário aberto")
                    break
                except:
                    continue

            if not calendar_opened:
                print("  [WARN] Não foi possível abrir o calendário")
                return False

            # Screenshot do calendário
            await page.screenshot(path=f"poc/reports/complete_1_calendar.png")

            # 2. Procurar e clicar na data de partida
            # O calendário mostra o dia como um botão/clickable element
            departure_selector = f'button:has-text("{dep_day}")'

            try:
                print(f"  Procurando dia {dep_day} no calendário...")
                await page.wait_for_selector(departure_selector, timeout=5000)
                await page.click(departure_selector)
                await asyncio.sleep(0.5)
                print(f"  ✓ Data de partida selecionada: {dep_day}/{dep_month_name}")
            except Exception as e:
                print(f"  [WARN] Não foi possível selecionar data de partida: {e}")
                # Tentar abordagem alternativa - procurar por texto
                try:
                    await page.click(f'text={dep_day}', timeout=3000)
                    await asyncio.sleep(0.5)
                    print(f"  ✓ Data de partida selecionada (alternativa)")
                except:
                    pass

            # Screenshot após seleção da ida
            await page.screenshot(path=f"poc/reports/complete_2_after_departure.png")

            # 3. Procurar e clicar na data de volta
            return_selector = f'button:has-text("{ret_day}")'

            try:
                print(f"  Procurando dia {ret_day} no calendário...")
                await page.wait_for_selector(return_selector, timeout=5000)
                await page.click(return_selector)
                await asyncio.sleep(0.5)
                print(f"  ✓ Data de volta selecionada: {ret_day}/{ret_month_name}")
            except Exception as e:
                print(f"  [WARN] Não foi possível selecionar data de volta: {e}")
                try:
                    await page.click(f'text={ret_day}', timeout=3000)
                    await asyncio.sleep(0.5)
                    print(f"  ✓ Data de volta selecionada (alternativa)")
                except:
                    pass

            # Screenshot após seleção da volta
            await page.screenshot(path=f"poc/reports/complete_3_after_return.png")

            # 4. Clicar no botão "Concluído"
            done_selectors = [
                'button:has-text("Concluído")',
                'button:has-text("Done")',
                'text="Concluído"',
            ]

            done_clicked = False
            for selector in done_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await asyncio.sleep(0.5)
                    done_clicked = True
                    print("  ✓ Botão 'Concluído' clicado")
                    break
                except:
                    continue

            if not done_clicked:
                print("  [WARN] Botão 'Concluído' não encontrado, tentando Enter...")
                await page.keyboard.press('Enter')
                await asyncio.sleep(0.5)

            # Screenshot final
            await page.screenshot(path=f"poc/reports/complete_4_dates_done.png")
            print("  ✓ Datas confirmadas")

            await asyncio.sleep(1)
            return True

        except Exception as e:
            print(f"  [ERROR] Erro ao selecionar datas: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_portuguese_month(self, month_num):
        """Retorna nome do mês em português."""
        months = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        return months[month_num - 1]

    async def run_search(self, origin):
        """Execute search com seleção visual de datas."""
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
                await self.type_and_confirm(
                    page,
                    'input[aria-label*="De onde?"]',
                    origin,
                    "Preenchendo ORIGEM"
                )
                await asyncio.sleep(1)

                # 2. Preencher DESTINO
                await self.type_and_confirm(
                    page,
                    'input[aria-label*="Para onde?"]',
                    DESTINATION,
                    "Preenchendo DESTINO"
                )
                await asyncio.sleep(1.5)

                # 3. Selecionar datas visualmente no calendário
                dates_selected = await self.select_dates_in_calendar(page, DEPARTURE_DATE, RETURN_DATE)

                if not dates_selected:
                    print("  [WARN] Datas não foram selecionadas, tentando continuar...")

                # 4. Submeter busca
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Submetendo BUSCA...")
                await page.keyboard.press('Enter')
                await asyncio.sleep(2)

                # 5. Aguardar resultados
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Aguardando resultados (30s)...")
                await asyncio.sleep(30)

                # Screenshot final
                await page.screenshot(path=f"poc/reports/complete_5_final_results.png", full_page=True)
                print(f"  [DEBUG] Screenshot final salvo")

                # Salvar HTML
                html_content = await page.content()
                with open(f"poc/reports/complete_html_results.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"  [DEBUG] HTML salvo")

                # 6. Analisar resultados
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Analisando resultados...")

                # Verificar se há voos
                flight_selectors = [
                    '[data-result-id]',
                    '[role="article"]',
                    '.gElC9',
                    '[jsname*="result"]',
                ]

                flights_found = False
                for selector in flight_selectors:
                    try:
                        flights = await page.query_selector_all(selector)
                        if flights and len(flights) > 0:
                            print(f"  ✓ {len(flights)} elementos encontrados com: {selector}")

                            if len(flights) > 2:  # Provavelmente são voos reais
                                print(f"  ✓✓✓ RESULTADOS DE VOOS ENCONTRADOS! ✓✓✓")
                                flights_found = True

                                # Extrair preços
                                import re
                                for i, flight in enumerate(flights[:10]):
                                    try:
                                        flight_text = await flight.text_content()
                                        prices = re.findall(r'R\$ ?([\d\.]+)', flight_text)
                                        if prices:
                                            price = prices[0]
                                            print(f"    Voo {i+1}: R$ {price}")
                                            self.results.append({
                                                'origin': origin,
                                                'destination': DESTINATION,
                                                'price': f"R$ {price}",
                                                'raw_price': price.replace('.', '')
                                            })
                                    except:
                                        pass
                                break
                    except:
                        continue

                if flights_found:
                    print(f"\n{'='*60}")
                    print(f"✓✓✓ EXTRAÇÃO BEM-SUCEDIDA! ✓✓✓")
                    print(f"Total de preços extraídos: {len(self.results)}")
                    print(f"{'='*60}\n")
                else:
                    print(f"\n{'='*60}")
                    print("Nenhum resultado de voo encontrado")
                    print("Verifique o screenshot para diagnóstico")
                    print(f"{'='*60}\n")

                return {'status': 'SUCCESS' if flights_found else 'NO_RESULTS', 'count': len(self.results)}

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
    print("GOOGLE FLIGHTS POC - VERSÃO COMPLETA")
    print("=" * 60)
    print("Correções finais:")
    print("• Seleção visual de datas no calendário")
    print("• Clique no botão 'Concluído'")
    print("• Extração com regex melhorada")
    print("=" * 60)

    await asyncio.sleep(2)

    poc = GoogleFlightsPOC()
    result = await poc.run_search("GRU")

    print(f"\nResultado final: {result}")

if __name__ == "__main__":
    asyncio.run(main())
