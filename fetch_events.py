import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

CSV_BASE_URL = "https://events.vtools.ieee.org/events/search/advanced"
API_BASE_URL = "https://events.vtools.ieee.org/RST/events/api/public/v8/events/list?id={event_id}"
EVENTS_JSON_DIR = "events_json"
EVENTS_CSV_DIR = "events_csv"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Preset mappings for IEEE Universidad del Valle organizational unit SPOIDs
OU_PRESETS = {
    # Student Branch / Default
    "default": "STB95801",
    "branch": "STB95801",
    "stb": "STB95801",
    "univalle": "STB95801",
    
    # Affinity Group
    "wie": "SBA95801",
    
    # Student Branch Chapters
    "cas": "SBC95801",
    "cas04": "SBC95801",
    
    "ras": "SBC95801A",
    "ra24": "SBC95801A",
    
    "aess": "SBC95801C",
    "aes10": "SBC95801C",
    
    "cs": "SBC95801G",
    "c16": "SBC95801G",
    "computer": "SBC95801G",
    
    "comsoc": "SBC95801H",
    "com19": "SBC95801H",
    "communications": "SBC95801H",
    
    "css": "SBC95801D",
    "cs23": "SBC95801D",
    "control": "SBC95801D",
    
    "ims": "SBC95801F",
    "im09": "SBC95801F",
    "instrumentation": "SBC95801F",
    
    "pes": "SBC95801B",
    "pe31": "SBC95801B",
    "power": "SBC95801B",
    
    "photonics": "SBC95801E",
    "pho36": "SBC95801E",
    "pho": "SBC95801E",
}


