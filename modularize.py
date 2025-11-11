#!/usr/bin/env python3
"""
Script para modularizar sql_query.html de forma precisa
"""
from pathlib import Path

def modularize_html():
    """Reemplaza la sección de módulos con includes de Jinja2"""
    
    html_file = Path('templates/sql_query.html')
    backup_file = Path('templates/sql_query.html.backup_modular')
    
    # Leer archivo original
    lines = html_file.read_text(encoding='utf-8').splitlines(keepends=True)
    
    print(f"📄 Total de líneas: {len(lines)}")
    print(f"📍 Línea 528 (antes de módulos): {lines[527][:60]}...")
    print(f"📍 Línea 1324 (fin módulos): {lines[1323][:60]}...")
    
    # Crear nuevo contenido
    # Parte 1: Desde el inicio hasta línea 528 (antes del comentario "Módulo 0")
    part1 = lines[:528]
    
    # Parte 2: Include de Jinja2 (reemplaza líneas 529-1324)
    jinja_includes = [
        "            <!-- Módulos cargados dinámicamente -->\n",
        "            {% for module_id in modules %}\n",
        "                {% include 'modules/' + module_id + '.html' %}\n",
        "            {% endfor %}\n",
        "\n"
    ]
    
    # Parte 3: Resto del archivo (desde línea 1325 en adelante)
    part3 = lines[1324:]
    
    # Combinar
    new_content = part1 + jinja_includes + part3
    
    # Guardar
    html_file.write_text(''.join(new_content), encoding='utf-8')
    
    print(f"\n✅ Archivo modularizado:")
    print(f"   - {len(part1)} líneas antes de módulos")
    print(f"   - {len(jinja_includes)} líneas de includes Jinja2")
    print(f"   - {len(part3)} líneas después de módulos")
    print(f"   - Total: {len(new_content)} líneas (antes: {len(lines)})")
    print(f"   - Reducción: {len(lines) - len(new_content)} líneas")

if __name__ == '__main__':
    print("🔄 Modularizando sql_query.html...")
    modularize_html()
    print("\n✅ Completado!")
