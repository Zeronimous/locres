import os
import json
import csv
import re
from collections import defaultdict

# --- Lógica de Reconstrucción ---
def reconstruir_texto(structure, traducciones_iter):
    resultado = []
    for part in structure:
        tipo = part.get('type')
        if tipo == 'text':
            if part['content'].strip():
                try:
                    resultado.append(next(traducciones_iter))
                except StopIteration:
                    print("Error: Faltan traducciones en el archivo CSV.")
                    resultado.append(part['content'])
            else:
                resultado.append(part['content'])
        elif tipo == 'variable':
            resultado.append(part['content'])
        elif tipo == 'tag_html':
            contenido_hijo = reconstruir_texto(part['children'], traducciones_iter)
            tag_name = part['tag'].split('=')[0]
            resultado.append(f"<{part['tag']}>{contenido_hijo}</{tag_name}>")
        elif tipo == 'tag_brace':
            contenido_hijo = reconstruir_texto(part['children'], traducciones_iter)
            resultado.append(f"{{{part['tag']}}}{contenido_hijo}{{/{part['tag']}}}")
    return "".join(resultado)

# --- Función Principal (Lógica v6 - Quirúrgica) ---

def importar_traducciones_quirurgico():
    carpeta_textos = 'textos'
    carpeta_espanol = 'espanol'

    ruta_csv = os.path.join(carpeta_textos, 'traducciones.csv')
    ruta_mapa = os.path.join(carpeta_textos, 'mapa.json')

    if not all(os.path.exists(p) for p in [ruta_csv, ruta_mapa]):
        print("Error: Faltan los archivos 'traducciones.csv' o 'mapa.json'.")
        return

    if not os.path.exists(carpeta_espanol):
        os.makedirs(carpeta_espanol)

    # 1. Cargar datos
    print("Cargando mapa y traducciones...")
    with open(ruta_mapa, 'r', encoding='utf-8') as f:
        mapa_traduccion = json.load(f)

    traducciones_csv = []
    with open(ruta_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if row:
                traducciones_csv.append(row[1])

    # 2. Preparar un diccionario con las traducciones por ID
    traducciones_por_id = {}
    traducciones_iter = iter(traducciones_csv)
    for entrada_mapa in mapa_traduccion:
        id_original = entrada_mapa['id_original']
        estructura = entrada_mapa['estructura']
        texto_traducido = reconstruir_texto(estructura, traducciones_iter)
        traducciones_por_id[id_original] = texto_traducido

    # 3. Agrupar IDs por archivo
    archivos_a_modificar = defaultdict(list)
    for entrada in mapa_traduccion:
        archivos_a_modificar[entrada['archivo_original']].append(entrada['id_original'])

    # 4. Modificar cada archivo de forma quirúrgica
    print("Aplicando traducciones con la lógica v6 (quirúrgica)...")
    for archivo_path, ids_en_archivo in archivos_a_modificar.items():
        print(f"  - Procesando archivo: {archivo_path}")

        try:
            # Usar 'utf-8-sig' para leer, garantizando que se maneja el BOM
            with open(archivo_path, 'r', encoding='utf-8-sig') as f:
                contenido_total = f.read()
        except Exception as e:
            print(f"    - ERROR: No se pudo leer el archivo {archivo_path}. Error: {e}")
            continue

        # Realizar el reemplazo para cada ID perteneciente a este archivo
        for id_original in ids_en_archivo:
            if id_original not in traducciones_por_id:
                continue

            # Escapar el ID para usarlo en la regex de forma segura
            id_escaped = re.escape(id_original)

            # Construir una regex para encontrar el objeto JSON por su ID
            # Esto es complejo: busca {"ID":"el_id", ... "English":"valor", ...}
            # y captura solo el valor de "English" para ese ID.
            patron_obj_id = re.compile(
                r'(\{\s*\\"ID\\"\s*:\s*\\"' + id_escaped + r'\\"\s*,' +  # Busca {"ID":"id",
                r'.*?' + # Cualquier caracter hasta llegar a English
                r'\\"English\\"\s*:\s*\\")' + # Busca "English":
                r'(.*?)' + # Captura el valor actual de English (Grupo 2)
                r'(\\"' + # Captura la comilla de cierre (Grupo 3)
                r'[,\}])', # El valor termina en comilla y luego , o }
                re.DOTALL
            )

            # Función de reemplazo que inserta el texto traducido
            def replacer_quirurgico(match):
                grupo_inicio = match.group(1) # {"ID"...,"English":
                # grupo_contenido_antiguo = match.group(2)
                grupo_fin = match.group(3) # "} o ",

                # Obtener la traducción y escaparla para JSON
                texto_traducido_nuevo = traducciones_por_id[id_original]
                texto_traducido_escaped = json.dumps(texto_traducido_nuevo, ensure_ascii=False)[1:-1]

                return f'{grupo_inicio}{texto_traducido_escaped}{grupo_fin}'

            # Aplicar el reemplazo en el contenido del archivo
            contenido_total, num_reemplazos = patron_obj_id.subn(replacer_quirurgico, contenido_total, count=1)

            if num_reemplazos == 0:
                print(f"    - ADVERTENCIA: No se pudo encontrar/reemplazar el texto para el ID {id_original}")

        # Guardar el archivo final
        nombre_archivo_salida = os.path.basename(archivo_path)
        ruta_salida = os.path.join(carpeta_espanol, nombre_archivo_salida)
        # Escribir con 'utf-8' es seguro, ya que el contenido no-ASCII no se ha tocado
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            f.write(contenido_total)

    print("\n¡Proceso de importación v6 completado!")

if __name__ == '__main__':
    importar_traducciones_quirurgico()
