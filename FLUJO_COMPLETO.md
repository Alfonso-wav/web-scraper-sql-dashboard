# Flujo Completo de Scraping desde el Frontend

## 🎯 Nuevo Flujo Automatizado

Ahora puedes hacer **todo desde el frontend web**:

### 1️⃣ Iniciar Scraping
En http://localhost:5000 encontrarás un campo de búsqueda en la parte superior:

```
🔍 Scraper de Amazon
┌──────────────────────────────────────────────┐
│ cafe descafeinado                      [🚀 Iniciar Scraping] │
└──────────────────────────────────────────────┘
```

### 2️⃣ Proceso Automático
Al hacer clic en "Iniciar Scraping":

1. **Scraping** (5-10 min):
   - Ejecuta `python main.py "tu_termino"`
   - Visita Amazon.es y extrae 50 productos
   - Guarda en `data/extractions/amazon/amazon_tu_termino.json`

2. **Carga a DB** (automático):
   - Ejecuta `python load_dynamic_tables.py`
   - Crea tabla `amazon_tu_termino` 
   - Infiere columnas del JSON
   - Datos anidados → tipo JSONB

3. **Actualización Frontend**:
   - Recarga panel de tablas cada 30 segundos
   - Nueva tabla aparece automáticamente
   - Puedes consultarla inmediatamente

### 3️⃣ Consultar Datos
Una vez completado el proceso:

- **Panel derecho**: Ver nueva tabla y su esquema
- **Editor SQL**: Consultar los datos
- **Consultas ejemplo**: Adaptables a tu nueva tabla

## 📊 Ejemplo de Uso Completo

### Paso 1: Buscar productos
```
Término: "teclado mecanico"
[🚀 Iniciar Scraping]

🔄 Scraping iniciado para "teclado mecanico"
⏱️ Esto puede tardar 5-10 minutos...
```

### Paso 2: Esperar (puedes seguir usando SQL)
```
✅ Scraping completado
🔄 Cargando datos a PostgreSQL...
```

### Paso 3: Nueva tabla disponible
```
🗄️ Tablas Disponibles
  📋 amazon_cafe
  📋 amazon_leche_de_vaca
  📋 amazon_monitor_gaming
  📋 amazon_teclado_mecanico  ← NUEVA
```

### Paso 4: Consultar
```sql
SELECT title, brand, price, rating 
FROM amazon_teclado_mecanico 
WHERE has_prime = true
ORDER BY rating DESC
LIMIT 10;
```

## 🔧 Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────┐
│              FRONTEND (localhost:5000)               │
│                                                      │
│  [Input: término búsqueda] → [🚀 Iniciar Scraping] │
│                        ↓                             │
│              POST /scrape endpoint                   │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌──────────────────────┴──────────────────────────────┐
│              BACKEND (Flask + Threading)             │
│                                                      │
│  Thread 1: main.py "término"                        │
│    ├─ Playwright abre Chrome                        │
│    ├─ Busca en Amazon.es                            │
│    ├─ Extrae 50 productos                           │
│    └─ Guarda JSON                                   │
│                        ↓                             │
│  Thread 2: load_dynamic_tables.py                   │
│    ├─ Lee JSON                                      │
│    ├─ Infiere esquema                               │
│    ├─ CREATE TABLE                                  │
│    └─ INSERT datos                                  │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌──────────────────────┴──────────────────────────────┐
│           PostgreSQL (puerto 5434)                   │
│                                                      │
│  • amazon_cafe                                      │
│  • amazon_leche_de_vaca                             │
│  • amazon_monitor_gaming                            │
│  • amazon_[tu_termino] ← NUEVA TABLA                │
└─────────────────────────────────────────────────────┘
```

## ⚡ Características Técnicas

### Frontend (templates/sql_query.html)
- Input para término de búsqueda
- Botón que llama `startScraping()`
- Status en tiempo real (loading/success/error)
- Auto-reload de tablas cada 30 segundos

### Backend (sql_frontend.py)
- **Endpoint `/scrape`**: Recibe término, lanza threads
- **Threading**: Proceso no bloquea el servidor
- **Timeout**: 10 minutos máximo por scraping
- **Auto-carga**: Llama a `load_dynamic_tables.py` automáticamente

### Scraper (main.py)
- **Args CLI**: `python main.py "término"` 
- **Modo detallado**: Activado por defecto desde API
- **Sin interacción**: No pide confirmaciones
- **Output**: `data/extractions/amazon/amazon_término.json`

### Cargador (load_dynamic_tables.py)
- **Dinámico**: Lee todos los JSON en carpeta
- **Inferencia**: Detecta tipos de columnas automáticamente
- **JSONB**: Datos anidados se almacenan consultables
- **Idempotente**: Recrea tablas (DROP + CREATE)

## 🎮 Tips de Uso

1. **Múltiples búsquedas simultáneas**: El sistema usa threading, puedes lanzar varias búsquedas (aunque no recomendado por carga)

2. **Monitoreo**: Mantén el panel de tablas visible para ver cuándo aparece la nueva tabla

3. **SQL mientras esperas**: Puedes consultar otras tablas mientras el scraping corre en background

4. **Nombres de tabla**: Se limpian automáticamente
   - `"café orgánico"` → `amazon_cafe_organico`
   - `"monitor 4K"` → `amazon_monitor_4k`

5. **Datos JSONB**: Consulta datos anidados
   ```sql
   SELECT title, specifications->>'Tamaño' 
   FROM amazon_tu_tabla;
   ```

## 🐛 Troubleshooting

**"No aparece la tabla"**
- Espera 10 minutos (scraping es lento)
- Verifica que haya JSON en `data/extractions/amazon/`
- Ejecuta manualmente: `python load_dynamic_tables.py`

**"Error en scraping"**
- Amazon puede bloquear: usa VPN o espera
- Chromium no instalado: `playwright install`
- Red lenta: aumenta timeout en main.py

**"Botón deshabilitado"**
- Hay un scraping en curso
- Espera o recarga la página

## 📝 Código Clave

### Frontend - Iniciar Scraping
```javascript
async function startScraping() {
    const searchTerm = document.getElementById('searchTermInput').value;
    
    const response = await fetch('/scrape', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ search_term: searchTerm })
    });
    
    // Auto-reload tablas cada 30 segundos
    setInterval(() => loadTables(), 30000);
}
```

### Backend - Endpoint Scraping
```python
@app.route('/scrape', methods=['POST'])
def start_scraping():
    search_term = request.get_json().get('search_term')
    
    def run_scraper():
        # Scraping
        subprocess.run(['.venv/bin/python', 'main.py', search_term])
        # Auto-carga
        subprocess.run(['.venv/bin/python', 'load_dynamic_tables.py'])
    
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True})
```

## 🚀 Mejoras Futuras Posibles

- ✅ Progreso en tiempo real (WebSocket)
- ✅ Cola de trabajos (múltiples scraping)
- ✅ Caché de resultados
- ✅ Notificaciones cuando termina
- ✅ Exportar a CSV/Excel desde frontend
- ✅ Gráficos y visualizaciones
- ✅ Comparación entre tablas
