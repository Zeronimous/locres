import os
import json
import csv
import re

# --- Marcadores y Expresiones Regulares (Versión Final) ---
EXCLUSION_PATTERN = re.compile(r'^\{[^}]+\}$')
HTML_TAG_REGEX = r'(<([a-zA-Z0-9]+)([^>]*)>(.*?)</\2>)'
BRACE_TAG_REGEX = r'(\{([a-zA-Z0-9]+)\}(.*?)\{/\6\})'
VARIABLE_REGEX = r'(\{[^}]+\})'
PARSER_REGEX = re.compile(f'{HTML_TAG_REGEX}|{BRACE_TAG_REGEX}|{VARIABLE_REGEX}', re.DOTALL)

# --- Lógica de Análisis (Parsing) ---
def parse_text(text):
    # ... (esta función no necesita cambios)
    parts = []
    last_index = 0
    for match in PARSER_REGEX.finditer(text):
        start, end = match.span()
        if start > last_index:
            parts.append({'type': 'text', 'content': text[last_index:start]})
        html_full, html_tag, html_attr, html_content, brace_full, brace_tag, brace_content, variable_full = match.groups()
        if html_full:
            children = parse_text(html_content)
            full_tag = f"{html_tag}{html_attr}" if html_attr else html_tag
            parts.append({'type': 'tag_html', 'tag': full_tag, 'children': children})
        elif brace_full:
            children = parse_text(brace_content)
            parts.append({'type': 'tag_brace', 'tag': brace_tag, 'children': children})
        elif variable_full:
            parts.append({'type': 'variable', 'content': variable_full})
        last_index = end
    if last_index < len(text):
        parts.append({'type': 'text', 'content': text[last_index:]})
    return parts

def flatten_structure_for_csv(structure, text_list):
    # ... (esta función no necesita cambios)
    for part in structure:
        if part['type'] == 'text' and part['content'].strip():
            text_list.append(part['content'])
        elif part.get('children'):
            flatten_structure_for_csv(part['children'], text_list)

# --- Función Principal (v12 - Extracción Quirúrgica) ---
def extraer_textos_quirurgico():
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

    # Regex para encontrar la línea de m_Script
    regex_script_line = re.compile(r'm_Script\s*=\s*"(.*)"', re.DOTALL)

    # Regex quirúrgica para extraer pares de ID y English del texto plano
    # Captura: 1=ID, 2=English
    regex_quirurgico = re.compile(r'\{\s*\\"ID\\"\s*:\s*\\"(.*?)\\"[^}]*?\\"English\\"\s*:\s*\\"(.*?)\\"')

    print(f"Buscando archivos en '{carpeta_ingles}' con la lógica v12 (quirúrgica)...")

    for nombre_archivo in sorted(os.listdir(carpeta_ingles)):
        if not nombre_archivo.endswith('.txt'):
            continue

        ruta_archivo = os.path.join(carpeta_ingles, nombre_archivo)
        print(f"Procesando: {ruta_archivo}")

        with open(ruta_archivo, 'r', encoding='utf-8-sig') as f:
            contenido_archivo = f.read()

        match_script = regex_script_line.search(contenido_archivo)
        if not match_script:
            continue

        script_content = match_script.group(1)
        if not script_content.strip():
            print(f"  - ADVERTENCIA: m_Script está vacío en {nombre_archivo}. Omitiendo.")
            continue

        # Iterar sobre todas las coincidencias de ID/English en el contenido
        for match_item in regex_quirurgico.finditer(script_content):
            id_original_escaped, texto_ingles_escaped = match_item.groups()

            # Un-escape del texto en inglés para poder procesarlo
            texto_ingles = texto_ingles_escaped.replace('\\"', '"').replace('\\\\', '\\')

            if not texto_ingles:
                continue

            if EXCLUSION_PATTERN.match(texto_ingles):
                print(f"  - Excluyendo ID {id_original_escaped}: '{texto_ingles}'")
                continue

            estructura_parseada = parse_text(texto_ingles)

            mapa_traduccion_final.append({
                'id_original': id_original_escaped,
                'archivo_original': ruta_archivo,
                'estructura': estructura_parseada
            })

            textos_para_traducir = []
            flatten_structure_for_csv(estructura_parseada, textos_para_traducir)

            if len(textos_para_traducir) == 1:
                csv_rows.append([base_index, textos_para_traducir[0]])
            else:
                for i, texto in enumerate(textos_para_traducir):
                    csv_rows.append([f"{base_index}_{i+1}", texto])

            base_index += 1

    # Guardar CSV y Mapa
    ruta_csv = os.path.join(carpeta_textos, 'traducciones.csv')
    with open(ruta_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Índice', 'Texto a Traducir'])
        writer.writerows(csv_rows)

    ruta_mapa = os.path.join(carpeta_textos, 'mapa.json')
    with open(ruta_mapa, 'w', encoding='utf-8') as f:
        json.dump(mapa_traduccion_final, f, indent=2, ensure_ascii=False)

    print(f"\n¡Proceso de extracción completado! Se han extraído {len(csv_rows)} fragmentos de texto.")

if __name__ == '__main__':
    extraer_textos_quirurgico()
