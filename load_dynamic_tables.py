"""
Carga dinámica de archivos JSON a PostgreSQL
Cada archivo JSON se convierte en una tabla independiente
"""
import json
import psycopg2
from psycopg2.extensions import AsIs
from pathlib import Path
from typing import Any, Dict, List, Set
import re

DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'scraper',
    'user': 'postgres',
    'password': 'postgres'
}

def clean_table_name(filename: str) -> str:
    """Convierte nombre de archivo a nombre de tabla válido"""
    # Remover extensión .json
    name = filename.replace('.json', '')
    # Reemplazar espacios y caracteres especiales con _
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Asegurar que empiece con letra
    if name[0].isdigit():
        name = 'table_' + name
    return name.lower()

def infer_column_type(value: Any) -> str:
    """Infiere el tipo de dato PostgreSQL basado en el valor"""
    if value is None:
        return 'TEXT'
    elif isinstance(value, bool):
        return 'BOOLEAN'
    elif isinstance(value, int):
        return 'INTEGER'
    elif isinstance(value, float):
        return 'NUMERIC'
    elif isinstance(value, (dict, list)):
        return 'JSONB'
    else:
        return 'TEXT'

def analyze_json_structure(data: List[Dict]) -> Dict[str, str]:
    """Analiza la estructura JSON para determinar tipos de columnas"""
    columns = {}
    
    for item in data:
        for key, value in item.items():
            # Limpiar nombre de columna
            col_name = re.sub(r'[^a-zA-Z0-9_]', '_', key).lower()
            
            if col_name not in columns:
                columns[col_name] = infer_column_type(value)
            else:
                # Si encontramos tipos mixtos, usar JSONB o TEXT
                current_type = infer_column_type(value)
                if current_type != columns[col_name]:
                    # Si hay conflicto, usar TEXT como fallback
                    if columns[col_name] != 'JSONB' and current_type != 'JSONB':
                        columns[col_name] = 'TEXT'
                    elif current_type == 'JSONB' or columns[col_name] == 'JSONB':
                        columns[col_name] = 'JSONB'
    
    return columns

def create_table(cursor, table_name: str, columns: Dict[str, str]):
    """Crea una tabla con las columnas especificadas, añadiendo constraint UNIQUE en ASIN"""
    # Primero eliminar la tabla si existe
    cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
    
    # Crear columnas
    col_definitions = []
    col_definitions.append("id SERIAL PRIMARY KEY")
    
    for col_name, col_type in columns.items():
        col_definitions.append(f"{col_name} {col_type}")
    
    # Agregar timestamp
    col_definitions.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # Si hay columna ASIN, añadir UNIQUE constraint
    unique_constraint = ""
    if 'asin' in columns:
        unique_constraint = ", UNIQUE(asin)"
    
    create_sql = f"""
        CREATE TABLE {table_name} (
            {', '.join(col_definitions)}{unique_constraint}
        );
    """
    
    cursor.execute(create_sql)
    print(f"✅ Tabla '{table_name}' creada con {len(columns)} columnas", flush=True)
    if 'asin' in columns:
        print(f"🔒 Constraint UNIQUE añadido en columna 'asin'", flush=True)

def insert_data(cursor, table_name: str, data: List[Dict], columns: Dict[str, str]):
    """Inserta datos en la tabla, usando ON CONFLICT para evitar duplicados por ASIN"""
    inserted = 0
    skipped = 0
    
    for item in data:
        # Preparar columnas y valores
        col_names = []
        col_values = []
        
        for key, value in item.items():
            col_name = re.sub(r'[^a-zA-Z0-9_]', '_', key).lower()
            
            if col_name in columns:
                col_names.append(col_name)
                
                # Si el tipo es JSONB, convertir dict/list a JSON
                if columns[col_name] == 'JSONB' and isinstance(value, (dict, list)):
                    col_values.append(json.dumps(value))
                else:
                    col_values.append(value)
        
        if col_names:
            placeholders = ', '.join(['%s'] * len(col_names))
            
            # Si hay columna ASIN, usar ON CONFLICT DO NOTHING
            if 'asin' in columns and 'asin' in col_names:
                insert_sql = f"""
                    INSERT INTO {table_name} ({', '.join(col_names)})
                    VALUES ({placeholders})
                    ON CONFLICT (asin) DO NOTHING
                """
            else:
                insert_sql = f"""
                    INSERT INTO {table_name} ({', '.join(col_names)})
                    VALUES ({placeholders})
                """
            
            cursor.execute(insert_sql, col_values)
            
            # Contar si se insertó o no
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
    
    return inserted, skipped

def load_json_file(json_path: Path):
    """Carga un archivo JSON y crea su tabla correspondiente"""
    print(f"\n📂 Procesando: {json_path.name}", flush=True)
    
    # Leer archivo JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        print(f"⚠️  Archivo vacío, saltando...", flush=True)
        return
    
    # Determinar nombre de tabla
    table_name = clean_table_name(json_path.stem)
    
    # Analizar estructura
    columns = analyze_json_structure(data)
    print(f"   Columnas detectadas: {len(columns)}", flush=True)
    for col, dtype in columns.items():
        print(f"   - {col}: {dtype}", flush=True)
    
    # Conectar a la base de datos
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Crear tabla
        create_table(cursor, table_name, columns)
        
        # Insertar datos
        inserted, skipped = insert_data(cursor, table_name, data, columns)
        
        conn.commit()
        
        # Mostrar estadísticas
        print(f"✅ {inserted} registros nuevos insertados en '{table_name}'", flush=True)
        if skipped > 0:
            print(f"⏭️  {skipped} registros duplicados omitidos", flush=True)
        print(f"📊 Total en JSON: {len(data)} productos", flush=True)
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error procesando {json_path.name}: {e}", flush=True)
    finally:
        cursor.close()
        conn.close()

def main():
    """Procesa todos los archivos JSON en la carpeta de extracciones"""
    base_path = Path("data/extractions")
    
    if not base_path.exists():
        print(f"❌ La ruta {base_path} no existe", flush=True)
        return
    
    # Buscar en todas las subcarpetas (amazon, corte_ingles, etc.)
    json_files = []
    for platform_dir in base_path.iterdir():
        if platform_dir.is_dir():
            platform_files = list(platform_dir.glob("*.json"))
            json_files.extend(platform_files)
            print(f"📁 Plataforma: {platform_dir.name} - {len(platform_files)} archivos", flush=True)
    
    if not json_files:
        print(f"⚠️  No se encontraron archivos JSON en {base_path}", flush=True)
        return
    
    print(f"🔍 Total: {len(json_files)} archivos JSON", flush=True)
    print("="*60, flush=True)
    
    for json_file in json_files:
        load_json_file(json_file)
    
    print("\n" + "="*60, flush=True)
    print("✨ Proceso completado", flush=True)
    print(f"📊 Archivos procesados: {len(json_files)}", flush=True)

if __name__ == "__main__":
    main()
