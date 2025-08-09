import winsound
import sys
import requests
import base64
import os
import time
from datetime import datetime
import traceback
import shutil
import random
import subprocess
import threading
from PIL import Image, ImageDraw, ImageFont
import io
import json
import glob
import urllib3

# Configuración de logging mejorada
def setup_logging():
    """Configura el sistema de logging para capturar todos los errores"""
    log_file = None
    try:
        # Intentar crear el archivo de log con nombre único si hay conflictos
        base_name = "execution_log"
        extension = ".txt"
        counter = 0
        
        while counter < 10:  # Máximo 10 intentos
            if counter == 0:
                log_filename = f"{base_name}{extension}"
            else:
                log_filename = f"{base_name}_{counter}{extension}"
            
            try:
                log_file = open(log_filename, "a", encoding="utf-8")
                print(f"📝 Log configurado: {log_filename}")
                break
            except PermissionError:
                counter += 1
                continue
        
        if log_file is None:
            print("⚠️ No se pudo crear archivo de log, continuando sin logging a archivo")
            return None, sys.stdout, sys.stderr
    
    except Exception as e:
        print(f"⚠️ Error al configurar logging: {e}")
        print("📝 Continuando sin logging a archivo")
        return None, sys.stdout, sys.stderr
    
    class DualOutput:
        def __init__(self, file, terminal):
            self.file = file
            self.terminal = terminal
        
        def write(self, message):
            try:
                if self.file:
                    self.file.write(message)
                    self.file.flush()
            except:
                pass  # Ignorar errores de escritura de archivo
            self.terminal.write(message)
            self.terminal.flush()
        
        def flush(self):
            try:
                if self.file:
                    self.file.flush()
            except:
                pass  # Ignorar errores de flush de archivo
            self.terminal.flush()
    
    # Mantener referencias a stdout/stderr originales
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Configurar salida dual (archivo + consola) solo si tenemos archivo
    if log_file:
        sys.stdout = DualOutput(log_file, original_stdout)
        sys.stderr = DualOutput(log_file, original_stderr)
    
    return log_file, original_stdout, original_stderr

# Configuración
API_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
PIXELDRAIN_UPLOAD = "https://pixeldrain.com/api/file"

# Configuración de Gumroad para venta automática
GUMROAD_CONFIG = {
    "access_token": "",  # Se configurará desde archivo
    "base_price": 5.00,  # Precio base por defecto
    "currency": "eur",   # Moneda por defecto (se actualizará desde archivo)
    "auto_publish": False,  # La API ya no permite auto-publicación
    "enable_pay_what_you_want": True,  # Permitir pagar más
    "min_price": 3.00,  # Precio mínimo si se habilita pay-what-you-want
}

# Configuración de marketplace
ENABLE_GUMROAD_UPLOAD = True   # Cambiar a True cuando tengas configurado Gumroad
CREATE_PREVIEW_IMAGES = True   # Crear imágenes de preview con watermark
PREVIEW_COUNT = 4              # Número de imágenes para el preview

# Configuración de Stable Diffusion WebUI
WEBUI_PATH = r"F:\StableDiffusion\stable-diffusion-webui\webui-user.bat"  # Ajusta esta ruta según tu instalación
WEBUI_STARTUP_WAIT = 180  # Segundos para esperar que WebUI se inicie completamente (aumentado)
WEBUI_CHECK_INTERVAL = 5   # Segundos entre verificaciones de inicio (más frecuente)

# Configuración de comportamiento
AUTO_CLOSE = True  # Cambiar a False si quieres que espere antes de cerrar
CLOSE_DELAY_SUCCESS = 3  # Segundos de espera después del éxito
CLOSE_DELAY_ERROR = 5    # Segundos de espera después de un error

def cleanup_old_logs():
    """Limpia archivos de log antiguos que puedan estar bloqueados"""
    try:
        import glob
        log_files = glob.glob("execution_log*.txt")
        
        for log_file in log_files:
            try:
                # Intentar abrir y cerrar para verificar si está libre
                with open(log_file, "a") as f:
                    pass
            except PermissionError:
                print(f"⚠️ Archivo bloqueado detectado: {log_file}")
                # Intentar renombrar el archivo bloqueado
                try:
                    backup_name = f"{log_file}.backup_{datetime.now().strftime('%H%M%S')}"
                    os.rename(log_file, backup_name)
                    print(f"📁 Archivo renombrado a: {backup_name}")
                except:
                    pass
    except Exception as e:
        print(f"⚠️ Error en limpieza de logs: {e}")

def check_write_permissions():
    """Verifica permisos de escritura en el directorio actual"""
    try:
        test_file = f"test_permissions_{datetime.now().strftime('%H%M%S')}.tmp"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except:
        return False

def setup_working_directory():
    """Configura un directorio de trabajo con permisos de escritura"""
    current_dir = os.getcwd()
    
    # Verificar si el directorio actual tiene permisos
    if check_write_permissions():
        print(f"✅ Directorio actual con permisos: {current_dir}")
        return current_dir
    
    print(f"❌ Sin permisos en directorio actual: {current_dir}")
    
    # Intentar directorios alternativos con permisos
    alternative_dirs = [
        os.path.expanduser("~/Documents/AnimeCarGenerator"),
        os.path.expanduser("~/Desktop/AnimeCarGenerator"),
        os.path.join(os.environ.get("USERPROFILE", ""), "AnimeCarGenerator"),
        os.path.join(os.environ.get("TEMP", ""), "AnimeCarGenerator"),
        "C:/temp/AnimeCarGenerator"
    ]
    
    for alt_dir in alternative_dirs:
        try:
            # Crear directorio si no existe
            os.makedirs(alt_dir, exist_ok=True)
            
            # Cambiar al directorio
            os.chdir(alt_dir)
            
            # Verificar permisos
            if check_write_permissions():
                print(f"✅ Cambiado a directorio con permisos: {alt_dir}")
                create_directory_info(alt_dir)
                return alt_dir
            else:
                print(f"❌ Sin permisos en: {alt_dir}")
                
        except Exception as e:
            print(f"❌ Error accediendo a {alt_dir}: {e}")
            continue
    
    # Si llegamos aquí, no encontramos ningún directorio con permisos
    print("❌ No se encontró ningún directorio con permisos de escritura")
    print("💡 Soluciones posibles:")
    print("   1. Ejecutar como administrador")
    print("   2. Mover el script a la carpeta de Documentos")
    print("   3. Mover el script al Escritorio")
    print("   4. Crear manualmente la carpeta C:/temp/AnimeCarGenerator")
    return None

def create_directory_info(work_dir):
    """Crea un archivo de información en el directorio de trabajo"""
    try:
        info_file = os.path.join(work_dir, "README_DirectorioTrabajo.txt")
        with open(info_file, "w", encoding="utf-8") as f:
            f.write("🚗 ANIME CAR GENERATOR - DIRECTORIO DE TRABAJO\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"📅 Creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"📂 Ubicación: {work_dir}\n\n")
            f.write("📁 ESTRUCTURA DE CARPETAS:\n")
            f.write("├── packs/                    # Imágenes generadas (solo carpetas)\n")
            f.write("├── previews/                # Previews de cada pack\n")
            f.write("├── prompt_backups/          # Respaldos diarios de prompts\n")
            f.write("├── prompts.txt              # Prompts del día actual\n")
            f.write("└── execution_log.txt        # Log de ejecución\n\n")
            f.write("ℹ️  INFORMACIÓN:\n")
            f.write("• Los prompts se regeneran automáticamente cada día\n")
            f.write("• Las imágenes se organizan en packs de 8 unidades (SIN ZIP)\n")
            f.write("• Solo se crean carpetas con imágenes PNG\n")
            f.write("• Todos los logs y respaldos se guardan aquí\n")
        print(f"📄 Archivo de información creado: {info_file}")
    except Exception as e:
        print(f"⚠️ No se pudo crear archivo de información: {e}")

