# IEEE vTools Event Data Fetcher 📡

Un script en Python diseñado para automatizar la extracción de eventos registrados en la plataforma [IEEE vTools Events](https://events.vtools.ieee.org/) para la **Rama Estudiantil IEEE Universidad del Valle** (y sus capítulos técnicos / grupos de afinidad).

El script descarga el reporte en formato CSV correspondiente a la unidad organizativa seleccionada, extrae los identificadores únicos (`Event ID`) y consulta la API pública v8 de vTools para almacenar la información completa y detallada de cada evento en archivos `.json` estructurados y organizados por carpeta.

---

## 🚀 Características

- **Cero dependencias externas:** Utiliza únicamente librerías estándar de Python (`urllib`, `json`, `csv`, `argparse`).
- **Sistema de Caché Inteligente y Detección de Cambios:** Compara la fecha `Updated On` del reporte CSV previo (`OLD_<spoid>.csv`) con el recién descargado para sobreescribir automáticamente solo los eventos que hayan sido modificados en IEEE vTools, ahorrando peticiones API.
- **Historial de CSVs:** Si ya existe un reporte CSV previo, lo respalda automáticamente como `OLD_<OU_SPOID>.csv` antes de guardar el nuevo reporte.
- **Opción para Forzar Actualización:** Parámetro `--flushcache` para re-descargar todos los eventos ignorando el caché.
- **Presets Integrados:** Mapeo de nombres comunes (ej. `comsoc`, `ras`, `wie`, `cs`, etc.) a sus respectivos `OU_SPOID`.
- **Estructura Organizada:** Guarda los reportes y archivos JSON dentro de subcarpetas correspondientes al `OU_SPOID` (`events_csv/<OU_SPOID>/` y `events_json/<OU_SPOID>/<event_id>.json`).
- **Reintentos y Rate Limiting:** Manejo de reintentos automáticos y pausas controladas para evitar bloqueos por parte del servidor.

---

## 📋 Requisitos

- **Python 3.7+** (No requiere instalación de paquetes adicionales vía `pip`).

---

## 🛠️ Instalación

1. Clona este repositorio:
   ```bash
   git clone https://github.com/SamuelOrtizS/IEEE-Event-Data-Fetcher-Script.git
   cd IEEE-Event-Data-Fetcher-Script
   ```

---

## 📖 Uso

### 1. Ejecución Básica (Rama Estudiantil por defecto `STB95801`)
```bash
python fetch_events.py
```

### 2. Consultar un Capítulo o Grupo de Afinidad específico
Puedes pasar el alias mediante `--ou` o `--spoid`:
```bash
# Communications Society (ComSoc)
python fetch_events.py --ou comsoc

# Robotics and Automation Society (RAS)
python fetch_events.py --ou ras

# Women in Engineering (WIE)
python fetch_events.py --ou wie
```

### 3. Usar un `OU_SPOID` Personalizado
Si deseas consultar otra unidad organizativa que no esté en la lista de presets:
```bash
python fetch_events.py --ou SBC95801C
```

### 4. Personalizar Región (`--region`) o Sección (`--section`)
Por defecto, el script busca en la **Región 9** (`R9` - Latinoamérica y el Caribe) y en la **Sección Colombia** (`R90705`). Puedes personalizar estos valores si deseas consultar eventos de otras regiones o secciones de IEEE:
```bash
# Cambiar región y sección
python fetch_events.py --region R9 --section R90705 --ou STB95801
```

### 5. Forzar Actualización Completa (`--flushcache`)
Sobrescribe el archivo CSV principal, elimina el estado previo (sin respaldar a `OLD_`) y descarga nuevamente todos los eventos desde la API como si fuera la primera ejecución:
```bash
python fetch_events.py --ou comsoc --flushcache
```

### 6. Ver Ayuda y Todos los Parámetros
```bash
python fetch_events.py --help
```

---

## 🏷️ Tabla de Presets Disponibles (IEEE Univalle)

| Tipo | Sociedad / Grupo | Aliases Aceptados (`--ou`) | SPOID |
| :--- | :--- | :--- | :--- |
| **Rama Estudiantil** | Rama Universidad del Valle | `default`, `branch`, `stb`, `univalle` | `STB95801` |
| **Grupo de Afinidad** | Women in Engineering (WIE) | `wie` | `SBA95801` |
| **Capítulo Técnico** | Circuits and Systems Society (CAS) | `cas`, `cas04` | `SBC95801` |
| **Capítulo Técnico** | Robotics and Automation Society (RAS) | `ras`, `ra24` | `SBC95801A` |
| **Capítulo Técnico** | Aerospace & Electronic Systems (AESS) | `aess`, `aes10` | `SBC95801C` |
| **Capítulo Técnico** | Computer Society (CS) | `cs`, `c16`, `computer` | `SBC95801G` |
| **Capítulo Técnico** | Communications Society (ComSoc) | `comsoc`, `com19`, `communications` | `SBC95801H` |
| **Capítulo Técnico** | Control Systems Society (CSS) | `css`, `cs23`, `control` | `SBC95801D` |
| **Capítulo Técnico** | Instrumentation & Measurement (IMS) | `ims`, `im09`, `instrumentation` | `SBC95801F` |
| **Capítulo Técnico** | Power & Energy Society (PES) | `pes`, `pe31`, `power` | `SBC95801B` |
| **Capítulo Técnico** | Photonics Society (PHO) | `photonics`, `pho36`, `pho` | `SBC95801E` |

---

## 📂 Estructura de Salida

Al ejecutar el script, se generarán las carpetas `events_csv/` y `events_json/` estructuradas por unidad organizativa:

```text
.
├── fetch_events.py
├── README.md
├── events_csv/
│   ├── STB95801/
│   │   └── STB95801.csv
│   └── SBC95801H/
│       └── SBC95801H.csv
└── events_json/
    ├── STB95801/
    │   ├── 220827.json
    │   ├── 220834.json
    │   └── ...
    └── SBC95801H/
        ├── 573628.json
        ├── 574654.json
        └── 575247.json
```

Cada archivo `.json` contiene el objeto completo retornado por la API v8 de IEEE vTools con metadatos del evento (fechas, ubicación, descripción, asistentes, categorías, etc.).

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
