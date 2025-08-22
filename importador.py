import os
import json
import csv
import re
from collections import defaultdict

# --- Lógica de Reconstrucción ---

def reconstruir_texto(structure, traducciones_iter):
    """
    Reconstruye el texto final a partir de la estructura y una lista
    de fragmentos traducidos. Es una función recursiva.
    """
    resultado = []
    for part in structure:
        tipo = part.get('type')
        if tipo == 'text':
            if part['content'].strip():
                try:
                    resultado.append(next(traducciones_iter))
                except StopIteration:
                    print("Error: Faltan traducciones en el archivo CSV para reconstruir una frase.")
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

# --- Lógica para encontrar el texto original ---

def get_original_text(structure):
    """
    Reconstruye el texto original desde la estructura para poder encontrarlo
    en el archivo y reemplazarlo.
    """
    resultado = []
    for part in structure:
        tipo = part.get('type')
        if tipo in ('text', 'variable'):
            resultado.append(part['content'])
        elif tipo == 'tag_html':
            contenido_hijo = get_original_text(part['children'])
            tag_name = part['tag'].split('=')[0]
            resultado.append(f"<{part['tag']}>{contenido_hijo}</{tag_name}>")
        elif tipo == 'tag_brace':
            contenido_hijo = get_original_text(part['children'])
            resultado.append(f"{{{part['tag']}}}{contenido_hijo}{{/{part['tag']}}}")
    return "".join(resultado)


# --- Función Principal ---

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

    # 1. Cargar datos
    with open(ruta_mapa, 'r', encoding='utf-8') as f:
        mapa_traduccion = json.load(f)

    traducciones = []
    with open(ruta_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if row:
                traducciones.append(row[1])

    traducciones_iter = iter(traducciones)

    # 2. Agrupar modificaciones por archivo
    modificaciones = defaultdict(list)
    for entrada_mapa in mapa_traduccion:
        archivo = entrada_mapa['archivo_original']
        modificaciones[archivo].append(entrada_mapa)

    # 3. Aplicar las modificaciones
    print("Aplicando traducciones con la lógica v3 (más robusta)...")
    for archivo_original, mods in modificaciones.items():
        print(f"  - Modificando {archivo_original}")

        with open(archivo_original, 'r', encoding='utf-8') as f:
            contenido_total = f.read()

        for mod in mods:
            estructura = mod['estructura']

            texto_original = get_original_text(estructura)
            texto_traducido = reconstruir_texto(estructura, traducciones_iter)

            # Escapar para el reemplazo en el JSON
            original_escaped = json.dumps(texto_original)[1:-1]
            traducido_escaped = json.dumps(texto_traducido)[1:-1]

            # Construir patrones de búsqueda y reemplazo usando REGEX para más flexibilidad
            # re.escape se asegura de que caracteres especiales como ( ) [ ] . ? no rompan la regex
            patron_busqueda_regex = f'(\\"English\\"\\s*:\\s*\\"){re.escape(original_escaped)}(\\")'
            # El reemplazo mantiene el formato original, pero con el texto traducido
            patron_reemplazo_regex = f'\\1{traducido_escaped}\\2'

            # Aplicar el reemplazo usando re.sub
            nuevo_contenido, num_reemplazos = re.subn(patron_busqueda_regex, patron_reemplazo_regex, contenido_total, count=1)

            if num_reemplazos > 0:
                contenido_total = nuevo_contenido
            else:
                print(f"  - ADVERTENCIA: No se encontró el patrón para el ID {mod['id_original']} en {archivo_original}.")
                print(f"    Buscando (regex): {patron_busqueda_regex}")

        # Guardar el archivo modificado
        nombre_archivo_salida = os.path.basename(archivo_original)
        ruta_salida = os.path.join(carpeta_espanol, nombre_archivo_salida)

        with open(ruta_salida, 'w', encoding='utf-8') as f:
            f.write(contenido_total)

    print("\n¡Proceso de importación v3 completado!")
    print(f"Los archivos traducidos se han guardado en la carpeta: '{carpeta_espanol}'")

if __name__ == '__main__':
    importar_traducciones_actualizado()
