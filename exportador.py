import os
import re

def diagnosticar_contenido():
    carpeta_ingles = 'ingles'
    print("--- INICIANDO DIAGNÓSTICO FINAL ---")

    if not os.path.isdir(carpeta_ingles):
        print(f"Error: No se encuentra la carpeta '{carpeta_ingles}'.")
        return

    regex_script_line = re.compile(r'm_Script\s*=\s*"(.*)"', re.DOTALL)

    # Procesar solo el primer archivo que se encuentre para obtener una muestra
    for nombre_archivo in sorted(os.listdir(carpeta_ingles)):
        if not nombre_archivo.endswith('.txt'):
            continue

        ruta_archivo = os.path.join(carpeta_ingles, nombre_archivo)
        print(f"\nAnalizando archivo: {ruta_archivo}")

        try:
            with open(ruta_archivo, 'r', encoding='utf-8-sig') as f:
                contenido_archivo = f.read()
        except Exception as e:
            print(f"No se pudo leer el archivo. Error: {e}")
            continue

        match = regex_script_line.search(contenido_archivo)
        if not match:
            print("No se encontró la línea 'm_Script' en este archivo.")
            continue

        script_content_raw = match.group(1)

        print("\n--- CONTENIDO EN CRUDO EXTRAÍDO (PRIMEROS 500 CARACTERES) ---")
        print(script_content_raw[:500])
        print("\n--- FIN DEL CONTENIDO ---")

        # Usamos repr() para ver los caracteres especiales de forma inequívoca (como \n, \t, \\, \")
        print("\n--- REPRESENTACIÓN DEL CONTENIDO (repr()) ---")
        print(repr(script_content_raw[:500]))
        print("\n--- FIN DE LA REPRESENTACIÓN ---")

        print("\nDiagnóstico completado. Por favor, envía toda esta salida al asistente.")
        # Salir después de analizar el primer archivo
        return

    print("No se encontraron archivos .txt en la carpeta 'ingles'.")

if __name__ == '__main__':
    diagnosticar_contenido()
