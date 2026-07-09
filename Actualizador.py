import os
import sys
import requests
import subprocess
import json

# Lista de librerías externas que requiere tu proyecto
LIBRERIAS_REQUERIDAS = {
    "colorama": "colorama"
}

def verificar_e_instalar_librerIAS():
    """Revisa si las librerías están instaladas; si no, las instala automáticamente"""
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

from colorama import init, Fore, Style

init(autoreset=True)
REPO_OWNER = "idwin1"
REPO_NAME = "Ejecutables"
RAMA = "main"

def obtener_ruta_apps_real():
    """Detecta con precisión la carpeta física real donde reside este ejecutable de forma externa"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        return os.path.dirname(os.path.abspath(__file__))

# Forzamos a que el directorio de trabajo apunte siempre a la carpeta física 'apps'
BASE_DIR = obtener_ruta_apps_real()
# -------------------------------------------------------------------------
# CARGA DE CONFIGURACIÓN SEGURA
# -------------------------------------------------------------------------

CONFIG_FILE  = os.path.join(BASE_DIR, "config.json")

def cargar_configuracion():
    if not os.path.exists(CONFIG_FILE):
        print(Fore.RED + f"[❌] Error crítico: No se encontró el archivo de configuración '{CONFIG_FILE}'.")
        sys.exit(1)
        
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(Fore.RED + f"[❌] Error al cargar la configuración: {e}")
        sys.exit(1)

def guardar_ultimo_commit(nuevo_commit):
    """Actualiza de forma segura el campo 'ultimo_commit' dentro del archivo JSON"""
    try:
        # 1. Volvemos a leer el estado actual del JSON para no perder otros datos
        datos = cargar_configuracion()

        # Aseguramos que la estructura de diccionario exista antes de guardar
        if "Ultimo_Commit" not in datos or not isinstance(datos["Ultimo_Commit"], dict):
            datos["Ultimo_Commit"] = {}

        # 2. Actualizamos o creamos la clave del commit
        datos["Ultimo_Commit"]["commit"] = nuevo_commit
        
        # 3. Guardamos los cambios de vuelta en el archivo de manera ordenada
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        print(Fore.RED + f"[⚠️] No se pudo actualizar el commit en el JSON: {e}")

# Carga inicial de datos
config_datos = cargar_configuracion()




def actualizar_solo_cambios():
    print("Verificando actualizaciones para la carpeta 'apps'...")
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{RAMA}"
    headers = {'User-Agent': 'request'}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            print(f"Error al conectar con GitHub: {response.status_code}")
            return
            
        data = response.json()
        sha_remoto = data["sha"]
        # Usamos .get() de forma anidada. Si no existe, devuelve un string vacío ""
        sha_local = config_datos.get("Ultimo_Commit", {}).get("commit", "")
        
        if sha_remoto == sha_local:
            print("Todo está actualizado.")
            return

        print(f"Nueva versión detectada: {sha_remoto[:7]}")
        
        if sha_local:
            url_cambios = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/compare/{sha_local}...{sha_remoto}"
        else:
            url_cambios = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{sha_remoto}"

        res_cambios = requests.get(url_cambios, headers=headers, timeout=5)
        
        if res_cambios.status_code == 200:
            cambios_data = res_cambios.json()
            archivos_cambiados = cambios_data.get("files", [])
            
            for archivo in archivos_cambiados:
                nombre_archivo = archivo["filename"]
                estado = archivo["status"]
                
                # --- REGLA DE REDIRECCIÓN PARA EL MENÚ ---
                # Si el archivo modificado en el repo es el Menu.exe de la raíz,
                # lo guardamos temporalmente en apps como Menu_NUEVO.exe
                if nombre_archivo == "Menu.exe":
                    ruta_local_archivo = os.path.join(BASE_DIR, "Menu_NUEVO.exe")
                else:
                    ruta_local_archivo = os.path.join(BASE_DIR, nombre_archivo)
                
                url_raw = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{sha_remoto}/{nombre_archivo}"
                
                if estado in ["modified", "added"]:
                    print(f"Descargando: {nombre_archivo}...")
                    os.makedirs(os.path.dirname(ruta_local_archivo), exist_ok=True)
                    
                    res_file = requests.get(url_raw)
                    if res_file.status_code == 200:
                        with open(ruta_local_archivo, "wb") as f:
                            f.write(res_file.content)
                            
                elif estado == "removed":
                    if os.path.exists(ruta_local_archivo):
                        print(f"Eliminando: {ruta_local_archivo}...")
                        os.remove(ruta_local_archivo)
            
            # Guardar el nuevo SHA una vez completada la descarga exitosa
            
            guardar_ultimo_commit(sha_remoto)
            print("¡Actualización completada!")

    except Exception as e:
        print(f"Error en actualización: {e}")

if __name__ == "__main__":
    actualizar_solo_cambios()