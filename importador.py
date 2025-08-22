import os
import json
import csv
import re
from collections import defaultdict

def importar_traducciones():
    """
    Lee los textos traducidos desde un archivo CSV y los reinserta en
    copias de los archivos originales, guardándolos en la carpeta 'español'.
    """
    carpeta_textos = 'textos'
    carpeta_español = 'espanol'

    ruta_csv = os.path.join(carpeta_textos, 'traducciones.csv')
    ruta_mapa = os.path.join(carpeta_textos, 'mapa.json')

    # Validar que los archivos necesarios existan
    if not os.path.exists(ruta_csv):
        print(f"Error: El archivo de traducciones '{ruta_csv}' no se encuentra.")
        print("Asegúrate de haber guardado tus traducciones en ese archivo.")
        return
    if not os.path.exists(ruta_mapa):
        print(f"Error: El archivo de mapeo '{ruta_mapa}' no se encuentra.")
        return

    if not os.path.exists(carpeta_español):
        os.makedirs(carpeta_español)

    # --- 1. Cargar datos ---
    # Cargar el mapa de traducción
    with open(ruta_mapa, 'r', encoding='utf-8') as f:
        mapa_traduccion = json.load(f)

    # Cargar las traducciones del CSV
    traducciones = []
    with open(ruta_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Omitir la cabecera
        for row in reader:
            if row: # Asegurarse de que la fila no esté vacía
                traducciones.append(row[1])

    if len(traducciones) != len(mapa_traduccion):
        print("Error: El número de traducciones en el CSV no coincide con el mapa.")
        return

    # --- 2. Preparar los datos para la modificación ---
    # Agrupar las modificaciones por archivo para eficiencia
    modificaciones_por_archivo = defaultdict(list)

    # Expresión regular para encontrar el JSON y el texto en inglés original
    regex_script = re.compile(r'(m_Script\s*=\s*")(.*)(")', re.DOTALL)

    # Cargar los textos originales para cada entrada del mapa
    for i, entrada_mapa in enumerate(mapa_traduccion):
        id_original = entrada_mapa['id_original']
        archivo_original = entrada_mapa['archivo_original']

        # Necesitamos el texto original para poder reemplazarlo
        # Esto es más seguro que solo usar el ID
        # Para obtenerlo, leemos el JSON original
        with open(archivo_original, 'r', encoding='utf-8') as f:
            contenido_original = f.read()

        match = regex_script.search(contenido_original)
        if not match:
            continue

        json_str = match.group(2)
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
        json_str = json_str.replace('\\r', '').replace('\\n', '').replace('\\"', '"')

        try:
            data = json.loads(json_str)
            for item in data.get('Data', []):
                if item.get('ID') == id_original:
                    texto_original_ingles = item['English']
                    modificaciones_por_archivo[archivo_original].append({
                        'texto_original': texto_original_ingles,
                        'texto_traducido': traducciones[i]
                    })
                    break
        except json.JSONDecodeError:
            print(f"Advertencia: No se pudo leer el JSON del archivo original {archivo_original} al buscar el texto original.")
            continue

    # --- 3. Aplicar las modificaciones ---
    print("Aplicando traducciones...")
    for archivo_original, mods in modificaciones_por_archivo.items():
        print(f"  - Modificando {archivo_original}")

        with open(archivo_original, 'r', encoding='utf-8') as f:
            contenido = f.read()

        # Realizar el reemplazo para cada texto en el contenido del archivo
        for mod in mods:
            # El texto original y traducido deben ser escapados para formato JSON
            original_text_json = json.dumps(mod['texto_original'])[1:-1]
            traducido_text_json = json.dumps(mod['texto_traducido'])[1:-1]

            # El patrón de búsqueda debe coincidir con el formato del archivo original,
            # que tiene las comillas escapadas (ej: \"English\":\"Hello\")
            patron_busqueda = f'\\"English\\":\\"{original_text_json}\\"'
            patron_reemplazo = f'\\"English\\":\\"{traducido_text_json}\\"'

            # Reemplazar solo la primera ocurrencia para evitar errores si el mismo texto aparece varias veces
            contenido = contenido.replace(patron_busqueda, patron_reemplazo, 1)

        # Guardar el archivo modificado en la carpeta 'español'
        nombre_archivo_salida = os.path.basename(archivo_original)
        ruta_salida = os.path.join(carpeta_español, nombre_archivo_salida)

        with open(ruta_salida, 'w', encoding='utf-8') as f:
            f.write(contenido)

    print("\n¡Proceso de importación completado!")
    print(f"Los archivos traducidos se han guardado en la carpeta: '{carpeta_español}'")

if __name__ == '__main__':
    importar_traducciones()
