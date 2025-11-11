# Estructura Modular del Proyecto

## 📁 Organización de Módulos

El frontend está organizado en una estructura modular para facilitar el mantenimiento y la edición de cada componente independiente.

### Estructura de Archivos

```
templates/
├── sql_query.html              # Plantilla principal (usa includes)
├── sql_query.html.backup_modular  # Backup del archivo original
├── modules_config.py           # Configuración de módulos a cargar
└── modules/                    # Carpeta con módulos individuales
    ├── scraper.html           # Módulo de scraping multi-plataforma
    ├── columnas.html          # Módulo de columnas comunes
    ├── vistas.html            # Módulo de vistas guardadas
    ├── editor.html            # Módulo de editor SQL
    ├── tablas.html            # Módulo de tablas disponibles
    ├── graficos.html          # Módulo generador de gráficos
    ├── conversor.html         # Módulo conversor de columnas
    ├── galeria-graficos.html  # Módulo galería de gráficos
    ├── personalizador.html    # Módulo personalizador visual
    ├── galeria-imagenes.html  # Módulo galería de imágenes
    ├── visualizador.html      # Módulo visualizador de productos
    ├── resultados.html        # Módulo de resultados SQL
    └── canvas-control.html    # Módulo de control de canvas
```

## 🔧 Cómo Funciona

### 1. Configuración de Módulos

El archivo `templates/modules_config.py` define qué módulos se cargan y en qué orden:

```python
MODULES = [
    'scraper',
    'columnas',
    'vistas',
    'editor',
    # ... más módulos
]
```

### 2. Carga Dinámica

El archivo principal `sql_query.html` usa Jinja2 para incluir los módulos:

```html
<!-- Módulos cargados dinámicamente -->
{% for module_id in modules %}
    {% include 'modules/' + module_id + '.html' %}
{% endfor %}
```

### 3. Backend Flask

El servidor Flask pasa la lista de módulos al template:

```python
@app.route('/')
def index():
    from templates.modules_config import MODULES
    return render_template('sql_query.html', modules=MODULES)
```

## ✏️ Editando Módulos

### Para editar un módulo específico:

1. Abre el archivo del módulo en `templates/modules/`
2. Realiza los cambios necesarios
3. Guarda el archivo
4. Recarga la página en el navegador

### Estructura de un módulo:

```html
<!-- Módulo: Nombre del Módulo -->
<div class="draggable-module" draggable="false" 
     data-module-id="id-del-modulo" 
     data-module-name="Nombre" 
     data-module-icon="bi-icono">
    
    <div class="card shadow-sm h-100">
        <div class="card-body">
            <!-- Contenido del módulo -->
        </div>
    </div>
    
    <!-- Resize handles -->
    <div class="resize-handle resize-right"></div>
    <div class="resize-handle resize-bottom"></div>
    <div class="resize-handle resize-corner"></div>
</div>
```

## 🆕 Añadiendo un Nuevo Módulo

1. Crea un nuevo archivo HTML en `templates/modules/`, ej: `nuevo-modulo.html`
2. Usa la estructura de módulo mostrada arriba
3. Añade el ID del módulo a `templates/modules_config.py`:
   ```python
   MODULES = [
       # ... módulos existentes
       'nuevo-modulo',  # Tu nuevo módulo
   ]
   ```
4. Reinicia el servidor Flask
5. Recarga la página

## 🗑️ Desactivando un Módulo

Para ocultar temporalmente un módulo sin eliminarlo:

1. Abre `templates/modules_config.py`
2. Comenta o elimina el ID del módulo de la lista:
   ```python
   MODULES = [
       'scraper',
       # 'columnas',  # Módulo desactivado temporalmente
       'vistas',
   ]
   ```
3. Reinicia el servidor Flask

## 🛠️ Scripts de Utilidad

### `extract_modules.py`
Extrae módulos del archivo monolítico original a archivos individuales.

```bash
python extract_modules.py
```

### `modularize.py`
Reemplaza la sección de módulos en `sql_query.html` con includes de Jinja2.

```bash
python modularize.py
```

## 📊 Estadísticas

- **Archivo original**: 4,832 líneas
- **Archivo modularizado**: 4,041 líneas
- **Reducción**: 791 líneas (-16.4%)
- **Módulos individuales**: 13 archivos
- **Líneas promedio por módulo**: ~60 líneas

## ✅ Ventajas de la Modularización

1. **Mantenibilidad**: Cada módulo se edita independientemente
2. **Legibilidad**: Archivos más pequeños y enfocados
3. **Reutilización**: Módulos pueden compartirse entre proyectos
4. **Colaboración**: Múltiples desarrolladores pueden trabajar en paralelo
5. **Testing**: Más fácil probar componentes individuales
6. **Git**: Diffs más claros, menos conflictos de merge

## 🔄 Proceso de Modularización

El proyecto fue modularizado siguiendo estos pasos:

1. ✅ Extracción automática de 13 módulos a archivos individuales
2. ✅ Creación de configuración centralizada (`modules_config.py`)
3. ✅ Modificación del backend para pasar lista de módulos
4. ✅ Reemplazo de módulos en template principal con includes Jinja2
5. ✅ Creación de backup del archivo original
6. ✅ Verificación de funcionamiento completo

## 🚨 Importante

- **NO elimines** el archivo `sql_query.html.backup_modular` - es el respaldo del archivo original
- Los módulos mantienen toda su funcionalidad JavaScript y CSS
- El orden de carga de módulos puede afectar la inicialización de algunos scripts
- Cada módulo es autocont enido pero comparte el contexto JavaScript global
