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

# --- Función Principal (v30 - Importador Quirúrgico Restaurado y Correcto) ---
def importar_traducciones_final():
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
    with open(ruta_csv, 'r', encoding='utf-8-sig') as f:
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

    # 3. Agrupar por archivo para eficiencia
    archivos_a_modificar = defaultdict(list)
    for entrada in mapa_traduccion:
        archivos_a_modificar[entrada['archivo_original']].append(entrada)

    # 4. Modificar cada archivo
    print("Aplicando traducciones con la lógica v30 (quirúrgica y segura)...")
    for archivo_path, mods in sorted(archivos_a_modificar.items()):
        print(f"  - Procesando archivo: {archivo_path}")

        try:
            with open(archivo_path, 'r', encoding='utf-8-sig') as f:
                contenido_total = f.read()
        except Exception as e:
            print(f"    - ERROR: No se pudo leer el archivo {archivo_path}. Error: {e}")
            continue

        for mod in mods:
            id_original = mod['id_original']
            formato_envuelto = mod['formato_envuelto']

            if id_original not in traducciones_por_id:
                continue

            id_escaped = re.escape(id_original)

            # Regex robusta para encontrar el valor de English para un ID
            patron_busqueda = re.compile(
                r'(\\"ID\\"\s*:\s*\\"' + id_escaped +
                r'\\".*?\\"English\\"\s*:\s*\\")' + # Grupo 1: Todo hasta la comilla inicial del valor
                r'(.*?)' +                         # Grupo 2: El valor actual
                r'(\\"(?=[,\}]))'                   # Grupo 3: La comilla de cierre
                , re.DOTALL
            )

            # Función de reemplazo segura con lambda
            def replacer_final(match):
                grupo_inicio = match.group(1)
                grupo_fin = match.group(3)

                texto_traducido_nuevo = traducciones_por_id[id_original]
                texto_traducido_escaped = texto_traducido_nuevo.replace('\\', '\\\\').replace('"', '\\"')

                if formato_envuelto:
                    texto_final = f'\\\\"{texto_traducido_escaped}\\\\"'
                else:
                    texto_final = texto_traducido_escaped

                return f'{grupo_inicio}{texto_final}{grupo_fin}'

            contenido_total, num_reemplazos = patron_busqueda.subn(replacer_final, contenido_total, count=1)

            if num_reemplazos == 0:
                print(f"    - ADVERTENCIA: No se pudo encontrar/reemplazar el texto para el ID {id_original}")

        # Guardar el archivo final
        nombre_archivo_salida = os.path.basename(archivo_path)
        ruta_salida = os.path.join(carpeta_espanol, nombre_archivo_salida)
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            f.write(contenido_total)

    print("\n¡Proceso de importación completado!")

if __name__ == '__main__':
    importar_traducciones_final()
