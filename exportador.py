import os
import json
import csv
import re
import codecs

# --- Marcadores y Expresiones Regulares (Versión Final) ---
EXCLUSION_PATTERN = re.compile(r'^\{[^}]+\}$')
HTML_TAG_REGEX = r'(<([a-zA-Z0-9]+)([^>]*)>(.*?)</\2>)'
BRACE_TAG_REGEX = r'(\{([a-zA-Z0-9]+)\}(.*?)\{/\6\})'
VARIABLE_REGEX = r'(\{[^}]+\})'
PARSER_REGEX = re.compile(f'{HTML_TAG_REGEX}|{BRACE_TAG_REGEX}|{VARIABLE_REGEX}', re.DOTALL)

# --- Lógica de Análisis (Parsing) ---
def parse_text(text):
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
    for part in structure:
        if part['type'] == 'text' and part['content'].strip():
            text_list.append(part['content'])
        elif part.get('children'):
            flatten_structure_for_csv(part['children'], text_list)

# --- Función Principal (v22 - Híbrida/Definitiva) ---
def extraer_textos_final():
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

    print(f"Buscando archivos en '{carpeta_ingles}' con la lógica v22 (híbrida)...")

    for nombre_archivo in sorted(os.listdir(carpeta_ingles)):
        if not nombre_archivo.endswith('.txt'):
            continue

        ruta_archivo = os.path.join(carpeta_ingles, nombre_archivo)
        print(f"Procesando: {ruta_archivo}")

        # Usar utf-8-sig es más robusto que utf-8 a secas
        with open(ruta_archivo, 'r', encoding='utf-8-sig') as f:
            contenido_archivo = f.read()

        match_script = regex_script_line.search(contenido_archivo)
        if not match_script:
            continue

        json_str_raw = match_script.group(1)
        if not json_str_raw.strip():
            continue

        # Lógica de decodificación del script funcional proporcionado por el usuario
        json_str_decoded = ""
        try:
            temp_str = json_str_raw
            # El BOM dentro del string se elimina manualmente
            if temp_str.startswith('\ufeff'):
                temp_str = temp_str[1:]

            # El método 'unicode_escape' es el correcto para este formato de C#
            json_str_decoded = codecs.decode(temp_str, 'unicode_escape')
        except Exception as e:
            print(f"  - ADVERTENCIA: Error de decodificación en {nombre_archivo}. Error: {e}")
            continue

        try:
            data = json.loads(json_str_decoded)
            for item in data.get('Data', []):
                texto_ingles_bruto = item.get('English')
                id_original = item.get('ID')

                if not id_original or texto_ingles_bruto is None:
                    continue

                es_envuelto = False
                # La detección del formato dual es clave
                if texto_ingles_bruto.startswith('"') and texto_ingles_bruto.endswith('"'):
                     es_envuelto = True
                     texto_ingles_limpio = texto_ingles_bruto[1:-1]
                else:
                     texto_ingles_limpio = texto_ingles_bruto

                if not texto_ingles_limpio or EXCLUSION_PATTERN.match(texto_ingles_limpio):
                    continue

                estructura_parseada = parse_text(texto_ingles_limpio)

                mapa_traduccion_final.append({
                    'id_original': id_original,
                    'archivo_original': ruta_archivo,
                    'estructura': estructura_parseada,
                    'formato_envuelto': es_envuelto,
                    'texto_original_completo': texto_ingles_limpio
                })

                textos_para_traducir = []
                flatten_structure_for_csv(estructura_parseada, textos_para_traducir)

                if textos_para_traducir:
                    if len(textos_para_traducir) == 1:
                        csv_rows.append([base_index, textos_para_traducir[0]])
                    else:
                        for i, texto in enumerate(textos_para_traducir):
                            csv_rows.append([f"{base_index}_{i+1}", texto])
                    base_index += 1

        except json.JSONDecodeError as e:
            print(f"  - Error JSON en {nombre_archivo}: {e}")
            continue

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
    extraer_textos_final()
