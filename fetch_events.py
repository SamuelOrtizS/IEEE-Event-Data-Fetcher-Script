"""
IEEE vTools Event Data Fetcher
==============================
Este script automatiza la extracción de datos de eventos registrados en la
plataforma oficial de IEEE (vTools Events).

¿Cómo funciona el flujo general?
1. Descarga un reporte CSV con el listado básico de eventos para una Unidad
   Organizativa (SPOID) de IEEE (Rama Estudiantil, Capítulo Técnico o Grupo de Afinidad).
2. Si ya existía un CSV anterior, lo respalda como 'OLD_<SPOID>.csv' para comparar
   las fechas de última actualización ('Updated On').
3. Compara cada evento del nuevo CSV contra la versión previa:
   - Si el evento no ha cambiado y ya está descargado en JSON -> Omite la petición (ahorra tiempo y peticiones).
   - Si es nuevo o fue modificado en vTools -> Consulta la API pública v8 y guarda los detalles en JSON.
"""

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

# ==============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ==============================================================================

# URL base para la búsqueda avanzada y descarga de CSV en IEEE vTools
CSV_BASE_URL = "https://events.vtools.ieee.org/events/search/advanced"

# URL base de la API REST pública de IEEE vTools (v8) para obtener detalles en JSON
API_BASE_URL = "https://events.vtools.ieee.org/RST/events/api/public/v8/events/list?id={event_id}"

# Directorios donde se organizarán las descargas
EVENTS_JSON_DIR = "events_json"
EVENTS_CSV_DIR = "events_csv"

# Cabecera User-Agent para identificarse ante los servidores y evitar bloqueos
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ==============================================================================
# DICCIONARIO DE PRESETS (IEEE Universidad del Valle)
# ==============================================================================
# Permite usar alias fáciles de escribir (ej: 'comsoc', 'wie') en lugar de
# tener que recordar el código SPOID exacto asignado por IEEE.
OU_PRESETS = {
    # Rama Estudiantil principal / Valores por defecto
    "default": "STB95801",
    "branch": "STB95801",
    "stb": "STB95801",
    "univalle": "STB95801",
    
    # Grupo de Afinidad (Affinity Group)
    "wie": "SBA95801",  # Women in Engineering
    
    # Capítulos Técnicos de la Rama (Student Branch Chapters)
    "cas": "SBC95801",  # Circuits and Systems Society
    "cas04": "SBC95801",
    
    "ras": "SBC95801A",  # Robotics and Automation Society
    "ra24": "SBC95801A",
    
    "aess": "SBC95801C",  # Aerospace and Electronic Systems Society
    "aes10": "SBC95801C",
    
    "cs": "SBC95801G",  # Computer Society
    "c16": "SBC95801G",
    "computer": "SBC95801G",
    
    "comsoc": "SBC95801H",  # Communications Society
    "com19": "SBC95801H",
    "communications": "SBC95801H",
    
    "css": "SBC95801D",  # Control Systems Society
    "cs23": "SBC95801D",
    "control": "SBC95801D",
    
    "ims": "SBC95801F",  # Instrumentation and Measurement Society
    "im09": "SBC95801F",
    "instrumentation": "SBC95801F",
    
    "pes": "SBC95801B",  # Power and Energy Society
    "pe31": "SBC95801B",
    "power": "SBC95801B",
    
    "photonics": "SBC95801E",  # Photonics Society
    "pho36": "SBC95801E",
    "pho": "SBC95801E",
}


# ==============================================================================
# FUNCIONES AUXILIARES DE RED Y DESCARGA
# ==============================================================================

def build_csv_url(ou_spoid: str, region_spoid: str = "R9", section_spoid: str = "R90705") -> str:
    """
    Construye la URL con parámetros de consulta (query string) para solicitar
    el archivo CSV con el listado de eventos a IEEE vTools.

    Parámetros:
      - ou_spoid: Identificador de la Unidad Organizativa (ej. STB95801).
      - region_spoid: Región IEEE (por defecto 'R9' - Latinoamérica y el Caribe).
      - section_spoid: Sección IEEE (por defecto 'R90705' - Sección Colombia).

    Retorna:
      - La URL completa lista para ser consultada.
    """
    params = [
        ("sub", "true"),
        ("store_values", "true"),
        ("search", ""),
        ("category_id", ""),
        ("subcategory_id", ""),
        ("meeting[region_spoid]", region_spoid),
        ("meeting[section_spoid]", section_spoid),
        ("meeting[ou_spoid]", ou_spoid),
        ("society", ""),
        ("meeting_after", ""),
        ("meeting_before", ""),
        ("geo_distance", ""),
        ("geo_search", ""),
        ("order", "start_time"),
        ("per_page", "30"),
        ("button", "Download results as CSV"),
    ]
    return f"{CSV_BASE_URL}?{urllib.parse.urlencode(params)}"


