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
        next(reader)  # Omitir cabecera
        for row in reader:
            if row:
                traducciones.append(row[1])

    # Crear un iterador para consumir las traducciones una a una
    traducciones_iter = iter(traducciones)

    # 2. Agrupar modificaciones por archivo
    modificaciones = defaultdict(list)
    for entrada_mapa in mapa_traduccion:
        archivo = entrada_mapa['archivo_original']
        modificaciones[archivo].append(entrada_mapa)

    # 3. Aplicar las modificaciones
    print("Aplicando traducciones con la lógica v4 (la más segura)...")
    for archivo_original, mods in modificaciones.items():
        print(f"  - Modificando {archivo_original}")

        with open(archivo_original, 'r', encoding='utf-8') as f:
            contenido_total = f.read()

        for mod in mods:
            estructura = mod['estructura']

            # Reconstruir el texto original y el traducido
            texto_original = get_original_text(estructura)
            texto_traducido = reconstruir_texto(estructura, traducciones_iter)

            # Escapar para el reemplazo en el JSON
            original_escaped_json = json.dumps(texto_original, ensure_ascii=False)[1:-1]
            traducido_escaped_json = json.dumps(texto_traducido, ensure_ascii=False)[1:-1]

            # Patrón de búsqueda con regex, escapando el texto original para seguridad
            patron_busqueda_regex = f'(\\"English\\"\\s*:\\s*\\"){re.escape(original_escaped_json)}(\\")'

            # FUNCIÓN DE REEMPLAZO (LA SOLUCIÓN DEFINITIVA)
            # Usamos una función 'lambda' para el reemplazo. Esto trata el texto
            # traducido como un texto literal y evita errores de 'bad escape'.
            def replacer(match):
                # Reconstruimos la cadena: (grupo 1) + texto traducido + (grupo 2)
                # match.group(1) es '\"English\":\"'
                # match.group(2) es '\"'
                return f'{match.group(1)}{traducido_escaped_json}{match.group(2)}'

            # Aplicar el reemplazo usando re.subn y la función replacer
            nuevo_contenido, num_reemplazos = re.subn(patron_busqueda_regex, replacer, contenido_total, count=1)

            if num_reemplazos > 0:
                contenido_total = nuevo_contenido
            else:
                print(f"  - ADVERTENCIA FINAL: No se encontró el patrón para el ID {mod['id_original']} en {archivo_original}.")
                print(f"    Buscando (regex): {patron_busqueda_regex}")

        # Guardar el archivo modificado
        nombre_archivo_salida = os.path.basename(archivo_original)
        ruta_salida = os.path.join(carpeta_espanol, nombre_archivo_salida)

        with open(ruta_salida, 'w', encoding='utf-8') as f:
            f.write(contenido_total)

    print("\n¡Proceso de importación v4 completado!")
    print(f"Los archivos traducidos se han guardado en la carpeta: '{carpeta_espanol}'")

if __name__ == '__main__':
    importar_traducciones_actualizado()
