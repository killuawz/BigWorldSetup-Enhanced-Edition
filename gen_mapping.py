#!/usr/bin/env python3
"""
Script to generate category mapping configuration between LCC and BWS formats.

This script creates a mapping configuration file that maps LCC category names
to BWS (Big World Setup) category names by matching mods by name between
both data sources.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


# Global variable to store the logger function
LOG_FUNCTION = None


def set_log_function(log_func):
    """
    Set the logging function to be used by this module.
    
    Args:
        log_func: A function that accepts a string message to log
    """
    global LOG_FUNCTION
    LOG_FUNCTION = log_func


def log_message(message: str = ""):
    """
    Log a message using either the set log function or print to console.
    
    Args:
        message: Message to log
    """
    if LOG_FUNCTION:
        LOG_FUNCTION(message)
    else:
        print(message)


def generate_category_mappings(lcc_mods_path: Path, local_mods_dir: Path) -> Dict[str, str]:
    """
    Generate category mappings between LCC and BWS formats by matching mod names.
    
    Args:
        lcc_mods_path: Path to lcc-docs/db/mods.json
        local_mods_dir: Path to data/mods directory
        
    Returns:
        Dictionary mapping LCC category names to BWS category names
    """
    # Create a mapping from mod name to its LCC categories
    lcc_mod_categories = {}
    bws_mod_categories = {}

    # Load LCC mods and their categories
    if lcc_mods_path.exists():
        log_message(f"Loading LCC mods from: {lcc_mods_path}")
        with open(lcc_mods_path, 'r', encoding='utf-8') as f:
            lcc_mods = json.load(f)
        
        for mod_entry in lcc_mods:
            mod_name = mod_entry.get('name', '').lower().strip()
            if mod_name and 'categories' in mod_entry:
                lcc_mod_categories[mod_name] = mod_entry['categories']
        log_message(f"Loaded {len(lcc_mod_categories)} LCC mods with category data")
    else:
        log_message(f"LCC mods file not found: {lcc_mods_path}")

    # Load local BWS mods and their categories
    if local_mods_dir.exists():
        log_message(f"Loading local BWS mods from: {local_mods_dir}")
        mod_files = list(local_mods_dir.glob('*.json'))
        processed_count = 0
        
        for mod_file in mod_files:
            try:
                with open(mod_file, 'r', encoding='utf-8') as f:
                    mod_data = json.load(f)
                
                # Get the mod name from the JSON file
                local_mod_name = mod_data.get('name', '').lower().strip()
                
                if local_mod_name and 'categories' in mod_data:
                    bws_mod_categories[local_mod_name] = mod_data['categories']
                    processed_count += 1
            except Exception as e:
                log_message(f"Warning: Could not process {mod_file.name}: {e}")
        
        log_message(f"Processed {processed_count} local BWS mod files")
    else:
        log_message(f"Local BWS mods directory not found: {local_mods_dir}")

    # Create a mapping from LCC categories to BWS categories
    # by matching mods with the same name
    category_mapping = {}

    # For each mod that exists in both LCC and BWS, map its categories
    matched_mods = set(lcc_mod_categories.keys()) & set(bws_mod_categories.keys())
    log_message(f"Found {len(matched_mods)} mods that exist in both LCC and BWS")

    # Create a mapping to track all possible LCC->BWS category connections
    temp_mapping = {}
    
    for mod_name in matched_mods:
        lcc_cats = lcc_mod_categories[mod_name]  # Keep original order, don't convert to set
        bws_cats = bws_mod_categories[mod_name]  # Keep original order, don't convert to set
        
        # Make sure both lists have the same length
        min_len = min(len(lcc_cats), len(bws_cats))
        
        # Map each LCC category to the corresponding BWS category based on position
        for i in range(min_len):
            lcc_cat = lcc_cats[i]
            bws_cat = bws_cats[i]
            
            if lcc_cat not in temp_mapping:
                temp_mapping[lcc_cat] = set()
            temp_mapping[lcc_cat].add(bws_cat)

    # Now determine the final mapping based on most common or first encountered mapping
    for lcc_cat, possible_bws_cats in temp_mapping.items():
        possible_bws_list = sorted(list(possible_bws_cats))  # Sort for consistency
        
        # Only add to final mapping if not already present
        if lcc_cat not in category_mapping:
            category_mapping[lcc_cat] = possible_bws_list[0]  # Choose the first one alphabetically
            
            if len(possible_bws_list) > 1:
                # More than one possible mapping exists, this is a conflict
                log_message(f"Warning: Category mapping conflict for '{lcc_cat}' -> "
                      f"possible mappings: {possible_bws_list}, selected: '{possible_bws_list[0]}'")
        else:
            # Mapping already exists, check if it's consistent
            existing_mapping = category_mapping[lcc_cat]
            if existing_mapping not in possible_bws_list:
                log_message(f"Warning: Inconsistent mapping for '{lcc_cat}' -> "
                      f"existing: '{existing_mapping}', possible: {possible_bws_list}")

    log_message(f"Generated {len(category_mapping)} unique category mappings")
    
    return category_mapping


def save_category_mappings(mappings: Dict[str, str], output_path: Path):
    """
    Save category mappings to a JSON file.
    
    Args:
        mappings: Dictionary of category mappings
        output_path: Path to save the mappings
    """
    log_message(f"Saving category mappings to: {output_path}")
    log_message(f"Total unique mappings: {len(mappings)}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)
    
    log_message("Category mappings saved successfully!")


def generate_and_save_mappings(
    lcc_mods_path: Path = Path("lcc-docs/db/mods.json"),
    local_mods_dir: Path = Path("data/mods"),
    output_path: Path = Path("category_mappings.json")
):
    """
    Convenience function to generate and save category mappings with default paths.
    
    Args:
        lcc_mods_path: Path to lcc-docs/db/mods.json
        local_mods_dir: Path to data/mods directory
        output_path: Path to save the category mappings
        
    Returns:
        Dictionary of generated category mappings
    """
    log_message("Generating category mappings...")
    log_message(f"LCC mods path: {lcc_mods_path}")
    log_message(f"BWS mods directory: {local_mods_dir}")
    log_message(f"Output path: {output_path}")
    
    # Generate mappings
    mappings = generate_category_mappings(lcc_mods_path, local_mods_dir)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save mappings
    save_category_mappings(mappings, output_path)
    
    # Print sample mappings
    log_message("\nSample mappings:")
    count = 0
    for lcc_cat, bws_cat in mappings.items():
        if count >= 10:  # Show first 10 mappings as samples
            break
        log_message(f"  LCC '{lcc_cat}' -> BWS '{bws_cat}'")
        count += 1

    return mappings


def main():
    """Main function to run the category mapping generator."""
    # Define paths
    lcc_mods_path = Path("lcc-docs/db/mods.json")
    local_mods_dir = Path("data/mods")
    output_path = Path("category_mappings.json")  # Save to project root
    
    # Allow custom paths via command line args
    if len(sys.argv) >= 2:
        lcc_mods_path = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        local_mods_dir = Path(sys.argv[2])
    if len(sys.argv) >= 4:
        output_path = Path(sys.argv[3])
    
    # Use the new function which returns the mappings
    generate_and_save_mappings(lcc_mods_path, local_mods_dir, output_path)


if __name__ == "__main__":
    main()