def fetch_csv(url: str) -> str:
    """
    Realiza una petición HTTP GET para descargar el contenido del reporte CSV.

    Parámetros:
      - url: Dirección web construida con build_csv_url.

    Retorna:
      - El contenido del archivo CSV como texto plano (string decodificado en utf-8).
    """
    print(f"Descargando reporte CSV desde: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_event_json(event_id: str, max_retries: int = 3) -> dict:
    """
    Consulta la API REST de vTools para obtener la información completa de un evento
    en formato JSON. Implementa reintentos automáticos en caso de fallo temporal de red.

    Parámetros:
      - event_id: Identificador numérico del evento (ej. '574654').
      - max_retries: Número máximo de intentos antes de reportar un error.

    Retorna:
      - Diccionario de Python parseado a partir del JSON devuelto por la API.
    """
    url = API_BASE_URL.format(event_id=urllib.parse.quote(str(event_id).strip()))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode("utf-8")
                return json.loads(content)
        except Exception as e:
            if attempt == max_retries:
                raise e
            print(f"  [Intento {attempt}/{max_retries}] Error al consultar evento {event_id}: {e}. Reintentando...")
            time.sleep(1)


# ==============================================================================
# PROCESAMIENTO Y ARGUMENTOS DE LÍNEA DE COMANDOS
# ==============================================================================

def parse_args():
    """
    Configura y procesa los argumentos de la línea de comandos usando argparse.
    Permite al usuario personalizar la consulta o forzar la actualización de caché.
    """
    parser = argparse.ArgumentParser(
        description="Descarga el CSV de eventos de IEEE vTools y obtiene el JSON detallado de cada evento."
    )
    parser.add_argument(
        "--ou",
        "--spoid",
        dest="ou_spoid",
        default="STB95801",
        help=(
            "SPOID de la Unidad Organizativa. Puedes ingresar un alias (ej. 'comsoc', 'default', 'wie') "
            "o un código SPOID directo (ej. 'SBC95801H', 'STB95801'). Valor por defecto: 'STB95801'."
        ),
    )
    parser.add_argument(
        "--region",
        "--region-spoid",
        dest="region_spoid",
        default="R9",
        help="SPOID de la Región IEEE (ej. 'R9' para Latinoamérica). Valor por defecto: 'R9'.",
    )
    parser.add_argument(
        "--section",
        "--section-spoid",
        dest="section_spoid",
        default="R90705",
        help="SPOID de la Sección IEEE (ej. 'R90705' para Sección Colombia). Valor por defecto: 'R90705'.",
    )
    parser.add_argument(
        "--flushcache",
        action="store_true",
        help="Fuerza la descarga de todos los eventos desde la API ignorando el caché existente.",
    )
    return parser.parse_args()


def resolve_ou_spoid(value: str) -> str:
    """
    Traduce un alias (como 'comsoc' o 'wie') a su código SPOID oficial correspondiente.
    Si el valor ingresado no coincide con ningún alias, se asume que es un SPOID directo
    y se devuelve tal como se recibió.
    """
    cleaned = value.strip()
    return OU_PRESETS.get(cleaned.lower(), cleaned)


def parse_csv_events(csv_text: str) -> dict:
    """
    Lee el contenido en texto del CSV y construye un diccionario que asocia
    cada ID de evento con su fecha de última modificación:
        { "ID_EVENTO": "FECHA_ULTIMA_MODIFICACION" }

    Esto es fundamental para saber qué eventos fueron modificados recientemente en vTools.
    """
    events = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        # Busca la columna que contenga el identificador del evento
        event_id = row.get("Id") or row.get("id") or row.get("Event ID") or row.get("event_id")
        if event_id and event_id.strip():
            event_id = event_id.strip()
            # Busca la columna de fecha de actualización para detección de cambios
            updated_on = (
                row.get("Updated On")
                or row.get("updated_on")
                or row.get("Updated")
                or row.get("updated")
                or ""
            ).strip()
            events[event_id] = updated_on
    return events


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    """
    Punto de entrada principal del script.
    Coordina la descarga, respaldos, detección de cambios y almacenamiento en disco.
    """
    # 1. Analizar argumentos pasados por consola
    args = parse_args()
    spoid = resolve_ou_spoid(args.ou_spoid)
    print(f"Región SPOID: {args.region_spoid} | Sección SPOID: {args.section_spoid}")
    print(f"Unidad Organizativa (SPOID): {spoid}" + (f" (alias resuelto desde '{args.ou_spoid}')" if args.ou_spoid.lower() in OU_PRESETS else ""))

    # 2. Crear carpetas de salida si no existen (estructuradas por SPOID)
    json_output_dir = os.path.join(EVENTS_JSON_DIR, spoid)
    csv_output_dir = os.path.join(EVENTS_CSV_DIR, spoid)
    os.makedirs(json_output_dir, exist_ok=True)
    os.makedirs(csv_output_dir, exist_ok=True)

    # 3. Preparar la URL de consulta
    csv_url = build_csv_url(
        ou_spoid=spoid,
        region_spoid=args.region_spoid.strip(),
        section_spoid=args.section_spoid.strip(),
    )

    # 4. Manejo de caché y respaldo del CSV anterior
    current_csv_filepath = os.path.join(csv_output_dir, f"{spoid}.csv")
    old_csv_filepath = os.path.join(csv_output_dir, f"OLD_{spoid}.csv")
    old_events = {}

    if args.flushcache:
        print("[Flush Cache] Limpiando estado anterior: se descargará todo de cero.")
        if os.path.exists(old_csv_filepath):
            try:
                os.remove(old_csv_filepath)
            except Exception:
                pass
    else:
        # Si ya existe un CSV descargado previamente, lo respaldamos como OLD_<spoid>.csv
        if os.path.exists(current_csv_filepath):
            try:
                with open(current_csv_filepath, "r", encoding="utf-8", errors="replace") as f:
                    old_csv_text = f.read()
                old_events = parse_csv_events(old_csv_text)

                with open(old_csv_filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(old_csv_text)
                print(f"Respaldo creado con éxito: {old_csv_filepath}")
            except Exception as e:
                print(f"Advertencia: No se pudo respaldar el CSV previo: {e}")

    # 5. Descargar el reporte CSV actualizado desde vTools
    try:
        new_csv_text = fetch_csv(csv_url)
    except Exception as e:
        print(f"Error al descargar el archivo CSV: {e}")
        sys.exit(1)

    # Guardar el CSV más reciente en disco
    with open(current_csv_filepath, "w", encoding="utf-8", newline="") as f:
        f.write(new_csv_text)
    print(f"Reporte CSV guardado en: {current_csv_filepath}")

    # 6. Procesar los eventos presentes en el CSV descargado
    new_events = parse_csv_events(new_csv_text)
    event_ids = list(new_events.keys())
    print(f"Se encontraron {len(event_ids)} evento(s) para procesar.")

    # 7. Iterar evento por evento y consultar la API v8 únicamente si es necesario
    successful = 0
    skipped = 0
    for idx, event_id in enumerate(event_ids, start=1):
        output_filepath = os.path.join(json_output_dir, f"{event_id}.json")
        new_updated_on = new_events.get(event_id, "")
        old_updated_on = old_events.get(event_id, "")

        # Verificaciones para decidir si descargar o reutilizar caché
        is_cached = os.path.exists(output_filepath)
        has_changed = (
            bool(old_events)
            and (event_id not in old_events or (new_updated_on and new_updated_on != old_updated_on))
        )

        reason = ""
        if args.flushcache:
            reason = "(--flushcache solicitado)"
        elif not is_cached:
            reason = "(nuevo evento / no estaba en caché)"
        elif has_changed:
            reason = f"(actualizado en el servidor: '{old_updated_on}' -> '{new_updated_on}')"
        else:
            # Si el evento no cambió y ya tenemos el JSON, omitimos la llamada a la API
            print(f"[{idx}/{len(event_ids)}] Evento ID {event_id} en caché y sin cambios -> Omitiendo API")
            skipped += 1
            continue

        print(f"[{idx}/{len(event_ids)}] Obteniendo detalles del evento ID: {event_id} desde la API {reason}...")
        try:
            data = fetch_event_json(event_id)
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  -> Guardado exitosamente en: {output_filepath}")
            successful += 1
        except Exception as e:
            print(f"  -> Error al obtener/guardar evento ID {event_id}: {e}")

        # Pequeña pausa (200 ms) entre peticiones para no saturar el servidor de IEEE
        time.sleep(0.2)

    # 8. Resumen final de la ejecución
    total_ready = successful + skipped
    print(
        f"\n¡Completado! {total_ready}/{len(event_ids)} eventos listos "
        f"({successful} descargados/actualizados, {skipped} en caché) en la carpeta '{json_output_dir}'."
    )


if __name__ == "__main__":
    main()
