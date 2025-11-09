# Configuración de PostgreSQL para Amazon Scraper

## 🐘 Información de Conexión

### PostgreSQL
- **Host:** localhost
- **Puerto:** 5434
- **Base de datos:** amazon_products
- **Usuario:** postgres
- **Contraseña:** postgres

## 🚀 Comandos

### Iniciar los servicios
```bash
docker-compose up -d
```

### Ver logs
```bash
docker-compose logs -f postgres
```

### Detener los servicios
```bash
docker-compose down
```

### Detener y eliminar volúmenes (⚠️ borra todos los datos)
```bash
docker-compose down -v
```

### Acceder a PostgreSQL desde terminal
```bash
docker exec -it amazon_scraper_postgres psql -U scraper_user -d amazon_products
```

## 📊 Estructura de la Base de Datos

### Tabla `products`
Almacena la información principal de cada producto.

### Tabla `product_specifications`
Almacena especificaciones técnicas de los productos.

### Tabla `nutrition_facts`
Almacena información nutricional (para productos alimenticios).

### Tabla `product_features`
Almacena las características destacadas de cada producto.

## 🔌 String de Conexión

Para usar con SQLAlchemy, psycopg2 o pandas:

```python
connection_string = "postgresql://postgres:postgres@localhost:5434/amazon_products"
```

### Ejemplo con pandas:
```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('postgresql://postgres:postgres@localhost:5434/amazon_products')

# Leer datos
df = pd.read_sql('SELECT * FROM products LIMIT 10', engine)

# Escribir datos
df.to_sql('products', engine, if_exists='append', index=False)
```

### Ejemplo con psycopg2:
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5434,
    database="amazon_products",
    user="postgres",
    password="postgres"
)
```

## 🔒 Seguridad

⚠️ **IMPORTANTE:** Las credenciales en este archivo son para desarrollo local. 

Para producción:
1. Cambia las contraseñas
2. Usa variables de entorno
3. Crea un archivo `.env` y añádelo al `.gitignore`
