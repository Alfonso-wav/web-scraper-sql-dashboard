"""
Frontend web simple para ejecutar consultas SQL en PostgreSQL
"""
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import subprocess
import os
from pathlib import Path
import threading
import time
import queue
import re
import base64
from datetime import datetime

app = Flask(__name__)

# Directorio para guardar gráficos
CHARTS_DIR = Path(__file__).parent / 'static' / 'charts'
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Cola global para eventos de progreso
progress_queues = {}

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'scraper',
    'user': 'postgres',
    'password': 'postgres'
}

# Consultas predefinidas
SAMPLE_QUERIES = {
    "Ver todos los cafés": "SELECT id, title, brand, price, rating FROM amazon_cafe LIMIT 10;",
    "Ver toda la leche": "SELECT id, title, brand, price, rating FROM amazon_leche_de_vaca LIMIT 10;",
    "Ver monitores": "SELECT id, title, brand, price, rating FROM amazon_monitor_gaming LIMIT 10;",
    "Café con Prime": """
        SELECT title, brand, price, rating, has_prime
        FROM amazon_cafe
        WHERE has_prime = true
        LIMIT 20;
    """,
    "Leche con info nutricional": """
        SELECT title, brand, price, nutrition_facts
        FROM amazon_leche_de_vaca
        WHERE nutrition_facts IS NOT NULL
        LIMIT 10;
    """,
    "Monitores con especificaciones": """
        SELECT title, brand, price, specifications
        FROM amazon_monitor_gaming
        WHERE specifications IS NOT NULL
        LIMIT 10;
    """,
    "Top 5 cafés mejor valorados": """
        SELECT title, brand, price, rating, reviews_count
        FROM amazon_cafe
        WHERE rating IS NOT NULL
        ORDER BY rating DESC
        LIMIT 5;
    """,
    "Unión de todas las tablas": """
        SELECT 'Café' as categoria, COUNT(*) as total FROM amazon_cafe
        UNION ALL
        SELECT 'Leche' as categoria, COUNT(*) as total FROM amazon_leche_de_vaca
        UNION ALL
        SELECT 'Monitor' as categoria, COUNT(*) as total FROM amazon_monitor_gaming;
    """,
    "Productos con descuento": """
        SELECT title, brand, price, original_price, discount
        FROM amazon_cafe
        WHERE discount IS NOT NULL AND discount != ''
        LIMIT 10;
    """
}


def execute_query(query):
    """Ejecuta una consulta SQL y devuelve los resultados"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query)
        
        # Si es SELECT, devolver resultados
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            conn.close()
            return {
                'success': True,
                'columns': columns,
                'data': [dict(row) for row in results],
                'row_count': len(results)
            }
        else:
            # Para INSERT, UPDATE, DELETE
            conn.commit()
            row_count = cursor.rowcount
            conn.close()
            return {
                'success': True,
                'message': f'Consulta ejecutada correctamente. Filas afectadas: {row_count}',
                'row_count': row_count
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_most_common_columns():
    """Obtiene las columnas más comunes en todas las tablas de la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener todas las columnas de todas las tablas en el esquema public
        query = """
            SELECT column_name, COUNT(*) as frequency
            FROM information_schema.columns
            WHERE table_schema = 'public' 
                AND table_name NOT LIKE 'pg_%'
                AND column_name NOT IN ('id', 'created_at')
            GROUP BY column_name
            ORDER BY frequency DESC, column_name ASC
            LIMIT 20;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        # Convertir a lista de diccionarios con nombre y frecuencia
        columns = [{'name': row['column_name'], 'frequency': row['frequency']} for row in results]
        return columns
        
    except Exception as e:
        print(f"Error obteniendo columnas comunes: {e}", flush=True)
        return []


def get_columns_by_table():
    """Obtiene todas las columnas agrupadas por tabla"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                table_name,
                column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' 
                AND table_name NOT LIKE 'pg_%'
                AND column_name NOT IN ('id', 'created_at')
            ORDER BY table_name, ordinal_position;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        # Organizar columnas por tabla
        columns_by_table = {}
        for row in results:
            table = row['table_name']
            column = row['column_name']
            if table not in columns_by_table:
                columns_by_table[table] = []
            columns_by_table[table].append(column)
        
        return columns_by_table
        
    except Exception as e:
        print(f"Error obteniendo columnas por tabla: {e}", flush=True)
        return {}


