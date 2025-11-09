#!/usr/bin/env python3
"""
Test del sistema de deduplicación
"""
import json
from pathlib import Path

# Datos de prueba
test_data = [
    {"asin": "B001", "title": "Producto 1", "price": "10€"},
    {"asin": "B002", "title": "Producto 2", "price": "20€"},
    {"asin": "B003", "title": "Producto 3", "price": "30€"},
]

test_file = Path("data/extractions/amazon/test_dedup.json")
test_file.parent.mkdir(parents=True, exist_ok=True)

# Primera inserción
print("📝 Primera inserción (3 productos nuevos)...")
with open(test_file, 'w', encoding='utf-8') as f:
    json.dump(test_data, f, ensure_ascii=False, indent=2)

print(f"✅ Creado: {len(test_data)} productos")

# Segunda inserción (2 duplicados + 1 nuevo)
print("\n📝 Segunda inserción (2 duplicados + 1 nuevo)...")
new_data = [
    {"asin": "B002", "title": "Producto 2 (duplicado)", "price": "20€"},  # Duplicado
    {"asin": "B003", "title": "Producto 3 (duplicado)", "price": "30€"},  # Duplicado
    {"asin": "B004", "title": "Producto 4 (nuevo)", "price": "40€"},      # Nuevo
]

# Simular la función save_to_json
existing_data = json.load(open(test_file, 'r'))
existing_asins = {item['asin'] for item in existing_data}

new_products = []
duplicates = 0

for product in new_data:
    if product['asin'] not in existing_asins:
        new_products.append(product)
        existing_asins.add(product['asin'])
    else:
        duplicates += 1

combined = existing_data + new_products

with open(test_file, 'w', encoding='utf-8') as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)

print(f"✅ {len(new_products)} nuevos añadidos")
print(f"⏭️  {duplicates} duplicados omitidos")
print(f"📊 Total: {len(combined)} productos")

# Verificar
final_data = json.load(open(test_file, 'r'))
print(f"\n✨ Verificación final: {len(final_data)} productos en archivo")
for p in final_data:
    print(f"   - {p['asin']}: {p['title']}")
