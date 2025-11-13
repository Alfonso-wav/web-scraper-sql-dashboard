import json
import asyncio
import sys
from playwright.async_api import async_playwright

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
        "product_overview": {},
        "nutrition_facts": {},
        "ingredients": "N/A",
        "description": "N/A",
        "features": [],
        "dimensions": "N/A",
        "weight": "N/A"
    }
    
    # Abrir en nueva página para no perder el contexto de la lista
    detail_page = await context.new_page()
    
    try:
        await detail_page.goto(product_url, timeout=15000, wait_until="domcontentloaded")
        
        # EXTRAER PRODUCT OVERVIEW (aquí está la marca y características principales)
        overview_rows = await detail_page.query_selector_all("#productOverview_feature_div table tr, #poExpander table tr")
        for row in overview_rows:
            try:
                # Buscar label y valor
                label_elem = await row.query_selector("td.a-span3, th")
                value_elem = await row.query_selector("td.a-span9, td:not(.a-span3)")
                
                if label_elem and value_elem:
                    label = await label_elem.inner_text()
                    value = await value_elem.inner_text()
                    
                    if label and value:
                        label_clean = label.strip()
                        value_clean = value.strip()
                        
                        # Si es la marca
                        if "brand" in label_clean.lower() or "marca" in label_clean.lower():
                            details["brand"] = value_clean
                        
                        # Guardar en product_overview
                        details["product_overview"][label_clean] = value_clean
            except:
                continue
        
        # Características/Especificaciones técnicas (tabla más detallada)
        # Selectores CSS que cubren diferentes formatos de tablas de Amazon
        spec_selectors = [
            "table.a-keyvalue tr",
            "#productDetails_techSpec_section_1 tr",
            "#productDetails_detailBullets_sections1 tr",
            "#productDetails_db_sections tr",  # Tabla de detalles alternativa
            "table.prodDetTable tr",  # Tabla de detalles de producto
            "div.a-section.table-padding table tbody tr"  # Tabla genérica en sección
        ]
        
        spec_rows = []
        for selector in spec_selectors:
            rows = await detail_page.query_selector_all(selector)
            if rows:
                spec_rows.extend(rows)
                if len(spec_rows) > 15:  # Si ya tenemos suficientes, no seguir buscando
                    break
        
        for row in spec_rows[:15]:  # Limitar a 15 especificaciones
            try:
                # Intentar extraer usando td[1] y td[2] (key-value en celdas separadas)
                label_elem = await row.query_selector("td:nth-child(1), th")
                value_elem = await row.query_selector("td:nth-child(2)")
                
                # Si no funciona, intentar con clases específicas de Amazon
                if not label_elem or not value_elem:
                    label_elem = await row.query_selector("th, td.a-span3")
                    value_elem = await row.query_selector("td:not(.a-span3)")
                
                if label_elem and value_elem:
                    label = await label_elem.inner_text()
                    value = await value_elem.inner_text()
                    if label and value:
                        label_clean = label.strip()
                        value_clean = value.strip()
                        
                        # Evitar duplicados
                        if not any(spec["label"] == label_clean for spec in details["specifications"]):
                            details["specifications"].append({
                                "label": label_clean,
                                "value": value_clean
                            })
                            
                            # Extraer marca si aparece aquí
                            if "marca" in label_clean.lower() or "brand" in label_clean.lower():
                                if details["brand"] == "N/A":
                                    details["brand"] = value_clean
                            
                            # Buscar dimensiones y peso específicamente
                            if "dimensiones" in label_clean.lower() or "dimensions" in label_clean.lower():
                                details["dimensions"] = value_clean
                            if "peso" in label_clean.lower() or "weight" in label_clean.lower():
                                details["weight"] = value_clean
            except:
                continue
        
        # Descripción del producto
        desc_selectors = [
            "#feature-bullets ul li span.a-list-item",
            "#productDescription p",
            ".a-unordered-list.a-vertical li span"
        ]
        for selector in desc_selectors:
            desc_elems = await detail_page.query_selector_all(selector)
            if desc_elems:
                for elem in desc_elems[:10]:  # Primeros 10 puntos
                    try:
                        text = await elem.inner_text()
                        if text and text.strip() and len(text.strip()) > 10:
                            details["features"].append(text.strip())
                    except:
                        continue
                if details["features"]:
                    break
        
        # Descripción completa
        desc_elem = await detail_page.query_selector("#productDescription p")
        if desc_elem:
            details["description"] = await desc_elem.inner_text()
        
        # EXTRAER INFORMACIÓN NUTRICIONAL (para productos alimenticios)
        try:
            # Intentar expandir la sección de información nutricional si existe
            nutrition_expander = await detail_page.query_selector("#nutritionalInfoAndIngredients_feature_div .a-expander-header, a.a-expander-header")
            if nutrition_expander:
                # Verificar si ya está expandida
                is_expanded = await detail_page.query_selector(".a-expander-content-expanded")
                if not is_expanded:
                    await nutrition_expander.click()
                    await detail_page.wait_for_timeout(1000)  # Esperar a que se expanda
                
                # PASO 1: Extraer Energía (está en una fila especial)
                energy_row = await detail_page.query_selector("#nic-eu-nutrition-facts-energy")
                if energy_row:
                    try:
                        energy_label_elem = await energy_row.query_selector("td:nth-child(1) span")
                        energy_value_elem = await energy_row.query_selector("td:nth-child(2) span")
                        if energy_label_elem and energy_value_elem:
                            energy_label = await energy_label_elem.inner_text()
                            energy_value = await energy_value_elem.inner_text()
                            if energy_label and energy_value:
                                details["nutrition_facts"][energy_label.strip()] = energy_value.strip()
                    except:
                        pass
                
                # PASO 2: Extraer el resto de nutrientes (están en tabla anidada)
                nutrition_rows = await detail_page.query_selector_all("#nic-eu-nutrition-facts-nutrients tbody tr")
                for row in nutrition_rows:
                    try:
                        # Buscar todos los spans en la primera celda (nombre del nutriente)
                        # El segundo span suele tener el nombre del nutriente
                        label_spans = await row.query_selector_all("td:nth-child(1) span")
                        # El valor está en la segunda celda
                        value_elem = await row.query_selector("td:nth-child(2) span")
                        
                        if label_spans and value_elem:
                            # Tomar el último span que suele tener el nombre real del nutriente
                            label_elem = label_spans[-1] if len(label_spans) > 0 else None
                            
                            if label_elem:
                                label = await label_elem.inner_text()
                                value = await value_elem.inner_text()
                                
                                if label and value and label.strip() and value.strip():
                                    label_clean = label.strip()
                                    value_clean = value.strip()
                                    
                                    # Filtrar textos vacíos o que sean solo guiones
                                    if label_clean and value_clean and label_clean not in ["—", "-", ""]:
                                        details["nutrition_facts"][label_clean] = value_clean
                    except:
                        continue
                
                # Extraer ingredientes si están disponibles
                ingredients_elem = await detail_page.query_selector("#ingredients_feature_div .a-section, #important-information .content")
                if ingredients_elem:
                    ingredients_text = await ingredients_elem.inner_text()
                    if ingredients_text and ingredients_text.strip():
                        details["ingredients"] = ingredients_text.strip()
        except Exception as e:
            # Si no hay información nutricional, simplemente continuar
            pass
        
    except Exception as e:
        print(f"    ⚠️ Error extrayendo detalles: {e}")
    finally:
        # Cerrar la página de detalles
        await detail_page.close()
    
    return details


