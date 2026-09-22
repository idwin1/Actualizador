
import os
import sys
import subprocess
import json

LIBRERIAS_REQUERIDAS = {
    "colorama": "colorama",
    "requests": "requests",
    "truststore": "truststore"
}

def verificar_e_instalar_librerIAS():
    for import_name, pip_name in LIBRERIAS_REQUERIDAS.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"[!] La librería '{import_name}' no está instalada.")
            print(f"[+] Instalando '{pip_name}' automáticamente en segundo plano...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
                print(f"[✔] '{pip_name}' instalada con éxito.\n")
            except Exception as e:
                print(f"[❌] Error crítico al intentar instalar {pip_name}: {e}")
                sys.exit(1)

verificar_e_instalar_librerIAS()

import requests
from colorama import init, Fore, Style
import truststore

truststore.inject_into_ssl()
init(autoreset=True)

REPO_OWNER = "idwin1"
REPO_NAME = "Ejecutables"
TAG_RELEASE = "Produccion"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}


def obtener_ruta_apps_real():
    """Detecta con precisión la carpeta física real donde reside este ejecutable de forma externa"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        return os.path.dirname(os.path.abspath(__file__))

# El actualizador vive dentro de 'apps', por ende BASE_DIR es la carpeta 'apps'
BASE_DIR = obtener_ruta_apps_real()
CONFIG_FILE  = os.path.join(BASE_DIR, "config.json")


def resolver_ruta_local(ruta_github):
    """Calcula la ruta exacta forzando las descargas a la carpeta local 'apps'"""
    nombre_archivo = os.path.basename(ruta_github)
    
    if nombre_archivo.lower() == "menu.exe":
        return os.path.join(BASE_DIR, "Menu_NUEVO.exe")
    if nombre_archivo.lower() == "actualizador.exe":
        return os.path.join(BASE_DIR, "actualizador_NUEVO.exe")
    return os.path.join(BASE_DIR, nombre_archivo)

# -------------------------------------------------------------------------
# CARGA DE CONFIGURACIÓN SEGURA
# -------------------------------------------------------------------------

def cargar_configuracion():
    default_config = {
        "Actualizaciones_Automaticas": True,
        "Fechas_Archivos": {},
        "Estado_Menu": 0,
        "Estado_Actualizador": 0
    }

    if not os.path.exists(CONFIG_FILE):
        # Si no existe, creamos una estructura inicial básica para evitar crasheos
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except Exception:
            return default_config
        
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
            if "Fechas_Archivos" not in datos:
                datos["Fechas_Archivos"] = {}
            return datos
    except Exception as e:
        return default_config

# --- MODIFICACIÓN 1: Añadir el parámetro a la función ---
def guardar_estado(fechas_actualizadas, actualizar_menu=False, actualizar_actualizador=False):
    datos = cargar_configuracion()
    datos["Fechas_Archivos"] = fechas_actualizadas
    
    if actualizar_menu:
        datos["Estado_Menu"] = 1
    if actualizar_actualizador:
        datos["Estado_Actualizador"] = 1
        
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[⚠️] Error al guardar config.json: {e}")

def actualizar_desde_releases():
    print("Verificando API de Releases...")
    
    # 1. Buscar el Release específico (o el último si falla)
    url_release = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{TAG_RELEASE}"
    try:
        res_release = requests.get(url_release, headers=HEADERS, timeout=10)
        
        # Si no encuentra el tag 'produccion', intenta buscar el 'latest'
        if res_release.status_code == 404:
            url_release = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
            res_release = requests.get(url_release, headers=HEADERS, timeout=10)

        if res_release.status_code != 200:
            print(f"Error al conectar con GitHub Releases: {res_release.status_code}")
            print("[UI] DONE") # Avísale a la interfaz que terminamos (con error)
            return
            
        datos_release = res_release.json()
        assets = datos_release.get("assets", [])
        
        if not assets:
            print("El release está vacío. No hay archivos por descargar.")
            print("[UI] DONE")
            return

        # 2. Leer estado local
        config_datos = cargar_configuracion()
        fechas_locales = config_datos.get("Fechas_Archivos", {})
        
        # 3. Determinar qué archivos necesitan descarga
        descargas_necesarias = []
        for asset in assets:
            nombre = asset["name"]
            fecha_nube = asset.get("updated_at", "")
            ruta_local = resolver_ruta_local(nombre)
            fecha_local = fechas_locales.get(nombre, "")
            
            # Descargar si: No existe el archivo físicamente, o la fecha en la nube es más nueva
            if not os.path.exists(ruta_local) or fecha_nube > fecha_local:
                descargas_necesarias.append(asset)
                
        # Si no hay nada que descargar, salimos limpiamente
        if not descargas_necesarias:
            print("[UI] DONE")
            return

        # 4. Iniciar proceso de descarga reportando a la UI de Menu.py
        total_tareas = len(descargas_necesarias)
        print(f"[UI] TAREAS:{total_tareas}", flush=True)
        
        hubo_cambio_menu = False
        hubo_cambio_actualizador = False
        tarea_actual = 0
        
        for asset in descargas_necesarias:
            tarea_actual += 1
            nombre_archivo = asset["name"]
            url_descarga = asset["browser_download_url"]
            fecha_nube = asset.get("updated_at", "")
            
            print(f"[UI] PROGRESO:{tarea_actual}|Descargando {nombre_archivo}...", flush=True)
            
            if nombre_archivo.lower() == "menu.exe":
                hubo_cambio_menu = True
            elif nombre_archivo.lower() == "actualizador.exe":
                hubo_cambio_actualizador = True
                
            ruta_local = resolver_ruta_local(nombre_archivo)
            os.makedirs(os.path.dirname(ruta_local), exist_ok=True)
            
            # Descarga por streaming (ideal para binarios pesados)
            res_file = requests.get(url_descarga, headers=HEADERS, stream=True, timeout=15)
            if res_file.status_code == 200:
                with open(ruta_local, "wb") as f:
                    for chunk in res_file.iter_content(chunk_size=8192):
                        if chunk: # Filtra fragmentos vacíos
                            f.write(chunk)
                # Actualizar el diccionario local con la nueva fecha de este archivo
                fechas_locales[nombre_archivo] = fecha_nube
            else:
                print(f"Error HTTP {res_file.status_code} al descargar {nombre_archivo}")
                
        # 5. Guardar configuraciones y banderas finales
        guardar_estado(fechas_locales, hubo_cambio_menu, hubo_cambio_actualizador)
        
        print("[UI] DONE", flush=True)
        
    except Exception as e:
        print(f"Error crítico durante la actualización: {e}")
        print("[UI] DONE")

        
if __name__ == "__main__":
    actualizar_desde_releases()