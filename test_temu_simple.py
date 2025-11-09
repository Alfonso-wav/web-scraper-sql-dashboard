"""
Script simple para probar el scraping de Temu
"""
import asyncio
from playwright.async_api import async_playwright

async def test_temu():
    async with async_playwright() as p:
        print("🌐 Abriendo navegador...")
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        url = "https://www.temu.com/search_result.html?search_key=monitor%20gaming"
        print(f"🔍 Navegando a: {url}")
        
        await page.goto(url, timeout=30000)
        print("⏳ Esperando 10 segundos para carga completa...")
        await asyncio.sleep(10)
        
        # Hacer scroll
        for i in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(1)
        
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        
        # Probar múltiples selectores
        selectors = [
            'a[href*="/goods.html?goods_id"]',
            'a[href*="goods"]',
            'div[class*="goods"]',
            'div[data-goods-id]',
            '[class*="GoodsCard"]',
            '[class*="goods-card"]',
            'img[alt]'
        ]
        
        print("\n📊 Probando selectores:")
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                print(f"  {selector}: {len(elements)} elementos")
            except Exception as e:
                print(f"  {selector}: ERROR - {e}")
        
        # Guardar screenshot
        await page.screenshot(path="data/extractions/temu/screenshot.png")
        print("\n📸 Screenshot guardado en: data/extractions/temu/screenshot.png")
        
        # Guardar HTML
        html = await page.content()
        with open("data/extractions/temu/page.html", 'w', encoding='utf-8') as f:
            f.write(html)
        print("📄 HTML guardado en: data/extractions/temu/page.html")
        
        # Esperar antes de cerrar
        print("\n⏸️  El navegador permanecerá abierto 30 segundos para inspección...")
        await asyncio.sleep(30)
        
        await browser.close()
        print("✅ Test completado")

if __name__ == "__main__":
    asyncio.run(test_temu())
