#!/usr/bin/env python3
"""
Script para reemplazar módulos en sql_query.html con includes de Jinja2
"""
import re
from pathlib import Path

def replace_modules_with_includes():
    """Reemplaza todos los módulos con includes de Jinja2"""
    
    html_file = Path('templates/sql_query.html')
    content = html_file.read_text(encoding='utf-8')
    
    # Patrón para encontrar todos los módulos
    pattern = r'            <!-- Módulo \d+:.*?-->\s*<div class="draggable-module".*?</div>\s*</div>'
    
    # Contar módulos a reemplazar
    modules_found = len(re.findall(pattern, content, re.DOTALL))
    print(f"📊 Módulos encontrados: {modules_found}")
    
    # Reemplazar con el loop de Jinja2
    jinja_loop = '''            <!-- Módulos cargados dinámicamente -->
            {% for module_id in modules %}
                {% include 'modules/' + module_id + '.html' %}
            {% endfor %}'''
    
    # Hacer el reemplazo
    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Insertar el loop de Jinja2 después de "<!-- Contenedor interno para módulos"
    insertion_point = r'(<!-- Contenedor interno para módulos.*?>\s*)'
    new_content = re.sub(
        insertion_point,
        r'\1\n' + jinja_loop + '\n',
        new_content,
        count=1,
        flags=re.DOTALL
    )
    
    return new_content, modules_found

def backup_original():
    """Crea backup del archivo original"""
    html_file = Path('templates/sql_query.html')
    backup_file = Path('templates/sql_query.html.backup_modular')
    
    if not backup_file.exists():
        backup_file.write_text(html_file.read_text(encoding='utf-8'), encoding='utf-8')
        print(f"💾 Backup creado: {backup_file}")
    else:
        print(f"ℹ️  Backup ya existe: {backup_file}")

if __name__ == '__main__':
    print("🔄 Creando backup del archivo original...")
    backup_original()
    
    print("\n🔄 Reemplazando módulos con includes de Jinja2...")
    new_content, count = replace_modules_with_includes()
    
    print(f"✅ {count} módulos reemplazados con includes")
    
    # Guardar el nuevo contenido
    html_file = Path('templates/sql_query.html')
    html_file.write_text(new_content, encoding='utf-8')
    
    print(f"💾 Archivo actualizado: {html_file}")
    print("\n✅ Modularización completada!")
    print("📁 Estructura:")
    print("   templates/sql_query.html (archivo principal con includes)")
    print("   templates/modules/*.html (13 módulos individuales)")
