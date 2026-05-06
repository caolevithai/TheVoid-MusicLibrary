import os
import json
import time

def update_index():
    repo_path = "/Users/vithai/Documents/GitHub/TheVoid-MusicLibrary"
    files_data = []
    # Branch name
    branch = "main"
    base_url = f"https://raw.githubusercontent.com/caolevithai/TheVoid-MusicLibrary/{branch}/"
    
    for root, dirs, files in os.walk(repo_path):
        if '.git' in dirs:
            dirs.remove('.git')
            
        for file in files:
            if file.lower().endswith(('.txt', '.json')) and file != "library.json" and file != "update_index.py":
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)
                size = os.path.getsize(full_path)
                
                # Percent encoding for URL
                import urllib.parse
                encoded_path = urllib.parse.quote(rel_path)
                
                files_data.append({
                    "name": file,
                    "path": rel_path,
                    "url": base_url + encoded_path,
                    "size": size
                })
    
    # Sort by name
    files_data.sort(key=lambda x: x["name"].lower())
    
    output_path = os.path.join(repo_path, "library.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(files_data, f, indent=2, ensure_ascii=False)
    
    print(f"[{time.strftime('%H:%M:%S')}] Updated library.json with {len(files_data)} files.")

if __name__ == "__main__":
    update_index()
