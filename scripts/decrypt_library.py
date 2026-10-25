#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TheVoid-Helper: SkyAutoMusic Sheet Decryption Tool
Decrypts SkyAutoMusic encrypted sheet music files (keyVersion 1) into clean, standard
unencrypted Sky Studio / TheVoid Mod Menu compatible format (.txt / .json).
"""

import os
import sys
import json
import argparse

ENC_RAGUS = [
    0x0E, 0x18, 0x76, 0x08, 0x7C, 0x0B, 0x27, 0x77,
    0x0F, 0x16, 0x1C, 0x02, 0x1C, 0x6D, 0x67, 0x21,
    0x34, 0x0F, 0x6D, 0x2C, 0x65, 0x3C, 0x23, 0x79,
    0x11, 0x32, 0x28, 0x63, 0x17, 0x32, 0x2F, 0x2F
]
ENC_TLAS = [
    0x20, 0x2E, 0x18, 0x05, 0x31, 0x3B, 0x1C, 0x3F,
    0x0B, 0x3F, 0x75, 0x2D, 0x3B, 0x62, 0x11, 0x2B,
    0x21, 0x28, 0x05, 0x30, 0x20, 0x7B, 0x28, 0x67,
    0x0A, 0x07, 0x73, 0x32, 0x0B, 0x16, 0x72, 0x3C
]
XOR_KEY = 0x5A
RAGUS = "".join(chr(b ^ XOR_KEY) for b in ENC_RAGUS)
TLAS = "".join(chr(b ^ XOR_KEY) for b in ENC_TLAS)
PITCH_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

def decrypt_notes(numbers):
    out = []
    ragus_len = len(RAGUS)
    for i, val in enumerate(numbers):
        c = ord(RAGUS[i % ragus_len])
        dec = val - c + 100
        out.append(chr(dec))
    s = "".join(out)
    if TLAS in s:
        s = s[:s.index(TLAS)]
    return json.loads(s)

def song_notes_to_columns(song_notes, bpm=800):
    if not song_notes:
        return [[0, []]]
    step_ms = 60000.0 / max(60, bpm)
    max_time = max(n.get("time", 0) for n in song_notes)
    total_cols = int(max_time / step_ms) + 4
    cols = [[0, []] for _ in range(total_cols)]

    for n in song_notes:
        key_str = n.get("key", "")
        # Extract trailing digits
        digits = "".join(ch for ch in key_str if ch.isdigit())
        if not digits:
            continue
        key_idx = int(digits)
        if 0 <= key_idx < 15:
            col_idx = int(round(n.get("time", 0) / step_ms))
            if col_idx < len(cols):
                existing = [item[0] for item in cols[col_idx][1]]
                if key_idx not in existing:
                    cols[col_idx][1].append([key_idx, "1"])

    while len(cols) > 1 and not cols[-1][1]:
        cols.pop()
    return cols

def decrypt_file(filepath, overwrite=True):
    try:
        with open(filepath, "rb") as fp:
            raw = fp.read()
        
        # Check encoding
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            text = raw.decode("utf-16").strip().lstrip("\ufeff")
        else:
            text = raw.decode("utf-8", errors="ignore").strip().lstrip("\ufeff")

        if not (text.startswith("[") or text.startswith("{")):
            return False, "Not JSON"

        data = json.loads(text)
        is_list = isinstance(data, list)
        song = data[0] if is_list else data

        if not song.get("isEncrypted"):
            return False, "Not encrypted"

        raw_notes = song.get("songNotes")
        if not isinstance(raw_notes, list) or not raw_notes or not isinstance(raw_notes[0], int):
            return False, "Encrypted data not found or invalid format"

        decrypted_notes = decrypt_notes(raw_notes)
        bpm = song.get("bpm") or 800

        # Resolve pitch
        pitch = song.get("pitch")
        if not pitch and isinstance(song.get("pitchLevel"), int):
            pitch = PITCH_NAMES[((song["pitchLevel"] % 12) + 12) % 12]
        if not pitch:
            pitch = "C"

        # Generate columns for full compatibility with Sky Studio & Mod Menu
        columns = song_notes_to_columns(decrypted_notes, bpm)

        song["isEncrypted"] = False
        if "keyVersion" in song:
            del song["keyVersion"]
        song["pitch"] = pitch
        song["songNotes"] = decrypted_notes
        song["columns"] = columns

        out_data = [song] if is_list else song

        target_path = filepath if overwrite else filepath + ".decrypted.txt"
        with open(target_path, "w", encoding="utf-8") as fp:
            json.dump(out_data, fp, ensure_ascii=False, indent=2)

        return True, f"Decrypted {len(decrypted_notes)} notes"
    except Exception as e:
        return False, str(e)

def batch_decrypt_library(library_dir):
    library_dir = os.path.abspath(library_dir)
    print(f"[*] Scanning library at: {library_dir}")
    count_ok = 0
    count_err = 0
    count_skipped = 0

    for root, _, files in os.walk(library_dir):
        for f in files:
            if f.endswith((".txt", ".json")) and f != "library.json":
                p = os.path.join(root, f)
                success, msg = decrypt_file(p, overwrite=True)
                if success:
                    print(f"[OK] {f}: {msg}")
                    count_ok += 1
                elif msg == "Not encrypted":
                    count_skipped += 1
                else:
                    count_err += 1

    print("\n[SUMMARY]")
    print(f"  • Successfully decrypted: {count_ok} files")
    print(f"  • Already unencrypted:   {count_skipped} files")
    print(f"  • Errors / non-sheets:   {count_err} files")

    # If update_index.py exists in library_dir, run it
    idx_script = os.path.join(library_dir, "update_index.py")
    if os.path.isfile(idx_script) and count_ok > 0:
        print("[*] Rebuilding library.json...")
        import subprocess
        subprocess.run([sys.executable, idx_script], cwd=library_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decrypt SkyAutoMusic sheets (.txt / .json)")
    parser.add_argument("-d", "--dir", help="Directory of music library to batch decrypt")
    parser.add_argument("-f", "--file", help="Single file to decrypt")
    args = parser.parse_args()

    if args.file:
        ok, msg = decrypt_file(args.file, overwrite=True)
        print(f"Result for {args.file}: {msg}")
    elif args.dir:
        batch_decrypt_library(args.dir)
    else:
        # Default to user library path
        default_dir = "/Users/vithai/Documents/GitHub/TheVoid-MusicLibrary"
        if os.path.isdir(default_dir):
            batch_decrypt_library(default_dir)
        else:
            parser.print_help()
