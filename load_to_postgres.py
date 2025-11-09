"""
Script para cargar datos de JSON a PostgreSQL
"""
import json
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from datetime import datetime
import re


class AmazonDataLoader:
    """Carga datos de productos de Amazon a PostgreSQL"""
    
    def __init__(self, host="localhost", port=5434, database="scraper", 
                 user="postgres", password="postgres"):
        """Inicializar conexión a PostgreSQL"""
        self.conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Conectar a PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor()
            print("✅ Conectado a PostgreSQL")
        except Exception as e:
            print(f"❌ Error conectando a PostgreSQL: {e}")
            raise
    
    def close(self):
        """Cerrar conexión"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("🔌 Conexión cerrada")
    
    def extract_numeric_price(self, price_str):
        """Extraer valor numérico del precio"""
        if not price_str or price_str == "N/A":
            return None
        # Remover símbolos y convertir coma a punto
        clean_price = re.sub(r'[€$]', '', price_str).replace(',', '.').strip()
        try:
            return float(clean_price)
        except:
            return None
    
    def extract_numeric_rating(self, rating_str):
        """Extraer valor numérico del rating"""
        if not rating_str or rating_str == "N/A":
            return None
        # Extraer primer número decimal
        match = re.search(r'(\d+\.?\d*)', rating_str)
        if match:
            try:
                return float(match.group(1))
            except:
                return None
        return None
    
    def insert_product(self, product):
        """Insertar producto en la tabla products"""
        query = """
        INSERT INTO products (
            asin, title, brand, price, price_numeric, original_price, 
            discount, rating, rating_numeric, reviews_count, 
            has_prime, free_shipping, availability, seller, 
            url, image_url, search_term, position
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (asin) DO UPDATE SET
            title = EXCLUDED.title,
            brand = EXCLUDED.brand,
            price = EXCLUDED.price,
            price_numeric = EXCLUDED.price_numeric,
            rating = EXCLUDED.rating,
            rating_numeric = EXCLUDED.rating_numeric,
            updated_at = CURRENT_TIMESTAMP
        """
        
        values = (
            product.get('asin'),
            product.get('title'),
            product.get('brand') if product.get('brand') != 'N/A' else None,
            product.get('price'),
            self.extract_numeric_price(product.get('price')),
            product.get('original_price'),
            product.get('discount'),
            product.get('rating'),
            self.extract_numeric_rating(product.get('rating')),
            product.get('reviews_count'),
            product.get('has_prime', False),
            product.get('free_shipping', False),
            product.get('availability'),
            product.get('seller'),
            product.get('url'),
            product.get('image_url'),
            product.get('search_term'),
            product.get('position')
        )
        
        self.cursor.execute(query, values)
    
    def insert_specifications(self, asin, specifications):
        """Insertar especificaciones del producto"""
        if not specifications:
            return
        
        # Eliminar especificaciones antiguas
        self.cursor.execute(
            "DELETE FROM product_specifications WHERE product_asin = %s", 
            (asin,)
        )
        
        # Insertar nuevas especificaciones
        if isinstance(specifications, list):
            values = [
                (asin, spec.get('label'), spec.get('value'))
                for spec in specifications
                if spec.get('label') and spec.get('value')
            ]
        elif isinstance(specifications, dict):
            values = [
                (asin, key, value)
                for key, value in specifications.items()
                if key and value
            ]
        else:
            return
        
        if values:
            execute_values(
                self.cursor,
                "INSERT INTO product_specifications (product_asin, label, value) VALUES %s",
                values
            )
    
    def insert_nutrition_facts(self, asin, nutrition_facts):
        """Insertar información nutricional"""
        if not nutrition_facts or not isinstance(nutrition_facts, dict):
            return
        
        # Eliminar información nutricional antigua
        self.cursor.execute(
            "DELETE FROM nutrition_facts WHERE product_asin = %s", 
            (asin,)
        )
        
        # Insertar nueva información nutricional
        values = [
            (asin, nutrient, value)
            for nutrient, value in nutrition_facts.items()
            if nutrient and value
        ]
        
        if values:
            execute_values(
                self.cursor,
                "INSERT INTO nutrition_facts (product_asin, nutrient, value) VALUES %s",
                values
            )
    
    def insert_features(self, asin, features):
        """Insertar características del producto"""
        if not features or not isinstance(features, list):
            return
        
        # Eliminar características antiguas
        self.cursor.execute(
            "DELETE FROM product_features WHERE product_asin = %s", 
            (asin,)
        )
        
        # Insertar nuevas características
        values = [(asin, feature) for feature in features if feature]
        
        if values:
            execute_values(
                self.cursor,
                "INSERT INTO product_features (product_asin, feature) VALUES %s",
                values
            )
    
    def load_json_file(self, json_path):
        """Cargar un archivo JSON completo"""
        print(f"\n📄 Cargando: {json_path.name}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        loaded_count = 0
        error_count = 0
        
        for product in products:
            try:
                asin = product.get('asin')
                if not asin or asin == 'N/A':
                    print(f"  ⚠️ Producto sin ASIN válido, saltando...")
                    error_count += 1
                    continue
                
                # Insertar producto principal
                self.insert_product(product)
                
                # Insertar especificaciones
                if 'specifications' in product:
                    self.insert_specifications(asin, product['specifications'])
                
                if 'product_overview' in product:
                    self.insert_specifications(asin, product['product_overview'])
                
                if 'additional_specs' in product:
                    self.insert_specifications(asin, product['additional_specs'])
                
                # Insertar información nutricional
                if 'nutrition_facts' in product:
                    self.insert_nutrition_facts(asin, product['nutrition_facts'])
                
                # Insertar características
                if 'features' in product:
                    self.insert_features(asin, product['features'])
                
                loaded_count += 1
                
            except Exception as e:
                print(f"  ❌ Error procesando producto {product.get('asin', 'unknown')}: {e}")
                error_count += 1
                continue
        
        # Commit después de cada archivo
        self.conn.commit()
        
        print(f"  ✅ Cargados: {loaded_count} productos")
        if error_count > 0:
            print(f"  ⚠️ Errores: {error_count}")
        
        return loaded_count, error_count
    
    def load_all_json_files(self, directory='data/extractions/amazon'):
        """Cargar todos los archivos JSON de un directorio"""
        data_dir = Path(directory)
        json_files = list(data_dir.glob('*.json'))
        
        if not json_files:
            print(f"❌ No se encontraron archivos JSON en {directory}")
            return
        
        print(f"📁 Encontrados {len(json_files)} archivos JSON")
        
        total_loaded = 0
        total_errors = 0
        
        for json_file in json_files:
            loaded, errors = self.load_json_file(json_file)
            total_loaded += loaded
            total_errors += errors
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN FINAL")
        print(f"{'='*60}")
        print(f"✅ Total de productos cargados: {total_loaded}")
        if total_errors > 0:
            print(f"⚠️ Total de errores: {total_errors}")
        print(f"{'='*60}")
    
    def get_statistics(self):
        """Obtener estadísticas de la base de datos"""
        print(f"\n{'='*60}")
        print("📊 ESTADÍSTICAS DE LA BASE DE DATOS")
        print(f"{'='*60}")
        
        # Total de productos
        self.cursor.execute("SELECT COUNT(*) FROM products")
        total_products = self.cursor.fetchone()[0]
        print(f"Total de productos: {total_products}")
        
        # Productos por término de búsqueda
        self.cursor.execute("""
            SELECT search_term, COUNT(*) 
            FROM products 
            WHERE search_term IS NOT NULL
            GROUP BY search_term 
            ORDER BY COUNT(*) DESC
        """)
        print(f"\nProductos por búsqueda:")
        for term, count in self.cursor.fetchall():
            print(f"  - {term}: {count}")
        
        # Top 5 marcas
        self.cursor.execute("""
            SELECT brand, COUNT(*) 
            FROM products 
            WHERE brand IS NOT NULL AND brand != 'N/A'
            GROUP BY brand 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        """)
        print(f"\nTop 5 marcas:")
        for brand, count in self.cursor.fetchall():
            print(f"  - {brand}: {count}")
        
        # Precio promedio por categoría
        self.cursor.execute("""
            SELECT search_term, 
                   AVG(price_numeric) as avg_price,
                   MIN(price_numeric) as min_price,
                   MAX(price_numeric) as max_price
            FROM products 
            WHERE price_numeric IS NOT NULL
            GROUP BY search_term
        """)
        print(f"\nPrecios por categoría:")
        for term, avg, min_p, max_p in self.cursor.fetchall():
            print(f"  - {term}: Promedio €{avg:.2f} (€{min_p:.2f} - €{max_p:.2f})")
        
        # Productos con información nutricional
        self.cursor.execute("SELECT COUNT(DISTINCT product_asin) FROM nutrition_facts")
        nutrition_count = self.cursor.fetchone()[0]
        print(f"\nProductos con información nutricional: {nutrition_count}")
        
        print(f"{'='*60}")


def main():
    """Función principal"""
    print("🚀 Amazon Data Loader - PostgreSQL")
    print("="*60)
    
    loader = AmazonDataLoader()
    
    try:
        # Conectar a la base de datos
        loader.connect()
        
        # Cargar todos los archivos JSON
        loader.load_all_json_files()
        
        # Mostrar estadísticas
        loader.get_statistics()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loader.close()


if __name__ == "__main__":
    main()