def build_csv_url(ou_spoid: str, region_spoid: str = "R9", section_spoid: str = "R90705") -> str:
    """Build the CSV download URL with the specified parameters."""
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
    """Download CSV data from the given URL."""
    print(f"Downloading CSV from: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_event_json(event_id: str, max_retries: int = 3) -> dict:
    """Fetch event details JSON from the vTools API."""
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
            print(f"  [Attempt {attempt}/{max_retries}] Error fetching {event_id}: {e}. Retrying...")
            time.sleep(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch IEEE vTools events CSV and retrieve detailed JSON data for each event."
    )
    parser.add_argument(
        "--ou",
        "--spoid",
        dest="ou_spoid",
        default="STB95801",
        help=(
            "Organizational Unit SPOID. Can be a preset name (e.g. 'comsoc', 'default') "
            "or a custom SPOID (e.g. 'SBC95801H', 'STB95801'). Defaults to 'STB95801'."
        ),
    )
    parser.add_argument(
        "--region",
        "--region-spoid",
        dest="region_spoid",
        default="R9",
        help="Region SPOID (e.g. 'R9' for Latin America). Defaults to 'R9'.",
    )
    parser.add_argument(
        "--section",
        "--section-spoid",
        dest="section_spoid",
        default="R90705",
        help="Section SPOID (e.g. 'R90705' for Colombia Section). Defaults to 'R90705'.",
    )
    parser.add_argument(
        "--flushcache",
        action="store_true",
        help="Force refetching all events from the API even if cached JSON exists.",
    )
    return parser.parse_args()


def resolve_ou_spoid(value: str) -> str:
    """Map named preset to its SPOID, or return custom SPOID as-is."""
    cleaned = value.strip()
    return OU_PRESETS.get(cleaned.lower(), cleaned)


def parse_csv_events(csv_text: str) -> dict:
    """Parse CSV and return mapping of event_id -> updated_on timestamp string."""
    events = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        event_id = row.get("Id") or row.get("id") or row.get("Event ID") or row.get("event_id")
        if event_id and event_id.strip():
            event_id = event_id.strip()
            # Look for updated_on / updated column
            updated_on = (
                row.get("Updated On")
                or row.get("updated_on")
                or row.get("Updated")
                or row.get("updated")
                or ""
            ).strip()
            events[event_id] = updated_on
    return events


def main():
    args = parse_args()
    spoid = resolve_ou_spoid(args.ou_spoid)
    print(f"Region SPOID: {args.region_spoid} | Section SPOID: {args.section_spoid}")
    print(f"Using OU SPOID: {spoid}" + (f" (resolved from '{args.ou_spoid}')" if args.ou_spoid.lower() in OU_PRESETS else ""))

    # Directories named after the OU_SPOID
    json_output_dir = os.path.join(EVENTS_JSON_DIR, spoid)
    csv_output_dir = os.path.join(EVENTS_CSV_DIR, spoid)
    os.makedirs(json_output_dir, exist_ok=True)
    os.makedirs(csv_output_dir, exist_ok=True)

    csv_url = build_csv_url(
        ou_spoid=spoid,
        region_spoid=args.region_spoid.strip(),
        section_spoid=args.section_spoid.strip(),
    )

    # 1. Check existing CSV to compare and create backup (OLD_<spoid>.csv)
    current_csv_filepath = os.path.join(csv_output_dir, f"{spoid}.csv")
    old_csv_filepath = os.path.join(csv_output_dir, f"OLD_{spoid}.csv")
    old_events = {}

    if args.flushcache:
        print("[Flush Cache] Resetting cache and CSV state: treating as first run.")
        if os.path.exists(old_csv_filepath):
            try:
                os.remove(old_csv_filepath)
            except Exception:
                pass
    else:
        if os.path.exists(current_csv_filepath):
            try:
                with open(current_csv_filepath, "r", encoding="utf-8", errors="replace") as f:
                    old_csv_text = f.read()
                old_events = parse_csv_events(old_csv_text)

                # Backup current CSV as OLD_<spoid>.csv
                with open(old_csv_filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(old_csv_text)
                print(f"Backed up previous CSV to {old_csv_filepath}")
            except Exception as e:
                print(f"Warning: Failed to backup previous CSV: {e}")

    # 2. Download new CSV
    try:
        new_csv_text = fetch_csv(csv_url)
    except Exception as e:
        print(f"Failed to download CSV: {e}")
        sys.exit(1)

    # Save / Overwrite CSV report
    with open(current_csv_filepath, "w", encoding="utf-8", newline="") as f:
        f.write(new_csv_text)
    print(f"Saved CSV report to {current_csv_filepath}")

    # 3. Parse new CSV
    new_events = parse_csv_events(new_csv_text)
    event_ids = list(new_events.keys())
    print(f"Found {len(event_ids)} event ID(s) to process.")

    # 4. Fetch each event JSON and save to disk
    successful = 0
    skipped = 0
    for idx, event_id in enumerate(event_ids, start=1):
        output_filepath = os.path.join(json_output_dir, f"{event_id}.json")
        new_updated_on = new_events.get(event_id, "")
        old_updated_on = old_events.get(event_id, "")

        is_cached = os.path.exists(output_filepath)
        has_changed = (
            bool(old_events)
            and (event_id not in old_events or (new_updated_on and new_updated_on != old_updated_on))
        )

        reason = ""
        if args.flushcache:
            reason = "(--flushcache requested)"
        elif not is_cached:
            reason = "(new event / not cached)"
        elif has_changed:
            reason = f"(updated on remote: '{old_updated_on}' -> '{new_updated_on}')"
        else:
            print(f"[{idx}/{len(event_ids)}] Event ID {event_id} cached and unchanged -> Skipped API call")
            skipped += 1
            continue

        print(f"[{idx}/{len(event_ids)}] Fetching event ID: {event_id} from API {reason}...")
        try:
            data = fetch_event_json(event_id)
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  -> Saved to {output_filepath}")
            successful += 1
        except Exception as e:
            print(f"  -> Failed to fetch/save event ID {event_id}: {e}")

        # Gentle throttle to avoid rate limits
        time.sleep(0.2)

    total_ready = successful + skipped
    print(
        f"\nDone! {total_ready}/{len(event_ids)} events ready "
        f"({successful} fetched/updated, {skipped} cached) in '{json_output_dir}' directory."
    )


if __name__ == "__main__":
    main()
