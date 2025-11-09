# Amazon Scraper con Playwright

Sistema completo de scraping de Amazon.es con análisis de datos y frontend SQL **integrado**.

## 🚀 Características

- **Scraping desde el Frontend**: Inicia búsquedas directamente desde la interfaz web
- **Proceso automático**: Scraping → JSON → PostgreSQL sin intervención manual
- **Datos detallados**: Título, precio, marca, valoraciones, especificaciones, información nutricional
- **Base de datos dinámica**: Cada búsqueda crea automáticamente su tabla en PostgreSQL
- **Frontend SQL completo**: Interfaz web para scraping, consultas y visualización

## ✨ Flujo Completo End-to-End

```
🌐 Frontend (http://localhost:5000)
    ↓ [Usuario introduce: "teclado mecanico"]
    ↓ [Click: 🚀 Iniciar Scraping]
    ↓
🤖 Scraper (main.py)
    ↓ Visita Amazon.es
    ↓ Extrae 50 productos con detalles
    ↓ Guarda: data/extractions/amazon/amazon_teclado_mecanico.json
    ↓
💾 Cargador (load_dynamic_tables.py)
    ↓ Lee JSON
    ↓ Infiere esquema (columnas + tipos)
    ↓ CREATE TABLE amazon_teclado_mecanico
    ↓ INSERT 50 productos
    ↓
🗄️ PostgreSQL (puerto 5434)
    ↓ Nueva tabla disponible
    ↓
🌐 Frontend
    ↓ Auto-actualiza panel de tablas
    ✅ ¡Lista para consultar con SQL!
```

## 📋 Estructura del Proyecto

```
scrapper_amazon/
├── main.py                      # Scraper principal con Playwright
├── load_dynamic_tables.py       # Carga JSON → PostgreSQL (dinámico)
├── sql_frontend.py              # Frontend web Flask para SQL
├── analysis.ipynb               # Análisis con pandas
├── docker-compose.yml           # PostgreSQL en Docker
├── data/
│   └── extractions/
│       └── amazon/
│           ├── amazon_cafe.json              → Tabla: amazon_cafe
│           ├── amazon_leche_de_vaca.json     → Tabla: amazon_leche_de_vaca
│           └── amazon_monitor_gaming.json    → Tabla: amazon_monitor_gaming
└── templates/
    └── sql_query.html           # UI del frontend

```

## 🔧 Instalación

```bash
# Instalar dependencias
uv pip install playwright pandas psycopg2-binary sqlalchemy flask

# Instalar navegadores de Playwright
playwright install

# Levantar PostgreSQL
docker-compose up -d
```

## 📊 Uso

### Modo Integrado (Recomendado) 🌟

```bash
# 1. Levantar PostgreSQL
docker-compose up -d

# 2. Iniciar frontend
python sql_frontend.py
```

Abre http://localhost:5000 y:

1. **Introduce término de búsqueda** (ej: "auriculares gaming")
2. **Click en "🚀 Iniciar Scraping"**
3. **Espera 5-10 minutos** (puedes usar SQL mientras tanto)
4. **La nueva tabla aparece automáticamente** en el panel derecho
5. **¡Consulta tus datos con SQL!**

### Modo Manual (Opcional)

#### 1. Scraping de productos

```bash
python main.py
# O con argumento: python main.py "cafe organico"
```

El script extraerá los 50 productos mejor valorados.

#### 2. Cargar datos a PostgreSQL

```bash
python load_dynamic_tables.py
```

Este script:
- Lee todos los archivos JSON en `data/extractions/amazon/`
- Crea una tabla por cada archivo JSON
- Las columnas se infieren automáticamente de las claves JSON
- Los datos anidados (objetos/arrays) se almacenan como JSONB

#### 3. Frontend SQL

```bash
python sql_frontend.py
```

Abre http://localhost:5000

## 🎯 Interfaz del Frontend

### Panel Superior: Scraper Integrado
```
┌─────────────────────────────────────────────────────────┐
│ 🔍 Scraper de Amazon                                    │
│ ┌─────────────────────────────────┬──────────────────┐ │
│ │ cafe descafeinado               │ 🚀 Iniciar      │ │
│ └─────────────────────────────────┴──────────────────┘ │
│ 🔄 Scraping iniciado... Visitando 50 productos        │
└─────────────────────────────────────────────────────────┘
```

