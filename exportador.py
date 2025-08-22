import os
import re
import csv
import json

# --- Mi lógica de parsing avanzado (es más robusta para los tags) ---
EXCLUSION_PATTERN = re.compile(r'^\{[^}]+\}$')
HTML_TAG_REGEX = r'(<([a-zA-Z0-9]+)([^>]*)>(.*?)</\2>)'
BRACE_TAG_REGEX = r'(\{([a-zA-Z0-9]+)\}(.*?)\{/\6\})'
VARIABLE_REGEX = r'(\{[^}]+\})'
PARSER_REGEX = re.compile(f'{HTML_TAG_REGEX}|{BRACE_TAG_REGEX}|{VARIABLE_REGEX}', re.DOTALL)

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

# --- Función Principal (v29 - Dos Regex) ---
def extraer_textos_dos_regex():
    input_dir = "ingles"
    output_dir = "textos"
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, "traducciones.csv")
    path_json = os.path.join(output_dir, "mapa.json")

    csv_rows = []
    mapa_traduccion_final = []
    base_index = 1

    regex_script_line = re.compile(r'string m_Script = "(.*?)"$', re.DOTALL)

    # Regex para formato complejo (con \\" dentro del valor)
    regex_compleja = re.compile(r'\\"ID\\"\s*:\s*\\"(.*?)\\".*?\\"English\\"\s*:\s*\\"(.*?)\\"', re.DOTALL)
    # Regex para formato simple (sin \\" dentro del valor), del script del usuario
    regex_simple = re.compile(r'"ID":"([^"]+)"[^}]*?"English":"((?:[^"\\]|\\.)*?)"', re.DOTALL)

    print(f"Buscando archivos en '{input_dir}' con la lógica v29 (dos regex)...")

    for filename in sorted(os.listdir(input_dir)):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(input_dir, filename)
        print(f"\nProcesando archivo: {filename}")
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            script_match = regex_script_line.search(content)
            if not script_match:
                print(f"Advertencia: No se encontró m_Script en {filename}")
                continue

            script_content = script_match.group(1).lstrip('\ufeff')
            if not script_content.strip():
                continue

            # Intentar primero con la regex compleja
            matches = regex_compleja.findall(script_content)
            is_complex_format = True
            # Si no encuentra nada, probar con la regex simple
            if not matches:
                matches = regex_simple.findall(script_content)
                is_complex_format = False

            if not matches:
                print(f"Advertencia: No se encontraron entradas 'English' en {filename}")
                continue

            print(f"Encontradas {len(matches)} entradas 'English' en {filename}")

            for id_value, english_text_raw in matches:
                # El des-escape depende del formato encontrado
                if is_complex_format:
                    texto_ingles = english_text_raw
                else:
                    texto_ingles = re.sub(r'\\([\\"])', r'\1', english_text_raw)

                es_envuelto = texto_ingles.startswith('"') and texto_ingles.endswith('"')
                texto_limpio_para_parser = texto_ingles[1:-1] if es_envuelto else texto_ingles

                if not texto_limpio_para_parser or EXCLUSION_PATTERN.match(texto_limpio_para_parser):
                    continue

                estructura_parseada = parse_text(texto_limpio_para_parser)

                mapa_traduccion_final.append({
                    'id_original': id_value,
                    'archivo_original': file_path,
                    'estructura': estructura_parseada,
                    'formato_envuelto': es_envuelto,
                    'texto_original_completo': texto_limpio_para_parser
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

        except Exception as e:
            print(f"Error al procesar el archivo {filename}: {e}")
            continue

    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Índice', 'Texto a Traducir'])
        writer.writerows(csv_rows)
    print(f"CSV generado en {output_csv} con {len(csv_rows)} entradas.")

    with open(path_json, 'w', encoding='utf-8') as jsonfile:
        json.dump(mapa_traduccion_final, jsonfile, ensure_ascii=False, indent=4)
    print(f"Archivo mapa.json generado en {path_json}.")

if __name__ == "__main__":
    extraer_textos_dos_regex()