@app.route('/')
def index():
    """Página principal"""
    common_columns = get_most_common_columns()
    return render_template('sql_query.html', sample_queries=SAMPLE_QUERIES, common_columns=common_columns)


@app.route('/execute', methods=['POST'])
def execute():
    """Endpoint para ejecutar consultas SQL"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'error': 'Query vacía'})
    
    result = execute_query(query)
    return jsonify(result)


@app.route('/tables')
def get_tables():
    """Obtener lista de tablas disponibles con conteo de filas"""
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """
    result = execute_query(query)
    
    if result['success'] and result['data']:
        # Añadir conteo de filas para cada tabla
        for table in result['data']:
            table_name = table['table_name']
            count_query = f"SELECT COUNT(*) as count FROM {table_name};"
            count_result = execute_query(count_query)
            
            if count_result['success'] and count_result['data']:
                table['row_count'] = count_result['data'][0]['count']
            else:
                table['row_count'] = 0
    
    return jsonify(result)


@app.route('/columns-by-table')
def columns_by_table():
    """Obtener todas las columnas agrupadas por tabla"""
    columns_data = get_columns_by_table()
    return jsonify({
        'success': True,
        'data': columns_data
    })


@app.route('/schema/<table_name>')
def get_schema(table_name):
    """Obtener esquema de una tabla"""
    query = f"""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
    """
    result = execute_query(query)
    return jsonify(result)


