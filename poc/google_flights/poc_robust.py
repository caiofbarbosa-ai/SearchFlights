"""
Google Flights POC - Versão Robusta com Diagnóstico
Com debugging extensivo e fallbacks para seletores.
"""

import asyncio
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

ORIGINS = ["GRU"]
DESTINATION = "BKK"
DEPARTURE_DATE = "2027-07-28"
RETURN_DATE = "2027-08-05"

class GoogleFlightsPOC:
    def __init__(self):
        self.results = []

    async def wait_and_diagnose(self, page):
        """Espera página carregar e diagnostica elementos disponíveis."""
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Aguardando carregamento da página...")

        # Esperar carregamento inicial
        await page.wait_for_load_state('domcontentloaded', timeout=30000)
        await asyncio.sleep(5)

        # Diagnosticar inputs disponíveis
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Diagnosticando inputs na página...")

        all_inputs = await page.query_selector_all('input')
        print(f"  Total de inputs: {len(all_inputs)}")

        for i, inp in enumerate(all_inputs[:15]):  # Primeiros 15
            try:
                aria = await inp.get_attribute('aria-label')
                ph = await inp.get_attribute('placeholder')
                val = await inp.get_attribute('value')
                print(f"    Input {i}: aria='{aria}', placeholder='{ph}', value='{val}'")
            except:
                pass

        return all_inputs

    async def type_and_enter_safe(self, page, text, description="", timeout=10000):
        """
        Digita texto procurando por múltiplos seletores possíveis.
        Tenta várias estratégias para encontrar o campo correto.
        """
        print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] {description} ({text})")

        # Estratégias de seletores para ORIGEM/DESTINO
        if "ORIGEM" in description or "origem" in description.lower():
            selectors = [
                'input[aria-label*="De onde?"]',
                'input[aria-label*="De onde"]',
                'input[aria-label*="Origem"]',
                'input[placeholder*="De onde?"]',
                'input[placeholder*="Origem"]',
                # Fallback inglês
                'input[aria-label*="Where from?"]',
                'input[aria-label*="Where from"]',
            ]
        else:  # DESTINO
            selectors = [
                'input[aria-label*="Para onde?"]',
                'input[aria-label*="Para onde"]',
                'input[aria-label*="Destino"]',
                'input[placeholder*="Para onde?"]',
                'input[placeholder*="Destino"]',
                # Fallback inglês
                'input[aria-label*="Where to?"]',
                'input[aria-label*="Where to"]',
            ]

        # Tentar cada seletor
        for selector in selectors:
            try:
                elem = await page.wait_for_selector(selector, timeout=3000)
                if elem:
                    print(f"    ✓ Campo encontrado: {selector}")

                    # Clicar e digitar
                    await elem.click()
                    await asyncio.sleep(0.3)

                    # Limpar
                    await page.keyboard.press('Control+A')
                    await asyncio.sleep(0.1)
                    await page.keyboard.press('Delete')
                    await asyncio.sleep(0.3)

                    # Digitar
                    for char in text:
                        await page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.05, 0.12))

                    await asyncio.sleep(1)

                    # Confirmar
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(1)

                    print(f"    ✓ {description} preenchido: {text}")
                    return True
            except:
                continue

        print(f"    [WARN] Nenhum seletor funcionou para {description}")
        return False

    async def use_url_direct(self, page, origin):
        """
        Abord alternativa: usar URL direta com parâmetros.
        Isso pode ser mais confiável que preencher campos.
        """
        try:
            print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] Tentando URL direta...")

            # Construir URL com parâmetros
            url = f"https://www.google.com/travel/flights?tfs={origin}:{DESTINATION}:{DEPARTURE_DATE.replace('-', '')}:{RETURN_DATE.replace('-', '')};tt=2"

            print(f"    URL: {url}")

            await page.goto(url, timeout=60000)
            await asyncio.sleep(10)

            print(f"    ✓ Navegou via URL direta")

            # Screenshot
            await page.screenshot(path=f"poc/reports/robust_{origin}_url_results.png")
            return True

        except Exception as e:
            print(f"    [WARN] URL direta falhou: {e}")
            return False

    async def run_search(self, origin):
        """Executa busca com abordagem robusta."""
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
                print(f"BUSCA: {origin} → {DESTINATION}")
                print(f"Datas: {DEPARTURE_DATE} - {RETURN_DATE}")
                print(f"{'='*70}\n")

                # 1. Navegar para página
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Navegando para Google Flights...")
                await page.goto('https://www.google.com/travel/flights', timeout=60000)

                # 2. Esperar e diagnosticar
                await self.wait_and_diagnose(page)

                # 3. Screenshot inicial
                await page.screenshot(path=f"poc/reports/robust_{origin}_initial.png")

                # 4. Tentar preencher campos
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Preenchendo campos...")

                origin_ok = await self.type_and_enter_safe(page, origin, "ORIGEM")
                await asyncio.sleep(1.5)

                dest_ok = await self.type_and_enter_safe(page, DESTINATION, "DESTINO")
                await asyncio.sleep(1.5)

                # 5. Screenshot após campos
                await page.screenshot(path=f"poc/reports/robust_{origin}_after_fields.png")

                # 6. Tentar URL direta como fallback se campos falharam
                if not origin_ok or not dest_ok:
                    print(f"\n  [INFO] Preenchimento de campos falhou, tentando URL direta...")
                    url_ok = await self.use_url_direct(page, origin)

                    if url_ok:
                        # Salvar HTML da URL direta
                        html = await page.content()
                        with open(f"poc/reports/robust_{origin}_url_html.html", "w", encoding="utf-8") as f:
                            f.write(html)

                        # Verificar resultados
                        await self.check_results(page, origin, "url_direta")
                else:
                    # 7. Tentar preencher datas
                    print(f"\n  [INFO] Campos OK, tentando selecionar datas...")
                    # (Implementação simplificada - apenas Enter para datas)
                    try:
                        await page.click('input[placeholder*="Partida"]', timeout=3000)
                        await asyncio.sleep(0.5)
                        for char in DEPARTURE_DATE:
                            await page.keyboard.type(char)
                            await asyncio.sleep(0.05)
                        await page.keyboard.press('Enter')
                        await asyncio.sleep(0.5)

                        await page.click('input[placeholder*="Volta"]', timeout=3000)
                        await asyncio.sleep(0.5)
                        for char in RETURN_DATE:
                            await page.keyboard.type(char)
                            await asyncio.sleep(0.05)
                        await page.keyboard.press('Enter')
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"    [WARN] Falha ao preencher datas: {e}")

                    # 8. Submeter
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Submetendo busca...")
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(30)

                    # 9. Verificar resultados
                    await self.check_results(page, origin, "standard")

            except Exception as e:
                print(f"[ERROR] {e}")
                import traceback
                traceback.print_exc()

            finally:
                print("\nAguardando 10 segundos...")
                await asyncio.sleep(10)
                await context.close()
                await browser.close()

    async def check_results(self, page, origin, method):
        """Verifica e extrai resultados."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Verificando resultados ({method})...")

        # Screenshot
        await page.screenshot(path=f"poc/reports/robust_{origin}_{method}_results.png", full_page=True)

        # Salvar HTML
        html = await page.content()
        with open(f"poc/reports/robust_{origin}_{method}_html.html", "w", encoding="utf-8") as f:
            f.write(html)

        # Verificar indicadores de voo
        indicators = [
            '[data-result-id]',
            '[role="article"]',
            '.gElC9',
        ]

        found = False
        for indicator in indicators:
            try:
                elements = await page.query_selector_all(indicator)
                if elements and len(elements) > 2:
                    print(f"  ✓ {len(elements)} resultados com: {indicator}")
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
            print(f"\n[INFO] Nenhum resultado de voo encontrado")

        return found

async def main():
    print("=" * 70)
    print("GOOGLE FLIGHTS POC - ROBUSTA")
    print("Com diagnóstico e fallbacks")
    print("=" * 70)

    await asyncio.sleep(2)

    poc = GoogleFlightsPOC()
    await poc.run_search("GRU")

    print(f"\nResultados: {len(poc.results)} preços extraídos")

if __name__ == "__main__":
    asyncio.run(main())