async def extract_product_basic_info(element, search_term: str, position: int, debug: bool = False):
    """
    Extrae información básica de un elemento de producto en la lista de resultados.
    Esta función se puede ejecutar en paralelo.
    """
    try:
        # ASIN (ID del producto)
        asin = await element.get_attribute("data-asin")
        
        if debug and position == 1:
            # Imprimir el HTML del primer elemento para debug
            html = await element.inner_html()
            print(f"\n🔍 DEBUG - HTML del primer producto:\n{html[:500]}...\n")
        
        # Título - intentar múltiples selectores
        title = "N/A"
        title_selectors = [
            "h2 a span",
            "h2 span",
            ".a-size-medium.a-color-base.a-text-normal",
            ".a-size-base-plus.a-color-base.a-text-normal",
            "h2.a-size-mini a span"
        ]
        for selector in title_selectors:
            title_elem = await element.query_selector(selector)
            if title_elem:
                title = await title_elem.inner_text()
                if title and title.strip():
                    break
        
        # URL del producto
        product_url = "N/A"
        link_elem = await element.query_selector("h2 a")
        if not link_elem:
            link_elem = await element.query_selector("a.a-link-normal")
        if link_elem:
            product_url = await link_elem.get_attribute("href")
            if product_url and not product_url.startswith("http"):
                product_url = f"https://www.amazon.es{product_url}"
        
        # Precio - capturar precio completo (euros + céntimos)
        price = "N/A"
        price_elem = await element.query_selector(".a-price .a-offscreen")
        if price_elem:
            price = await price_elem.inner_text()
            price = price.strip()
        else:
            # Si no está, construir desde whole + fraction
            price_whole = ""
            price_fraction = ""
            
            whole_elem = await element.query_selector(".a-price-whole")
            if whole_elem:
                price_whole = await whole_elem.inner_text()
                price_whole = price_whole.replace("\n", "").replace(",", ".").strip()
            
            fraction_elem = await element.query_selector(".a-price-fraction")
            if fraction_elem:
                price_fraction = await fraction_elem.inner_text()
                price_fraction = price_fraction.strip()
            
            if price_whole:
                price_whole = price_whole.rstrip(".,")
                if price_fraction:
                    price = f"{price_whole},{price_fraction}€"
                else:
                    price = f"{price_whole}€"
        
        # Rating
        rating = "N/A"
        rating_elem = await element.query_selector(".a-icon-alt")
        if rating_elem:
            rating = await rating_elem.inner_text()
        
        # Número de reseñas
        reviews_count = "0"
        reviews_selectors = [
            "span.a-size-base.s-underline-text",
            "span[aria-label*='valoraciones']",
            ".a-size-base"
        ]
        for selector in reviews_selectors:
            reviews_elem = await element.query_selector(selector)
            if reviews_elem:
                reviews_text = await reviews_elem.inner_text()
                if reviews_text and any(char.isdigit() for char in reviews_text):
                    reviews_count = reviews_text
                    break
        
        # Imagen
        image_url = "N/A"
        img_elem = await element.query_selector("img.s-image")
        if img_elem:
            image_url = await img_elem.get_attribute("src")
        
        # Marca
        brand = "N/A"
        additional_specs = {}
        
        details_container = await element.query_selector("div.a-section.a-spacing-small")
        if details_container:
            detail_rows = await details_container.query_selector_all("div.a-row")
            for row in detail_rows:
                row_text = await row.inner_text()
                if row_text and ":" in row_text:
                    parts = row_text.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if "brand" in key.lower() or "marca" in key.lower():
                            brand = value
                        else:
                            additional_specs[key] = value
        
        if brand == "N/A":
            brand_selectors = [
                "h5 span.a-size-base.a-color-base",
                "span.a-size-base-plus.a-color-base",
                "div.a-row.a-size-base.a-color-secondary span.a-size-base.a-color-base",
                ".s-line-clamp-1 .a-size-base-plus",
                "span.a-color-base.puis-normal-weight-text"
            ]
            for selector in brand_selectors:
                brand_elem = await element.query_selector(selector)
                if brand_elem:
                    brand_text = await brand_elem.inner_text()
                    if brand_text and brand_text.strip():
                        brand_clean = brand_text.strip()
                        if (len(brand_clean) < 50 and 
                            not brand_clean.replace(".", "").replace(",", "").isdigit() and
                            "€" not in brand_clean and
                            "valoraciones" not in brand_clean.lower()):
                            brand = brand_clean
                            break
        
        # Prime
        has_prime = False
        prime_elem = await element.query_selector("i.a-icon-prime, span[aria-label='Amazon Prime']")
        if prime_elem:
            has_prime = True
        
        # Envío gratis
        free_shipping = False
        shipping_elem = await element.query_selector("span[aria-label*='envío'], span:has-text('Envío GRATIS')")
        if shipping_elem:
            free_shipping = True
        
        # Disponibilidad
        availability = "N/A"
        availability_elem = await element.query_selector(".a-size-base.a-color-price, .a-size-base.a-color-success")
        if availability_elem:
            availability = await availability_elem.inner_text()
        
        # Descuento/Cupón
        discount = "N/A"
        discount_elem = await element.query_selector(".s-coupon-unclipped, .savingPriceOverride")
        if discount_elem:
            discount = await discount_elem.inner_text()
        
        # Precio anterior (tachado)
        original_price = "N/A"
        original_price_elem = await element.query_selector(".a-price.a-text-price .a-offscreen")
        if original_price_elem:
            original_price = await original_price_elem.inner_text()
        
        # Vendedor/Seller
        seller = "N/A"
        seller_elem = await element.query_selector(".a-size-base.a-color-secondary")
        if seller_elem:
            seller_text = await seller_elem.inner_text()
            if seller_text and "de " in seller_text.lower():
                seller = seller_text
        
        # Opciones de color/tamaño disponibles
        options = []
        options_elems = await element.query_selector_all(".a-button-text")
        for opt_elem in options_elems[:5]:
            opt_text = await opt_elem.inner_text()
            if opt_text and opt_text.strip():
                options.append(opt_text.strip())
        
        product_data = {
            "asin": asin or "N/A",
            "title": title.strip() if title else "N/A",
            "brand": brand.strip() if brand else "N/A",
            "price": price.strip() if price else "N/A",
            "original_price": original_price.strip() if original_price else "N/A",
            "discount": discount.strip() if discount else "N/A",
            "rating": rating.strip() if rating else "N/A",
            "reviews_count": reviews_count.strip() if reviews_count else "0",
            "has_prime": has_prime,
            "free_shipping": free_shipping,
            "availability": availability.strip() if availability else "N/A",
            "seller": seller.strip() if seller else "N/A",
            "options": options,
            "additional_specs": additional_specs,
            "url": product_url,
            "image_url": image_url,
            "search_term": search_term,
            "position": position
        }
        
        return product_data if title != "N/A" else None
    except Exception as e:
        print(f"⚠️  Error extrayendo producto {position}: {e}", flush=True)
        return None