@app.route('/scrape', methods=['POST'])
def start_scraping():
    """Inicia el proceso de scraping"""
    data = request.get_json()
    platform = data.get('platform', 'amazon').strip()  # amazon o corte_ingles
    search_term = data.get('search_term', '').strip()
    num_products = data.get('num_products', 50)
    headless = data.get('headless', True)  # Por defecto en modo headless
    
    if not search_term:
        return jsonify({'success': False, 'error': 'Término de búsqueda vacío'})
    
    if platform not in ['amazon', 'corte_ingles']:
        return jsonify({'success': False, 'error': 'Plataforma no soportada'})
    
    # Validar número de productos
    try:
        num_products = int(num_products)
        if num_products < 1:
            return jsonify({'success': False, 'error': 'El número debe ser mayor a 0'})
    except ValueError:
        return jsonify({'success': False, 'error': 'Número de productos inválido'})
    
    # Generar ID único para este scraping
    job_id = f"{platform}_{search_term}_{int(time.time())}"
    progress_queues[job_id] = queue.Queue()
    
    def send_progress(step, status, progress, message):
        """Envía un evento de progreso"""
        try:
            event = {
                'step': step,
                'status': status,  # 'running', 'completed', 'error'
                'message': message
            }
            # Solo añadir progress si no es None
            if progress is not None:
                event['progress'] = progress
            
            # Debug: imprimir evento
            print(f"[SSE] Step {step}: {progress}% - {message[:50]}", flush=True)
            
            progress_queues[job_id].put(event)
        except Exception as e:
            print(f"[ERROR] send_progress: {e}", flush=True)
    
    def run_scraper():
        try:
            # PASO 1: Scraping
            # Mapeo de plataformas a emojis y nombres
            platform_config = {
                'amazon': {'emoji': '🛒', 'name': 'Amazon'},
                'corte_ingles': {'emoji': '🏬', 'name': 'El Corte Inglés'},
                'temu': {'emoji': '🛍️', 'name': 'Temu'},
                'aliexpress': {'emoji': '📦', 'name': 'AliExpress'}
            }
            
            # Obtener configuración o usar valores por defecto
            config = platform_config.get(platform, {'emoji': '🌐', 'name': platform.capitalize()})
            platform_emoji = config['emoji']
            platform_name = config['name']
            
            send_progress(1, 'running', 0, f'{platform_emoji} Iniciando scraping de "{search_term}" en {platform_name}...')
            time.sleep(0.3)
            
            # Usar PYTHONUNBUFFERED como variable de entorno
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            # Seleccionar script según la plataforma
            script_name = 'main.py' if platform == 'amazon' else 'scraper_temu.py'
            
            # Construir argumentos del comando
            cmd_args = ['.venv/bin/python', script_name, search_term, str(num_products)]
            
            # Agregar flag --headless si corresponde
            if headless:
                cmd_args.append('--headless')
            
            result = subprocess.Popen(
                cmd_args,
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            
            # Leer salida en tiempo real
            product_count = 0
            for line in iter(result.stdout.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Detectar progreso con mucha más granularidad
                if '🚀 iniciando' in line.lower():
                    send_progress(1, 'running', 2, f'{line[:70]}...')
                elif '� objetivo' in line.lower():
                    send_progress(1, 'running', 5, f'{line[:70]}...')
                elif '🌐 abriendo navegador' in line.lower():
                    send_progress(1, 'running', 8, f'{line[:70]}...')
                elif '� navegando a amazon' in line.lower():
                    send_progress(1, 'running', 12, f'{line[:70]}...')
                elif '✅ página cargada' in line.lower():
                    send_progress(1, 'running', 15, f'{line[:70]}...')
                elif '📄 procesando página' in line.lower():
                    send_progress(1, 'running', 18, f'{line[:70]}...')
                elif '⏳ esperando carga' in line.lower():
                    send_progress(1, 'running', 20, f'{line[:70]}...')
                elif '🔎 encontrados' in line.lower() and 'productos en la página' in line.lower():
                    send_progress(1, 'running', 22, f'{line[:70]}...')
                elif '🔄' in line and '[' in line and '/' in line and ']' in line:
                    # Detectar "[X/Y]" para calcular progreso exacto
                    try:
                        match = re.search(r'\[(\d+)/(\d+)\]', line)
                        if match:
                            current = int(match.group(1))
                            total = int(match.group(2))
                            # Rango 22-75% para extracción
                            progress = 22 + int((current / total) * 53)
                            send_progress(1, 'running', progress, f'{line[:70]}...')
                    except:
                        pass
                elif '✅' in line and '[' in line and '/' in line and ']' in line:
                    # Productos completados
                    try:
                        match = re.search(r'\[(\d+)/(\d+)\]', line)
                        if match:
                            current = int(match.group(1))
                            total = int(match.group(2))
                            progress = 22 + int((current / total) * 53)
                            send_progress(1, 'running', progress, f'{line[:70]}...')
                    except:
                        pass
                elif '💾 agregando' in line.lower():
                    send_progress(1, 'running', 76, f'{line[:70]}...')
                elif '📊 total acumulado' in line.lower():
                    send_progress(1, 'running', 78, f'{line[:70]}...')
                elif '➡️  navegando a página' in line.lower():
                    send_progress(1, 'running', 80, f'{line[:70]}...')
                elif '📍' in line:
                    send_progress(1, 'running', 85, f'{line[:70]}...')
                elif '🔍 extrayendo información detallada' in line.lower():
                    send_progress(1, 'running', 82, f'{line[:70]}...')
                elif '🌐' in line and 'visitando:' in line.lower():
                    # Modo detallado visitando producto
                    try:
                        match = re.search(r'\[(\d+)/(\d+)\]', line)
                        if match:
                            current = int(match.group(1))
                            total = int(match.group(2))
                            progress = 82 + int((current / total) * 10)  # 82-92%
                            send_progress(1, 'running', progress, f'{line[:70]}...')
                    except:
                        send_progress(1, 'running', 85, f'{line[:70]}...')
                elif '✔️' in line and 'completado' in line.lower():
                    send_progress(1, 'running', 90, f'{line[:70]}...')
                elif '📋 guardando' in line.lower() or ('json' in line.lower() and 'guardando' in line.lower()):
                    send_progress(1, 'running', 95, f'{line[:70]}...')
                elif line:  # Cualquier otra línea
                    # No cambiar el progreso, solo actualizar mensaje
                    send_progress(1, 'running', None, f'{line[:70]}...')
            
            result.wait()
            
            if result.returncode != 0:
                send_progress(1, 'error', 0, '❌ Error en el scraping')
                return
            
            send_progress(1, 'completed', 100, f'✅ Scraping completado: {num_products} productos extraídos')
            time.sleep(0.5)
            
            # PASO 2: Guardando JSON
            send_progress(2, 'running', 50, '💾 Verificando archivo JSON generado...')
            
            # Construir ruta según la plataforma
            json_path = Path(f"data/extractions/{platform}/{platform}_{search_term.replace(' ', '_')}.json")
            
            if not json_path.exists():
                send_progress(2, 'error', 0, '❌ Archivo JSON no encontrado')
                return
            
            # Leer y validar JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = len(data)
            
            send_progress(2, 'completed', 100, f'✅ JSON creado: {count} productos guardados')
            time.sleep(0.5)
            
            # PASO 3: Subida a PostgreSQL
            send_progress(3, 'running', 0, '🗄️ Conectando a PostgreSQL...')
            time.sleep(0.3)
            
            # Usar PYTHONUNBUFFERED como variable de entorno
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            result = subprocess.Popen(
                ['.venv/bin/python', 'load_dynamic_tables.py'],
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            
            db_progress = 0
            for line in iter(result.stdout.readline, ''):
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Detección mejorada de progreso
                if '🚀 iniciando' in line.lower():
                    db_progress = 10
                    send_progress(3, 'running', db_progress, f'🔄 {line[:70]}...')
                elif '🔍 encontrados' in line.lower():
                    db_progress = 20
                    send_progress(3, 'running', db_progress, f'🔄 {line[:70]}...')
                elif '📂 procesando' in line.lower():
                    db_progress = 30
                    send_progress(3, 'running', db_progress, f'🔄 {line[:70]}...')
                elif 'columnas detectadas' in line.lower():
                    db_progress = 50
                    send_progress(3, 'running', db_progress, f'📊 {line[:70]}...')
                elif 'tabla' in line.lower() and 'creada' in line.lower():
                    db_progress = 70
                    send_progress(3, 'running', db_progress, f'📋 {line[:70]}...')
                elif 'registros insertados' in line.lower():
                    db_progress = 90
                    send_progress(3, 'running', db_progress, f'✅ {line[:70]}...')
                elif '✨ proceso completado' in line.lower():
                    db_progress = 95
                    send_progress(3, 'running', db_progress, f'✨ {line[:70]}...')
                elif line:  # Cualquier otra línea
                    db_progress = min(db_progress + 5, 85)
                    send_progress(3, 'running', db_progress, f'💾 {line[:70]}...')
            
            result.wait()
            
            if result.returncode != 0:
                send_progress(3, 'error', 0, '❌ Error al cargar datos a PostgreSQL')
                return
            
            send_progress(3, 'completed', 100, f'✅ Datos cargados en tabla: amazon_{search_term.replace(" ", "_")}')
            time.sleep(0.5)
            
            # PASO 4: Finalización
            send_progress(4, 'running', 50, '🔄 Actualizando frontend...')
            time.sleep(0.3)
            send_progress(4, 'completed', 100, f'✨ ¡Proceso completado! Tabla "amazon_{search_term.replace(" ", "_")}" lista')
            
            # Señal de finalización
            progress_queues[job_id].put({'complete': True})
            
        except Exception as e:
            send_progress(0, 'error', 0, f'❌ Error general: {str(e)}')
            progress_queues[job_id].put({'complete': True})
    
    # Ejecutar en background
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'Scraping iniciado'
    })


@app.route('/scrape/progress/<job_id>')
def scrape_progress(job_id):
    """Stream de progreso usando Server-Sent Events"""
    def generate():
        if job_id not in progress_queues:
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return
        
        q = progress_queues[job_id]
        
        while True:
            try:
                # Esperar eventos con timeout
                event = q.get(timeout=30)
                
                # Si es señal de finalización, terminar
                if event.get('complete'):
                    # Limpiar cola después de un tiempo
                    threading.Timer(60, lambda: progress_queues.pop(job_id, None)).start()
                    break
                
                # Enviar evento al cliente
                data = f"data: {json.dumps(event)}\n\n"
                yield data
                
            except queue.Empty:
                # Keepalive cada 30 segundos
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response



@app.route('/scrape/status')
def scrape_status():
    """Verifica si hay archivos JSON disponibles"""
    data_path = Path("data/extractions/amazon")
    
    if not data_path.exists():
        return jsonify({'files': []})
    
    json_files = list(data_path.glob("*.json"))
    files_info = []
    
    for file in json_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                files_info.append({
                    'name': file.stem,
                    'count': len(data),
                    'modified': file.stat().st_mtime
                })
        except:
            pass
    
    return jsonify({'files': files_info})


@app.route('/views', methods=['GET'])
def get_views():
    """Obtiene todas las vistas disponibles en la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener todas las vistas del esquema public
        query = """
            SELECT 
                table_name as view_name,
                view_definition
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        views = [{'name': row['view_name'], 'definition': row['view_definition']} for row in results]
        return jsonify({'success': True, 'views': views})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/views/create', methods=['POST'])
def create_view():
    """Crea una nueva vista en la base de datos"""
    try:
        data = request.get_json()
        view_name = data.get('view_name', '').strip()
        query = data.get('query', '').strip()
        
        if not view_name or not query:
            return jsonify({'success': False, 'error': 'Nombre de vista y consulta son requeridos'})
        
        # Validar nombre de vista (solo letras, números y guión bajo)
        if not re.match(r'^[a-z_][a-z0-9_]*$', view_name):
            return jsonify({'success': False, 'error': 'Nombre de vista inválido. Use solo letras minúsculas, números y guión bajo'})
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Crear la vista con CREATE OR REPLACE
        create_query = f"CREATE OR REPLACE VIEW {view_name} AS {query}"
        cursor.execute(create_query)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Vista "{view_name}" creada correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/views/definition/<view_name>', methods=['GET'])
def get_view_definition(view_name):
    """Obtiene la definición SQL de una vista específica"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener la definición de la vista
        query = """
            SELECT view_definition
            FROM information_schema.views
            WHERE table_schema = 'public' AND table_name = %s;
        """
        
        cursor.execute(query, (view_name,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Limpiar la definición (PostgreSQL puede agregar puntos y comas extra)
            definition = result['view_definition'].strip()
            if definition.endswith(';'):
                definition = definition[:-1].strip()
            
            return jsonify({'success': True, 'definition': definition})
        else:
            return jsonify({'success': False, 'error': f'Vista "{view_name}" no encontrada'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/views/drop/<view_name>', methods=['DELETE'])
def drop_view(view_name):
    """Elimina una vista de la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Validar nombre de vista
        if not re.match(r'^[a-z_][a-z0-9_]*$', view_name):
            return jsonify({'success': False, 'error': 'Nombre de vista inválido'})
        
        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Vista "{view_name}" eliminada correctamente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/convert-column-type', methods=['POST'])
def convert_column_type():
    """Crea una nueva columna con tipo numérico a partir de una columna existente"""
    try:
        data = request.get_json()
        column = data.get('column', '').strip()
        new_column_name = data.get('new_column_name', '').strip()
        target_type = data.get('target_type', '').strip()
        tables = data.get('tables', [])
        
        print(f"🔄 Conversión solicitada: {column} → {new_column_name} ({target_type}) en {len(tables)} tablas")
        
        if not column or not new_column_name or not target_type or not tables:
            return jsonify({'success': False, 'error': 'Faltan parámetros requeridos'})
        
        # Validar nombre de columna origen
        if not re.match(r'^[a-z_][a-z0-9_]*$', column):
            return jsonify({'success': False, 'error': 'Nombre de columna origen inválido'})
        
        # Validar nombre de columna destino
        if not re.match(r'^[a-z_][a-z0-9_]*$', new_column_name):
            return jsonify({'success': False, 'error': 'Nombre de columna destino inválido'})
        
        # Validar tipo de dato
        valid_types = ['NUMERIC', 'INTEGER', 'DOUBLE PRECISION']
        if target_type not in valid_types:
            return jsonify({'success': False, 'error': 'Tipo de dato no válido'})
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        successful_conversions = 0
        errors = []
        
        for table in tables:
            try:
                # Validar nombre de tabla (protección SQL injection)
                if not re.match(r'^[a-z_][a-z0-9_]*$', table):
                    errors.append(f'{table}: Nombre de tabla inválido')
                    continue
                
                print(f"  📋 Procesando tabla: {table}")
                
                # Verificar si la columna nueva ya existe
                cursor.execute(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = '{new_column_name}';
                """)
                if cursor.fetchone():
                    errors.append(f'{table}: La columna "{new_column_name}" ya existe')
                    continue
                
                # Paso 1: Crear nueva columna con tipo correcto
                print(f"     ➕ Creando columna {new_column_name} tipo {target_type}")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {new_column_name} {target_type};")
                
                # Paso 2: Copiar datos desde columna original limpiando caracteres no numéricos
                print(f"     🔄 Copiando y limpiando datos desde {column}...")
                update_query = f"""
                    UPDATE {table}
                    SET {new_column_name} = NULLIF(
                        regexp_replace(
                            regexp_replace(CAST({column} AS TEXT), '[^0-9.,-]', '', 'g'),
                            ',', '.', 'g'
                        ), 
                        ''
                    )::{target_type}
                    WHERE {column} IS NOT NULL;
                """
                cursor.execute(update_query)
                
                # ✅ COMMIT INMEDIATO después de cada tabla exitosa
                conn.commit()
                print(f"  ✅ Columna {new_column_name} creada en {table}")
                successful_conversions += 1
                
            except Exception as e:
                error_msg = f'{table}: {str(e)}'
                errors.append(error_msg)
                print(f"  ❌ Error en {table}: {str(e)}")
                conn.rollback()
                # Intentar limpiar columna si existe
                try:
                    cursor.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {new_column_name};")
                    conn.commit()
                except:
                    pass
                continue
        
        conn.close()
        
        if successful_conversions == len(tables):
            return jsonify({
                'success': True,
                'message': f'Columna "{new_column_name}" creada exitosamente en {successful_conversions} tablas'
            })
        elif successful_conversions > 0:
            return jsonify({
                'success': True,
                'message': f'Conversión parcial: {successful_conversions}/{len(tables)} tablas. Errores: {"; ".join(errors)}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'No se pudo crear la columna en ninguna tabla. Errores: {"; ".join(errors)}'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/charts/save', methods=['POST'])
def save_chart():
    """Guarda un gráfico en el servidor"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'chart')
        image_data = data.get('image_data', '')
        format_type = data.get('format', 'png')
        
        if not image_data:
            return jsonify({'success': False, 'error': 'No hay datos de imagen'})
        
        # Validar nombre de archivo
        filename = re.sub(r'[^a-z0-9_-]', '_', filename.lower())
        
        # Generar nombre único con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_filename = f"{filename}_{timestamp}.{format_type}"
        filepath = CHARTS_DIR / final_filename
        
        # Decodificar y guardar imagen
        if image_data.startswith('data:'):
            # Remover el prefijo data:image/png;base64,
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        print(f"📊 Gráfico guardado: {final_filename}")
        
        return jsonify({
            'success': True,
            'filename': final_filename,
            'url': f'/static/charts/{final_filename}',
            'message': f'Gráfico guardado como {final_filename}'
        })
        
    except Exception as e:
        print(f"❌ Error guardando gráfico: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/images/save', methods=['POST'])
def save_image():
    """Guarda una imagen desde URL en el directorio de gráficos"""
    try:
        data = request.get_json()
        image_url = data.get('imageUrl')
        filename = data.get('filename', 'imagen')
        format_type = data.get('format', 'png').lower()
        
        if not image_url:
            return jsonify({'success': False, 'error': 'No se proporcionó URL de imagen'})
        
        # Validar formato
        if format_type not in ['png', 'jpg', 'jpeg', 'svg']:
            return jsonify({'success': False, 'error': 'Formato no soportado'})
        
        # Validar y limpiar nombre de archivo
        filename = re.sub(r'[^a-z0-9_-]', '_', filename.lower())
        
        # Generar nombre único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_filename = f"{filename}_{timestamp}.{format_type}"
        filepath = CHARTS_DIR / final_filename
        
        # Descargar imagen desde URL
        import requests
        from PIL import Image
        from io import BytesIO
        
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Abrir imagen con PIL
        img = Image.open(BytesIO(response.content))
        
        # Convertir a RGB si es necesario (para JPEG)
        if format_type in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
            # Crear fondo blanco
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Guardar en el formato deseado
        if format_type == 'svg':
            # Para SVG, solo copiar el archivo si ya es SVG
            with open(filepath, 'wb') as f:
                f.write(response.content)
        else:
            # Guardar como PNG o JPEG
            save_format = 'JPEG' if format_type in ['jpg', 'jpeg'] else 'PNG'
            img.save(filepath, format=save_format, quality=95 if save_format == 'JPEG' else None)
        
        print(f"🖼️ Imagen guardada: {final_filename}")
        
        return jsonify({
            'success': True,
            'filename': final_filename,
            'url': f'/static/charts/{final_filename}',
            'message': f'Imagen guardada como {final_filename}'
        })
        
    except Exception as e:
        print(f"❌ Error guardando imagen: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/charts/list', methods=['GET'])
def list_charts():
    """Lista todos los gráficos guardados"""
    try:
        charts = []
        
        for file in sorted(CHARTS_DIR.glob('*.*'), key=lambda x: x.stat().st_mtime, reverse=True):
            if file.suffix.lower() in ['.png', '.svg', '.jpg', '.jpeg']:
                stat = file.stat()
                charts.append({
                    'filename': file.name,
                    'url': f'/static/charts/{file.name}',
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'format': file.suffix[1:].upper()
                })
        
        return jsonify({
            'success': True,
            'charts': charts,
            'total': len(charts)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/charts/delete/<filename>', methods=['DELETE'])
def delete_chart(filename):
    """Elimina un gráfico guardado"""
    try:
        # Validar nombre de archivo para prevenir path traversal
        if '..' in filename or '/' in filename:
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'})
        
        filepath = CHARTS_DIR / filename
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'Archivo no encontrado'})
        
        filepath.unlink()
        print(f"🗑️  Gráfico eliminado: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'Gráfico {filename} eliminado correctamente'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("🌐 SQL Frontend iniciado")
    print("📊 Accede a: http://localhost:5000")
    print("💾 Base de datos: scraper (puerto 5434)")
    print(f"📁 Gráficos en: {CHARTS_DIR}")
    app.run(debug=True, host='0.0.0.0', port=5000)
