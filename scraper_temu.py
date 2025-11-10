"""
Script para scrapear productos de El Corte Inglés
"""
import json
import asyncio
import sys
from playwright.async_api import async_playwright
import re
from pathlib import Path

DEFAULT_ITERATIONS = 50


async def extract_detailed_product_info(context, product_url: str):
    """
    Extrae información detallada visitando la página del producto en una nueva pestaña.
    
    Args:
        context: Contexto del browser de Playwright
        product_url: URL del producto
    
    Returns:
        dict con información detallada
    """
    details = {
        "brand": "N/A",
        "specifications": [],
        "description": "N/A",
        "features": [],
        "dimensions": "N/A",
        "weight": "N/A",
        "material": "N/A",
        "color_options": []
    }
    
    # Abrir en nueva página para no perder el contexto de la lista
    detail_page = await context.new_page()
    
    try:
        print(f"    🔍 Visitando página de detalle...", flush=True)
        await detail_page.goto(product_url, timeout=20000, wait_until="domcontentloaded")
        
        # Esperar a que cargue el contenido
        await asyncio.sleep(2)
        
        # EXTRAER MARCA
        brand_selectors = [
            '[data-test="product-brand"]',
            '.product-brand',
            '[class*="brand"]',
            'meta[property="product:brand"]'
        ]
        
        for selector in brand_selectors:
            try:
                if selector.startswith('meta'):
                    elem = await detail_page.query_selector(selector)
                    if elem:
                        details["brand"] = await elem.get_attribute("content") or "N/A"
                        break
                else:
                    elem = await detail_page.query_selector(selector)
                    if elem:
                        brand_text = await elem.inner_text()
                        if brand_text and len(brand_text) > 0:
                            details["brand"] = brand_text.strip()
                            break
            except:
                continue
        
        # EXTRAER DESCRIPCIÓN
        desc_selectors = [
            '[data-test="product-description"]',
            '.product-description',
            '[class*="description"]',
            '[id*="description"]'
        ]
        
        for selector in desc_selectors:
            try:
                desc_elem = await detail_page.query_selector(selector)
                if desc_elem:
                    desc_text = await desc_elem.inner_text()
                    if desc_text and len(desc_text) > 20:
                        details["description"] = desc_text.strip()[:500]
                        break
            except:
                continue
        
        # EXTRAER CARACTERÍSTICAS
        feature_elements = await detail_page.query_selector_all('ul li, .feature-item, [class*="feature"]')
        for elem in feature_elements[:15]:
            try:
                feature_text = await elem.inner_text()
                if feature_text and 5 < len(feature_text) < 200:
                    details["features"].append(feature_text.strip())
            except:
                continue
        
        # EXTRAER ESPECIFICACIONES
        spec_rows = await detail_page.query_selector_all('table tr, .spec-row, [class*="specification"]')
        for row in spec_rows[:20]:
            try:
                cells = await row.query_selector_all('td, th, span')
                if len(cells) >= 2:
                    label = await cells[0].inner_text()
                    value = await cells[1].inner_text()
                    if label and value:
                        label_lower = label.lower()
                        
                        if 'peso' in label_lower or 'weight' in label_lower:
                            details["weight"] = value.strip()
                        elif 'dimensi' in label_lower or 'medida' in label_lower:
                            details["dimensions"] = value.strip()
                        elif 'material' in label_lower:
                            details["material"] = value.strip()
                        
                        details["specifications"].append({
                            "label": label.strip(),
                            "value": value.strip()
                        })
            except:
                continue
        
        print(f"    ✅ Información detallada extraída", flush=True)
        
    except Exception as e:
        print(f"    ⚠️ Error extrayendo detalles: {e}", flush=True)
    finally:
        await detail_page.close()
    
    return details