async def scrape_amazon_products(search_term: str, max_products: int = 50, debug: bool = False, detailed: bool = False, headless: bool = False):
    """
    Scraper de productos de Amazon con extracción paralela y asíncrona.
    
    Args:
        search_term: Término de búsqueda
        max_products: Número máximo de productos a extraer (default: 50)
        debug: Si es True, imprime información de depuración
        detailed: Si es True, visita cada producto para obtener más información (procesamiento paralelo)
        headless: Si es True, ejecuta el navegador sin ventana visible
    """
    products = []
    
    print(f"🚀 Iniciando scraping para: {search_term}", flush=True)
    print(f"📦 Objetivo: {max_products} productos", flush=True)
    print(f"🖥️  Modo headless: {'Activado (sin ventana)' if headless else 'Desactivado (con ventana)'}", flush=True)
    print(f"⚡ Modo paralelo: {'Activado' if detailed else 'Desactivado (solo info básica)'}", flush=True)
    
    async with async_playwright() as p:
        print("🌐 Abriendo navegador...", flush=True)
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # Navegar a Amazon
        search_url = f"https://www.amazon.es/s?k={search_term.replace(' ', '+')}"
        print(f"🔍 Navegando a Amazon.es...", flush=True)
        await page.goto(search_url, wait_until="domcontentloaded")
        print(f"✅ Página cargada, extrayendo productos...", flush=True)
        await page.wait_for_timeout(2000)
        
        page_num = 1
        all_product_elements = []
        
        # FASE 1: Recopilar todos los elementos de productos de todas las páginas
        print(f"\n📋 FASE 1: Recopilando URLs de productos...", flush=True)
        while len(all_product_elements) < max_products:
            print(f"📄 Página {page_num}...", flush=True)
            
            # Esperar a que los productos se carguen
            await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)
            
            # Extraer elementos de productos
            product_elements = await page.query_selector_all('[data-component-type="s-search-result"]')
            print(f"   Encontrados {len(product_elements)} productos", flush=True)
            
            # Añadir a la lista general
            for element in product_elements:
                if len(all_product_elements) >= max_products:
                    break
                all_product_elements.append(element)
            
            print(f"   Total acumulado: {len(all_product_elements)}/{max_products}", flush=True)
            
            # Verificar si necesitamos más productos y hay siguiente página
            if len(all_product_elements) < max_products:
                next_button = await page.query_selector("a.s-pagination-next")
                if next_button:
                    is_disabled = await next_button.get_attribute("aria-disabled")
                    if is_disabled != "true":
                        print(f"   ➡️  Navegando a página {page_num + 1}...", flush=True)
                        await next_button.click()
                        await page.wait_for_timeout(2000)
                        page_num += 1
                    else:
                        print("   📍 No hay más páginas disponibles", flush=True)
                        break
                else:
                    print("   📍 No se encontró botón de siguiente página", flush=True)
                    break
            else:
                break
        
        print(f"\n✅ FASE 1 completada: {len(all_product_elements)} productos encontrados", flush=True)
        
        # FASE 2: Extraer información básica en paralelo (batch processing)
        print(f"\n⚡ FASE 2: Extrayendo información básica en paralelo...", flush=True)
        
        # Procesar en lotes para no sobrecargar
        batch_size = 10
        products_data = []
        
        for i in range(0, len(all_product_elements), batch_size):
            batch = all_product_elements[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_product_elements) + batch_size - 1) // batch_size
            
            print(f"   Lote {batch_num}/{total_batches} ({len(batch)} productos)...", flush=True)
            
            # Crear tareas para procesar este lote en paralelo
            tasks = [
                extract_product_basic_info(element, search_term, i + idx + 1, debug)
                for idx, element in enumerate(batch)
            ]
            
            # Ejecutar todas las tareas del lote en paralelo
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtrar resultados válidos
            for result in batch_results:
                if result and not isinstance(result, Exception):
                    products_data.append(result)
            
            print(f"   ✓ Lote {batch_num} completado ({len([r for r in batch_results if r and not isinstance(r, Exception)])} válidos)", flush=True)
        
        products.extend(products_data)
        print(f"\n✅ FASE 2 completada: {len(products)} productos con información básica", flush=True)
        
        # FASE 3: Si modo detallado, extraer información adicional en paralelo
        if detailed and products:
            print(f"\n🔍 FASE 3: Extrayendo información detallada en paralelo...", flush=True)
            print(f"   Procesando {len(products)} productos con {len(products)//5 + 1} conexiones simultáneas", flush=True)
            
            # Crear tareas para extraer información detallada en paralelo
            # Limitar concurrencia a 5 para no sobrecargar
            semaphore = asyncio.Semaphore(5)
            
            async def extract_with_limit(product_data, idx):
                async with semaphore:
                    if product_data.get("url") and product_data["url"] != "N/A":
                        print(f"   [{idx+1}/{len(products)}] {product_data['title'][:40]}...", flush=True)
                        detailed_info = await extract_detailed_product_info(context, product_data["url"])
                        
                        # Actualizar marca si se encontró en la página de detalle
                        if detailed_info.get("brand") and detailed_info["brand"] != "N/A":
                            product_data["brand"] = detailed_info["brand"]
                        
                        # Añadir el resto de información detallada
                        product_data.update(detailed_info)
                        return True
                    return False
            
            # Ejecutar todas las extracciones detalladas en paralelo (con límite de 5 simultáneas)
            detail_tasks = [extract_with_limit(product, idx) for idx, product in enumerate(products)]
            detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
            
            completed = sum(1 for r in detail_results if r and not isinstance(r, Exception))
            print(f"\n✅ FASE 3 completada: {completed}/{len(products)} productos con información detallada", flush=True)
        
        await browser.close()
    
    return products[:max_products]


