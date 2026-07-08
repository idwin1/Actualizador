import os
import sys
import requests

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
COMMIT_LOG_FILE = os.path.join(BASE_DIR, "ultimo_commit.txt")

def obtener_ultimo_commit_local():
    if os.path.exists(COMMIT_LOG_FILE):
        with open(COMMIT_LOG_FILE, "r") as f:
            return f.read().strip()
    return ""

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
        sha_local = obtener_ultimo_commit_local()
        
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
            with open(COMMIT_LOG_FILE, "w") as f:
                f.write(sha_remoto)
            print("¡Actualización completada!")

    except Exception as e:
        print(f"Error en actualización: {e}")

if __name__ == "__main__":
    actualizar_solo_cambios()