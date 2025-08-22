import os
import json
import csv
import re
import codecs
from collections import defaultdict

# --- Lógica de Reconstrucción ---
# Esta función sigue siendo necesaria para construir la cadena traducida final a partir de los fragmentos.
def reconstruir_texto(structure, traducciones_iter):
    """
    Reconstruye el texto final a partir de la estructura y una lista
    de fragmentos traducidos. Es una función recursiva.
    """
    resultado = []
    for part in structure:
        tipo = part.get('type')
        if tipo == 'text':
            # Si el texto original estaba vacío o solo espacios, no está en el CSV.
            if part['content'].strip():
                try:
                    # Tomar el siguiente texto de la lista de traducciones
                    resultado.append(next(traducciones_iter))
                except StopIteration:
                    print("Error: Faltan traducciones en el archivo CSV para reconstruir una frase.")
                    # Añadir el contenido original como fallback
                    resultado.append(part['content'])
            else:
                # Añadir el texto original si estaba vacío o era solo espacio
                resultado.append(part['content'])

        elif tipo == 'variable':
            resultado.append(part['content'])

        elif tipo == 'tag_html':
            # Reconstruir el contenido de los hijos recursivamente
            contenido_hijo = reconstruir_texto(part['children'], traducciones_iter)
            # Envolver con la etiqueta HTML
            tag_name = part['tag'].split('=')[0] # Para <color=..> nos quedamos con "color"
            resultado.append(f"<{part['tag']}>{contenido_hijo}</{tag_name}>")

        elif tipo == 'tag_brace':
            # Reconstruir el contenido de los hijos recursivamente
            contenido_hijo = reconstruir_texto(part['children'], traducciones_iter)
            # Envolver con la etiqueta de llaves
            resultado.append(f"{{{part['tag']}}}{contenido_hijo}{{/{part['tag']}}}")

    return "".join(resultado)

# --- Función Principal (Lógica v5) ---

def importar_traducciones_actualizado():
    carpeta_textos = 'textos'
    carpeta_espanol = 'espanol'

    ruta_csv = os.path.join(carpeta_textos, 'traducciones.csv')
    ruta_mapa = os.path.join(carpeta_textos, 'mapa.json')

    if not all(os.path.exists(p) for p in [ruta_csv, ruta_mapa]):
        print("Error: Faltan los archivos 'traducciones.csv' o 'mapa.json'.")
        return

    if not os.path.exists(carpeta_espanol):
        os.makedirs(carpeta_espanol)

    # 1. Cargar todos los datos necesarios
    print("Cargando mapa y traducciones...")
    with open(ruta_mapa, 'r', encoding='utf-8') as f:
        mapa_traduccion = json.load(f)

    traducciones_csv = []
    with open(ruta_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader) # Omitir cabecera
        for row in reader:
            if row:
                traducciones_csv.append(row[1])

    # 2. Preparar un diccionario con las traducciones reconstruidas por ID
    traducciones_por_id = {}
    traducciones_iter = iter(traducciones_csv)
    for entrada_mapa in mapa_traduccion:
        id_original = entrada_mapa['id_original']
        estructura = entrada_mapa['estructura']
        texto_traducido = reconstruir_texto(estructura, traducciones_iter)
        traducciones_por_id[id_original] = texto_traducido

    # 3. Agrupar archivos a modificar para procesar cada archivo una sola vez
    archivos_a_modificar = sorted(list(set(e['archivo_original'] for e in mapa_traduccion)))

    # 4. Modificar cada archivo
    print("Aplicando traducciones con la lógica v5 (edición de datos)...")
    regex_script_line = re.compile(r'(m_Script\s*=\s*")(.*)(")', re.DOTALL)

    for archivo_path in archivos_a_modificar:
        print(f"  - Procesando archivo: {archivo_path}")

        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido_total = f.read()
        except Exception as e:
            print(f"    - ERROR: No se pudo leer el archivo {archivo_path}. Error: {e}")
            continue

        match = regex_script_line.search(contenido_total)
        if not match:
            print(f"    - ADVERTENCIA: No se encontró 'm_Script' en {archivo_path}.")
            continue

        # Capturamos el contenido original del script para reemplazarlo al final
        script_line_prefix = match.group(1) # m_Script = "
        json_str_raw = match.group(2)
        script_line_suffix = match.group(3) # "

        # Decodificar y cargar la data original
        data = None
        try:
            temp_json_str = json_str_raw
            if temp_json_str.startswith('\ufeff'):
                temp_json_str = temp_json_str[1:]
            json_str_decoded = codecs.decode(temp_json_str, 'unicode_escape')
            data = json.loads(json_str_decoded)
        except Exception as e:
            print(f"    - ERROR: No se pudo decodificar o cargar el JSON de {archivo_path}. Error: {e}")
            continue

        # Modificar la data en memoria
        modificado = False
        for item in data.get('Data', []):
            if item.get('ID') in traducciones_por_id:
                item['English'] = traducciones_por_id[item['ID']]
                modificado = True

        # Si se modificó algo, volver a generar el string y reemplazarlo en el archivo
        if modificado:
            # Convertir la data modificada a un string JSON
            nuevo_json_str = json.dumps(data, ensure_ascii=False)

            # Escapar el string JSON para que sea un literal de C# válido
            nuevo_json_escaped = nuevo_json_str.replace('\\', '\\\\').replace('"', '\\"')

            # Reconstruir la línea completa de m_Script
            linea_script_antigua = match.group(0)
            linea_script_nueva = f"{script_line_prefix}{nuevo_json_escaped}{script_line_suffix}"

            # Reemplazar la línea de script antigua por la nueva en el contenido total
            contenido_total = contenido_total.replace(linea_script_antigua, linea_script_nueva)

            # Guardar el archivo final
            nombre_archivo_salida = os.path.basename(archivo_path)
            ruta_salida = os.path.join(carpeta_espanol, nombre_archivo_salida)
            with open(ruta_salida, 'w', encoding='utf-8') as f:
                f.write(contenido_total)
        else:
            print(f"    - ADVERTENCIA: No se realizó ninguna modificación en {archivo_path}, aunque se esperaba.")

    print("\n¡Proceso de importación v5 completado!")

if __name__ == '__main__':
    importar_traducciones_actualizado()