def save_to_json(data: list, filename: str = "amazon_products.json"):
    """
    Guarda los datos en un archivo JSON, evitando duplicados.
    Si el archivo existe, solo añade productos nuevos (por ASIN).
    """
    from pathlib import Path
    
    filepath = Path(filename)
    existing_data = []
    existing_asins = set()
    
    # Leer datos existentes si el archivo existe
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_asins = {item.get('asin') for item in existing_data if item.get('asin')}
            print(f"📂 Archivo existente encontrado con {len(existing_data)} productos", flush=True)
        except Exception as e:
            print(f"⚠️  Error leyendo archivo existente: {e}", flush=True)
    
    # Filtrar productos nuevos (por ASIN)
    new_products = []
    duplicates = 0
    
    for product in data:
        asin = product.get('asin')
        if asin and asin != 'N/A' and asin not in existing_asins:
            new_products.append(product)
            existing_asins.add(asin)
        else:
            duplicates += 1
    
    # Combinar datos existentes + nuevos
    combined_data = existing_data + new_products
    
    # Guardar
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    
    # Reportar resultados
    if new_products:
        print(f"✅ {len(new_products)} productos nuevos añadidos", flush=True)
    if duplicates > 0:
        print(f"⏭️  {duplicates} productos duplicados omitidos", flush=True)
    
    print(f"💾 Total en archivo: {len(combined_data)} productos", flush=True)
    print(f"📄 Guardado en: {filename}", flush=True)


