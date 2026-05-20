#!/usr/bin/env python3
import os
import re
import json
import argparse
import sys

# Allowed rom extensions and their mapping to systems and emulator cores
SYSTEM_MAPPING = {
    # Extensions -> (System ID, Emu Core, System Name)
    '.nes': ('NES', 'nes', 'Nintendo Entertainment System'),
    '.a26': ('A26', 'atari2600', 'Atari 2600'),
    '.bin': ('A26', 'atari2600', 'Atari 2600'),
    '.7z': ('A26', 'atari2600', 'Atari 2600'), # Defaulting to A26 for 7z files in Atari context
    '.zip': ('NES', 'nes', 'NES / Atari'),      # General archive
    '.smc': ('SNES', 'snes9x', 'Super Nintendo'),
    '.sfc': ('SNES', 'snes9x', 'Super Nintendo'),
    '.gb': ('GB', 'gambatte', 'Game Boy'),
    '.gbc': ('GBC', 'gambatte', 'Game Boy Color'),
    '.gba': ('GBA', 'mgba', 'Game Boy Advance'),
}

# Rich Emoji mapping based on common keywords in retro titles
EMOJI_MAP = {
    'space': '🚀', 'star': '⭐', 'astro': '🚀', 'invader': '👾', 'alien': '👾', 'galaxy': '🌌',
    'combat': '⚔️', 'raid': '⚔️', 'battle': '⚔️', 'war': '⚔️', 'attack': '⚔️', 'defense': '🛡️',
    'boxing': '🥊', 'karate': '🥊', 'kung': '🥊', 'fight': '🥊', 'punch': '🥊', 'wrestle': '🤼',
    'soccer': '⚽', 'football': '⚽', 'baseball': '⚾', 'tennis': '🎾', 'golf': '⛳', 'basketball': '🏀', 'hockey': '🏒',
    'donkey': '🦍', 'kong': '🦍',
    'spider': '🕷️', 'superman': '🦸', 'batman': '🦇', 'hero': '🦸',
    'pac': '🍕', 'burger': '🍕', 'food': '🍕', 'cake': '🍰',
    'motor': '🏍️', 'racer': '🏎️', 'race': '🏎️', 'speed': '🏎️', 'grand prix': '🏎️', 'drive': '🚗',
    'adventure': '🛩️', 'quest': '🗺️', 'pitfall': '🧗',
    'chase': '🐕', 'dog': '🐕', 'cat': '🐱', 'frog': '🐸', 'duck': '🦆', 'bird': '🐦', 'pig': '🐷',
    'ghost': '👻', 'haunt': '👻', 'monster': '👹', 'frankenstein': '🧟', 'halloween': '🎃', 'vampire': '🦇',
    'maze': '🌀', 'puzzle': '🧩', 'brick': '🧱', 'block': '🧱', 'cube': '🧊', 'pinball': '🎳',
    'air': '✈️', 'fly': '✈️', 'copter': '🚁', 'plane': '✈️',
    'sea': '🌊', 'ocean': '🌊', 'sub': '🚢', 'ship': '🚢', 'fish': '🐟',
    'command': '🎖️', 'mission': '🎖️',
    'wizard': '🧙', 'magic': '🪄', 'spell': '🪄',
}

# Keyword-based genre guessing
GENRE_MAP = {
    'shoot': 'Shooter', 'space': 'Shooter', 'invader': 'Shooter', 'blast': 'Shooter',
    'combat': 'Action', 'battle': 'Action', 'war': 'Action', 'fight': 'Action', 'kung': 'Action', 'karate': 'Action',
    'soccer': 'Sports', 'football': 'Sports', 'baseball': 'Sports', 'tennis': 'Sports', 'golf': 'Sports', 'basketball': 'Sports', 'hockey': 'Sports', 'boxing': 'Sports',
    'racer': 'Racing', 'race': 'Racing', 'speed': 'Racing', 'drive': 'Racing', 'motor': 'Racing',
    'adventure': 'Adventure', 'quest': 'Adventure', 'pitfall': 'Platformer', 'mario': 'Platformer', 'donkey': 'Platformer',
    'puzzle': 'Puzzle', 'maze': 'Puzzle', 'cube': 'Puzzle', 'math': 'Educational',
}

