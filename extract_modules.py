#!/usr/bin/env python3
"""
Script para extraer módulos de sql_query.html a archivos individuales
"""
import re
from pathlib import Path

def extract_modules():
    """Extrae todos los módulos draggable-module a archivos separados"""
    
    # Leer el archivo principal
    html_file = Path('templates/sql_query.html')
    content = html_file.read_text(encoding='utf-8')
    
    # Patrón para encontrar módulos completos
    # Busca desde <div class="draggable-module" hasta su cierre incluyendo los resize-handles
    pattern = r'(<div class="draggable-module"[^>]*data-module-id="([^"]+)"[^>]*>.*?<!-- Resize handles -->.*?</div>\s*</div>)'
    
    modules = []
    for match in re.finditer(pattern, content, re.DOTALL):
        module_html = match.group(1)
        module_id = match.group(2)
        
        # Limpiar y formatear
        module_html = module_html.strip()
        
        # Agregar comentario al inicio
        module_name = re.search(r'data-module-name="([^"]+)"', module_html)
        module_name = module_name.group(1) if module_name else module_id
        
        final_html = f'<!-- Módulo: {module_name} -->\n{module_html}\n'
        
        modules.append({
            'id': module_id,
            'name': module_name,
            'html': final_html
        })
        
        print(f"✓ Extraído módulo: {module_id} ({module_name})")
    
    return modules

def save_modules(modules):
    """Guarda cada módulo en su propio archivo"""
    modules_dir = Path('templates/modules')
    modules_dir.mkdir(exist_ok=True)
    
    for module in modules:
        filename = modules_dir / f"{module['id']}.html"
        filename.write_text(module['html'], encoding='utf-8')
        print(f"💾 Guardado: {filename}")

if __name__ == '__main__':
    print("🔄 Extrayendo módulos de sql_query.html...")
    modules = extract_modules()
    print(f"\n📦 Total de módulos encontrados: {len(modules)}")
    
    print("\n💾 Guardando módulos en archivos individuales...")
    save_modules(modules)
    
    print("\n✅ Proceso completado!")
    print(f"📁 Módulos guardados en: templates/modules/")