async def main():
    """Función principal"""
    print("🛒 Amazon Product Scraper")
    print("=" * 50)
    
    # Verificar si se pasa el término como argumento
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        # Segundo argumento opcional: número de productos
        iterations = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_ITERATIONS
        detailed = True  # Modo detallado por defecto desde API
        debug = False
        headless_mode = "--headless" in sys.argv
        print(f"🖥️  Modo: {'Headless (sin ventana)' if headless_mode else 'Con ventana visible'}")
    else:
        # Solicitar término de búsqueda al usuario
        search_term = input("\n📝 Introduce el término de búsqueda: ").strip()
        
        if not search_term:
            print("❌ Debes introducir un término de búsqueda")
            return
        
        # Preguntar número de productos
        iterations_input = input(f"🔢 ¿Cuántos productos quieres scrapear? (default: {DEFAULT_ITERATIONS}): ").strip()
        iterations = int(iterations_input) if iterations_input.isdigit() else DEFAULT_ITERATIONS
        
        # Preguntar si quiere modo detallado
        detailed_input = input("📊 ¿Extraer información DETALLADA de cada producto? (más lento) (s/n): ").strip().lower()
        detailed = detailed_input in ['s', 'si', 'sí', 'y', 'yes']
        
        # Preguntar si quiere modo debug
        debug_input = input("🐛 ¿Activar modo debug? (s/n): ").strip().lower()
        debug = debug_input in ['s', 'si', 'sí', 'y', 'yes']
        
        headless_mode = False  # Por defecto con ventana en modo interactivo
    
    if detailed:
        print("\n⏱️  AVISO: El modo detallado visita cada producto individualmente.")
        print(f"   Esto puede tardar varios minutos para {iterations} productos.\n")
    
    # Scraping
    products = await scrape_amazon_products(search_term, max_products=iterations, debug=debug, detailed=detailed, headless=headless_mode)
    
    # Guardar resultados
    filename = f"data/extractions/amazon/amazon_{search_term.replace(' ', '_')}.json"
    save_to_json(products, filename)
    
    print(f"\n✨ Scraping completado!")
    print(f"📊 Total de productos extraídos: {len(products)}")
    
    return filename


if __name__ == "__main__":
    asyncio.run(main())