async def scrape_corte_ingles(search_term: str, max_products: int = DEFAULT_ITERATIONS, detailed: bool = False, headless: bool = False):
    """
    Realiza scraping de productos en El Corte Inglés
    
    Args:
        search_term: Término de búsqueda
        max_products: Número máximo de productos a scrapear
        detailed: Si es True, visita cada producto para obtener información detallada
        headless: Si es True, ejecuta el navegador sin ventana visible
    
    Returns:
        list: Lista de productos scrapeados
    """
    products = []
    
    async with async_playwright() as p:
        print("🌐 Iniciando navegador...", flush=True)
        print(f"🖥️  Modo headless: {'Activado (sin ventana)' if headless else 'Desactivado (con ventana)'}", flush=True)
        
        try:
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
        except Exception as e:
            print(f"❌ Error al iniciar navegador en modo {'headless' if headless else 'visible'}: {e}", flush=True)
            print(f"🔄 Intentando con modo {'visible' if headless else 'headless'}...", flush=True)
            browser = await p.chromium.launch(
                headless=not headless,  # Invertir el modo
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
        
        # Configurar contexto
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale='es-ES'
        )
        
        page = await context.new_page()
        
        # Construir URL de búsqueda para El Corte Inglés
        search_url = f"https://www.elcorteingles.es/search/?term={search_term.replace(' ', '+')}"
        
        print(f"🔍 Buscando: {search_term}", flush=True)
        print(f"🎯 Objetivo: {max_products} productos", flush=True)
        print(f"📊 Modo detallado: {'Activado' if detailed else 'Desactivado'}", flush=True)
        
        try:
            print(f"🌐 Navegando a: {search_url}", flush=True)
            
            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as nav_error:
                print(f"⚠️ Error de navegación inicial: {nav_error}", flush=True)
                print("🔄 Reintentando con timeout más largo...", flush=True)
                await page.goto(search_url, timeout=90000, wait_until="networkidle")
            
            # Esperar a que aparezca el buscador
            print("⏳ Esperando que aparezca el buscador...", flush=True)
            await asyncio.sleep(3)
            
            try:
                # Esperar y escribir en el input de búsqueda
                await page.wait_for_selector('input.search-bar__input', timeout=15000)
                print(f"✏️  Escribiendo término de búsqueda: {search_term}", flush=True)
                
                # Limpiar y escribir en el input
                await page.fill('input.search-bar__input', '')
                await page.fill('input.search-bar__input', search_term)
                await asyncio.sleep(1)
                
                # Hacer clic en el botón de búsqueda
                print(f"🔍 Haciendo clic en el botón de búsqueda...", flush=True)
                await page.click('button.search-bar__button')
                
                # Esperar a que carguen los resultados
                print(f"⏳ Esperando resultados de búsqueda...", flush=True)
                await asyncio.sleep(5)
                
                # Hacer scroll para cargar productos lazy-loaded
                print("📜 Cargando productos con scroll...", flush=True)
                for i in range(6):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await asyncio.sleep(1)
                
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                
            except Exception as search_error:
                print(f"❌ Error al usar el buscador: {search_error}", flush=True)
                print("🔄 Intentando continuar de todas formas...", flush=True)
                await asyncio.sleep(3)
            
            # Selectores para productos de El Corte Inglés
            selectors_to_try = [
                'article.product_tile',
                '.product-item',
                '[data-test="product-tile"]',
                'article[class*="product"]',
                'div.product-grid-item',
                'a[href*="/p/"]'  # URLs de producto
            ]
            
            product_elements = []
            selector_used = None
            
            for selector in selectors_to_try:
                try:
                    product_elements = await page.query_selector_all(selector)
                    if len(product_elements) > 0:
                        selector_used = selector
                        print(f"✅ Encontrados {len(product_elements)} productos con selector: {selector}", flush=True)
                        break
                except:
                    continue
            
            if len(product_elements) == 0:
                print("❌ No se encontraron productos.", flush=True)
                # Guardar HTML para debug
                html_content = await page.content()
                debug_path = Path("data/extractions/corte_ingles/debug_page.html")
                debug_path.parent.mkdir(parents=True, exist_ok=True)
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"📄 HTML guardado en: {debug_path}", flush=True)
            
            products_data = []
            
            for idx, element in enumerate(product_elements):
                if len(products_data) >= max_products:
                    break
                
                try:
                    # TÍTULO
                    title_selectors = [
                        'h3',
                        'h2',
                        '.product-title',
                        '[data-test="product-title"]',
                        'a[class*="title"]',
                        '.product-name'
                    ]
                    
                    title = "N/A"
                    for selector in title_selectors:
                        try:
                            title_elem = await element.query_selector(selector)
                            if title_elem:
                                title_text = await title_elem.inner_text()
                                if title_text and len(title_text) > 3:
                                    title = title_text.strip()
                                    break
                        except:
                            continue
                    
                    if title == "N/A":
                        continue
                    
                    # PRECIO
                    price_selectors = [
                        '.price',
                        '[data-test="product-price"]',
                        '[class*="price"]',
                        'span[class*="amount"]',
                        '.product-price'
                    ]
                    
                    price = "N/A"
                    for selector in price_selectors:
                        try:
                            price_elem = await element.query_selector(selector)
                            if price_elem:
                                price_text = await price_elem.inner_text()
                                if price_text:
                                    price = price_text.strip()
                                    break
                        except:
                            continue
                    
                    # RATING
                    rating_selectors = [
                        '[class*="rating"]',
                        '[data-test="product-rating"]',
                        '.stars',
                        '[class*="star"]'
                    ]
                    
                    rating = "N/A"
                    for selector in rating_selectors:
                        try:
                            rating_elem = await element.query_selector(selector)
                            if rating_elem:
                                # Intentar obtener de atributo aria-label o similar
                                rating_text = await rating_elem.get_attribute('aria-label')
                                if not rating_text:
                                    rating_text = await rating_elem.inner_text()
                                if rating_text:
                                    rating = rating_text.strip()
                                    break
                        except:
                            continue
                    
                    # NÚMERO DE RESEÑAS
                    reviews_selectors = [
                        '[class*="review"]',
                        '[data-test="reviews-count"]',
                        '.reviews-count',
                        '[class*="opinion"]'
                    ]
                    
                    reviews_count = "0"
                    for selector in reviews_selectors:
                        try:
                            reviews_elem = await element.query_selector(selector)
                            if reviews_elem:
                                reviews_text = await reviews_elem.inner_text()
                                if reviews_text:
                                    reviews_count = reviews_text.strip()
                                    break
                        except:
                            continue
                    
                    # URL DEL PRODUCTO
                    product_url = "N/A"
                    
                    # Intentar diferentes selectores para el link
                    link_selectors = [
                        'a[href*="/p/"]',
                        'a.product-link',
                        'a[class*="product"]',
                        'a[href]'
                    ]
                    
                    link_elem = None
                    for selector in link_selectors:
                        try:
                            link_elem = await element.query_selector(selector)
                            if link_elem:
                                href = await link_elem.get_attribute("href")
                                # Filtrar enlaces válidos (no javascript:void, no #)
                                if href and not href.startswith('javascript:') and not href.startswith('#'):
                                    product_url = href
                                    break
                        except:
                            continue
                    
                    if product_url != "N/A" and not product_url.startswith("http"):
                        product_url = f"https://www.elcorteingles.es{product_url}"
                    
                    # IMAGEN
                    image_elem = await element.query_selector('img')
                    image_url = "N/A"
                    if image_elem:
                        # Intentar src, data-src, srcset
                        image_url = await image_elem.get_attribute("src")
                        if not image_url or 'placeholder' in image_url:
                            image_url = await image_elem.get_attribute("data-src")
                        if not image_url:
                            srcset = await image_elem.get_attribute("srcset")
                            if srcset:
                                # Tomar la primera URL del srcset
                                image_url = srcset.split(',')[0].split(' ')[0]
                    
                    if image_url and not image_url.startswith("http"):
                        if image_url.startswith("//"):
                            image_url = f"https:{image_url}"
                        elif image_url.startswith("/"):
                            image_url = f"https://www.elcorteingles.es{image_url}"
                    
                    # ID DEL PRODUCTO (extraer de URL)
                    product_id = "N/A"
                    if product_url != "N/A":
                        id_match = re.search(r'/p/([^/]+)', product_url)
                        if id_match:
                            product_id = id_match.group(1)
                    
                    # MARCA (intentar extraer del título o de un elemento específico)
                    brand = "N/A"
                    brand_elem = await element.query_selector('[class*="brand"], [data-test="brand"]')
                    if brand_elem:
                        brand = await brand_elem.inner_text()
                    
                    product_data = {
                        "platform": "corte_ingles",
                        "product_id": product_id,
                        "title": title,
                        "brand": brand.strip() if brand != "N/A" else "N/A",
                        "price": price,
                        "rating": rating,
                        "reviews_count": reviews_count,
                        "url": product_url,
                        "image_url": image_url,
                        "search_term": search_term,
                        "position": len(products_data) + 1
                    }
                    
                    products_data.append(product_data)
                    print(f"  ✅ Producto {len(products_data)}: {title[:50]}...", flush=True)
                    
                except Exception as e:
                    print(f"  ⚠️ Error en producto {idx + 1}: {e}", flush=True)
                    continue
            
            print(f"📦 Productos extraídos: {len(products_data)}", flush=True)
            
            # Si modo detallado, visitar cada producto
            if detailed and len(products_data) > 0:
                print(f"🔍 Extrayendo información detallada de {len(products_data)} productos...", flush=True)
                for idx, product_data in enumerate(products_data, 1):
                    if product_data.get("url") and product_data["url"] != "N/A":
                        print(f"🌐 [{idx}/{len(products_data)}] Visitando: {product_data['title'][:40]}...", flush=True)
                        detailed_info = await extract_detailed_product_info(context, product_data["url"])
                        
                        # Actualizar marca si se encontró
                        if detailed_info.get("brand") and detailed_info["brand"] != "N/A":
                            product_data["brand"] = detailed_info["brand"]
                        
                        product_data.update(detailed_info)
                        print(f"✔️  [{idx}/{len(products_data)}] Completado", flush=True)
            
            # Añadir todos los productos
            print(f"💾 Agregando {len(products_data)} productos al resultado...", flush=True)
            products.extend(products_data)
            print(f"📊 Total acumulado: {len(products)}/{max_products} productos", flush=True)
            
        except Exception as e:
            print(f"❌ Error durante el scraping: {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()
    
    return products


def save_to_json(products, search_term):
    """Guarda los productos en un archivo JSON"""
    clean_term = search_term.replace(" ", "_").replace("/", "_")
    filename = f"data/extractions/corte_ingles/corte_ingles_{clean_term}.json"
    
    # Crear directorio si no existe
    import os
    os.makedirs("data/extractions/corte_ingles", exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Guardado en: {filename}")
    print(f"📊 Total de productos: {len(products)}")
    
    return filename


async def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("❌ Error: Debes proporcionar un término de búsqueda")
        print("📝 Uso: python scraper_temu.py <término_búsqueda> [max_productos] [--detailed] [--headless]")
        print("📝 Ejemplo: python scraper_temu.py 'cafe' 30 --detailed --headless")
        sys.exit(1)
    
    search_term = sys.argv[1]
    max_products = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else DEFAULT_ITERATIONS
    detailed = "--detailed" in sys.argv
    headless_mode = "--headless" in sys.argv
    
    print("=" * 80)
    print("🛒 EL CORTE INGLÉS SCRAPER")
    print("=" * 80)
    print(f"🖥️  Modo: {'Headless (sin ventana)' if headless_mode else 'Con ventana visible'}")
    
    products = await scrape_corte_ingles(search_term, max_products, detailed, headless_mode)
    
    if products:
        save_to_json(products, search_term)
        print("\n✅ Scraping completado exitosamente!")
    else:
        print("\n⚠️ No se encontraron productos")


if __name__ == "__main__":
    asyncio.run(main())