def ensure_webui_api_enabled():
    """Verifica y habilita la API en webui-user.bat si es necesario"""
    try:
        webui_bat = find_webui_path()
        if not webui_bat:
            print("❌ No se encontró webui-user.bat")
            return False
        
        print("🔍 Verificando configuración de API en webui-user.bat...")
        
        # Leer el archivo actual
        with open(webui_bat, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar si ya tiene --api habilitado
        if '--api' in content:
            print("✅ API ya está habilitada en webui-user.bat")
            return True
        
        print("⚠️ API no está habilitada, configurando automáticamente...")
        
        # Buscar la línea COMMANDLINE_ARGS y modificarla
        lines = content.split('\n')
        modified = False
        
        for i, line in enumerate(lines):
            if line.strip().startswith('set COMMANDLINE_ARGS='):
                # Extraer argumentos existentes
                existing_args = line.split('=', 1)[1].strip()
                if existing_args:
                    # Agregar --api a argumentos existentes
                    new_args = f"{existing_args} --api"
                else:
                    # Solo agregar --api
                    new_args = "--api"
                
                lines[i] = f"set COMMANDLINE_ARGS={new_args}"
                modified = True
                print(f"✅ Modificado: {lines[i]}")
                break
        
        if not modified:
            print("⚠️ No se encontró línea COMMANDLINE_ARGS, agregándola...")
            # Buscar dónde insertar la línea
            insert_pos = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('call webui.bat'):
                    insert_pos = i
                    break
            
            if insert_pos > 0:
                lines.insert(insert_pos, "set COMMANDLINE_ARGS=--api")
                modified = True
                print("✅ Agregada línea: set COMMANDLINE_ARGS=--api")
        
        if modified:
            # Crear respaldo del archivo original
            backup_path = f"{webui_bat}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"💾 Respaldo creado: {backup_path}")
            
            # Escribir el archivo modificado
            with open(webui_bat, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print("✅ webui-user.bat actualizado para habilitar API")
            print("⚠️ Necesitarás reiniciar el WebUI para que los cambios surtan efecto")
            return True
        else:
            print("❌ No se pudo modificar webui-user.bat")
            return False
    
    except Exception as e:
        print(f"❌ Error al configurar API: {e}")
        return False

def restart_webui_with_api():
    """Reinicia WebUI con API habilitada"""
    print("🔄 Reiniciando WebUI con API habilitada...")
    
    # Intentar cerrar procesos existentes de WebUI
    try:
        print("🛑 Cerrando procesos existentes de WebUI...")
        result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/T'], 
                              capture_output=True, text=True)
        time.sleep(3)  # Esperar a que se cierren
        print("✅ Procesos cerrados")
    except Exception as e:
        print(f"⚠️ Error cerrando procesos: {e}")
    
    # Iniciar WebUI nuevamente
    print("🚀 Iniciando WebUI con API habilitada...")
    process = start_webui()
    if process:
        print("✅ WebUI reiniciado")
        return process
    else:
        print("❌ Error al reiniciar WebUI")
        return None

def find_webui_path():
    """Busca automáticamente el archivo webui-user.bat"""
    possible_paths = [
        WEBUI_PATH,  # Ruta configurada
        r"F:\StableDiffusion\stable-diffusion-webui\webui-user.bat",
        r"C:\stable-diffusion-webui\webui-user.bat",
        r".\stable-diffusion-webui\webui-user.bat",
        r"..\stable-diffusion-webui\webui-user.bat"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ WebUI encontrado en: {path}")
            return path
    
    print("❌ No se encontró webui-user.bat en las ubicaciones esperadas")
    print("📍 Rutas verificadas:")
    for path in possible_paths:
        print(f"   - {path}")
    return None

def is_webui_running():
    """Verifica si WebUI ya está ejecutándose"""
    try:
        # Primero verificar el endpoint de samplers (más ligero)
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/samplers", timeout=10)
        if response.status_code == 200:
            # Verificación adicional del endpoint principal
            response2 = requests.get("http://127.0.0.1:7860/sdapi/v1/options", timeout=5)
            return response2.status_code == 200
        return False
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        print("⚠️ Timeout en verificación - WebUI puede estar iniciando...")
        return False
    except Exception as e:
        print(f"⚠️ Error en verificación: {e}")
        return False

def start_webui():
    """Inicia Stable Diffusion WebUI en segundo plano"""
    webui_path = find_webui_path()
    if not webui_path:
        return None
    
    try:
        print("🚀 Iniciando Stable Diffusion WebUI...")
        print(f"📂 Ejecutando: {webui_path}")
        
        # Cambiar al directorio del WebUI
        webui_dir = os.path.dirname(webui_path)
        
        # Iniciar el proceso en segundo plano
        process = subprocess.Popen(
            [webui_path],
            cwd=webui_dir,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        print(f"✅ WebUI iniciado (PID: {process.pid})")
        print("⏳ Esperando que el servidor esté listo...")
        
        return process
    
    except Exception as e:
        print(f"❌ Error al iniciar WebUI: {e}")
        return None

def wait_for_webui_ready(max_wait=WEBUI_STARTUP_WAIT):
    """Espera a que WebUI esté completamente iniciado"""
    print(f"⏳ Esperando hasta {max_wait} segundos para que WebUI esté listo...")
    
    for i in range(0, max_wait, WEBUI_CHECK_INTERVAL):
        try:
            if is_webui_running():
                print("✅ WebUI está listo y responde correctamente")
                # Verificación adicional para asegurar estabilidad
                time.sleep(3)
                if is_webui_running():
                    return True
                else:
                    print("⚠️ WebUI respondió pero se volvió inestable, esperando más...")
        except Exception as e:
            print(f"🔄 Verificando conexión... Error: {e}")
        
        remaining = max_wait - i
        print(f"🔄 Verificando conexión... ({remaining}s restantes)")
        time.sleep(WEBUI_CHECK_INTERVAL)
    
    print(f"❌ WebUI no respondió después de {max_wait} segundos")
    print("💡 Posibles soluciones:")
    print("   - El WebUI puede estar descargando modelos (primera ejecución)")
    print("   - Verifica que no haya errores en la consola del WebUI")
    print("   - Asegúrate de tener suficiente espacio en disco")
    print("   - Revisa que los modelos estén en la carpeta correcta")
    return False

def ensure_webui_running():
    """Asegura que WebUI esté ejecutándose, iniciándolo si es necesario"""
    print("🔍 Verificando estado de Stable Diffusion WebUI...")
    
    if is_webui_running():
        print("✅ WebUI ya está ejecutándose")
        return True
    
    print("⚠️ WebUI no está ejecutándose, iniciando automáticamente...")
    
    process = start_webui()
    if not process:
        print("❌ No se pudo iniciar WebUI automáticamente")
        return False
    
    # Esperar a que esté listo
    print(f"⏳ Esperando inicialización completa del WebUI...")
    print(f"💡 Esto puede tomar varios minutos si es la primera ejecución")
    print(f"📱 Puedes revisar el progreso en la ventana de la consola del WebUI")
    
    if wait_for_webui_ready():
        print("🎉 WebUI iniciado exitosamente y listo para usar")
        return True
    else:
        print("❌ WebUI no se inició correctamente en el tiempo esperado")
        print("🔍 Verificando si el proceso aún está ejecutándose...")
        
        # Verificar si el proceso aún existe
        try:
            if process.poll() is None:
                print("✅ El proceso WebUI aún está ejecutándose")
                print("⚠️ Puede que necesite más tiempo para cargar")
                print("💡 Opciones:")
                print("   1. Esperar más tiempo y ejecutar el script nuevamente")
                print("   2. Verificar la consola del WebUI para errores")
                print("   3. Verificar que tienes modelos instalados")
                return False
            else:
                print("❌ El proceso WebUI se cerró inesperadamente")
                return False
        except:
            print("⚠️ No se pudo verificar el estado del proceso")
            return False

def check_webui_models():
    """Verifica si hay modelos disponibles en WebUI"""
    try:
        print("🔍 Verificando modelos disponibles...")
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=10)
        if response.status_code == 200:
            models = response.json()
            if models:
                print(f"✅ {len(models)} modelo(s) encontrado(s):")
                for model in models[:3]:  # Mostrar solo los primeros 3
                    model_name = model.get('title', 'Desconocido')
                    print(f"   - {model_name}")
                if len(models) > 3:
                    print(f"   ... y {len(models) - 3} más")
                return True
            else:
                print("❌ No se encontraron modelos")
                print("💡 Descargar un modelo (ej: v1-5-pruned-emaonly.safetensors)")
                print("   y colocarlo en: models/Stable-diffusion/")
                return False
        else:
            print(f"⚠️ No se pudo verificar modelos (código: {response.status_code})")
            return False
    except Exception as e:
        print(f"⚠️ Error verificando modelos: {e}")
        return False

def provide_troubleshooting_tips():
    """Proporciona consejos detallados de solución de problemas"""
    print("\n" + "="*60)
    print("🔧 GUÍA DE SOLUCIÓN DE PROBLEMAS")
    print("="*60)
    print("\n📋 PASOS RECOMENDADOS:")
    print("\n1. � VERIFICAR API HABILITADA:")
    print("   • El problema más común es que la API no está habilitada")
    print("   • Este script puede configurarlo automáticamente")
    print("   • Manual: edita webui-user.bat y agrega --api a COMMANDLINE_ARGS")
    
    print("\n2. �🖥️ VERIFICAR CONSOLA DEL WEBUI:")
    print("   • Busca la ventana negra que se abrió con webui-user.bat")
    print("   • Lee los mensajes para ver si hay errores o descargas en progreso")
    print("   • Si dice 'Downloading...', espera a que termine")
    
    print("\n3. 📁 VERIFICAR MODELOS:")
    webui_models_path = os.path.join(os.path.dirname(WEBUI_PATH), "models", "Stable-diffusion")
    print(f"   • Ve a: {webui_models_path}")
    print("   • Debe haber al menos un archivo .safetensors o .ckpt")
    print("   • Si está vacío, descarga un modelo desde:")
    print("     https://huggingface.co/stabilityai/stable-diffusion-2-1")
    
    print("\n3. 💾 VERIFICAR RECURSOS:")
    print("   • RAM: Mínimo 8GB, recomendado 16GB+")
    print("   • VRAM: Mínimo 4GB, recomendado 8GB+")
    print("   • Espacio: Al menos 10GB libres")
    
    print("\n4. 🔄 REINICIAR WEBUI:")
    print("   • Cierra la ventana del WebUI (Ctrl+C)")
    print("   • Ejecuta webui-user.bat nuevamente")
    print("   • Espera hasta ver 'Running on local URL: http://127.0.0.1:7860'")
    
    print("\n5. 🌐 VERIFICAR MANUALMENTE:")
    print("   • Abre navegador web")
    print("   • Ve a: http://127.0.0.1:7860")
    print("   • Si aparece la interfaz, la API debería funcionar pronto")
    
    print("\n❓ PROBLEMAS COMUNES:")
    print("   • 'API not enabled': Falta --api en webui-user.bat")
    print("   • 'CUDA out of memory': Reduce resolución o usa --lowvram")
    print("   • 'No module named': Reinstala dependencias")
    print("   • 'Model not found': Verifica carpeta de modelos")
    print("   • Puerto ocupado: Cambia puerto en webui-user.bat")
    print("="*60)

def check_api_connection():
    """Verifica que la API de Stable Diffusion esté disponible y la inicia si es necesario"""
    try:
        print("🔄 Verificando conexión con Stable Diffusion API...")
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/samplers", timeout=8)
        if response.status_code == 200:
            print("✅ API de Stable Diffusion disponible")
            # Verificación rápida de modelos sin timeout largo
            try:
                models_check = requests.get("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=3)
                if models_check.status_code == 200 and models_check.json():
                    print("🎉 WebUI completamente configurado y listo")
                else:
                    print("⚠️ API disponible, continuando...")
            except:
                print("⚠️ API disponible, continuando...")
            return True
        elif response.status_code == 404:
            print("⚠️ WebUI responde pero API no está lista")
            print("💡 Modo emergencia: iniciando generación directa...")
            
            # Modo emergencia: intentar generar directamente sin verificaciones extensas
            print("� Saltando verificaciones adicionales...")
            return True
        else:
            print(f"❌ API responde con código: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar a la API de Stable Diffusion")
        print("� Asegúrate de que WebUI esté ejecutándose en: http://127.0.0.1:7860")
        print("🚀 Para iniciarlo manualmente ejecuta: webui-user.bat")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al verificar API: {e}")
        return False
def provide_manual_instructions():
    """Proporciona instrucciones detalladas para iniciar WebUI manualmente"""
    print("\n" + "="*60)
    print("🔧 INSTRUCCIONES PARA INICIO MANUAL DE WEBUI")
    print("="*60)
    print("1. 📂 Abre el Explorador de archivos y ve a:")
    print(f"   {os.path.dirname(WEBUI_PATH)}")
    print("\n2. 🔄 Ejecuta el archivo:")
    print("   webui-user.bat")
    print("\n3. ⏳ Espera a ver estos mensajes en la consola:")
    print("   - 'Installing requirements...' (primera vez)")
    print("   - 'Loading weights...'")
    print("   - 'Model loaded in X seconds'")
    print("   - 'Running on local URL: http://127.0.0.1:7860'")
    print("\n4. 🌐 Opcional: Abre tu navegador y ve a:")
    print("   http://127.0.0.1:7860")
    print("   Para verificar que la interfaz web funciona")
    print("\n5. 🔄 Una vez que veas 'Running on local URL', ejecuta este script nuevamente")
    print("\n💡 CONSEJOS:")
    print("   - La primera ejecución puede tardar 10-20 minutos descargando modelos")
    print("   - Asegúrate de tener al menos 8GB de espacio libre")
    print("   - Si hay errores, revisa que tienes una GPU compatible")
    print("   - Mantén la ventana del WebUI abierta mientras usas este script")
    print("="*60)

def wait_for_manual_start():
    """Espera a que el usuario inicie WebUI manualmente"""
    provide_manual_instructions()
    
    print("\n🔄 Esperando a que inicies WebUI manualmente...")
    print("⏹️  Presiona Ctrl+C para cancelar")
    
    try:
        max_wait = 600  # 10 minutos máximo
        for i in range(0, max_wait, 10):
            if is_webui_running():
                print("\n✅ ¡WebUI detectado y funcionando!")
                return True
            
            remaining = max_wait - i
            print(f"🔄 Verificando cada 10 segundos... ({remaining//60}min {remaining%60}s restantes)")
            time.sleep(10)
        
        print(f"\n⏰ Tiempo de espera agotado ({max_wait//60} minutos)")
        return False
    
    except KeyboardInterrupt:
        print("\n⚠️ Cancelado por el usuario")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al verificar API: {e}")
        return False

def generate_daily_prompts():
    """Genera prompts únicos para el día actual basados en la fecha"""
    # Usar la fecha como semilla para generar prompts consistentes cada día
    today = datetime.now().strftime("%Y%m%d")
    random.seed(int(today))
    
    # Elementos base para construir prompts variados
    car_types = [
        "sports car", "racing car", "convertible", "sedan", "coupe", "hatchback",
        "supercar", "muscle car", "vintage car", "concept car", "drift car",
        "rally car", "street racer", "luxury car", "compact car", "roadster"
    ]
    
    anime_styles = [
        "anime style", "kawaii style", "chibi style", "manga style", "moe style",
        "shounen style", "shoujo style", "mecha anime style", "slice of life anime",
        "cyberpunk anime", "fantasy anime", "magical girl style", "90s anime style"
    ]
    
    colors = [
        "neon blue", "hot pink", "electric purple", "lime green", "sunset orange",
        "cherry red", "midnight black", "pearl white", "galaxy purple", "cyan blue",
        "golden yellow", "rose gold", "silver metallic", "matte black", "rainbow holographic"
    ]
    
    environments = [
        "Tokyo streets at night", "cherry blossom avenue", "cyberpunk city",
        "mountain pass", "beach sunset", "neon-lit tunnel", "anime school courtyard",
        "futuristic highway", "traditional Japanese village", "space station garage",
        "rain-soaked streets", "festival fireworks background", "autumn forest road"
    ]
    
    details = [
        "with LED underglow", "with flame decals", "with cute mascot decorations",
        "with holographic panels", "with racing stripes", "with anime girl livery",
        "with glowing rims", "with spoiler wing", "with custom bodykit",
        "with kawaii stickers", "with dragon artwork", "with galaxy paint job",
        "with carbon fiber details", "with chrome accents", "with tribal designs"
    ]
    
    moods = [
        "dynamic action pose", "peaceful parked scene", "high-speed motion blur",
        "dramatic lighting", "soft pastel lighting", "vibrant colors",
        "moody atmospheric", "bright and cheerful", "mysterious night scene",
        "energetic racing scene", "serene morning light", "festival celebration"
    ]
    
    # Generar 50 prompts únicos para el día
    prompts = []
    for i in range(50):
        # Seleccionar elementos aleatorios
        car = random.choice(car_types)
        style = random.choice(anime_styles)
        color = random.choice(colors)
        environment = random.choice(environments)
        detail = random.choice(details)
        mood = random.choice(moods)
        
        # Construir prompt con estructura variada
        prompt_structures = [
            f"{style}, {car} {detail}, {color} colors, {environment}, {mood}",
            f"{car} in {style}, {environment}, {detail}, {mood}, {color} theme",
            f"{mood} {style} {car}, {environment} background, {detail}, {color} accents",
            f"{color} {car} with {style} design, {environment}, {detail}, {mood}",
            f"{style} {car}, {detail}, {environment}, {color} lighting, {mood}"
        ]
        
        prompt = random.choice(prompt_structures)
        prompts.append(prompt)
    
    # Añadir algunos prompts especiales temáticos
    special_prompts = [
        "anime maid cafe themed car, pink and white colors, cute decorations, kawaii style",
        "samurai warrior car, traditional Japanese design, katana decorations, honor theme",
        "magical girl transformation car, sparkles and ribbons, pastel rainbow colors",
        "giant robot pilot car, mecha anime style, cockpit design, futuristic",
        "shrine maiden car, red and white colors, traditional Japanese elements",
        "ninja stealth car, dark colors, shadow effects, mysterious aura",
        "idol singer car, stage lights, microphone decorations, pop star theme",
        "school festival car, student decorations, youth energy, colorful banners"
    ]
    
    # Añadir prompts especiales al conjunto
    prompts.extend(random.sample(special_prompts, 8))
    
    return prompts

def should_regenerate_prompts(file_path="prompts.txt"):
    """Verifica si se deben regenerar los prompts basado en la fecha"""
    if not os.path.exists(file_path):
        return True
    
    # Verificar la fecha de modificación del archivo
    try:
        mod_time = os.path.getmtime(file_path)
        file_date = datetime.fromtimestamp(mod_time).strftime("%Y%m%d")
        today = datetime.now().strftime("%Y%m%d")
        
        # Regenerar si el archivo no es de hoy
        return file_date != today
    except:
        return True

def backup_daily_prompts(prompts):
    """Crea una copia de respaldo de los prompts del día"""
    try:
        # Crear carpeta de respaldos si no existe
        backup_dir = "prompt_backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Crear archivo de respaldo con fecha
        today = datetime.now().strftime("%Y%m%d")
        backup_file = os.path.join(backup_dir, f"prompts_{today}.txt")
        
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(f"# Prompts generados para {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"# Total: {len(prompts)} prompts únicos\n\n")
            f.write("\n".join(prompts))
        
        print(f"💾 Respaldo guardado: {backup_file}")
        return backup_file
    
    except Exception as e:
        print(f"⚠️ No se pudo crear respaldo: {e}")
        return None

def load_prompts(file_path="prompts.txt"):
    """Carga los prompts desde archivo con generación automática diaria"""
    try:
        # Verificar si necesitamos regenerar prompts para hoy
        if should_regenerate_prompts(file_path):
            print("🔄 Generando nuevos prompts para hoy...")
            new_prompts = generate_daily_prompts()
            
            # Guardar los nuevos prompts
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_prompts))
            
            today = datetime.now().strftime("%Y-%m-%d")
            print(f"✅ Generados {len(new_prompts)} prompts únicos para {today}")
            print(f"📝 Guardados en {file_path}")
            
            # Crear respaldo de los prompts del día
            backup_daily_prompts(new_prompts)
            
            return new_prompts
        
        # Cargar prompts existentes si son del día actual
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                prompts = [line.strip() for line in f if line.strip()]
            
            if prompts:
                print(f"✅ Cargados {len(prompts)} prompts del día actual desde {file_path}")
                return prompts
        
        # Fallback: crear prompts por defecto si algo falla
        print(f"⚠️ Creando prompts por defecto...")
        default_prompts = generate_daily_prompts()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(default_prompts))
        print(f"✅ Creados {len(default_prompts)} prompts por defecto")
        backup_daily_prompts(default_prompts)
        return default_prompts
    
    except Exception as e:
        print(f"❌ Error al cargar/generar prompts: {e}")
        traceback.print_exc()
        return []

def test_api_with_different_params():
    """Prueba la API con diferentes configuraciones para encontrar qué funciona"""
    test_configs = [
        {
            "name": "Mínimo absoluto",
            "payload": {
                "prompt": "realistic anime style car, detailed automotive design, photorealistic car",
                "negative_prompt": "toy car, plastic toy, miniature car, no car, no vehicle, abstract art, person, human, animal",
                "steps": 20,
                "cfg_scale": 7.5,
                "width": 1024,
                "height": 1024,
                "sampler_name": "Euler a"
            }
        },
        {
            "name": "Básico simple", 
            "payload": {
                "prompt": "realistic anime style car, detailed red sports car, photorealistic automotive design",
                "negative_prompt": "toy car, plastic toy, miniature car, toy-like, no car, no vehicle, abstract art, person, human, animal, building only",
                "steps": 22,
                "cfg_scale": 7.5,
                "width": 1152,
                "height": 1152,
                "sampler_name": "Euler a"
            }
        },
        {
            "name": "Estándar reducido",
            "payload": {
                "prompt": "realistic anime style car, detailed automotive design, photorealistic car, professional car photography style, high detail car body",
                "negative_prompt": "toy car, plastic toy, miniature car, toy-like, childish, no car, no vehicle, abstract art, person, human, animal, building only, landscape only",
                "steps": 25,
                "cfg_scale": 7.5,
                "width": 1280,
                "height": 1280,
                "sampler_name": "Euler a"
            }
        }
    ]
    
    for config in test_configs:
        try:
            print(f"🧪 Probando: {config['name']}")
            response = requests.post(API_URL, json=config['payload'], timeout=30)
            
            if response.status_code == 200:
                print(f"✅ {config['name']} - FUNCIONA!")
                return config['payload']
            else:
                print(f"❌ {config['name']} - Error {response.status_code}")
                
        except Exception as e:
            print(f"❌ {config['name']} - Excepción: {e}")
    
    print("❌ Ninguna configuración funciona")
    return None

def get_webui_info():
    """Obtiene información detallada del WebUI para diagnóstico"""
    try:
        print("🔍 Obteniendo información del WebUI...")
        
        # Información de samplers disponibles
        try:
            response = requests.get("http://127.0.0.1:7860/sdapi/v1/samplers", timeout=10)
            if response.status_code == 200:
                samplers = response.json()
                print(f"📋 Samplers disponibles: {len(samplers)}")
                if samplers:
                    print(f"   Primer sampler: {samplers[0].get('name', 'Desconocido')}")
        except Exception as e:
            print(f"⚠️ No se pudo obtener lista de samplers: {e}")
        
        # Información del modelo actual
        try:
            response = requests.get("http://127.0.0.1:7860/sdapi/v1/options", timeout=10)
            if response.status_code == 200:
                options = response.json()
                current_model = options.get('sd_model_checkpoint', 'Desconocido')
                print(f"🎯 Modelo actual: {current_model}")
        except Exception as e:
            print(f"⚠️ No se pudo obtener modelo actual: {e}")
        
        # Información de scripts
        try:
            response = requests.get("http://127.0.0.1:7860/sdapi/v1/scripts", timeout=10)
            if response.status_code == 200:
                scripts = response.json()
                print(f"🔧 Scripts disponibles: {len(scripts.get('txt2img', []))}")
        except Exception as e:
            print(f"⚠️ No se pudo obtener información de scripts: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo información del WebUI: {e}")
        return False

def test_api_with_simple_prompt():
    """Prueba la API con un prompt simple para diagnosticar problemas"""
    try:
        print("🔧 Probando API con prompt simple...")
        
        simple_payload = {
            "prompt": "realistic anime style car, detailed automotive design, photorealistic car, simple car design",
            "negative_prompt": "toy car, plastic toy, miniature car, toy-like, no car, no vehicle, abstract art, person, human, animal, text, watermark",
            "sampler_name": "Euler a",
            "steps": 20,
            "cfg_scale": 7.5,
            "width": 1024,
            "height": 1024,
            "seed": -1
        }
        
        response = requests.post(API_URL, json=simple_payload, timeout=60)
        
        if response.status_code == 200:
            print("✅ API funciona correctamente con parámetros simples")
            return True
        else:
            print(f"❌ API falla incluso con parámetros simples: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en prueba de API: {e}")
        return False

def try_model_reload():
    """Intenta recargar el modelo actual para solucionar errores 500"""
    try:
        print("🔄 Intentando recargar el modelo actual...")
        
        # Obtener modelo actual
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/options", timeout=10)
        if response.status_code == 200:
            options = response.json()
            current_model = options.get('sd_model_checkpoint', '')
            print(f"📋 Modelo actual: {current_model}")
            
            if current_model:
                # Forzar recarga del mismo modelo
                reload_payload = {"sd_model_checkpoint": current_model}
                reload_response = requests.post(
                    "http://127.0.0.1:7860/sdapi/v1/options",
                    json=reload_payload,
                    timeout=30
                )
                
                if reload_response.status_code == 200:
                    print("✅ Modelo recargado exitosamente")
                    # Esperar a que se complete la recarga
                    time.sleep(10)
                    return True
                else:
                    print(f"❌ Error recargando modelo: {reload_response.status_code}")
                    return False
            else:
                print("❌ No se pudo obtener el modelo actual")
                return False
        else:
            print("❌ No se pudo acceder a la configuración")
            return False
            
    except Exception as e:
        print(f"❌ Error al recargar modelo: {e}")
        return False

def try_different_models():
    """Intenta usar diferentes modelos disponibles para solucionar errores 500"""
    try:
        print("🔍 Buscando modelos alternativos...")
        
        # Obtener lista de modelos disponibles
        response = requests.get("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=15)
        if response.status_code == 200:
            models = response.json()
            print(f"📋 {len(models)} modelo(s) disponible(s)")
            
            for model in models:
                model_name = model.get('title', 'Desconocido')
                model_filename = model.get('filename', model.get('model_name', ''))
                
                print(f"🧪 Probando modelo: {model_name}")
                
                # Cambiar al modelo
                change_payload = {"sd_model_checkpoint": model_filename}
                change_response = requests.post(
                    "http://127.0.0.1:7860/sdapi/v1/options",
                    json=change_payload,
                    timeout=60
                )
                
                if change_response.status_code == 200:
                    print(f"✅ Cambiado a modelo: {model_name}")
                    # Esperar a que se cargue el modelo
                    time.sleep(15)
                    
                    # Probar generación simple
                    test_payload = {
                        "prompt": "realistic anime style car, detailed automotive design, test car",
                        "negative_prompt": "toy car, plastic toy, miniature car, no car, abstract art, person",
                        "steps": 20,
                        "cfg_scale": 7.5,
                        "width": 1024,
                        "height": 1024,
                        "sampler_name": "Euler a"
                    }
                    
                    test_response = requests.post(API_URL, json=test_payload, timeout=30)
                    if test_response.status_code == 200:
                        print(f"🎉 ¡Modelo {model_name} funciona!")
                        return model_filename
                    else:
                        print(f"❌ Modelo {model_name} también falla")
                else:
                    print(f"❌ No se pudo cambiar a {model_name}")
            
            print("❌ Ningún modelo funciona")
            return None
        else:
            print("❌ No se pudo obtener lista de modelos")
            return None
            
    except Exception as e:
        print(f"❌ Error probando modelos: {e}")
        return None

def emergency_webui_recovery():
    """Intenta soluciones de emergencia para recuperar el WebUI"""
    print("🚨 MODO DE RECUPERACIÓN DE EMERGENCIA")
    print("="*50)
    
    # 1. Intentar recargar modelo actual
    print("1️⃣ Intentando recargar modelo actual...")
    if try_model_reload():
        # Probar si funciona
        test_payload = {
            "prompt": "realistic anime style car, detailed automotive design, test car",
            "negative_prompt": "toy car, plastic toy, miniature car, no car, abstract art, person",
            "steps": 20,
            "cfg_scale": 7.5,
            "width": 1024,
            "height": 1024,
            "sampler_name": "Euler a"
        }
        
        try:
            test_response = requests.post(API_URL, json=test_payload, timeout=20)
            if test_response.status_code == 200:
                print("✅ Recarga del modelo solucionó el problema!")
                return True
        except:
            pass
    
    # 2. Intentar modelos alternativos
    print("2️⃣ Probando modelos alternativos...")
    working_model = try_different_models()
    if working_model:
        print(f"✅ Modelo funcional encontrado: {working_model}")
        return True
    
    # 3. Información para reinicio manual
    print("3️⃣ Requiere intervención manual:")
    print("   💡 ACCIONES RECOMENDADAS:")
    print("   1. 🛑 Cerrar WebUI (Ctrl+C en su consola)")
    print("   2. 🔄 Reiniciar webui-user.bat")
    print("   3. ⏳ Esperar hasta ver 'Running on local URL'")
    print("   4. 🚀 Ejecutar este script nuevamente")
    print()
    print("   🔍 SI EL PROBLEMA PERSISTE:")
    print("   • Revisar logs detallados en la consola del WebUI")
    print("   • Verificar que el modelo no esté corrupto")
    print("   • Considerar usar un modelo diferente")
    print("   • Verificar configuración de CUDA/GPU")
    
    return False

def check_webui_health():
    """Verifica el estado de salud del WebUI y sugiere soluciones"""
    try:
        print("🏥 Verificando salud del WebUI...")
        
        # Obtener información detallada del WebUI
        get_webui_info()
        
        # Verificar información del sistema
        try:
            response = requests.get("http://127.0.0.1:7860/sdapi/v1/memory", timeout=10)
            if response.status_code == 200:
                memory_info = response.json()
                print(f"💾 Memoria: {memory_info}")
        except:
            print("⚠️ No se pudo obtener información de memoria")
        
        # Verificar configuración
        try:
            response = requests.get("http://127.0.0.1:7860/sdapi/v1/options", timeout=10)
            if response.status_code == 200:
                print("✅ Configuración del WebUI accesible")
            else:
                print("⚠️ No se pudo acceder a la configuración")
        except:
            print("⚠️ Error accediendo a configuración del WebUI")
        
        # Probar con diferentes configuraciones
        print("🧪 Probando diferentes configuraciones...")
        working_config = test_api_with_different_params()
        
        if working_config:
            print("✅ Encontrada configuración que funciona!")
            return working_config
        else:
            print("❌ Ninguna configuración funciona - iniciando recuperación de emergencia")
            
            # Intentar recuperación automática
            if emergency_webui_recovery():
                print("🎉 Recuperación exitosa - probando nuevamente...")
                # Probar una vez más después de la recuperación
                working_config = test_api_with_different_params()
                if working_config:
                    return working_config
            
            print("❌ Problema crítico del WebUI - requiere intervención manual")
            return False
        
    except Exception as e:
        print(f"❌ Error verificando salud del WebUI: {e}")
        return False

def generate_image(prompt, working_config=None):
    """Genera una imagen usando la API de Stable Diffusion con configuración adaptativa"""
    try:
        # Prompt mejorado para coches más realistas (no juguetes)
        enhanced_prompt = f"realistic anime style car, detailed automotive design, photorealistic car, {prompt}, high detail car body, realistic car proportions, professional car photography style, detailed car interior, realistic wheels and tires, automotive artwork, car illustration, detailed metallic paint, realistic car lighting, high quality car render"
        
        # Negative prompt MUY FUERTE para evitar aspecto de juguete
        enhanced_negative = "toy car, plastic toy, miniature car, toy-like, childish, cartoon style, simple car, low detail, flat colors, no car, no vehicle, no automobile, abstract art, abstract shapes, geometric patterns, landscape only, building only, architecture, person, human, face, body, animal, creature, food, plant, flower, sky only, clouds only, text, watermark, lowres, blurry, bad quality, portrait, character, anime character, girl, boy, woman, man, people, toy, plastic, miniature"
        
        # Usar configuración que sabemos que funciona, o configuración por defecto
        if working_config:
            print("🎯 Usando configuración probada que funciona")
            payload = working_config.copy()
            payload["prompt"] = enhanced_prompt
            payload["negative_prompt"] = enhanced_negative
        else:
            # Configuración equilibrada: calidad alta pero eficiente
            payload = {
                "prompt": enhanced_prompt,
                "negative_prompt": enhanced_negative,
                "sampler_name": "Euler a",
                "steps": 22,
                "cfg_scale": 7.5,
                "width": 1152,
                "height": 1152,
                "seed": -1,
                "batch_size": 1,
                "n_iter": 1
            }
        
        print(f"🎨 Generando: {prompt[:50]}...")
        print(f"🔥 PROMPT COMPLETO: {enhanced_prompt}")
        print(f"❌ NEGATIVE PROMPT: {enhanced_negative}")
        print(f"   📐 Configuración: {payload['width']}x{payload['height']}, {payload['steps']} pasos, CFG {payload['cfg_scale']}")
        
        # Intentar con timeout más largo
        response = requests.post(API_URL, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if 'images' in result and result['images']:
                img_data = result['images'][0]
                # Manejar diferentes formatos de respuesta
                if ',' in img_data:
                    img_bytes = base64.b64decode(img_data.split(",", 1)[1])
                else:
                    img_bytes = base64.b64decode(img_data)
                print("✅ Imagen generada exitosamente")
                return img_bytes
            else:
                print("❌ Respuesta de API sin imágenes")
                return None
        elif response.status_code == 500:
            print(f"❌ Error interno del servidor (500)")
            
            # Intentar obtener más detalles del error
            try:
                error_detail = response.json() if response.content else {}
                if error_detail:
                    print(f"   Detalle del error: {error_detail}")
            except:
                print(f"   Respuesta del servidor: {response.text[:200] if response.text else 'Sin detalles'}")
            
            print("💡 Esto puede indicar:")
            print("   - Problema con el modelo cargado")
            print("   - Memoria insuficiente (VRAM/RAM)")
            print("   - Parámetros incompatibles")
            print("   - Modelo corrupto o configuración incorrecta")
            return None
        else:
            print(f"❌ Error en API: {response.status_code}")
            if response.text:
                print(f"   Detalles: {response.text[:200]}...")
            return None
    
    except requests.exceptions.Timeout:
        print("❌ Timeout al generar imagen (120s)")
        return None
    except Exception as e:
        print(f"❌ Error al generar imagen: {e}")
        traceback.print_exc()
        return None

def create_pack(pack_number, prompts, images_per_pack=40, working_config=None):
    """Crea un pack de imágenes"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d")
        pack_name = f"Anime_Cars_Pack_{pack_number:02d}_{timestamp}"
        pack_folder = os.path.join("packs", pack_name)
        os.makedirs(pack_folder, exist_ok=True)
        
        print(f"📦 Creando {pack_name}...")
        if working_config:
            print(f"🎯 Usando configuración optimizada: {working_config['width']}x{working_config['height']}")
        
        successful_images = 0
        for i in range(images_per_pack):
            prompt = prompts[i % len(prompts)]
            print(f"🔄 Imagen {i+1}/{images_per_pack}")
            
            img = generate_image(prompt, working_config)
            if img:
                img_path = os.path.join(pack_folder, f"img_{i+1:03d}.png")
                with open(img_path, "wb") as f:
                    f.write(img)
                successful_images += 1
            else:
                print(f"❌ Falló imagen {i+1}")
            
            # Pequeña pausa entre imágenes
            time.sleep(2)
        
        print(f"✅ Pack completado: {successful_images}/{images_per_pack} imágenes")
        return pack_name, pack_folder, successful_images
    
    except Exception as e:
        print(f"❌ Error al crear pack: {e}")
        traceback.print_exc()
        return None, None, 0

def zip_pack(folder_path, zip_name):
    """Comprime el pack en un archivo ZIP"""
    try:
        print(f"📁 Comprimiendo pack...")
        zip_path = shutil.make_archive(zip_name, 'zip', folder_path)
        print(f"✅ Pack comprimido: {os.path.basename(zip_path)}")
        print(f"📂 Guardado en: {zip_path}")
        return zip_path
    except Exception as e:
        print(f"❌ Error al comprimir: {e}")
        traceback.print_exc()
        return None

def upload_to_pixeldrain(zip_path, title, description):
    """Sube el pack a PixelDrain usando la API actualizada"""
    try:
        print(f"☁️ Subiendo a PixelDrain...")
        
        # Configurar sesión con SSL verificación deshabilitada para resolver problemas de certificados
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        session = requests.Session()
        session.verify = False  # Deshabilitar verificación SSL para evitar errores de certificado
        
        # Método actualizado según la documentación de PixelDrain
        filename = os.path.basename(zip_path)
        
        # Usar el método PUT como indica la documentación más reciente
        with open(zip_path, "rb") as f:
            headers = {
                'Content-Type': 'application/octet-stream'
            }
            
            # Intentar primero con POST (método tradicional)
            try:
                files = {"file": (filename, f, 'application/zip')}
                response = session.post(
                    "https://pixeldrain.com/api/file", 
                    files=files, 
                    timeout=300, 
                    verify=False
                )
            except Exception as e:
                print(f"⚠️ POST falló: {e}, intentando PUT...")
                f.seek(0)  # Resetear el archivo
                # Intentar con PUT method
                response = session.put(
                    f"https://pixeldrain.com/api/file/{filename}",
                    data=f,
                    headers=headers,
                    timeout=300,
                    verify=False
                )
        
        if response.ok:
            result = response.json()
            file_id = result.get("id")
            if file_id:
                link = f"https://pixeldrain.com/u/{file_id}"
                print(f"✅ Subido: {link}")
                return link
            else:
                print(f"⚠️ Respuesta exitosa pero sin ID: {result}")
                return None
        else:
            print(f"❌ Error al subir: {response.status_code} - {response.text}")
            # Si falla, ofrecer alternativas
            print("💡 El archivo ZIP está listo para subida manual:")
            print(f"   📁 {zip_path}")
            print("   🌐 Puedes subirlo manualmente a https://pixeldrain.com")
            return None
    
    except Exception as e:
        print(f"❌ Error al subir: {e}")
        # Ofrecer alternativas si falla la subida
        print("💡 Alternativas de subida:")
        print(f"   • Archivo ZIP listo: {zip_path}")
        print("   • Puedes subir manualmente a:")
        print("     - PixelDrain.com")
        print("     - Google Drive")
        print("     - Dropbox")
        print("     - WeTransfer")
        traceback.print_exc()
        return None

def create_watermarked_preview(image_paths, output_path):
    """Crea una imagen de preview persuasiva con marca de agua IA"""
    try:
        if not image_paths:
            return False
        
        # Configuración del preview (más grande y persuasivo)
        preview_size = (1600, 1200)
        grid_cols = 2
        grid_rows = 2
        margin = 30
        title_height = 120
        footer_height = 100
        
        # Área útil para imágenes
        content_height = preview_size[1] - title_height - footer_height
        cell_width = (preview_size[0] - margin * 3) // grid_cols
        cell_height = (content_height - margin * 3) // grid_rows
        cell_size = (cell_width, cell_height)
        
        # Crear imagen base con gradiente atractivo
        preview = Image.new('RGB', preview_size)
        draw_bg = ImageDraw.Draw(preview)
        
        # Gradiente de fondo atractivo (azul oscuro a negro)
        for y in range(preview_size[1]):
            color_ratio = y / preview_size[1]
            r = int(15 * (1 - color_ratio) + 5 * color_ratio)
            g = int(30 * (1 - color_ratio) + 10 * color_ratio)  
            b = int(60 * (1 - color_ratio) + 20 * color_ratio)
            draw_bg.line([(0, y), (preview_size[0], y)], fill=(r, g, b))
        
        # Añadir imágenes al grid
        for i, img_path in enumerate(image_paths[:4]):
            if i >= 4:
                break
                
            try:
                # Cargar y redimensionar imagen
                img = Image.open(img_path)
                img = img.resize(cell_size, Image.Resampling.LANCZOS)
                
                # Calcular posición en el grid
                col = i % grid_cols
                row = i // grid_cols
                x = margin + col * (cell_width + margin)
                y = title_height + margin + row * (cell_height + margin)
                
                # Añadir borde dorado atractivo
                border_size = 3
                border_img = Image.new('RGB', (cell_width + border_size*2, cell_height + border_size*2), (255, 215, 0))
                border_img.paste(img, (border_size, border_size))
                preview.paste(border_img, (x - border_size, y - border_size))
                
                # Crear marca de agua "IA" más prominente
                overlay = Image.new('RGBA', cell_size, (0, 0, 0, 0))
                draw_overlay = ImageDraw.Draw(overlay)
                
                # Marca de agua "IA" grande y visible
                watermark_text = "IA"
                try:
                    watermark_font = ImageFont.truetype("arial.ttf", 80)
                    preview_font = ImageFont.truetype("arial.ttf", 24)
                except:
                    watermark_font = ImageFont.load_default()
                    preview_font = ImageFont.load_default()
                
                # Posición de marca de agua "IA"
                bbox = draw_overlay.textbbox((0, 0), watermark_text, font=watermark_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = cell_size[0] - text_width - 20
                text_y = cell_size[1] - text_height - 20
                
                # Dibujar sombra para la marca de agua
                draw_overlay.text((text_x + 2, text_y + 2), watermark_text, font=watermark_font, fill=(0, 0, 0, 180))
                # Dibujar marca de agua "IA"
                draw_overlay.text((text_x, text_y), watermark_text, font=watermark_font, fill=(255, 255, 255, 200))
                
                # Añadir "PREVIEW" pequeño en esquina superior
                preview_text = "PREVIEW"
                draw_overlay.text((10, 10), preview_text, font=preview_font, fill=(255, 255, 255, 160))
                
                # Aplicar overlay
                preview.paste(overlay, (x, y), overlay)
                
            except Exception as e:
                print(f"⚠️ Error procesando imagen {img_path}: {e}")
                continue
        
        # Añadir título llamativo
        draw = ImageDraw.Draw(preview)
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            subtitle_font = ImageFont.truetype("arial.ttf", 24)
            info_font = ImageFont.truetype("arial.ttf", 20)
            footer_font = ImageFont.truetype("arial.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
            footer_font = ImageFont.load_default()
        
        # Título principal con sombra
        title_text = "🚗 ANIME CARS COLLECTION"
        title_x = preview_size[0] // 2
        
        # Sombra del título
        bbox = draw.textbbox((0, 0), title_text, font=title_font)
        text_width = bbox[2] - bbox[0]
        shadow_x = title_x - text_width // 2 + 3
        draw.text((shadow_x, 23), title_text, font=title_font, fill=(0, 0, 0), anchor="lt")
        
        # Título principal
        title_x_final = title_x - text_width // 2
        draw.text((title_x_final, 20), title_text, font=title_font, fill=(255, 215, 0), anchor="lt")
        
        # Subtítulo
        subtitle_text = "🎨 AI-Generated High Quality Artwork"
        bbox_sub = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
        subtitle_width = bbox_sub[2] - bbox_sub[0]
        subtitle_x = title_x - subtitle_width // 2
        draw.text((subtitle_x, 75), subtitle_text, font=subtitle_font, fill=(255, 255, 255), anchor="lt")
        
        # Footer persuasivo
        footer_y = preview_size[1] - footer_height + 20
        
        # Información del pack
        info_lines = [
            f"✨ {len(image_paths)} STUNNING ANIME CAR IMAGES",
            f"🖼️ 4K RESOLUTION (2048x2048) • COMMERCIAL USE OK",
            f"🎯 PERFECT FOR: Digital Art • Gaming • Design Projects",
            f"⚡ INSTANT DOWNLOAD • AI-GENERATED EXCLUSIVE CONTENT"
        ]
        
        for i, line in enumerate(info_lines):
            draw.text((margin, footer_y + i * 20), line, font=footer_font, fill=(200, 255, 200))
        
        # Guardar preview en alta calidad
        preview.save(output_path, "PNG", quality=95, optimize=True)
        print(f"✅ Preview persuasivo creado: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creando preview: {e}")
        traceback.print_exc()
        return False

def generate_gumroad_description(pack_title, img_count, prompts_sample):
    """Genera una descripción atractiva para Gumroad"""
    description = f"""🚗 **{pack_title}** - Premium AI-Generated Anime Car Collection

**What you get:**
• {img_count} high-quality images (768x768px)
• Unique anime-style car designs
• Perfect for digital art projects, wallpapers, or inspiration
• Instant download after purchase

**Features:**
✨ Professional AI-generated artwork
🎨 Diverse anime art styles (kawaii, mecha, cyberpunk, etc.)
🚗 Various car types (sports cars, supercars, concept cars, etc.)
🌈 Vibrant color schemes and lighting effects
📱 High resolution suitable for print and digital use

**Sample Themes Included:**
{chr(10).join([f"• {prompt[:80]}..." for prompt in prompts_sample[:5]])}

**Perfect for:**
• Digital artists and designers
• Anime and car enthusiasts
• Social media content creators
• Game developers and modders
• Art collectors and wallpaper enthusiasts

**Technical Details:**
• Format: PNG
• Resolution: 768x768 pixels
• Generated with professional AI models
• No watermarks on purchased images
• Commercial use allowed

💝 **Bonus:** Each pack includes unique daily-generated prompts ensuring you get exclusive content that won't be repeated!

🔔 **Note:** This is digital content. No physical items will be shipped.

⭐ **Satisfaction Guaranteed** - If you're not happy with your purchase, contact us for a full refund!

#AnimeArt #DigitalArt #AIGenerated #Cars #Anime #Wallpapers #DigitalDownload"""

    return description

def get_currency_symbol(currency):
    """Retorna el símbolo de moneda apropiado"""
    return {
        'usd': '$', 'eur': '€', 'gbp': '£', 
        'cad': 'C$', 'aud': 'A$'
    }.get(currency.lower(), '$')

def setup_gumroad_config():
    """Configura la integración con Gumroad de forma interactiva"""
    config_file = "gumroad_config.json"
    config_changed = False
    
    # Intentar cargar configuración existente
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                GUMROAD_CONFIG.update(saved_config)
                print("📋 Configuración de Gumroad encontrada")
        except Exception as e:
            print(f"⚠️ Error cargando configuración: {e}")
    
    # Verificar si necesitamos configuración interactiva
    need_setup = (
        not GUMROAD_CONFIG.get("access_token") or 
        GUMROAD_CONFIG.get("access_token") == "tu_token_aqui" or
        not GUMROAD_CONFIG.get("base_price") or
        not GUMROAD_CONFIG.get("currency")
    )
    
    if need_setup:
        print("\n" + "="*60)
        print("🔧 CONFIGURACIÓN DE GUMROAD REQUERIDA")
        print("="*60)
        print("Para vender automáticamente en Gumroad necesitas configurar:")
        print("1. 🔑 Tu Access Token de la API")
        print("2. 💰 Precios y moneda")
        print("3. ⚙️ Opciones de publicación")
        print("4. 🎯 Configuración de Pay-What-You-Want")
        print()
        
        try:
            # 1. Configurar Access Token
            print("=" * 40)
            print("🔑 PASO 1: ACCESS TOKEN")
            print("=" * 40)
            print("Para obtener tu Access Token:")
            print("1. Ve a: https://gumroad.com/settings/advanced")
            print("2. Busca 'Application Access Token'")
            print("3. Haz clic en 'Generate access token'")
            print("4. Copia el token que aparece")
            print()
            
            current_token = GUMROAD_CONFIG.get("access_token", "")
            if current_token and current_token != "tu_token_aqui":
                print(f"Token actual: {current_token[:20]}...{current_token[-10:]}")
                keep_token = input("¿Mantener este token? (s/n): ").lower().strip()
                if keep_token in ['n', 'no']:
                    current_token = ""
            
            if not current_token or current_token == "tu_token_aqui":
                token = input("🔑 Introduce tu Gumroad Access Token: ").strip()
                if token:
                    GUMROAD_CONFIG["access_token"] = token
                    config_changed = True
                    print("✅ Token configurado")
                else:
                    print("❌ Sin token - Gumroad estará deshabilitado")
                    return False
            
            # 2. Configurar moneda
            print("\n" + "=" * 40)
            print("💱 PASO 2: MONEDA")
            print("=" * 40)
            print("Monedas disponibles:")
            print("1. USD - Dólar estadounidense (recomendado)")
            print("2. EUR - Euro")
            print("3. GBP - Libra esterlina")
            print("4. CAD - Dólar canadiense")
            print("5. AUD - Dólar australiano")
            print()
            
            current_currency = GUMROAD_CONFIG.get("currency", "usd").upper()
            print(f"Moneda actual: {current_currency}")
            
            currency_input = input("Elige moneda (usd/eur/gbp/cad/aud) [actual]: ").lower().strip()
            if currency_input:
                if currency_input in ['usd', 'eur', 'gbp', 'cad', 'aud']:
                    GUMROAD_CONFIG["currency"] = currency_input
                    config_changed = True
                    print(f"✅ Moneda configurada: {currency_input.upper()}")
                else:
                    print("⚠️ Moneda no válida, manteniendo actual")
            
            # 3. Configurar precios
            print("\n" + "=" * 40)
            print("💰 PASO 3: PRECIOS")
            print("=" * 40)
            currency_symbol = get_currency_symbol(GUMROAD_CONFIG["currency"])
            
            try:
                current_price = GUMROAD_CONFIG.get("base_price", 5.0)
                print(f"Precio base actual: {currency_symbol}{current_price:.2f}")
                price_input = input(f"Precio base ({currency_symbol}) [actual]: ").strip()
                if price_input:
                    price = float(price_input)
                    if price > 0:
                        GUMROAD_CONFIG["base_price"] = price
                        config_changed = True
                        print(f"✅ Precio base: {currency_symbol}{price:.2f}")
                    else:
                        print("⚠️ Precio debe ser mayor a 0")
                
            except ValueError:
                print("⚠️ Precio no válido, manteniendo actual")
            
            # 4. Configurar Pay-What-You-Want
            print("\n" + "=" * 40)
            print("🎯 PASO 4: PAY-WHAT-YOU-WANT")
            print("=" * 40)
            print("¿Permitir que los clientes paguen más del precio base?")
            print("Esto puede aumentar las ventas significativamente.")
            print()
            
            current_pwyw = GUMROAD_CONFIG.get("enable_pay_what_you_want", True)
            print(f"Estado actual: {'✅ Activado' if current_pwyw else '❌ Desactivado'}")
            
            pwyw_input = input("¿Activar Pay-What-You-Want? (s/n) [actual]: ").lower().strip()
            if pwyw_input:
                enable_pwyw = pwyw_input in ['s', 'si', 'y', 'yes']
                GUMROAD_CONFIG["enable_pay_what_you_want"] = enable_pwyw
                config_changed = True
                
                if enable_pwyw:
                    print("✅ Pay-What-You-Want activado")
                    try:
                        current_min = GUMROAD_CONFIG.get("min_price", 3.0)
                        print(f"Precio mínimo actual: {currency_symbol}{current_min:.2f}")
                        min_input = input(f"Precio mínimo ({currency_symbol}) [actual]: ").strip()
                        if min_input:
                            min_price = float(min_input)
                            if min_price > 0 and min_price <= GUMROAD_CONFIG["base_price"]:
                                GUMROAD_CONFIG["min_price"] = min_price
                                print(f"✅ Precio mínimo: {currency_symbol}{min_price:.2f}")
                            else:
                                print("⚠️ Precio mínimo debe ser mayor a 0 y menor al precio base")
                    except ValueError:
                        print("⚠️ Precio no válido, manteniendo actual")
                else:
                    print("❌ Pay-What-You-Want desactivado")
            
            # 5. Configurar auto-publicación
            print("\n" + "=" * 40)
            print("🚀 PASO 5: AUTO-PUBLICACIÓN")
            print("=" * 40)
            print("NOTA: Debido a cambios en la API de Gumroad, la auto-publicación")
            print("ya no está disponible. Los productos se crearán como borradores.")
            
            GUMROAD_CONFIG["auto_publish"] = False
            
            # Guardar configuración si hubo cambios
            if config_changed:
                try:
                    config_to_save = GUMROAD_CONFIG.copy()
                    config_to_save["note"] = "Configuración de Gumroad - Generado automáticamente"
                    config_to_save["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    with open(config_file, "w", encoding="utf-8") as f:
                        json.dump(config_to_save, f, indent=2, ensure_ascii=False)
                    
                    print(f"\n✅ Configuración guardada en {config_file}")
                except Exception as e:
                    print(f"⚠️ Error guardando configuración: {e}")
            
            print("\n" + "="*60)
            print("🎉 ¡CONFIGURACIÓN DE GUMROAD COMPLETADA!")
            print("="*60)
            print(f"🔑 Token: Configurado")
            print(f"💱 Moneda: {GUMROAD_CONFIG['currency'].upper()}")
            print(f"💰 Precio base: {currency_symbol}{GUMROAD_CONFIG['base_price']:.2f}")
            print(f"🎯 Pay-What-You-Want: {'✅ Activado' if GUMROAD_CONFIG['enable_pay_what_you_want'] else '❌ Desactivado'}")
            if GUMROAD_CONFIG['enable_pay_what_you_want']:
                print(f"� Precio mínimo: {currency_symbol}{GUMROAD_CONFIG['min_price']:.2f}")
            print("🚀 Auto-publicación: ❌ Manual (limitación de API)")
            print("="*60)
            
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️ Configuración cancelada por el usuario")
            return False
        except Exception as e:
            print(f"❌ Error en configuración: {e}")
            return False
    else:
        print("✅ Configuración de Gumroad cargada correctamente")
        return True

def validate_gumroad_token():
    """Valida que el token de Gumroad sea correcto"""
    try:
        if not GUMROAD_CONFIG.get("access_token"):
            print("❌ No hay token de Gumroad configurado")
            return False
        
        headers = {
            "Authorization": f"Bearer {GUMROAD_CONFIG['access_token']}"
        }
        
        # Intentar obtener información del usuario para validar el token
        response = requests.get(
            "https://api.gumroad.com/v2/user",
            headers=headers,
            timeout=30
        )
        
        if response.ok:
            user_data = response.json()
            print(f"✅ Token válido - Usuario: {user_data.get('user', {}).get('name', 'Usuario')}")
            return True
        else:
            print(f"❌ Token inválido - Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error validando token: {e}")
        return False

def list_gumroad_products():
    """Lista los productos existentes en Gumroad"""
    try:
        if not validate_gumroad_token():
            return None
        
        headers = {
            "Authorization": f"Bearer {GUMROAD_CONFIG['access_token']}"
        }
        
        response = requests.get(
            "https://api.gumroad.com/v2/products",
            headers=headers,
            timeout=30
        )
        
        if response.ok:
            data = response.json()
            products = data.get('products', [])
            print(f"📋 Productos existentes en Gumroad: {len(products)}")
            
            if products:
                for i, product in enumerate(products, 1):
                    status = "✅ Publicado" if product.get('published') else "⏸️ Draft"
                    print(f"   {i}. {product.get('name', 'Sin nombre')} - {status}")
                    print(f"      💰 ${product.get('price', 0)/100:.2f} - URL: {product.get('short_url', 'N/A')}")
            
            return products
        else:
            print(f"❌ Error obteniendo productos: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error listando productos: {e}")
        return None

def upload_to_gumroad(zip_path, preview_path, pack_title, description, price):
    """Prepara información para Gumroad (la API ya no permite crear productos automáticamente)"""
    try:
        # Validar token primero
        if not validate_gumroad_token():
            return None
        
        print(f"� Preparando información para Gumroad: {pack_title}")
        print("\n" + "="*60)
        print("🚨 IMPORTANTE: CAMBIO EN LA API DE GUMROAD")
        print("="*60)
        print("❗ La API de Gumroad ya NO permite crear productos automáticamente.")
        print("❗ Debes crear el producto manualmente en https://gumroad.com")
        print("\n� PASOS PARA PUBLICAR EN GUMROAD:")
        print("1. Ve a: https://gumroad.com/products/new")
        print("2. Usa estos datos para el producto:")
        print(f"   📝 Título: {pack_title}")
        print(f"   💰 Precio: €{price:.2f} EUR")
        print(f"   📄 Descripción: {description[:100]}...")
        print(f"   📁 Archivo: {zip_path}")
        if preview_path and os.path.exists(preview_path):
            print(f"   🖼️ Preview: {preview_path}")
        print("\n📋 Información completa guardada en: gumroad_manual_upload.txt")
        
        # Guardar información para subida manual
        manual_info = {
            "title": pack_title,
            "price": price,
            "currency": "EUR",
            "description": description,
            "zip_file": zip_path,
            "preview_file": preview_path if preview_path and os.path.exists(preview_path) else None,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "manual_url": "https://gumroad.com/products/new"
        }
        
        # Guardar en archivo para referencia
        with open("gumroad_manual_upload.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"PRODUCTO: {pack_title}\n")
            f.write(f"FECHA: {manual_info['timestamp']}\n")
            f.write(f"{'='*60}\n")
            f.write(f"Título: {manual_info['title']}\n")
            f.write(f"Precio: €{manual_info['price']:.2f} {manual_info['currency']}\n")
            f.write(f"Archivo ZIP: {manual_info['zip_file']}\n")
            if manual_info['preview_file']:
                f.write(f"Preview: {manual_info['preview_file']}\n")
            f.write(f"URL para crear: {manual_info['manual_url']}\n")
            f.write(f"\nDescripción:\n{description}\n")
            f.write(f"\n{'='*60}\n")
        
        print("="*60)
        
        # Devolver información estructurada
        return {
            "status": "manual_upload_required",
            "title": pack_title,
            "price": price,
            "manual_url": "https://gumroad.com/products/new",
            "zip_path": zip_path,
            "preview_path": preview_path,
            "info_file": "gumroad_manual_upload.txt"
        }
        
    except Exception as e:
        print(f"❌ Error preparando información para Gumroad: {e}")
        traceback.print_exc()
        return None

def save_sales_log(product_info, pack_title, pixeldrain_link=None):
    """Guarda información de ventas en un log"""
    try:
        sales_log_file = "sales_log.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(sales_log_file, "a", encoding="utf-8") as f:
            f.write(f"{'='*60}\n")
            f.write(f"PRODUCTO CREADO: {timestamp}\n")
            f.write(f"{'='*60}\n")
            f.write(f"Título: {pack_title}\n")
            f.write(f"ID Producto: {product_info['id']}\n")
            f.write(f"URL Gumroad: {product_info['url']}\n")
            f.write(f"Precio: ${product_info['price']:.2f} USD\n")
            f.write(f"Estado: {'🟢 Publicado' if product_info['published'] else '🟡 Borrador'}\n")
            if pixeldrain_link:
                f.write(f"Backup PixelDrain: {pixeldrain_link}\n")
            f.write(f"\n")
        
        print(f"📊 Log de ventas actualizado: {sales_log_file}")
        
    except Exception as e:
        print(f"⚠️ Error guardando log de ventas: {e}")

def create_marketplace_summary():
    """Crea un resumen de todos los productos creados"""
    try:
        summary_file = "marketplace_summary.html"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Leer log de ventas si existe
        products = []
        if os.path.exists("sales_log.txt"):
            with open("sales_log.txt", "r", encoding="utf-8") as f:
                content = f.read()
                # Parse básico del log (se puede mejorar)
                blocks = content.split("="*60)
                for block in blocks:
                    if "URL Gumroad:" in block:
                        lines = block.strip().split("\n")
                        product = {}
                        for line in lines:
                            if "Título:" in line:
                                product["title"] = line.split("Título:", 1)[1].strip()
                            elif "URL Gumroad:" in line:
                                product["url"] = line.split("URL Gumroad:", 1)[1].strip()
                            elif "Precio:" in line:
                                product["price"] = line.split("Precio:", 1)[1].strip()
                        if product:
                            products.append(product)
        
        # Crear HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🚗 Anime Cars Generator - Marketplace Summary</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 10px; }}
        .product {{ background: white; margin: 10px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stats {{ background: #3498db; color: white; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .url {{ color: #e74c3c; text-decoration: none; font-weight: bold; }}
        .url:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚗 Anime Cars Generator - Marketplace</h1>
        <p>Resumen generado: {timestamp}</p>
    </div>
    
    <div class="stats">
        <h2>📊 Estadísticas</h2>
        <p><strong>Total de productos:</strong> {len(products)}</p>
        <p><strong>Última actualización:</strong> {timestamp}</p>
        <p><strong>Estado del sistema:</strong> ✅ Activo</p>
    </div>
    
    <h2>🛒 Productos en Gumroad</h2>
"""
        
        if products:
            for i, product in enumerate(products, 1):
                html_content += f"""
    <div class="product">
        <h3>#{i} - {product.get('title', 'Sin título')}</h3>
        <p><strong>Precio:</strong> {product.get('price', 'No disponible')}</p>
        <p><strong>URL:</strong> <a href="{product.get('url', '#')}" class="url" target="_blank">{product.get('url', 'No disponible')}</a></p>
    </div>
"""
        else:
            html_content += """
    <div class="product">
        <p>No hay productos registrados aún.</p>
        <p>Los productos aparecerán aquí cuando se ejecute el generador con Gumroad habilitado.</p>
    </div>
"""
        
        html_content += """
    <div style="margin-top: 40px; text-align: center; color: #7f8c8d;">
        <p>Generado automáticamente por Anime Cars Generator</p>
    </div>
</body>
</html>
"""
        
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"📄 Resumen del marketplace creado: {summary_file}")
        return summary_file
        
    except Exception as e:
        print(f"⚠️ Error creando resumen: {e}")
        return None

def main():
    """Función principal con manejo completo de errores"""
    global ENABLE_GUMROAD_UPLOAD
    
    # Configurar directorio de trabajo con permisos
    working_dir = setup_working_directory()
    if not working_dir:
        print("❌ No se puede continuar sin permisos de escritura")
        return False
    
    print(f"� Directorio de trabajo: {working_dir}")
    
    # Limpiar logs antiguos que puedan estar bloqueados
    cleanup_old_logs()
    
    # Configurar logging con manejo robusto de errores
    log_file, original_stdout, original_stderr = setup_logging()
    
    try:
        print("=" * 60)
        print("🚗 GENERADOR DE ANIME CARS - INICIANDO")
        print("=" * 60)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Trabajando en: {os.getcwd()}")
        
        if log_file:
            print("📝 Sistema de logging activado")
        else:
            print("⚠️ Ejecutándose sin logging a archivo")
        
        # Verificar conexión API
        if not check_api_connection():
            print("\n❌ No se puede continuar sin conexión a la API")
            return False
        
        # Verificar configuración de Gumroad si está habilitado
        if ENABLE_GUMROAD_UPLOAD:
            print("\n🛒 Verificando configuración de Gumroad...")
            setup_gumroad_config()  # Cargar configuración desde archivo
            if not validate_gumroad_token():
                print("⚠️ Problema con token de Gumroad - continuando solo con PixelDrain")
                ENABLE_GUMROAD_UPLOAD = False
            else:
                print("✅ Gumroad configurado correctamente")
        
        # Verificar salud del WebUI antes de empezar generación masiva
        print("\n🏥 Verificando salud del WebUI antes de generar...")
        webui_health_result = check_webui_health()
        
        working_config = None
        if isinstance(webui_health_result, dict):
            # check_webui_health devolvió una configuración que funciona
            working_config = webui_health_result
            print("✅ WebUI funcionando con configuración optimizada")
        elif webui_health_result == True:
            print("✅ WebUI funcionando correctamente")
        else:
            print("⚠️ WebUI tiene problemas - intentando con parámetros reducidos")
            print("💡 Recomendaciones:")
            print("   1. Verifica la consola del WebUI para errores específicos")
            print("   2. Considera reiniciar el WebUI")
            print("   3. Verifica que tienes suficiente VRAM/RAM libre")
            
            # Ofrecer continuar con parámetros reducidos
            try:
                choice = input("\n¿Continuar con parámetros reducidos? (s/n): ").lower().strip()
                if choice not in ['s', 'si', 'sí', 'y', 'yes']:
                    print("❌ Cancelado por el usuario")
                    return False
            except:
                print("❌ Error en entrada - cancelando")
                return False
        
        # Cargar prompts
        prompts = load_prompts()
        if not prompts:
            print("\n❌ No se pueden cargar prompts")
            return False
        
        # Configuración
        packs_per_day = 10
        images_per_pack = 8  # Cambiado de 40 a 8 imágenes por pack
        os.makedirs("packs", exist_ok=True)
        # os.makedirs("packs_zip", exist_ok=True)  # DESHABILITADO - Sin archivos ZIP
        os.makedirs("previews", exist_ok=True)   # Carpeta para previews
        
        # Configurar Gumroad si está habilitado
        if ENABLE_GUMROAD_UPLOAD:
            print("\n🛒 Configurando Gumroad para venta automática...")
            if not setup_gumroad_config():
                print("⚠️ Gumroad no configurado - solo se subirá a PixelDrain")
                ENABLE_GUMROAD_UPLOAD = False
        
        print(f"\n🎯 Configuración:")
        print(f"   - Packs a generar: {packs_per_day}")
        print(f"   - Imágenes por pack: {images_per_pack}")
        print(f"   - Prompts disponibles: {len(prompts)}")
        print(f"   - Prompts únicos generados para: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"   - Regeneración automática: ✅ Diaria")
        print(f"   - WebUI Auto-start: ✅ Activado")
        print(f"   - WebUI Path: {WEBUI_PATH}")
        print(f"   - Venta en Gumroad: {'✅ Habilitada' if ENABLE_GUMROAD_UPLOAD else '❌ Deshabilitada'}")
        print(f"   - Crear previews: {'✅ Sí' if CREATE_PREVIEW_IMAGES else '❌ No'}")
        if ENABLE_GUMROAD_UPLOAD:
            currency_symbol = get_currency_symbol(GUMROAD_CONFIG['currency'])
            print(f"   - Precio base: {currency_symbol}{GUMROAD_CONFIG['base_price']:.2f} {GUMROAD_CONFIG['currency']}")
            print(f"   - Auto-publicar: {'✅ Sí' if GUMROAD_CONFIG['auto_publish'] else '❌ No'}")
        
        # Generar packs
        successful_packs = 0
        for i in range(1, packs_per_day + 1):
            print(f"\n📦 PACK {i}/{packs_per_day}")
            print("-" * 40)
            
            # Mostrar configuración que se usará si hay una optimizada
            if working_config:
                print(f"🎯 Usando configuración optimizada: {working_config['width']}x{working_config['height']}, {working_config['steps']} pasos")
            
            pack_result = create_pack(i, prompts, images_per_pack, working_config)
            if pack_result[0] is None:
                print(f"❌ Falló la creación del pack {i}")
                continue
            
            pack_title, folder, img_count = pack_result
            
            if img_count == 0:
                print(f"❌ Pack {i} sin imágenes válidas")
                continue
            
            # ---- COMPRESIÓN ZIP DESHABILITADA ----
            # Las imágenes quedan en carpetas, sin ZIP
            # zip_path = zip_pack(folder, os.path.join("packs_zip", pack_title))
            # if not zip_path:
            #     print(f"❌ No se pudo comprimir pack {i}")
            #     continue
            
            print(f"📁 Pack guardado en carpeta: {folder}")
            print("ℹ️  Sin archivo ZIP - usando solo carpeta con imágenes")
            
            # Crear preview con watermark si está habilitado
            preview_path = None
            if CREATE_PREVIEW_IMAGES:
                print("🖼️ Creando preview con watermark...")
                # Obtener las primeras imágenes del pack
                pack_images = []
                for img_file in os.listdir(folder):
                    if img_file.endswith('.png'):
                        pack_images.append(os.path.join(folder, img_file))
                        if len(pack_images) >= PREVIEW_COUNT:
                            break
                
                if pack_images:
                    preview_filename = f"{pack_title}_preview.png"
                    preview_path = os.path.join("previews", preview_filename)
                    if create_watermarked_preview(pack_images, preview_path):
                        print(f"✅ Preview creado: {preview_filename}")
                    else:
                        preview_path = None
            
            # Subir a PixelDrain (respaldo)
            description = f"""{pack_title}
Contiene {img_count} imágenes generadas por IA con estilo anime automovilístico.
Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Prompts incluidos:
{', '.join(prompts[:5])}...
"""
            # ---- SUBIDA A PIXELDRAIN DESHABILITADA ----
            # Solo funciona con archivos ZIP, ahora usamos solo carpetas
            # pixeldrain_link = upload_to_pixeldrain(zip_path, pack_title, description)
            print("ℹ️  Subida a PixelDrain omitida - sin archivo ZIP")
            pixeldrain_link = None  # Para mantener compatibilidad
            
            # Preparar información para Gumroad (subida manual requerida)
            gumroad_info = None
            if ENABLE_GUMROAD_UPLOAD and GUMROAD_CONFIG.get("access_token"):
                print("🛒 Preparando información para Gumroad...")
                
                # Listar productos existentes
                print("\n📋 Revisando productos existentes en Gumroad:")
                list_gumroad_products()
                
                # Generar descripción para Gumroad
                gumroad_description = generate_gumroad_description(
                    pack_title, 
                    img_count, 
                    prompts[:10]  # Primeros 10 prompts como muestra
                )
                
                # Calcular precio (puede variar por pack)
                pack_price = GUMROAD_CONFIG["base_price"]
                
                # ---- GUMROAD DESHABILITADO (sin ZIP) ----
                # Preparar información para subida manual
                # gumroad_info = upload_to_gumroad(
                #     zip_path,
                #     preview_path,
                #     pack_title,
                #     gumroad_description,
                #     pack_price
                # )
                
                print("ℹ️  Subida a Gumroad omitida - funcionaba con archivos ZIP")
                gumroad_info = {"status": "skipped_no_zip"}
                
                if gumroad_info:
                    if gumroad_info.get("status") == "manual_upload_required":
                        print(f"📋 Información preparada para subida manual a Gumroad")
                        print(f"📄 Detalles guardados en: {gumroad_info['info_file']}")
                        successful_packs += 1
                        
                        # Guardar en log de ventas adaptado
                        save_sales_log({
                            "status": "manual_upload_required",
                            "title": pack_title,
                            "price": pack_price,
                            "url": gumroad_info["manual_url"],
                            "info_file": gumroad_info["info_file"]
                        }, pack_title, pixeldrain_link)
                        
                        # Sonido de información
                        winsound.Beep(800, 200)
                        time.sleep(0.1)
                        winsound.Beep(1000, 200)
                    else:
                        print("❌ Error preparando información para Gumroad")
                        if pixeldrain_link:
                            successful_packs += 1
                else:
                    print("❌ Error con configuración de Gumroad, pero PixelDrain disponible")
                    if pixeldrain_link:
                        successful_packs += 1
            else:
                # Solo PixelDrain
                if pixeldrain_link:
                    successful_packs += 1
                    # Guardar enlace en log tradicional
                    with open("upload_log.txt", "a", encoding="utf-8") as log:
                        log.write(f"{pack_title}\n{pixeldrain_link}\n{datetime.now()}\n\n")
                    
                    # Sonido de éxito tradicional
                    winsound.Beep(1000, 300)
            
            print(f"⏳ Pausa de 15 segundos...")
            time.sleep(15)
        
        print("\n" + "=" * 60)
        print(f"🎉 PROCESO COMPLETADO")
        print(f"✅ Packs exitosos: {successful_packs}/{packs_per_day}")
        print("=" * 60)
        print(f"📂 Archivos generados:")
        print(f"   • Directorio de trabajo: {working_dir}")
        print(f"   • Imágenes sin comprimir: packs/")
        print(f"   • Archivos ZIP: packs_zip/")
        print(f"   • Prompts del día: prompts.txt")
        print(f"   • Respaldo de prompts: prompt_backups/")
        if CREATE_PREVIEW_IMAGES:
            print(f"   • Previews con watermark: previews/")
        print(f"   • Log de subidas: upload_log.txt")
        if ENABLE_GUMROAD_UPLOAD:
            print(f"   • Log de ventas: sales_log.txt")
        if log_file:
            print(f"   • Log de ejecución: ✅ Activado")
        else:
            print(f"   • Log de ejecución: ⚠️ No disponible")
        print("=" * 60)
        print(f"🔮 Prompts automáticos:")
        print(f"   • Se regeneran automáticamente cada día")
        print(f"   • Basados en la fecha para consistencia")
        print(f"   • {len(prompts)} prompts únicos por día")
        if ENABLE_GUMROAD_UPLOAD:
            # Obtener símbolo de moneda para mostrar
            currency_symbols = {
                'usd': '$', 'eur': '€', 'gbp': '£', 
                'cad': 'C$', 'aud': 'A$'
            }
            currency_symbol = currency_symbols.get(GUMROAD_CONFIG.get("currency", "eur"), "€")
            currency_name = GUMROAD_CONFIG.get("currency", "eur").upper()
            
            print("=" * 60)
            print(f"💰 Información de ventas:")
            print(f"   • Plataforma: Gumroad (subida manual requerida)")
            print(f"   • Precio base: {currency_symbol}{GUMROAD_CONFIG['base_price']:.2f} {currency_name}")
            print("   • Información de productos guardada en: gumroad_manual_upload.txt")
            print("   • URL para crear productos: https://gumroad.com/products/new")
            print("   • Auto-publicación: ❌ Manual (API cambió)")
            print(f"   • Pay-what-you-want: {'✅ Activado' if GUMROAD_CONFIG['enable_pay_what_you_want'] else '❌ Desactivado'}")
            if GUMROAD_CONFIG['enable_pay_what_you_want']:
                print(f"   • Precio mínimo: {currency_symbol}{GUMROAD_CONFIG['min_price']:.2f} {currency_name}")
            
            # Crear resumen del marketplace
            summary_file = create_marketplace_summary()
            if summary_file:
                print(f"   • Resumen HTML: {summary_file}")
        print("=" * 60)
        
        # Sonido final
        if successful_packs > 0:
            print("🎵 Reproduciendo sonido de éxito...")
            for _ in range(3):
                winsound.Beep(800, 200)
                time.sleep(0.1)
        else:
            print("🔔 Reproduciendo sonido de advertencia...")
            winsound.Beep(400, 500)
        
        return True
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        return False
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        traceback.print_exc()
        return False
    
    finally:
        # Restaurar salida original
        try:
            if log_file:
                log_file.close()
        except:
            pass  # Ignorar errores al cerrar el archivo
        
        # Restaurar stdout/stderr solo si fueron modificados
        if 'original_stdout' in locals() and original_stdout:
            sys.stdout = original_stdout
        if 'original_stderr' in locals() and original_stderr:
            sys.stderr = original_stderr

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ El proceso terminó con errores")
            if AUTO_CLOSE:
                print(f"⏳ Cerrando automáticamente en {CLOSE_DELAY_ERROR} segundos...")
                time.sleep(CLOSE_DELAY_ERROR)
            else:
                print("Presiona Enter para salir...")
                input()
        else:
            print("\n✅ Proceso completado exitosamente")
            if AUTO_CLOSE:
                print(f"⏳ Cerrando automáticamente en {CLOSE_DELAY_SUCCESS} segundos...")
                time.sleep(CLOSE_DELAY_SUCCESS)
            else:
                print("Presiona Enter para salir...")
                input()
    
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        traceback.print_exc()
        if AUTO_CLOSE:
            print(f"⏳ Cerrando automáticamente en {CLOSE_DELAY_ERROR} segundos...")
            time.sleep(CLOSE_DELAY_ERROR)
        else:
            print("Presiona Enter para salir...")
            input()
    
    finally:
        print("\n" + "="*50)
        print("🔚 Finalizando script...")
        # Script se cierra automáticamente
