#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TheVoid-Helper: Sky1984 Community Sheets Syncer with Smart Duplicate Detection
Downloads and synchronizes Sky1984 Sheets Collection (15,000+ active Sky CotL songs)
into TheVoid-MusicLibrary while detecting and filtering out duplicates already present
in your collection.
"""

import os
import sys
import re
import shutil
import subprocess
import argparse
import unicodedata

REPO_URL = "https://github.com/Ai-Vonie/Sky1984-Sheets-Collection.git"

def normalize_title(name):
    """
    Normalizes a song title to catch cross-source duplicates:
    - Removes extensions (.txt, .json)
    - Removes parenthetical tags: (by ...), (arranged by ...), (Kaiz remix), [ver 1], etc.
    - Strips artist prefix before ' - ' if present
    - Strips accents and diacritics
    - Lowercase and strips non-alphanumeric characters
    """
    s = os.path.splitext(name)[0]
    # Remove content in brackets/parentheses
    s = re.sub(r'[\(\[].*?[\)\]]', '', s)
    # Remove prefix before ' - '
    if ' - ' in s:
        s = s.split(' - ')[-1]
    # Remove accents/diacritics
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    # Strip non-alphanumeric
    s = re.sub(r'[^a-zA-Z0-9]', '', s).lower()
    return s if s else name.lower()

def build_existing_library_fingerprints(music_lib_dir):
    """
    Scans the existing library and builds a lookup map of existing titles.
    """
    existing_map = {}
    print(f"[*] Scanning existing library for duplicate detection...", flush=True)

    for root, dirs, files in os.walk(music_lib_dir):
        if ".git" in dirs:
            dirs.remove(".git")
        if ".tmp" in root or "Sky1984" in root:
            continue
        for f in files:
            if f.endswith((".txt", ".json")) and f != "library.json":
                norm_key = normalize_title(f)
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, music_lib_dir)
                existing_map[norm_key] = rel_path

    print(f"[*] Found {len(existing_map)} unique song signatures in existing library.", flush=True)
    return existing_map

def sync_library(music_lib_dir, skip_duplicates=True):
    music_lib_dir = os.path.abspath(music_lib_dir)
    if not os.path.isdir(music_lib_dir):
        print(f"[ERROR] Directory does not exist: {music_lib_dir}", file=sys.stderr)
        sys.exit(1)

    dest_folder = os.path.join(music_lib_dir, "Collection", "Sky1984")
    tmp_clone_dir = os.path.join(music_lib_dir, ".tmp_sky1984_clone")

    # Step 1: Download
    print(f"[STEP 1/4] Downloading Sky1984 Sheets Collection (approx 66 MB)...", flush=True)
    if os.path.exists(tmp_clone_dir):
        shutil.rmtree(tmp_clone_dir, ignore_errors=True)

    cmd = ["git", "clone", "--depth", "1", REPO_URL, tmp_clone_dir]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"[ERROR] Failed to clone repo: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Index existing library
    print(f"[STEP 2/4] Indexing existing songs to detect duplicates...", flush=True)
    existing_fingerprints = build_existing_library_fingerprints(music_lib_dir)

    # Step 3: Copy and filter
    print(f"[STEP 3/4] Copying unique songs and filtering duplicates...", flush=True)
    src_songs = os.path.join(tmp_clone_dir, "Songs")
    if not os.path.isdir(src_songs):
        src_songs = tmp_clone_dir

    os.makedirs(dest_folder, exist_ok=True)

    copied_count = 0
    skipped_duplicates = 0

    for root, dirs, files in os.walk(src_songs):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            if f.endswith((".txt", ".json")) and not f.startswith("."):
                norm_key = normalize_title(f)
                if skip_duplicates and norm_key in existing_fingerprints:
                    skipped_duplicates += 1
                    continue

                src_file = os.path.join(root, f)
                rel_path = os.path.relpath(src_file, src_songs)
                target_file = os.path.join(dest_folder, rel_path)
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                shutil.copy2(src_file, target_file)
                copied_count += 1
                # Register so we don't duplicate within Sky1984 either
                existing_fingerprints[norm_key] = target_file

    # Cleanup temp clone
    shutil.rmtree(tmp_clone_dir, ignore_errors=True)
    print(f"[SUCCESS] Filtered {skipped_duplicates} duplicate songs already in your collection.", flush=True)
    print(f"[SUCCESS] Added {copied_count} new unique songs into: {dest_folder}", flush=True)

    # Step 4: Rebuild library.json
    print(f"[STEP 4/4] Rebuilding library.json index...", flush=True)
    update_script = os.path.join(music_lib_dir, "update_index.py")
    if os.path.isfile(update_script):
        subprocess.run([sys.executable, update_script], cwd=music_lib_dir, check=True)
    else:
        print(f"[WARN] update_index.py not found in {music_lib_dir}, skipping index rebuild.")

    print(f"\n[DONE] Library synchronization complete!", flush=True)
    print(f"  • New unique songs added: {copied_count}")
    print(f"  • Duplicates skipped:     {skipped_duplicates}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Sky1984 Sheets with Duplicate Detection")
    parser.add_argument("-d", "--dir", default="/Users/vithai/Documents/GitHub/TheVoid-MusicLibrary", help="TheVoid-MusicLibrary root path")
    parser.add_argument("--no-skip-dupes", action="store_true", help="Do not skip duplicates")
    args = parser.parse_args()

    sync_library(args.dir, skip_duplicates=not args.no_skip_dupes)
