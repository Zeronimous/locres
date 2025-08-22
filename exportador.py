import os
import json
import csv
import re
import codecs

# --- Marcadores y Expresiones Regulares (Versión 2) ---

# Expresión para excluir textos que son solo una variable interna (ej: {sigh1}, {Wrap})
EXCLUSION_PATTERN = re.compile(r'^\{[^}]+\}$')

# Regex para marcadores estilo HTML: <tag>...</tag> o <tag=value>...</tag>
# Grupo 1: El tag completo (ej: <T>...</T>)
# Grupo 2: El nombre del tag (ej: T, color)
# Grupo 3: El atributo (ej: =#ff003c)
# Grupo 4: El contenido interno (ej: under the wire mesh)
HTML_TAG_REGEX = r'(<([a-zA-Z0-9]+)([^>]*)>(.*?)</\2>)'

# Regex para marcadores estilo llave: {tag}...{/tag}
# Se ha corregido para que el backreference (\6) funcione correctamente dentro del OR de la regex principal.
# Grupo 5: El tag completo (ej: {i}...{/i})
# Grupo 6: El nombre del tag (ej: i)
# Grupo 7: El contenido interno (ej: ...Rattle...)
BRACE_TAG_REGEX = r'(\{([a-zA-Z0-9]+)\}(.*?)\{/\6\})'

# Regex para variables que no se traducen: {p1}, {x1}, {Wrap}, etc.
# Grupo 8: La variable completa (ej: {x1})
VARIABLE_REGEX = r'(\{[^}]+\})'

# Combinamos todas las expresiones en una sola. El orden es importante.
# Buscamos tags HTML, o tags de llave, o variables.
PARSER_REGEX = re.compile(f'{HTML_TAG_REGEX}|{BRACE_TAG_REGEX}|{VARIABLE_REGEX}', re.DOTALL)

# --- Lógica de Análisis (Parsing) ---

def parse_text(text):
    """
    Analiza un texto y lo descompone en una estructura de nodos anidada.
    """
    parts = []
    last_index = 0

    for match in PARSER_REGEX.finditer(text):
        start, end = match.span()
        # 1. Añadir el texto plano que está ANTES del marcador encontrado
        if start > last_index:
            parts.append({'type': 'text', 'content': text[last_index:start]})

        # 2. Determinar qué tipo de marcador se encontró y procesarlo
        # Los grupos de captura nos dicen qué regex coincidió
        html_full, html_tag, html_attr, html_content, \
        brace_full, brace_tag, brace_content, \
        variable_full = match.groups()

        if html_full:
            # Coincidió un tag HTML: <T>...</T> o <color=...>...</color>
            # Analizamos su contenido de forma recursiva para manejar anidación
            children = parse_text(html_content)
            # Guardamos el nombre del tag y su atributo (si lo tiene)
            full_tag = f"{html_tag}{html_attr}" if html_attr else html_tag
            parts.append({'type': 'tag_html', 'tag': full_tag, 'children': children})

        elif brace_full:
            # Coincidió un tag de llave: {i}...{/i}
            children = parse_text(brace_content)
            parts.append({'type': 'tag_brace', 'tag': brace_tag, 'children': children})

        elif variable_full:
            # Coincidió una variable: {p1}
            parts.append({'type': 'variable', 'content': variable_full})

        last_index = end

    # 3. Añadir el texto plano que queda DESPUÉS del último marcador
    if last_index < len(text):
        parts.append({'type': 'text', 'content': text[last_index:]})

    return parts

def flatten_structure_for_csv(structure, text_list):
    """
    Recorre la estructura de nodos y extrae solo el texto traducible para el CSV.
    """
    for part in structure:
        if part['type'] == 'text' and part['content'].strip():
            text_list.append(part['content'])
        elif part.get('children'):
            flatten_structure_for_csv(part['children'], text_list)

# --- Función Principal ---

