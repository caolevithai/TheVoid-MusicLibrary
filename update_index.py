import os
import json
import time
import urllib.parse

PITCH_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

def extract_meta(full_path):
    try:
        with open(full_path, "rb") as fp:
            raw = fp.read()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            t = raw.decode("utf-16").strip().lstrip("\ufeff")
        else:
            t = raw.decode("utf-8", errors="ignore").strip().lstrip("\ufeff")
        if not (t.startswith("[") or t.startswith("{")):
            return {}
        data = json.loads(t)
        song = data[0] if isinstance(data, list) else data

        bpm = int(song.get("bpm") or 800)
        pitch = song.get("pitch")
        if not pitch and isinstance(song.get("pitchLevel"), int):
            pitch = PITCH_NAMES[((song["pitchLevel"] % 12) + 12) % 12]
        if not pitch:
            pitch = "C"

        cols = len(song.get("columns") or [])
        sn = song.get("songNotes") or []
        notes = len(sn)
        if cols == 0 and notes > 0:
            step_ms = 60000.0 / max(60, bpm)
            max_t = max((n.get("time", 0) for n in sn if isinstance(n, dict)), default=0)
            cols = int(max_t / step_ms) + 1
        elif cols > 0 and notes == 0:
            notes = sum(len(c[1]) for c in song.get("columns") if len(c) > 1 and isinstance(c[1], list))

        res = {"bpm": bpm, "pitch": pitch, "columns": cols, "notes": notes}
        if song.get("reviewedBy"):
            res["reviewedBy"] = song.get("reviewedBy")
        return res
    except:
        return {}

def update_index():
    repo_path = "/Users/vithai/Documents/GitHub/TheVoid-MusicLibrary"
    files_data = []
    # Branch name
    branch = "main"
    base_url = f"https://raw.githubusercontent.com/caolevithai/TheVoid-MusicLibrary/{branch}/"
    
    for root, dirs, files in os.walk(repo_path):
        if '.git' in dirs:
            dirs.remove('.git')
        if '.tmp' in root:
            continue
            
        for file in files:
            if file.lower().endswith(('.txt', '.json')) and file != "library.json" and file != "update_index.py" and file != "duplicates_report.json":
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)
                size = os.path.getsize(full_path)
                
                # Percent encoding for URL
                encoded_path = urllib.parse.quote(rel_path)
                
                meta = extract_meta(full_path)

                item = {
                    "name": file,
                    "path": rel_path,
                    "url": base_url + encoded_path,
                    "size": size
                }
                if meta:
                    item.update(meta)
                
                files_data.append(item)
    
    # Sort by name
    files_data.sort(key=lambda x: x["name"].lower())
    
    output_path = os.path.join(repo_path, "library.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(files_data, f, indent=2, ensure_ascii=False)
    
    print(f"[{time.strftime('%H:%M:%S')}] Updated library.json with {len(files_data)} files (including pitch, bpm, columns, notes).")

if __name__ == "__main__":
    update_index()
