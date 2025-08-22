import os
import json
import csv
import re

def extraer_textos():
    """
    Analiza los archivos de la carpeta 'ingles', extrae los textos en inglés
    y los guarda en un archivo CSV para su traducción.
    """
    carpeta_ingles = 'ingles'
    carpeta_textos = 'textos'

    # Asegurarse de que las carpetas de entrada y salida existan
    if not os.path.isdir(carpeta_ingles):
        print(f"Error: La carpeta '{carpeta_ingles}' no se encuentra.")
        print("Por favor, asegúrate de que tus archivos .txt estén dentro de una carpeta llamada 'ingles'.")
        return

    if not os.path.exists(carpeta_textos):
        os.makedirs(carpeta_textos)

    textos_para_csv = []
    mapa_traduccion = []

    # Expresión regular para encontrar la línea que contiene el JSON
    regex_script = re.compile(r'm_Script\s*=\s*"(.*)"', re.DOTALL)

    print(f"Buscando archivos en la carpeta '{carpeta_ingles}'...")

    # Recorrer todos los archivos en la carpeta 'ingles'
    for nombre_archivo in os.listdir(carpeta_ingles):
        if nombre_archivo.endswith('.txt'):
            ruta_archivo = os.path.join(carpeta_ingles, nombre_archivo)
            print(f"Procesando archivo: {ruta_archivo}")

            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()

            # Buscar el contenido del script JSON
            match = regex_script.search(contenido)
            if not match:
                print(f"  - Advertencia: No se encontró la línea 'm_Script' en {nombre_archivo}.")
                continue

            json_str = match.group(1)

            # Limpiar y decodificar el string JSON
            # Elimina el BOM (Byte Order Mark) si existe al inicio
            if json_str.startswith('\ufeff'):
                json_str = json_str[1:]

            # Reemplazar secuencias de escape de C# por las de JSON
            json_str = json_str.replace('\\r', '').replace('\\n', '').replace('\\"', '"')

            try:
                # Cargar los datos JSON
                data = json.loads(json_str)

                # Extraer los textos en inglés
                for item in data.get('Data', []):
                    if 'English' in item and 'ID' in item:
                        textos_para_csv.append(item['English'])
                        mapa_traduccion.append({
                            'id_original': item['ID'],
                            'archivo_original': ruta_archivo
                        })
            except json.JSONDecodeError as e:
                print(f"  - Error: No se pudo decodificar el JSON en {nombre_archivo}. Error: {e}")
                print(f"    Contenido problemático (primeros 100 caracteres): {json_str[:100]}")
                continue

    # Guardar los textos en el archivo CSV
    ruta_csv = os.path.join(carpeta_textos, 'traducciones.csv')
    with open(ruta_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Índice', 'Texto en Inglés'])
        for i, texto in enumerate(textos_para_csv, 1):
            writer.writerow([i, texto])

    # Guardar el mapa para la reimportación
    ruta_mapa = os.path.join(carpeta_textos, 'mapa.json')
    with open(ruta_mapa, 'w', encoding='utf-8') as f:
        json.dump(mapa_traduccion, f, indent=4, ensure_ascii=False)

    print("\n¡Proceso completado!")
    print(f"Se han extraído {len(textos_para_csv)} textos.")
    print(f"Puedes encontrar los textos para traducir en: {ruta_csv}")
    print(f"El archivo de mapeo se ha guardado en: {ruta_mapa}")

if __name__ == '__main__':
    extraer_textos()