### Panel Izquierdo: Consultas de Ejemplo
- Ver todos los cafés
- Ver toda la leche
- Café con Prime
- Top 5 mejor valorados
- Productos con descuento
- etc.

### Panel Central: Editor SQL
- Escribe consultas personalizadas
- Ejecuta con Ctrl+Enter
- Resultados en tabla interactiva

### Panel Derecho: Tablas Disponibles
- Lista de todas las tablas
- Click para ver esquema completo
- Se actualiza automáticamente

## 📋 Ejemplos de Tablas Creadas

**Ejemplos actuales:**
- `amazon_cafe.json` → tabla `amazon_cafe` (50 productos)
- `amazon_leche_de_vaca.json` → tabla `amazon_leche_de_vaca` (50 productos)
- `amazon_monitor_gaming.json` → tabla `amazon_monitor_gaming` (50 productos)

**Después de buscar "teclado mecanico":**
- `amazon_teclado_mecanico.json` → tabla `amazon_teclado_mecanico` (50 productos)
- Ver todas las tablas disponibles con sus esquemas
- Ejecutar consultas SQL personalizadas
- Usar consultas de ejemplo predefinidas
- Explorar datos con campos JSONB

## 🗄️ Esquema de Base de Datos (Dinámico)

Cada tabla se crea automáticamente con:

**Columnas básicas** (inferidas del JSON):
- `id` (SERIAL PRIMARY KEY)
- `title` (TEXT)
- `brand` (TEXT)
- `price` (TEXT)
- `rating` (TEXT)
- `has_prime` (BOOLEAN)
- `created_at` (TIMESTAMP)

**Columnas JSONB** (para datos anidados):
- `specifications` (JSONB) - Especificaciones técnicas
- `nutrition_facts` (JSONB) - Información nutricional
- `features` (JSONB) - Características del producto
- `product_overview` (JSONB) - Vista general del producto
- `options` (JSONB) - Variantes del producto

## 💡 Ejemplos de Consultas SQL

```sql
-- Ver todos los cafés
SELECT id, title, brand, price, rating FROM amazon_cafe LIMIT 10;

-- Productos con Prime
SELECT title, brand, price, rating 
FROM amazon_cafe 
WHERE has_prime = true;

-- Extraer información nutricional (JSONB)
SELECT 
    title, 
    brand, 
    nutrition_facts->>'Energía' as energia,
    nutrition_facts->>'Proteína' as proteina
FROM amazon_leche_de_vaca
WHERE nutrition_facts IS NOT NULL;

-- Consultar especificaciones técnicas (JSONB)
SELECT 
    title,
    brand,
    specifications->>'Tamaño de la pantalla' as pantalla,
    specifications->>'Frecuencia de actualización' as hz
FROM amazon_monitor_gaming
WHERE specifications IS NOT NULL;

-- Unión de todas las categorías
SELECT 'Café' as categoria, COUNT(*) FROM amazon_cafe
UNION ALL
SELECT 'Leche', COUNT(*) FROM amazon_leche_de_vaca
UNION ALL  
SELECT 'Monitor', COUNT(*) FROM amazon_monitor_gaming;
```

## 🎯 Ventajas del Enfoque Dinámico

1. **Todo desde el navegador**: No necesitas terminal, todo en http://localhost:5000
2. **Sin esquema fijo**: Cada JSON puede tener estructura diferente
3. **Automático**: No necesitas definir columnas manualmente
4. **Flexible**: Datos anidados en JSONB consultables con operadores JSON
5. **Escalable**: Agrega nuevos términos de búsqueda y automáticamente se crean tablas
6. **Tiempo real**: Ve el progreso y usa SQL mientras el scraping corre en background

## 🐛 Troubleshooting

- **Puerto ocupado**: PostgreSQL usa puerto 5434 (no 5432)
- **Error de conexión**: Verifica que Docker esté corriendo: `docker ps`
- **Tablas vacías**: Ejecuta primero `python load_dynamic_tables.py`

## 📝 Notas Técnicas

- Los datos anidados (dict/list) se convierten a tipo JSONB
- Los nombres de columnas se limpian (sin espacios ni caracteres especiales)
- Las tablas se recrean cada vez que ejecutas `load_dynamic_tables.py`
- Frontend usa RealDictCursor para retornar resultados como diccionarios
