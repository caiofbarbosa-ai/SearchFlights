"""
Google Flights POC - Versão Final com Navegação Precisa de Calendário

CORREÇÃO FINAL: Navega para o mês correto antes de clicar nos dias.
O problema é que o calendário mostra o mês atual, e precisamos ir até julho 2027.
"""

import asyncio
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Configuração
ORIGINS = ["GRU"]
DESTINATION = "BKK"
DEPARTURE_DATE = "2027-07-28"
RETURN_DATE = "2027-08-05"
PASSENGERS = 2

class GoogleFlightsPOC:
    def __init__(self):
        self.results = []

    async def type_and_enter(self, page, selector, text, description=""):
        """Digita e confirma com Enter."""
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
            await asyncio.sleep(0.8)
            print(f"    ✓ {description}: {text}")
            return True
        except Exception as e:
            print(f"    [WARN] Falha: {e}")
            return False

    async def navigate_calendar_to_month(self, page, target_year, target_month):
        """
        Navega no calendário até o mês/ano desejado.
        O calendário mostra meses em pares, então precisa navegar até encontrar julho 2027.
        """
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Navegando para {target_month}/{target_year}...")

        target_month_pt = self._month_portuguese(target_month)
        print(f"    Procurando: {target_month_pt} de {target_year}")

        max_clicks = 60  # Máximo de cliques para evitar loop infinito
        clicks = 0

        while clicks < max_clicks:
            try:
                # Verificar se já estamos no mês correto
                calendar_text = await page.text_content('body')

                # Buscar pelo mês/ano no calendário
                if target_month_pt in calendar_text and str(target_year) in calendar_text:
                    # Verificar se o dia 28 existe neste mês
                    if await self._check_day_exists_in_month(page, "28"):
                        print(f"  ✓ Mês correto encontrado: {target_month_pt} {target_year}")
                        return True

                # Clicar no botão "Próximo" para avançar um mês
                next_selectors = [
                    'button[aria-label="Próximo mês"]',
                    'button[aria-label="Next month"]',
                    'button:has-text("›")',
                    'button:has-text(">")',
                ]

                clicked = False
                for selector in next_selectors:
                    try:
                        await page.click(selector, timeout=1000)
                        await asyncio.sleep(0.3)
                        clicked = True
                        clicks += 1
                        break
                    except:
                        continue

                if not clicked:
                    # Tentar clicar na seta direita visualmente
                    try:
                        arrows = await page.query_selector_all('button')
                        for arrow in arrows:
                            text = await arrow.text_content()
                            if text and ('›' in text or '>' in text):
                                await arrow.click()
                                await asyncio.sleep(0.3)
                                clicked = True
                                clicks += 1
                                break
                    except:
                        pass

                if not clicked:
                    print(f"  [WARN] Não foi possível navegar no calendário")
                    return False

            except Exception as e:
                print(f"  [WARN] Erro na navegação: {e}")
                clicks += 1
                await asyncio.sleep(0.5)

        print(f"  [WARN] Limite de cliques atingido ({max_clicks})")
        return False

    async def _check_day_exists_in_month(self, page, day):
        """Verifica se o dia existe no mês atual do calendário."""
        try:
            day_btn = await page.query_selector(f'button:has-text("{day}")')
            return day_btn is not None
        except:
            return False

    def _month_portuguese(self, month_num):
        months = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        return months[month_num - 1]

    async def select_dates_with_navigation(self, page, dep_date_str, ret_date_str):
        """Seleciona datas com navegação para o mês correto."""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Selecionando datas...")

            dep_date = datetime.strptime(dep_date_str, "%Y-%m-%d")
            ret_date = datetime.strptime(ret_date_str, "%Y-%m-%d")

            # 1. Abrir calendário
            date_selectors = [
                'input[aria-label*="Data de partida"]',
                'input[placeholder*="Partida"]',
            ]

            opened = False
            for selector in date_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await asyncio.sleep(1)
                    opened = True
                    break
                except:
                    continue

            if not opened:
                print("  [WARN] Não foi possível abrir calendário")
                return False

            # 2. Navegar até julho 2027
            nav_ok = await self.navigate_calendar_to_month(page, dep_date.year, dep_date.month)
            if not nav_ok:
                print("  [WARN] Não foi possível navegar para o mês correto")

            # 3. Clicar no dia de partida
            await asyncio.sleep(0.5)
            dep_clicked = await self._click_day_safe(page, str(dep_date.day), "ida")

            # 4. Navegar até agosto 2027 se necessário
            if dep_clicked:
                await asyncio.sleep(0.5)
                await self.navigate_calendar_to_month(page, ret_date.year, ret_date.month)

            # 5. Clicar no dia de volta
            await asyncio.sleep(0.5)
            ret_clicked = await self._click_day_safe(page, str(ret_date.day), "volta")

            # 6. Confirmar
            await asyncio.sleep(0.5)
            await self._confirm_dates(page)

            return dep_clicked and ret_clicked

        except Exception as e:
            print(f"  [ERROR] Erro ao selecionar datas: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _click_day_safe(self, page, day, trip_type):
        """Clica no dia com validação."""
        try:
            print(f"    Clicando dia {day} ({trip_type})...")

            # Tentar encontrar o dia no calendário atual
            selectors = [
                f'button:has-text("{day}")',
                f'[data-day="{day}"]',
                f'text={day}',
            ]

            for selector in selectors:
                try:
                    elem = await page.wait_for_selector(selector, timeout=2000)
                    if elem:
                        await elem.click()
                        await asyncio.sleep(0.3)
                        print(f"    ✓ Dia {day} clicado")
                        return True
                except:
                    continue

            print(f"    [WARN] Dia {day} não encontrado")
            return False
        except Exception as e:
            print(f"    [WARN] Erro ao clicar dia {day}: {e}")
            return False

    async def _confirm_dates(self, page):
        """Confirma seleção de datas."""
        try:
            # Tentar botão Concluído
            selectors = [
                'button:has-text("Concluído")',
                'button:has-text("Done")',
                'button[aria-label*="Concluído"]',
            ]

            for selector in selectors:
                try:
                    await page.click(selector, timeout=2000)
                    await asyncio.sleep(0.5)
                    print("  ✓ Datas confirmadas")
                    return True
                except:
                    continue

            # Fallback: Enter
            await page.keyboard.press('Enter')
            await asyncio.sleep(0.5)
            print("  ✓ Datas confirmadas (Enter)")
            return True
        except:
            return False

    async def run_search(self, origin):
        """Executa busca completa."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='pt-BR'
            )

            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            try:
                print(f"\n{'='*70}")
                print(f"BUSCA: {origin} → {DESTINATION} | {DEPARTURE_DATE} - {RETURN_DATE}")
                print(f"{'='*70}\n")

                # Navegar
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navegando...")
                await page.goto('https://www.google.com/travel/flights', timeout=60000)
                await asyncio.sleep(5)

                # Preencher campos
                await self.type_and_enter(page, 'input[aria-label*="De onde?"]', origin, "Origem")
                await asyncio.sleep(1)

                await self.type_and_enter(page, 'input[aria-label*="Para onde?"]', DESTINATION, "Destino")
                await asyncio.sleep(1.5)

                # Selecionar datas com navegação
                dates_ok = await self.select_dates_with_navigation(page, DEPARTURE_DATE, RETURN_DATE)

                await asyncio.sleep(1)

                # Screenshot antes de buscar
                await page.screenshot(path=f"poc/reports/final_{origin}_before_search.png")

                # Buscar
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Executando busca...")
                await page.keyboard.press('Enter')
                await asyncio.sleep(30)

                # Capturar resultados
                await page.screenshot(path=f"poc/reports/final_{origin}_results.png", full_page=True)

                html = await page.content()
                with open(f"poc/reports/final_{origin}_html.html", "w", encoding="utf-8") as f:
                    f.write(html)

                # Verificar se há voos
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Verificando resultados...")

                flight_indicators = [
                    '[data-result-id]',
                    '[role="article"]',
                    '.gElC9',
                ]

                found = False
                for indicator in flight_indicators:
                    try:
                        elements = await page.query_selector_all(indicator)
                        if elements and len(elements) > 2:
                            print(f"  ✓ {len(elements)} resultados encontrados!")
                            found = True

                            # Extrair preços
                            for i, elem in enumerate(elements[:5]):
                                try:
                                    text = await elem.text_content()
                                    prices = re.findall(r'R\$ ?([\d\.]+)', text)
                                    if prices:
                                        print(f"    Voo {i+1}: R$ {prices[0]}")
                                        self.results.append({'price': f"R$ {prices[0]}"})
                                except:
                                    pass
                            break
                    except:
                        continue

                if found:
                    print(f"\n✓✓✓ SUCESSO! {len(self.results)} preços extraídos")
                else:
                    print(f"\n[INFO] Nenhum resultado encontrado")

                return {'success': found, 'prices': len(self.results)}

            except Exception as e:
                print(f"[ERROR] {e}")
                import traceback
                traceback.print_exc()
                return {'success': False, 'error': str(e)}

            finally:
                await asyncio.sleep(5)
                await context.close()
                await browser.close()

async def main():
    print("=" * 70)
    print("GOOGLE FLIGHTS POC - FINAL")
    print("Com navegação precisa de calendário")
    print("=" * 70)

    await asyncio.sleep(2)

    poc = GoogleFlightsPOC()
    result = await poc.run_search("GRU")

    print(f"\nResultado: {result}")

if __name__ == "__main__":
    asyncio.run(main())
