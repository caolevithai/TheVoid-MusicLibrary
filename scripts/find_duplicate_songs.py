#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TheVoid-Helper: Deep Music Duplicate Detector
Scans sheet music files and detects duplicates based on:
1. Exact and normalized title matching
2. Deep note sequence similarity (90%+ melody match)
"""

import os
import sys
import re
import json
import time
import argparse
import unicodedata
from difflib import SequenceMatcher

# SkyAutoMusic decryption keys
ENC_RAGUS = [0x0E, 0x18, 0x76, 0x08, 0x7C, 0x0B, 0x27, 0x77, 0x0F, 0x16, 0x1C, 0x02, 0x1C, 0x6D, 0x67, 0x21, 0x34, 0x0F, 0x6D, 0x2C, 0x65, 0x3C, 0x23, 0x79, 0x11, 0x32, 0x28, 0x63, 0x17, 0x32, 0x2F, 0x2F]
ENC_TLAS = [0x20, 0x2E, 0x18, 0x05, 0x31, 0x3B, 0x1C, 0x3F, 0x0B, 0x3F, 0x75, 0x2D, 0x3B, 0x62, 0x11, 0x2B, 0x21, 0x28, 0x05, 0x30, 0x20, 0x7B, 0x28, 0x67, 0x0A, 0x07, 0x73, 0x32, 0x0B, 0x16, 0x72, 0x3C]
XOR_KEY = 0x5A
RAGUS = ''.join(chr(b ^ XOR_KEY) for b in ENC_RAGUS)
TLAS = ''.join(chr(b ^ XOR_KEY) for b in ENC_TLAS)

def decrypt_notes(numbers):
    out = []
    r_len = len(RAGUS)
    for i, v in enumerate(numbers):
        c = ord(RAGUS[i % r_len])
        out.append(chr(v - c + 100))
    s = ''.join(out)
    if TLAS in s:
        s = s[:s.index(TLAS)]
    try:
        return json.loads(s)
    except:
        return []

def normalize_title(name):
    s = os.path.splitext(name)[0]
    s = re.sub(r'[\(\[].*?[\)\]]', '', s)
    if ' - ' in s:
        s = s.split(' - ')[-1]
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    return s if s else name.lower()

def extract_note_string(filepath, max_notes=160):
    try:
        with open(filepath, 'rb') as fp:
            raw = fp.read()
        if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            t = raw.decode('utf-16')
        else:
            t = raw.decode('utf-8', errors='ignore')
        t = t.strip().lstrip('\ufeff')
        if not (t.startswith('[') or t.startswith('{')):
            return ''
        data = json.loads(t)
        song = data[0] if isinstance(data, list) else data

        sn = song.get('songNotes')
        if song.get('isEncrypted') and isinstance(sn, list) and sn and isinstance(sn[0], int):
            sn = decrypt_notes(sn)

        if isinstance(sn, list) and sn and isinstance(sn[0], dict):
            res = []
            for n in sn[:max_notes]:
                m = re.search(r'(\d+)$', n.get('key', ''))
                if m:
                    res.append(chr(65 + (int(m.group(1)) % 15)))
            return ''.join(res)

        cols = song.get('columns')
        if isinstance(cols, list) and cols:
            res = []
            for col in cols:
                if len(res) >= max_notes:
                    break
                if isinstance(col, list) and len(col) > 1 and isinstance(col[1], list):
                    for n in col[1]:
                        if isinstance(n, list) and len(n) > 0 and isinstance(n[0], int):
                            res.append(chr(65 + (n[0] % 15)))
            return ''.join(res)

        return ''
    except:
        return ''

def compute_note_similarity(str_a, str_b):
    if not str_a or not str_b:
        return 0.0
    return SequenceMatcher(None, str_a, str_b, autojunk=False).ratio()

def find_duplicates(music_lib_dir, threshold=0.95):
    music_lib_dir = os.path.abspath(music_lib_dir)
    print(f"[*] Scanning library for near-identical duplicate files (>= {int(threshold*100)}% note match) at: {music_lib_dir}", flush=True)

    lib_json_path = os.path.join(music_lib_dir, "library.json")
    if not os.path.isfile(lib_json_path):
        print(f"[ERROR] library.json not found in {music_lib_dir}", file=sys.stderr)
        sys.exit(1)

    with open(lib_json_path, "r", encoding="utf-8") as fp:
        items = json.load(fp)

    print(f"[*] Loaded {len(items)} items from index. Extracting note signatures...", flush=True)

    title_groups = {}

    for i, it in enumerate(items):
        name = it.get("name", "")
        norm_t = normalize_title(name)
        title_groups.setdefault(norm_t, []).append(it)

        if i % 2000 == 0 and i > 0:
            print(f"  • Processed {i}/{len(items)} songs...", flush=True)

    # Note cluster / exact sequence matching (>= 95% threshold)
    duplicate_groups = []
    min_pct = int(threshold * 100)

    for key, group_items in title_groups.items():
        if len(group_items) > 1:
            first_path = os.path.join(music_lib_dir, group_items[0]["path"])
            base_str = extract_note_string(first_path)

            if not base_str:
                continue

            # Compare each subsequent item against the base note cluster
            matching_items = [group_items[0]]
            sim_scores = []

            for other_item in group_items[1:]:
                op = os.path.join(music_lib_dir, other_item["path"])
                other_str = extract_note_string(op)
                if other_str:
                    sim = compute_note_similarity(base_str, other_str)
                    sim_pct = int(round(sim * 100))
                    # Only group if note sequence is 95%+ identical!
                    if sim_pct >= min_pct:
                        matching_items.append(other_item)
                        sim_scores.append(sim_pct)

            if len(matching_items) > 1:
                # If ALL items in this group were already confirmed by user (vithai), skip this group!
                all_reviewed = all(it.get("reviewedBy") == "vithai" for it in matching_items)
                if all_reviewed:
                    continue

                avg_pct = int(round(sum(sim_scores) / len(sim_scores)))
                match_type = "File double 100%" if avg_pct >= 99 else f"Chỉnh sửa rất ít ({avg_pct}%)"
                duplicate_groups.append({
                    "key": key,
                    "normalizedTitle": group_items[0]["name"].replace(".txt", "").replace(".json", ""),
                    "matchPercentage": avg_pct,
                    "matchType": match_type,
                    "items": matching_items,
                })

    # Sort groups by count descending, then match percentage descending
    duplicate_groups.sort(key=lambda g: (len(g["items"]), g["matchPercentage"]), reverse=True)

    out_file = os.path.join(music_lib_dir, "duplicates_report.json")
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(duplicate_groups, fp, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] Found {len(duplicate_groups)} duplicate/minor-edit groups (>= {min_pct}% notes).")
    print(f"[SUCCESS] Wrote duplicate report to: {out_file}", flush=True)
    return duplicate_groups

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find duplicate songs by 95%+ note sequence match")
    parser.add_argument("-d", "--dir", default="/Users/vithai/Documents/GitHub/TheVoid-MusicLibrary", help="Library path")
    parser.add_argument("-t", "--threshold", type=float, default=0.95, help="Note similarity threshold (default: 0.95 for 95%)")
    args = parser.parse_args()

    find_duplicates(args.dir, args.threshold)
