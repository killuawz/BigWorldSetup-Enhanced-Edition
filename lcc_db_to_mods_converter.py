#!/usr/bin/env python3
"""
LCC-Docs Database to BigWorldSetup Mods Converter

This script converts the data from lcc-docs/db into JSON configuration files
compatible with data/mods directory structure.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


LOG_FILE = None


def log(message: str = ""):
    """Log message to console and optional log file"""
    print(message)
    if LOG_FILE:
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except Exception:
            pass


def write_json_compact(path: Path, data: Any, indent: int = 2) -> None:
    """
    Write JSON to `path` using a compact formatting rule:
    - Empty dict/list are written inline `{}` / `[]`
    - Lists of primitives (str/num/bool/null) are written on a single line
    - Other structures are pretty-printed with indentation
    """
    def to_json_str(o: Any, level: int = 0) -> str:
        pad = ' ' * (indent * level)
        if isinstance(o, dict):
            if not o:
                return '{}'
            items = []
            for k, v in o.items():
                key = json.dumps(k, ensure_ascii=False)
                val = to_json_str(v, level + 1)
                items.append(f"{pad}{' ' * indent}{key}: {val}")
            return '{\n' + ',\n'.join(items) + '\n' + pad + '}'
        if isinstance(o, list):
            if not o:
                return '[]'
            # compact if all primitives
            if all(isinstance(x, (str, int, float, bool, type(None))) for x in o):
                items = [json.dumps(x, ensure_ascii=False) for x in o]
                return '[' + ', '.join(items) + ']'
            items = []
            for v in o:
                items.append(f"{pad}{' ' * indent}{to_json_str(v, level + 1)}")
            return '[\n' + ',\n'.join(items) + '\n' + pad + ']'
        return json.dumps(o, ensure_ascii=False)

    s = to_json_str(data, 0)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(s)


class GameNameMapper:
    """
    Maps LCC game names to BigWorldSetup game names.
    
    This class provides a mapping table for converting game names from the LCC-Docs
    database format to the normalized format used by BigWorldSetup Enhanced Edition.
    
    Supported games:
    - BG / bg (Baldur's Gate)
    - BGEE / bgee (Baldur's Gate Enhanced Edition)
    - BG2 / bg2 (Baldur's Gate II)
    - BG2EE / bg2ee (Baldur's Gate II Enhanced Edition)
    - SoD / sod (Siege of Dragonspear)
    - EET / eet (Enhanced Edition Trilogy)
    - IWD / iwd (Icewind Dale)
    - IWD2 / iwd2 (Icewind Dale II)
    - IWDEE / iwdee (Icewind Dale Enhanced Edition)
    - PST / pst (Planescape: Torment)
    - PSTEE / pstee (Planescape: Torment Enhanced Edition)
    - BGT / bgt (Baldur's Gate Trilogy)
    - Tutu / tutu (BGT - Tutu)
    """

    MAPPING = {
        "BG": "bg",
        "BGEE": "bgee",
        "BG2": "bg2",
        "BG2EE": "bg2ee",
        "SoD": "sod",
        "EET": "eet",
        "IWD": "iwd",
        "IWD2": "iwd2",
        "IWDEE": "iwdee",
        "PST": "pst",
        "PSTEE": "pstee",
        "BGT": "bgt",
        "Tutu": "tutu",
    }

    @staticmethod
    def normalize(game_name: str) -> str:
        """
        Normalize a game name to lowercase standard form.
        
        Args:
            game_name: Game name from LCC database (e.g., 'BG2EE', 'SoD')
        
        Returns:
            Normalized game name (e.g., 'bg2ee', 'sod')
        
        Raises:
            ValueError: If game name is not in the mapping
        """
        normalized = GameNameMapper.MAPPING.get(game_name)
        if normalized is None:
            raise ValueError(f"Unknown game name: {game_name}")
        return normalized


class CategoryMapper:
    """
    Maps LCC category names to BigWorldSetup category names.
    
    Provides category normalization for converting from LCC-Docs format to
    BigWorldSetup Enhanced Edition standard categories.
    """

    MAPPING = {
        "Quest Packs & Adventures": "quest",
        "NPCs": "npcs",
        "Kit": "kit",
        "Tweak": "tweak",
        "Spell": "spell",
        "Item": "item",
        "Creature": "creature",
        "Portrait Pack": "portraits",
        "Sound": "sound",
        "UI": "ui",
        "Romance": "romance",
        "Tactical": "tactical",
        "Encounter": "encounter",
        "Mechanics": "mechanics",
        "Enhancement": "enhancement",
        "BG2": "bg2",
        "BG1": "bg1",
        "Overhaul": "overhaul",
        "Cosmetic": "cosmetic",
        "Balance": "balance",
        "Armor": "armor",
        "Weapon": "weapon",
        "Cleric": "cleric",
        "Druid": "druid",
        "Fighter": "fighter",
        "Mage": "mage",
        "Thief": "thief",
        "Ranger": "ranger",
        "Bard": "bard",
        "Paladin": "paladin",
        "Monk": "monk",
        "Sorcerer": "sorcerer",
    }

    @staticmethod
    def normalize(category: str) -> str:
        """
        Normalize a category name.
        
        Args:
            category: Category name from LCC database
        
        Returns:
            Normalized category name, or original if not in mapping
        """
        return CategoryMapper.MAPPING.get(category, category.lower().replace(' ', '-'))


class AuthorNameNormalizer:
    """
    Normalizes author names using mapping from JSON configuration.
    
    This class loads author name mappings from a JSON file and provides
    methods to normalize author names from LCC format to standard form.
    """

    def __init__(self, author_mappings: Optional[Dict[str, str]] = None):
        """
        Initialize author normalizer with optional mappings.
        
        Args:
            author_mappings: Dictionary mapping original author names to normalized names
        """
        self.mappings = author_mappings or {}

    def normalize(self, author_name: str) -> str:
        """
        Normalize an author name using the mapping.
        
        Args:
            author_name: Original author name from LCC database
        
        Returns:
            Normalized author name
        """
        return self.mappings.get(author_name, author_name)

    def load_from_json(self, json_path: Path):
        """
        Load author mappings from JSON file.
        
        Args:
            json_path: Path to JSON file with author mappings
        """
        try:
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.mappings = json.load(f)
        except Exception as e:
            log(f"Warning: Could not load author mappings from {json_path}: {e}")


class LCCDatabaseConverter:
    """
    Main converter class for LCC-Docs database to BigWorldSetup mods format.
    
    This class orchestrates the conversion process:
    1. Loads mod data from lcc-docs/db/en_US.json
    2. Loads translation data for supported languages
    3. Loads author name mappings
    4. Creates individual mod configuration files
    5. Merges with existing configurations if requested
    6. Tracks conversion statistics
    
    Attributes:
        lcc_db_path: Path to lcc-docs/db directory
        output_path: Path to data/mods directory
        mods_data: Dictionary of loaded mod data
        translations: Dictionary of loaded translations
        author_normalizer: AuthorNameNormalizer instance
        conversion_report: Dictionary tracking conversion statistics
    """

    def __init__(self, lcc_db_path: str, output_path: str):
        """
        Initialize the converter.
        
        Args:
            lcc_db_path: Path to lcc-docs/db directory
            output_path: Path to data/mods directory
        """
        self.lcc_db_path = Path(lcc_db_path)
        self.output_path = Path(output_path)
        self.mods_data = {}
        self.translations = {}
        self.author_normalizer = AuthorNameNormalizer()
        self.conversion_report = {
            'created': [],
            'merged': [],
            'skipped': [],
            'errors': []
        }

    @staticmethod
    def sanitize_filename(tp2_name: str) -> Optional[str]:
        """
        Sanitize tp2 name to create a valid filename.
        
        Handles:
        - Empty values (returns None)
        - Multiple tp2 names separated by semicolons (uses first one)
        - Invalid filename characters (replaces with underscores)
        
        Args:
            tp2_name: The tp2 field value from LCC database
        
        Returns:
            Sanitized filename suitable for filesystem, or None if invalid
        """
        if not tp2_name:
            return None
        
        # If multiple tp2s separated by semicolons, use the first one
        if ';' in tp2_name:
            tp2_name = tp2_name.split(';')[0].strip()
        
        # Replace invalid filename characters
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', tp2_name)
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')
        
        return sanitized if sanitized else None

    def resolve_mod_references(self, text: Any) -> Any:
        """
        Resolve mod references in format [[ID]] to actual mod names.
        
        Replaces [[64]] with the name of the mod with id=64 from the database.
        Handles strings and lists of strings.
        
        Args:
            text: Text, list of texts, or other data that may contain mod references like [[64]]
        
        Returns:
            Data with all mod references resolved to mod names
        """
        if isinstance(text, list):
            # If it's a list, process each element
            return [self.resolve_mod_references(item) for item in text]
        
        if not isinstance(text, str):
            return text
        
        def replace_reference(match):
            mod_id_str = match.group(1)
            try:
                mod_id = int(mod_id_str)
                if mod_id in self.mods_data:
                    return self.mods_data[mod_id].get('name', match.group(0))
            except (ValueError, KeyError):
                pass
            return match.group(0)
        
        return re.sub(r'\[\[(\d+)\]\]', replace_reference, text)

    def load_mods_data(self):
        """
        Load mod data from lcc-docs/db/mods.json and language files.
        
        This method:
        1. Reads the base mod data from mods.json
        2. Builds a dictionary indexed by mod ID
        3. Loads translation data for all supported languages (mods_XX.json files)
        4. Loads author name mappings
        
        Side Effects:
        - Populates self.mods_data
        - Populates self.translations
        - Initializes self.author_normalizer
        
        Raises:
        - FileNotFoundError: If mods.json not found
        - json.JSONDecodeError: If JSON is invalid
        """
        # Try mods.json first, fallback to mods_en.json
        mods_file = self.lcc_db_path / 'mods.json'
        if not mods_file.exists():
            mods_file = self.lcc_db_path / 'mods_en.json'
        
        if not mods_file.exists():
            raise FileNotFoundError(f"Mods data file not found: {self.lcc_db_path / 'mods.json'}")
        
        with open(mods_file, 'r', encoding='utf-8') as f:
            mods_list = json.load(f)
            self.mods_data = {item['id']: item for item in mods_list}
        
        log(f"Loaded {len(self.mods_data)} mods from {mods_file}")
        
        # Map language codes to file prefixes in lcc-docs/db
        lang_file_map = {
            'en_US': 'mods_en.json',
            'fr_FR': 'mods_fr.json',
            'zh_CN': 'mods_cn.json',
            'pl_PL': 'mods_pl.json',
            'de_DE': 'mods_de.json',
            'es_ES': 'mods_es.json',
            'ru_RU': 'mods_ru.json',
        }
        
        for lang_code, filename in lang_file_map.items():
            lang_file = self.lcc_db_path / filename
            if lang_file.exists():
                with open(lang_file, 'r', encoding='utf-8') as f:
                    lang_data = json.load(f)
                    self.translations[lang_code] = {item['id']: item for item in lang_data}
        
        # Load author mappings
        author_file = self.lcc_db_path / 'author_pseudos.json'
        if author_file.exists():
            self.author_normalizer.load_from_json(author_file)

    def create_mod_config(self, mod_id: int, base_mod: Dict[str, Any], existing_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a mod configuration from base mod data and translations.
        
        This method:
        1. Starts with existing config if provided, otherwise empty dict
        2. Adds basic mod info (name, tp2, safe flag)
        3. Normalizes and adds game compatibility list
        4. Normalizes and adds categories
        5. Normalizes and adds authors
        6. Builds translations from base mod and language-specific data
        7. Merges translation data for all supported languages
        
        Args:
            mod_id: The numeric ID of the mod from LCC database
            base_mod: Base mod data from mods.json
            existing_config: Existing configuration to merge with (optional)
        
        Returns:
            Complete mod configuration dictionary ready for JSON output
        
        Side Effects:
        - Uses self.translations to add localized content
        - Uses self.author_normalizer for author name normalization
        """
        config = existing_config.copy() if existing_config else {}

        config['name'] = base_mod.get('name', '')
        config['tp2'] = base_mod.get('tp2', '')
        config['safe'] = base_mod.get('safe', 0)

        games = [GameNameMapper.normalize(g) for g in base_mod.get('games', [])]
        if games:
            config['games'] = games

        categories = [CategoryMapper.normalize(c) for c in base_mod.get('categories', [])]
        if categories:
            config['categories'] = categories

        authors = [self.author_normalizer.normalize(a) for a in base_mod.get('authors', [])]
        if authors:
            config['authors'] = authors

        # Add additional fields from base_mod
        if 'urls' in base_mod and base_mod['urls']:
            config['urls'] = base_mod['urls']
        
        if 'team' in base_mod and base_mod['team']:
            config['team'] = base_mod['team']
        
        if 'translation_state' in base_mod:
            config['translation_state'] = base_mod['translation_state']
        
        if 'languages' in base_mod and base_mod['languages']:
            # Normalize languages to mapping like { 'en_US': 0, 'fr_FR': 1 }
            langs = base_mod['languages']
            if isinstance(langs, dict):
                config['languages'] = langs
            else:
                # langs expected as list of short codes or full codes
                code_map = {
                    'en': 'en_US', 'en_US': 'en_US',
                    'fr': 'fr_FR', 'fr_FR': 'fr_FR',
                    'zh': 'zh_CN', 'zh_CN': 'zh_CN', 'zh_CN': 'zh_CN',
                    'pl': 'pl_PL', 'pl_PL': 'pl_PL',
                    'de': 'de_DE', 'de_DE': 'de_DE',
                    'es': 'es_ES', 'es_ES': 'es_ES',
                    'it': 'it_IT', 'it_IT': 'it_IT',
                    'ru': 'ru_RU', 'ru_RU': 'ru_RU',
                    'cs': 'cs_CZ', 'cs_CZ': 'cs_CZ', 'cz': 'cs_CZ'
                }
                mapped = []
                for item in langs:
                    if not item:
                        continue
                    key = str(item)
                    full = code_map.get(key, None)
                    if full is None:
                        # try normalize two-letter to upper/lower
                        k = key.lower()
                        if k == 'en':
                            full = 'en_US'
                        elif k == 'fr':
                            full = 'fr_FR'
                        elif k == 'zh':
                            full = 'zh_CN'
                        elif k == 'pl':
                            full = 'pl_PL'
                        elif k == 'de':
                            full = 'de_DE'
                        elif k == 'es':
                            full = 'es_ES'
                        elif k == 'it':
                            full = 'it_IT'
                        elif k == 'ru':
                            full = 'ru_RU'
                        elif k == 'cs':
                            full = 'cs_CZ'
                        else:
                            full = key
                    if full not in mapped:
                        mapped.append(full)
                lang_map = {code: idx for idx, code in enumerate(mapped)}
                if lang_map:
                    config['languages'] = lang_map
        
        if 'status' in base_mod:
            config['status'] = base_mod['status']
        
        if 'last_update' in base_mod:
            config['last_update'] = base_mod['last_update']
        
        if 'compatibilities' in base_mod and base_mod['compatibilities']:
            config['compatibilities'] = base_mod['compatibilities']

        translations = config.get('translations', {})

        if 'description' in base_mod:
            if 'en_US' not in translations:
                translations['en_US'] = {}
            if 'description' not in translations.get('en_US', {}):
                translations['en_US']['description'] = self.resolve_mod_references(base_mod['description'])

        if 'en_US' in self.translations and mod_id in self.translations['en_US']:
            en_data = self.translations['en_US'][mod_id]
            if 'description' in en_data:
                if 'en_US' not in translations:
                    translations['en_US'] = {}
                if 'description' not in translations.get('en_US', {}):
                    translations['en_US']['description'] = self.resolve_mod_references(en_data['description'])
            if 'notes' in en_data and en_data['notes']:
                if 'en_US' not in translations:
                    translations['en_US'] = {}
                if 'notes' not in translations.get('en_US', {}):
                    translations['en_US']['notes'] = self.resolve_mod_references(en_data['notes'])

        for lang_code in ['fr_FR', 'zh_CN', 'pl_PL', 'de_DE', 'es_ES', 'cs_CZ', 'ru_RU']:
            if lang_code in self.translations and mod_id in self.translations[lang_code]:
                lang_data = self.translations[lang_code][mod_id]
                if 'description' in lang_data:
                    if lang_code not in translations:
                        translations[lang_code] = {}
                    if 'description' not in translations.get(lang_code, {}):
                        translations[lang_code]['description'] = self.resolve_mod_references(lang_data['description'])
                if 'notes' in lang_data and lang_data['notes']:
                    if lang_code not in translations:
                        translations[lang_code] = {}
                    if 'notes' not in translations.get(lang_code, {}):
                        translations[lang_code]['notes'] = self.resolve_mod_references(lang_data['notes'])

        if translations:
            config['translations'] = translations

        notes = base_mod.get('notes', [])
        if notes and ('translations' not in config or 'en_US' not in config['translations']
                      or 'notes' not in config['translations']['en_US']):
            if 'translations' not in config:
                config['translations'] = {}
            if 'en_US' not in config['translations']:
                config['translations']['en_US'] = {}
            config['translations']['en_US']['notes'] = self.resolve_mod_references(notes)

        # Resolve all mod references in the final config
        if 'translations' in config:
            for lang_code, lang_trans in config['translations'].items():
                if isinstance(lang_trans, dict):
                    if 'description' in lang_trans:
                        lang_trans['description'] = self.resolve_mod_references(lang_trans['description'])
                    if 'notes' in lang_trans:
                        lang_trans['notes'] = self.resolve_mod_references(lang_trans['notes'])

        # Ensure zh_CN translation exists and fill missing/empty subfields from en_US/fr_FR
        translations = config.get('translations', {})

        def is_empty(value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip() == ''
            if isinstance(value, (list, dict, tuple, set)):
                return len(value) == 0
            return False

        if 'zh_CN' not in translations:
            translations['zh_CN'] = {}

        zh = translations['zh_CN']

        for src in ('en_US', 'fr_FR'):
            if src in translations:
                src_obj = translations[src]
                for key, val in src_obj.items():
                    if key not in zh or is_empty(zh.get(key)):
                        if not is_empty(val):
                            # copy and resolve any mod references
                            zh[key] = self.resolve_mod_references(val)

        # final fallback for specific common fields
        if ('description' not in zh) or is_empty(zh.get('description')):
            for src in ('en_US', 'fr_FR'):
                if src in translations and 'description' in translations[src] and not is_empty(translations[src]['description']):
                    zh['description'] = self.resolve_mod_references(translations[src]['description'])
                    break

        if ('notes' not in zh) or is_empty(zh.get('notes')):
            for src in ('en_US', 'fr_FR'):
                if src in translations and 'notes' in translations[src] and not is_empty(translations[src]['notes']):
                    zh['notes'] = self.resolve_mod_references(translations[src]['notes'])
                    break

        if translations:
            config['translations'] = translations

        return config

    def convert(self, force: bool = False, merge_existing: bool = True) -> int:
        """
        Convert all mods from LCC database to data/mods format.
        
        This method:
        1. Loads all mod data and translations
        2. Creates output directory if needed
        3. Iterates through each mod in the database
        4. For each mod:
           - Checks if output file already exists
           - Loads existing config if present
           - Creates new config from base mod and translations
           - Merges with existing config if requested and appropriate
           - Writes config to JSON file
        5. Tracks statistics of created, merged, skipped, and error files
        
        Args:
            force: If True, overwrite all existing files
            merge_existing: If True, merge with existing files (ignored if force=True)
        
        Returns:
            Total number of files created or merged
        
        Side Effects:
        - Creates/modifies JSON files in self.output_path
        - Populates self.conversion_report with statistics
        """
        self.load_mods_data()
        self.output_path.mkdir(parents=True, exist_ok=True)

        log(f"Converting {len(self.mods_data)} mods...")

        for mod_id, base_mod in sorted(self.mods_data.items()):
            tp2_name = base_mod.get('tp2', '')
            
            # If tp2 is empty or n/a, use the mod name as filename instead
            if not tp2_name or tp2_name.lower() == 'n/a':
                filename_base = base_mod.get('name', '')
                sanitized_tp2 = self.sanitize_filename(filename_base)
            else:
                # Sanitize the tp2 name for use as filename
                sanitized_tp2 = self.sanitize_filename(tp2_name)
            
            if not sanitized_tp2:
                self.conversion_report['skipped'].append(f"Mod ID {mod_id}: no valid filename source")
                log(f"  Skipping mod ID {mod_id}: no valid filename source")
                continue
            
            output_filename = f"{sanitized_tp2}.json"
            output_file = self.output_path / output_filename

            existing_config = None
            if output_file.exists():
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                except Exception as e:
                    self.conversion_report['errors'].append(
                        f"Failed to load existing {output_filename}: {e}"
                    )

            if output_file.exists() and not force and not merge_existing:
                self.conversion_report['skipped'].append(output_filename)
                log(f"  Skipping {output_filename} (already exists)")
                continue

            if output_file.exists() and merge_existing and existing_config and not force:
                config = self.create_mod_config(mod_id, base_mod, existing_config)
                self.conversion_report['merged'].append(output_filename)
                action = "Merged"
            else:
                config = self.create_mod_config(mod_id, base_mod, None)
                self.conversion_report['created'].append(output_filename)
                action = "Created"

            try:
                write_json_compact(output_file, config)
                log(f"  {action} {output_filename}")
            except Exception as e:
                self.conversion_report['errors'].append(f"Error writing {output_filename}: {e}")
                log(f"  Error writing {output_filename}: {e}")

        return len(self.conversion_report['created']) + len(self.conversion_report['merged'])

    def print_report(self):
        """
        Print a detailed conversion report with statistics.
        
        The report includes:
        - Number of files created
        - Number of files merged
        - Number of files skipped
        - Number of errors encountered
        - Details of up to 10 errors
        
        Side Effects:
        - Writes report to log using the log() function
        """
        log("\n" + "="*60)
        log("CONVERSION REPORT")
        log("="*60)
        log(f"Created: {len(self.conversion_report['created'])}")
        log(f"Merged: {len(self.conversion_report['merged'])}")
        log(f"Skipped: {len(self.conversion_report['skipped'])}")
        log(f"Errors: {len(self.conversion_report['errors'])}")

        if self.conversion_report['errors']:
            log("\nErrors encountered:")
            for error in self.conversion_report['errors'][:10]:
                log(f"  - {error}")
            if len(self.conversion_report['errors']) > 10:
                log(f"  ... and {len(self.conversion_report['errors']) - 10} more")

        log("="*60)

    def normalize_languages(self) -> int:
        """
        Normalize `languages` fields in all JSON files under `self.output_path`.

        Converts lists to mapping {full_code: index} and normalizes short codes
        (e.g., 'cn' -> 'zh_CN'). Returns the number of files modified.
        """
        CODE_MAP = {
            'en': 'en_US', 'en_US': 'en_US',
            'fr': 'fr_FR', 'fr_FR': 'fr_FR',
            'zh': 'zh_CN', 'cn': 'zh_CN', 'zh_CN': 'zh_CN',
            'pl': 'pl_PL', 'pl_PL': 'pl_PL',
            'de': 'de_DE', 'de_DE': 'de_DE',
            'es': 'es_ES', 'es_ES': 'es_ES',
            'ru': 'ru_RU', 'ru_RU': 'ru_RU',
            'cs': 'cs_CZ', 'cs_CZ': 'cs_CZ', 'cz': 'cs_CZ'
        }

        def normalize_mapping(langs: Dict[str, Any]) -> Dict[str, Any]:
            out: Dict[str, Any] = {}
            for k, v in langs.items():
                full = CODE_MAP.get(k, k)
                out[full] = v
            return out

        def list_to_mapping(langs: Any) -> Dict[str, int]:
            mapped: List[str] = []
            for item in langs:
                if not item:
                    continue
                key = str(item)
                full = CODE_MAP.get(key, None)
                if full is None:
                    k = key.lower()
                    full = CODE_MAP.get(k, key)
                if full not in mapped:
                    mapped.append(full)
            return {code: idx for idx, code in enumerate(mapped)}

        mods_dir = self.output_path.resolve()
        if not mods_dir.exists():
            log(f"normalize_languages: mods dir not found: {mods_dir}")
            return 0

        files = sorted(mods_dir.glob('*.json'))
        fixed = 0

        for p in files:
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue

            changed = False
            if 'languages' in data:
                langs = data['languages']
                if isinstance(langs, dict):
                    new = normalize_mapping(langs)
                    if new != langs:
                        data['languages'] = new
                        changed = True
                elif isinstance(langs, list):
                    new = list_to_mapping(langs)
                    if new:
                        data['languages'] = new
                        changed = True

            if changed:
                try:
                    write_json_compact(p, data)
                    fixed += 1
                    log(f"Normalized languages: {p.name}")
                except Exception as e:
                    log(f"Error writing {p.name}: {e}")

        log(f"Language normalization complete. Files changed: {fixed}")
        return fixed

    def fix_missing_translations(self) -> tuple[int, int, int]:
        """
        Fix missing or empty `zh_CN` translation subfields across JSON files in `self.output_path`.

        Returns a tuple (fixed_count, unchanged_count, error_count).
        """
        mods_dir = self.output_path.resolve()
        if not mods_dir.exists():
            log(f"fix_missing_translations: mods dir not found: {mods_dir}")
            return 0, 0, 0

        files = sorted(mods_dir.glob('*.json'))
        fixed_count = 0
        unchanged_count = 0
        error_count = 0

        def is_empty(value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip() == ''
            if isinstance(value, (list, dict, tuple, set)):
                return len(value) == 0
            return False

        def get_fallback_text(mod_config: Dict[str, Any], field: str) -> Optional[Any]:
            translations = mod_config.get('translations', {})
            if 'en_US' in translations and field in translations['en_US']:
                return translations['en_US'][field]
            if 'fr_FR' in translations and field in translations['fr_FR']:
                return translations['fr_FR'][field]
            for lang_code, lang_trans in translations.items():
                if lang_code not in ('en_US', 'fr_FR', 'zh_CN') and field in lang_trans:
                    text = lang_trans[field]
                    if text:
                        return text
            return None

        for p in files:
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                log(f"Error reading {p.name}: {e}")
                error_count += 1
                continue

            modified = False
            translations = config.get('translations', {})

            if 'zh_CN' not in translations:
                translations['zh_CN'] = {}
                modified = True

            zh_cn_trans = translations['zh_CN']

            for src_lang in ('en_US', 'fr_FR'):
                if src_lang in translations:
                    src = translations[src_lang]
                    for key, val in src.items():
                        if key not in zh_cn_trans or is_empty(zh_cn_trans.get(key)):
                            if not is_empty(val):
                                zh_cn_trans[key] = val
                                modified = True

            if ('description' not in zh_cn_trans) or is_empty(zh_cn_trans.get('description')):
                fallback = get_fallback_text(config, 'description')
                if fallback:
                    zh_cn_trans['description'] = fallback
                    modified = True

            if ('notes' not in zh_cn_trans) or is_empty(zh_cn_trans.get('notes')):
                fallback = get_fallback_text(config, 'notes')
                if fallback:
                    zh_cn_trans['notes'] = fallback
                    modified = True

            if modified:
                if 'translations' not in config:
                    config['translations'] = {}
                config['translations']['zh_CN'] = zh_cn_trans
                try:
                    write_json_compact(p, config)
                    fixed_count += 1
                    log(f"Fixed translations: {p.name}")
                except Exception as e:
                    error_count += 1
                    log(f"Error writing {p.name}: {e}")
            else:
                unchanged_count += 1

        log("\n" + "="*60)
        log(f"Translation fix summary - Fixed: {fixed_count}, Unchanged: {unchanged_count}, Errors: {error_count}")
        log("="*60)

        return fixed_count, unchanged_count, error_count


def main():
    """
    Main entry point for the LCC database converter.
    
    This function:
    1. Parses command-line arguments
    2. Initializes logging
    3. Resolves input/output paths (supports both absolute and relative)
    4. Validates paths and creates directories if needed
    5. Runs the conversion process
    6. Prints a summary report
    
    Returns:
        0 on success, 1 on error
        
    Command-line Arguments:
        --db-path: Path to lcc-docs/db directory
        --output-path: Path to data/mods directory
        --force: Overwrite existing files
        --no-merge: Don't merge with existing files
        --log-file: Path to log file (optional)
    """
    global LOG_FILE
    
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert LCC-Docs database to BigWorldSetup mods format'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing mod files (default: merge with existing)'
    )
    parser.add_argument(
        '--no-merge',
        action='store_true',
        help='Do not merge with existing files (requires --force to write new files)'
    )
    parser.add_argument(
        '--db-path',
        default=None,
        help='Path to lcc-docs/db directory'
    )
    parser.add_argument(
        '--output-path',
        default=None,
        help='Path to data/mods directory'
    )
    parser.add_argument(
        '--log-file',
        default=None,
        help='Log file path (optional)'
    )

    args = parser.parse_args()

    # Initialize log file first, before any operations
    if args.log_file:
        global LOG_FILE
        LOG_FILE = args.log_file
        # Write initial header to log file
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write("LCC Database to Mods Converter Log\n")
                f.write("=" * 60 + "\n\n")
                f.flush()
        except Exception as e:
            print(f"Failed to create log file {LOG_FILE}: {e}", file=sys.stderr)
            LOG_FILE = None

    # Get workspace root and resolve paths
    workspace_root = Path(__file__).parent
    
    # Resolve db path - handle both absolute and relative paths
    if args.db_path:
        db_path_arg = Path(args.db_path)
        if db_path_arg.is_absolute():
            lcc_db_path = db_path_arg
        else:
            lcc_db_path = workspace_root / db_path_arg
    else:
        lcc_db_path = workspace_root / "lcc-docs" / "db"
    
    # Resolve output path - handle both absolute and relative paths
    if args.output_path:
        output_path_arg = Path(args.output_path)
        if output_path_arg.is_absolute():
            output_path = output_path_arg
        else:
            output_path = workspace_root / output_path_arg
    else:
        output_path = workspace_root / "data" / "mods"

    log(f"Starting conversion...")
    log(f"LCC DB Path: {lcc_db_path.resolve()}")
    log(f"Output Path: {output_path.resolve()}")
    log("")

    if not lcc_db_path.exists():
        log(f"Error: LCC database path not found: {lcc_db_path.resolve()}")
        return 1

    if not output_path.exists():
        log(f"Creating output directory: {output_path.resolve()}")
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log(f"Error creating output directory: {e}")
            return 1

    converter = LCCDatabaseConverter(str(lcc_db_path), str(output_path))

    try:
        merge = not args.no_merge
        converted = converter.convert(force=args.force, merge_existing=merge)
        converter.print_report()
        log(f"\nTotal converted/merged: {converted}")
        
        if LOG_FILE:
            log(f"\nLog saved to: {Path(LOG_FILE).resolve()}")
        
        return 0
    except Exception as e:
        log(f"Error during conversion: {e}")
        import traceback
        log(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main())