def clean_game_name(filename):
    """
    Cleans up ROM filenames into human-readable titles.
    E.g. "Space Invaders (USA).7z" -> "Space Invaders"
         "Adventure, The.7z" -> "The Adventure"
    """
    # Remove file extension
    name, _ = os.path.splitext(filename)
    
    # Remove brackets, parentheses and content inside
    name = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    
    # Clean up double spaces or underscores
    name = name.replace('_', ' ')
    name = ' '.join(name.split())
    
    # Handle inverted articles
    if name.endswith(', The'):
        name = 'The ' + name[:-5]
    elif name.endswith(', A'):
        name = 'A ' + name[:-3]
        
    return name.strip()

def get_emoji(name):
    """Assigns a relevant retro emoji based on game name keywords."""
    lower_name = name.lower()
    for keyword, emoji in EMOJI_MAP.items():
        if keyword in lower_name:
            return emoji
    return '🎮' # Fallback classic gamepad

def get_genre(name):
    """Guesses the genre based on name keywords."""
    lower_name = name.lower()
    for keyword, genre in GENRE_MAP.items():
        if keyword in lower_name:
            return genre
    return 'Action' # Default fallback

def extract_year(filename):
    """Tries to extract a year from parentheses if it looks like a year, e.g., (1982)."""
    match = re.search(r'\((19[7-9]\d|200\d)\)', filename)
    if match:
        return int(match.group(1))
    return 1980 # Default retro year

def scan_roms(roms_dir):
    games = []
    print(f"[*] Scanning ROMs in: {roms_dir}")
    
    if not os.path.exists(roms_dir):
        print(f"[!] Directory '{roms_dir}' does not exist. Creating empty directory...")
        os.makedirs(roms_dir, exist_ok=True)
        return games

    # Recursively traverse directory
    for root, _, files in os.walk(roms_dir):
        for file in sorted(files):
            ext = os.path.splitext(file)[1].lower()
            if ext in SYSTEM_MAPPING:
                sys_id, core, sys_name = SYSTEM_MAPPING[ext]
                
                # If nested in a specific system folder, override system classification
                rel_path = os.path.relpath(os.path.join(root, file), roms_dir)
                lower_rel = rel_path.lower()
                
                if 'nes' in lower_rel or 'nintendo' in lower_rel:
                    sys_id = 'NES'
                    core = 'nes'
                elif 'atari' in lower_rel or '2600' in lower_rel or 'a26' in lower_rel:
                    sys_id = 'A26'
                    core = 'atari2600'
                
                clean_name = clean_game_name(file)
                emoji = get_emoji(clean_name)
                genre = get_genre(clean_name)
                year = extract_year(file)
                
                # Construct unique ID
                safe_id = re.sub(r'[^a-z0-9]', '-', clean_name.lower())
                safe_id = re.sub(r'-+', '-', safe_id).strip('-')
                game_id = f"{sys_id.lower()}-{safe_id}"
                
                # URL is relative to the page root, pointing inside the roms folder
                rom_url = os.path.join('roms', rel_path).replace('\\', '/')
                
                game_data = {
                    "id": game_id,
                    "name": clean_name,
                    "system": sys_id,
                    "year": year,
                    "genre": genre,
                    "emoji": emoji,
                    "desc": f"Classic {sys_name} title: {clean_name}.",
                    "romUrl": rom_url,
                    "emuCore": core
                }
                games.append(game_data)
                print(f" [+] Found {sys_id}: {clean_name} ({file})")
                
    return games

def main():
    parser = argparse.ArgumentParser(description="Scan ROMs directory and generate dynamic library database.")
    parser.add_argument('--dir', default='./roms', help="Path to ROMs directory (default: ./roms)")
    parser.add_argument('--out', default='roms.json', help="Output database path (default: roms.json)")
    args = parser.parse_args()
    
    roms_dir = args.dir
    out_file = args.out
    
    # Ensure roms_dir is absolute if relative is evaluated against current script directory
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if not os.path.isabs(roms_dir):
        roms_dir = os.path.join(script_dir, roms_dir)
        
    if not os.path.isabs(out_file):
        out_file = os.path.join(script_dir, out_file)
        
    games = scan_roms(roms_dir)
    
    print(f"[*] Total games found: {len(games)}")
    
    # Write JSON database
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
        
    print(f"[✓] Library saved successfully to: {out_file}")
    print("[*] You can now commit and push 'roms.json' and the 'roms' folder to GitHub Pages!")

if __name__ == '__main__':
    main()
