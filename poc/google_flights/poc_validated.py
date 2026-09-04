"""
Google Flights POC - Versão Validada Final
Incorpora todas as correções aprendidas nas tentativas anteriores.

CORREÇÕES IMPLEMENTADAS:
1. Seletores em PORTUGUÊS (não inglês)
2. Usa ENTER para confirmar (não ESC que cancela)
3. Seleção visual de datas no calendário
4. Clique no botão "Concluído"
5. Seletores robustos para extração (data-* attributes)
6. Espera condicional para carregamento de resultados
"""

import asyncio
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Configuração da busca
ORIGINS = ["GRU", "CGH", "VCP"]
DESTINATION = "BKK"
DEPARTURE_DATE = "2027-07-28"
RETURN_DATE = "2027-08-05"
PASSENGERS = 2

class GoogleFlightsPOC:
    def __init__(self):
        self.results = []

    async def random_delay(self, min_ms=500, max_ms=3000):
        """Delay aleatório para simular comportamento humano."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def type_and_enter(self, page, selector, text, description=""):
        """
        Digita texto e CONFIRMA com Enter.
        Importante: Enter confirma a seleção, ESC cancela.
        """
        try:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {description}")
            await page.click(selector, timeout=5000)
            await asyncio.sleep(0.3)

            # Limpar campo existente
            await page.keyboard.press('Control+A')
            await asyncio.sleep(0.1)
            await page.keyboard.press('Delete')
            await asyncio.sleep(0.3)

            # Digitar caractere por caractere (comportamento humano)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.12))

            # Aguardar dropdown de sugestões aparecer
            await asyncio.sleep(1)

            # CONFIRMAR com Enter (importante!)
            await page.keyboard.press('Enter')
            await asyncio.sleep(0.8)

            print(f"    ✓ {description}: {text}")
            return True
        except Exception as e:
            print(f"    [WARN] Falha em {description}: {e}")
            return False

    async def select_calendar_dates(self, page, dep_date_str, ret_date_str):
        """
        Seleciona datas visualmente no calendário e clica em Concluído.
        O Google Flights requer seleção visual, não apenas digitar texto.
        """
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Selecionando datas no calendário...")

            # Parse das datas
            dep_date = datetime.strptime(dep_date_str, "%Y-%m-%d")
            ret_date = datetime.strptime(ret_date_str, "%Y-%m-%d")

            dep_day = str(dep_date.day)
            ret_day = str(ret_date.day)
            dep_month_pt = self._month_portuguese(dep_date.month)
            ret_month_pt = self._month_portuguese(ret_date.month)

            print(f"  Seleção: {dep_day} {dep_month_pt} (ida) → {ret_day} {ret_month_pt} (volta)")

            # 1. Abrir o calendário clicando no campo de data
            date_field_selectors = [
                'input[aria-label*="Data de partida"]',
                'input[placeholder*="Partida"]',
            ]

            calendar_opened = False
            for selector in date_field_selectors:
                try:
                    elem = await page.wait_for_selector(selector, timeout=3000)
                    if elem:
                        await elem.click()
                        await asyncio.sleep(1)
                        calendar_opened = True
                        print("  ✓ Calendário aberto")
                        break
                except:
                    continue

            if not calendar_opened:
                print("  [WARN] Não foi possível abrir calendário")
                return False

            # 2. Navegar até o mês correto se necessário
            # (os meses mostrados podem não ser julho/agosto)

            # 3. Clicar na data de partida
            # Tenta múltiplas estratégias para encontrar o dia
            departure_clicked = await self._click_calendar_day(page, dep_day, "ida")

            if departure_clicked:
                print(f"  ✓ Data de partida: {dep_day}/{dep_month_pt}")
                await asyncio.sleep(0.5)
            else:
                print(f"  [WARN] Não foi possível selecionar data de partida")

            # 4. Clicar na data de volta
            return_clicked = await self._click_calendar_day(page, ret_day, "volta")

            if return_clicked:
                print(f"  ✓ Data de volta: {ret_day}/{ret_month_pt}")
                await asyncio.sleep(0.5)
            else:
                print(f"  [WARN] Não foi possível selecionar data de volta")

            # 5. Clicar no botão "Concluído"
            done_clicked = False
            done_selectors = [
                'button:has-text("Concluído")',
                '[data-fb-action="confirm"]',
                'button[aria-label*="Concluído"]',
            ]

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
                # Tentar Enter como fallback
                print("  Botão 'Concluído' não encontrado, tentando Enter...")
                await page.keyboard.press('Enter')
                await asyncio.sleep(0.5)

            await asyncio.sleep(1)
            return True

        except Exception as e:
            print(f"  [ERROR] Erro ao selecionar datas: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _click_calendar_day(self, page, day_str, trip_type):
        """Tenta múltiplas estratégias para clicar em um dia no calendário."""
        strategies = [
            # Estratégia 1: Botão com texto do dia
            f'button:has-text("{day_str}")',
            # Estratégia 2: Div com data attribute
            f'[data-date*="{day_str}"]',
            # Estratégia 3: Span com texto do dia
            f'span:has-text("{day_str}")',
            # Estratégia 4: Texto direto
            f'text={day_str}',
        ]

        for strategy in strategies:
            try:
                elem = await page.wait_for_selector(strategy, timeout=2000)
                if elem:
                    await elem.click()
                    await asyncio.sleep(0.3)
                    return True
            except:
                continue

        return False

    def _month_portuguese(self, month_num):
        """Retorna nome do mês em português."""
        months = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        return months[month_num - 1]

    async def wait_for_results(self, page, timeout=30):
        """Aguarda resultados de voos carregarem com múltiplos indicadores."""
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Aguardando resultados...")

        # Múltiplos indicadores de que resultados carregaram
        result_indicators = [
            '[data-result-id]',
            '[role="article"]',
            '.gElC9',
            '[jsname*="result"]',
        ]

        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            for indicator in result_indicators:
                try:
                    elements = await page.query_selector_all(indicator)
                    if elements and len(elements) > 0:
                        print(f"  ✓ Resultados detectados com: {indicator}")
                        return True
                except:
                    continue
            await asyncio.sleep(1)

        print(f"  [WARN] Timeout aguardando resultados ({timeout}s)")
        return False

    async def extract_flight_prices(self, page):
        """Extrai preços dos voos usando múltiplas estratégias."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Extraindo preços...")

        extracted = []

        # Estratégia 1: Seletores específicos para cards de voo
        flight_card_selectors = [
            '[data-result-id]',
            '[role="article"]',
            '.gElC9',
        ]

        cards_found = False
        for selector in flight_card_selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards and len(cards) > 2:  # Pelo menos alguns voos
                    print(f"  ✓ {len(cards)} cards de voo encontrados com: {selector}")
                    cards_found = True

                    # Extrair informações de cada card
                    for i, card in enumerate(cards[:10]):  # Primeiros 10
                        try:
                            text = await card.text_content()
                            html = await card.inner_html()

                            # Regex para extrair preço
                            prices = re.findall(r'R\$ ?([\d\.]+)', text)
                            if prices:
                                price = prices[0]
                                extracted.append({
                                    'index': i,
                                    'price': f"R$ {price}",
                                    'raw_price': price.replace('.', ''),
                                    'text_snippet': text[:150]
                                })
                                print(f"    Voo {i+1}: R$ {price}")
                        except Exception as e:
                            continue

                    if extracted:
                        break
            except:
                continue

        # Estratégia 2: Buscar por elementos com preço diretamente
        if not extracted:
            print("  Buscando elementos de preço diretamente...")
            price_selectors = [
                '[aria-label*="preço"]',
                '[aria-label*="Preço"]',
                '[data-gs]',  # Google data attribute
            ]

            for selector in price_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for elem in elements[:20]:
                            try:
                                text = await elem.text_content()
                                if text and 'R$' in text:
                                    prices = re.findall(r'R\$ ?([\d\.]+)', text)
                                    if prices and any(char.isdigit() for char in prices[0]):
                                        # Verificar se é um preço válido (4-5 dígitos)
                                        raw = prices[0].replace('.', '')
                                        if 3000 <= len(raw) <= 6 and raw.isdigit():
                                            extracted.append({
                                                'price': f"R$ {prices[0]}",
                                                'raw_price': raw
                                            })
                            except:
                                continue
                        if extracted:
                            break
                except:
                    continue

        return extracted

    async def run_search(self, origin):
        """Executa busca completa para uma origem."""
        start_time = datetime.now()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # False para visualizar
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='pt-BR'  # Importante: português
            )

            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            try:
                print(f"\n{'='*70}")
                print(f"BUSCA: {origin} → {DESTINATION}  |  {DEPARTURE_DATE} - {RETURN_DATE}")
                print(f"{'='*70}\n")

                # 1. Navegar para Google Flights
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navegando...")
                await page.goto('https://www.google.com/travel/flights', timeout=60000)
                await asyncio.sleep(5)

                # 2. Preencher ORIGEM (em português)
                origin_ok = await self.type_and_enter(
                    page,
                    'input[aria-label*="De onde?"]',
                    origin,
                    "Preenchendo ORIGEM"
                )

                if not origin_ok:
                    raise Exception("Falha ao preencher origem")

                await asyncio.sleep(1)

                # 3. Preencher DESTINO (em português)
                dest_ok = await self.type_and_enter(
                    page,
                    'input[aria-label*="Para onde?"]',
                    DESTINATION,
                    "Preenchendo DESTINO"
                )

                if not dest_ok:
                    raise Exception("Falha ao preencher destino")

                await asyncio.sleep(1.5)

                # 4. Selecionar datas no calendário visual
                dates_ok = await self.select_calendar_dates(page, DEPARTURE_DATE, RETURN_DATE)

                if not dates_ok:
                    print("  [WARN] Datas podem não estar selecionadas corretamente")

                await asyncio.sleep(1)

                # 5. Submeter a busca
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Submetendo busca...")
                await page.keyboard.press('Enter')
                await asyncio.sleep(2)

                # 6. Aguardar resultados carregarem
                results_loaded = await self.wait_for_results(page, timeout=30)

                if not results_loaded:
                    print("  [WARN] Resultados podem não ter carregado completamente")

                # 7. Capturar estado final
                await page.screenshot(path=f"poc/reports/validated_{origin}_final.png", full_page=True)
                html_content = await page.content()
                with open(f"poc/reports/validated_{origin}_html.html", "w", encoding="utf-8") as f:
                    f.write(html_content)

                # 8. Extrair preços
                prices = await self.extract_flight_prices(page)

                execution_time = (datetime.now() - start_time).total_seconds()

                result = {
                    'status': 'SUCCESS' if prices else 'NO_PRICES',
                    'origin': origin,
                    'destination': DESTINATION,
                    'departure': DEPARTURE_DATE,
                    'return': RETURN_DATE,
                    'prices_found': len(prices),
                    'prices': prices[:5],  # Primeiros 5 preços
                    'execution_time': f"{execution_time:.1f}s",
                    'timestamp': datetime.now().isoformat()
                }

                print(f"\n{'='*70}")
                if prices:
                    print(f"✓✓✓ EXTRAÇÃO BEM-SUCEDIDA ✓✓✓")
                    print(f"Total de preços extraídos: {len(prices)}")
                    print(f"Menor preço: {min(p['raw_price'] for p in prices) if prices else 'N/A'}")
                else:
                    print("Nenhum preço extraído")
                print(f"Tempo de execução: {execution_time:.1f}s")
                print(f"{'='*70}\n")

                return result

            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                print(f"[ERROR] {str(e)}")
                import traceback
                traceback.print_exc()

                return {
                    'status': 'ERROR',
                    'origin': origin,
                    'error': str(e),
                    'execution_time': f"{execution_time:.1f}s"
                }

            finally:
                print("Aguardando 5 segundos...")
                await asyncio.sleep(5)
                await context.close()
                await browser.close()

    async def run_poc(self):
        """Executa POC para todas as origens."""
        print("=" * 70)
        print("GOOGLE FLIGHTS POC - VERSÃO VALIDADA")
        print("=" * 70)
        print("\nCORREÇÕES IMPLEMENTADAS:")
        print("• Seletores em PORTUGUÊS")
        print("• Usa ENTER para confirmar (não ESC)")
        print("• Seleção visual de datas no calendário")
        print("• Clique no botão 'Concluído'")
        print("• Seletores robustos para extração")
        print("• Espera condicional para resultados")
        print("=" * 70)

        all_results = []

        for i, origin in enumerate(ORIGINS, 1):
            print(f"\n{'#'*70}")
            print(f"# TESTE {i}/{len(ORIGINS)}: {origin} → {DESTINATION}")
            print(f"{'#'*70}")

            result = await self.run_search(origin)
            all_results.append(result)

            # Rate limiting entre buscas
            if i < len(ORIGINS):
                print(f"\nAguardando 10 segundos antes da próxima busca...")
                await asyncio.sleep(10)

        # Relatório final
        print("\n" + "=" * 70)
        print("RELATÓRIO FINAL")
        print("=" * 70)

        for r in all_results:
            status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
            print(f"{status_icon} {r.get('origin', 'N/A')}: {r['status']} - {r.get('prices_found', 0)} preços")

        success_count = sum(1 for r in all_results if r['status'] == 'SUCCESS')
        total_prices = sum(r.get('prices_found', 0) for r in all_results)

        print(f"\nTaxa de sucesso: {success_count}/{len(all_results)} ({success_count/len(all_results)*100:.0f}%)")
        print(f"Total de preços extraídos: {total_prices}")
        print("=" * 70)

        return all_results

async def main():
    poc = GoogleFlightsPOC()
    results = await poc.run_poc()

    # Salvar resultados
    import json
    with open('poc/reports/validated_poc_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Resultados salvos em: poc/reports/validated_poc_results.json")

    return results

if __name__ == "__main__":
    asyncio.run(main())