def extraer_textos_actualizado():
    carpeta_ingles = 'ingles'
    carpeta_textos = 'textos'

    if not os.path.isdir(carpeta_ingles):
        print(f"Error: La carpeta '{carpeta_ingles}' no existe.")
        return

    if not os.path.exists(carpeta_textos):
        os.makedirs(carpeta_textos)

    csv_rows = []
    mapa_traduccion_final = []
    base_index = 1

    regex_script_line = re.compile(r'm_Script\s*=\s*"(.*)"', re.DOTALL)

    print(f"Buscando archivos en '{carpeta_ingles}' con la lógica v3 (sub-índices)...")

    for nombre_archivo in sorted(os.listdir(carpeta_ingles)):
        if not nombre_archivo.endswith('.txt'):
            continue

        ruta_archivo = os.path.join(carpeta_ingles, nombre_archivo)
        print(f"Procesando: {ruta_archivo}")

        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido_archivo = f.read()

        match = regex_script_line.search(contenido_archivo)
        if not match:
            continue

        json_str_raw = match.group(1)

        # Usar codecs.decode para un manejo robusto de secuencias de escape (ej: \", \\, \n)
        # Esto es clave para manejar correctamente textos con comillas internas.
        json_str_decoded = ""
        try:
            # Primero, quitamos el BOM si existe, que no es parte del escape
            if json_str_raw.startswith('\ufeff'):
                json_str_raw = json_str_raw[1:]

            # Decodificar la cadena para interpretar correctamente los escapes
            json_str_decoded = codecs.decode(json_str_raw, 'unicode_escape')
        except Exception as e:
            print(f"  - ADVERTENCIA: Error de decodificación en {nombre_archivo}. Puede que algunos textos no se procesen. Error: {e}")
            # Como fallback, intentamos con el método antiguo
            json_str_decoded = json_str_raw.replace('\\r', '').replace('\\n', '').replace('\\"', '"')

        try:
            data = json.loads(json_str_decoded)
            for item in data.get('Data', []):
                texto_ingles = item.get('English', '')
                id_original = item.get('ID', '')

                if not texto_ingles:
                    continue

                if EXCLUSION_PATTERN.match(texto_ingles):
                    print(f"  - Excluyendo ID {id_original}: '{texto_ingles}'")
                    continue

                estructura_parseada = parse_text(texto_ingles)

                mapa_traduccion_final.append({
                    'id_original': id_original,
                    'archivo_original': ruta_archivo,
                    'estructura': estructura_parseada
                })

                # Aplanar la estructura para obtener los fragmentos de texto
                textos_para_traducir = []
                flatten_structure_for_csv(estructura_parseada, textos_para_traducir)

                # Generar las filas del CSV con el formato de sub-índice
                if len(textos_para_traducir) == 1:
                    csv_rows.append([base_index, textos_para_traducir[0]])
                else:
                    for i, texto in enumerate(textos_para_traducir):
                        csv_rows.append([f"{base_index}_{i+1}", texto])

                base_index += 1

        except json.JSONDecodeError as e:
            print(f"  - Error JSON en {nombre_archivo}: {e}")
            continue

    # Guardar los textos en el archivo CSV
    ruta_csv = os.path.join(carpeta_textos, 'traducciones.csv')
    with open(ruta_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Índice', 'Texto a Traducir'])
        writer.writerows(csv_rows)

    # Guardar el mapa de reconstrucción
    ruta_mapa = os.path.join(carpeta_textos, 'mapa.json')
    with open(ruta_mapa, 'w', encoding='utf-8') as f:
        json.dump(mapa_traduccion_final, f, indent=2, ensure_ascii=False)

    print("\n¡Proceso de extracción v3 (sub-índices) completado!")
    print(f"Se han extraído {len(csv_rows)} fragmentos de texto.")
    print(f"Puedes encontrar los textos para traducir en: {ruta_csv}")
    print(f"El nuevo mapa de estructura se ha guardado en: {ruta_mapa}")

if __name__ == '__main__':
    extraer_textos_actualizado()
