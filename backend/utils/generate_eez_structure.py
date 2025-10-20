#!/usr/bin/env python3
"""
Script to analyze the actual EEZ data and generate the proper improved structure
"""

import json
from collections import defaultdict

def analyze_eez_data():
    """Analyze the actual EEZ data and create logical groupings"""
    
    with open('eez_data.json', 'r') as f:
        eez_data = json.load(f)
    
    # Group EEZs by ISO3 code
    iso3_groups = defaultdict(list)
    eez_entries = {}
    
    for eez_id, eez in eez_data.items():
        iso3 = eez.get('iso3')
        if iso3:
            iso3_groups[iso3].append(eez_id)
            
            # Determine if this is the main EEZ (usually the one with just the country name)
            is_main = eez.get('label') == get_country_name(iso3)
            
            eez_entries[eez_id] = {
                "label": eez.get("label", ""),
                "iso3_codes": [iso3],
                "bbox": eez.get("bbox", []),
                "group": eez.get("group", ""),
                "type": eez.get("type", "sovereign"),
                "parent_group": eez.get("group", ""),
                "is_main_eez": is_main
            }
    
    # Create logical groups for countries with multiple EEZs
    logical_groups = {}
    country_mappings = {}
    
    for iso3, eez_ids in iso3_groups.items():
        country_name = get_country_name(iso3)
        
        # Find main EEZ
        main_eez_id = None
        for eez_id in eez_ids:
            if eez_data[eez_id]["label"] == country_name:
                main_eez_id = eez_id
                break
        
        # If no main EEZ found, use the first one
        if not main_eez_id:
            main_eez_id = eez_ids[0]
        
        # Store country mapping
        country_mappings[iso3] = {
            "name": country_name,
            "eez_ids": eez_ids,
            "type": "sovereign",
            "main_eez_id": main_eez_id
        }
        
        # If country has multiple EEZs, create a logical group
        if len(eez_ids) > 1:
            group_key = f"{country_name} ({iso3})"
            logical_groups[group_key] = {
                "label": f"{country_name} (All Territories)",
                "description": f"All {country_name} EEZs including overseas territories",
                "eez_ids": eez_ids,
                "type": "country_group",
                "iso3_codes": [iso3],
                "main_eez_id": main_eez_id
            }
    
    # Create the improved structure
    improved_structure = {
        "metadata": {
            "version": "2.0",
            "description": "Proper EEZ data structure based on actual data analysis",
            "generated": "2024-01-01",
            "total_eezs": len(eez_entries),
            "total_countries": len(country_mappings),
            "countries_with_groups": len(logical_groups)
        },
        "eez_entries": eez_entries,
        "logical_groups": logical_groups,
        "country_mappings": country_mappings
    }
    
    return improved_structure

def get_country_name(iso3):
    """Get country name from ISO3 code"""
    country_names = {
        'FRA': 'France',
        'GBR': 'United Kingdom',
        'USA': 'United States',
        'EST': 'Estonia',
        'FIN': 'Finland',
        'CMR': 'Cameroon',
        'DNK': 'Denmark',
        'GIN': 'Guinea',
        'DOM': 'Dominican Republic',
        'ATG': 'Antigua and Barbuda',
        'QAT': 'Qatar',
        'SAU': 'Saudi Arabia',
        'ARE': 'United Arab Emirates',
        'VEN': 'Venezuela',
        'COL': 'Colombia',
        'VGB': 'British Virgin Islands',
        'BHS': 'Bahamas',
        'BRB': 'Barbados',
        'BLZ': 'Belize',
        'CAN': 'Canada',
        'CHL': 'Chile',
        'CHN': 'China',
        'CIV': 'Côte d\'Ivoire',
        'CUB': 'Cuba',
        'CZE': 'Czech Republic',
        'DEU': 'Germany',
        'GRC': 'Greece',
        'HRV': 'Croatia',
        'IDN': 'Indonesia',
        'IND': 'India',
        'IRL': 'Ireland',
        'ISL': 'Iceland',
        'ITA': 'Italy',
        'JAM': 'Jamaica',
        'JPN': 'Japan',
        'KEN': 'Kenya',
        'KHM': 'Cambodia',
        'KOR': 'South Korea',
        'LBR': 'Liberia',
        'LBY': 'Libya',
        'LKA': 'Sri Lanka',
        'MAR': 'Morocco',
        'MEX': 'Mexico',
        'MLT': 'Malta',
        'MNG': 'Mongolia',
        'MOZ': 'Mozambique',
        'MRT': 'Mauritania',
        'MUS': 'Mauritius',
        'MWI': 'Malawi',
        'MYS': 'Malaysia',
        'NAM': 'Namibia',
        'NER': 'Niger',
        'NGA': 'Nigeria',
        'NLD': 'Netherlands',
        'NOR': 'Norway',
        'NZL': 'New Zealand',
        'OMN': 'Oman',
        'PAK': 'Pakistan',
        'PAN': 'Panama',
        'PER': 'Peru',
        'PHL': 'Philippines',
        'POL': 'Poland',
        'PRT': 'Portugal',
        'RUS': 'Russia',
        'SDN': 'Sudan',
        'SEN': 'Senegal',
        'SGP': 'Singapore',
        'SLE': 'Sierra Leone',
        'SLV': 'El Salvador',
        'SOM': 'Somalia',
        'SSD': 'South Sudan',
        'SWE': 'Sweden',
        'SYR': 'Syria',
        'TCD': 'Chad',
        'THA': 'Thailand',
        'TGO': 'Togo',
        'TUN': 'Tunisia',
        'TUR': 'Turkey',
        'TZA': 'Tanzania',
        'UGA': 'Uganda',
        'URY': 'Uruguay',
        'VNM': 'Vietnam',
        'YEM': 'Yemen',
        'ZAF': 'South Africa',
        'ZWE': 'Zimbabwe'
    }
    return country_names.get(iso3, iso3)

if __name__ == "__main__":
    print("Analyzing EEZ data...")
    improved_structure = analyze_eez_data()
    
    # Save the improved structure
    with open('eez_data_improved.json', 'w') as f:
        json.dump(improved_structure, f, indent=2)
    
    print(f"Generated eez_data_improved.json")
    print(f"Total EEZs: {improved_structure['metadata']['total_eezs']}")
    print(f"Total countries: {improved_structure['metadata']['total_countries']}")
    print(f"Countries with logical groups: {improved_structure['metadata']['countries_with_groups']}")
    
    # Show some examples
    print("\nExample logical groups:")
    for group_key, group in list(improved_structure['logical_groups'].items())[:5]:
        print(f"  {group_key}: {len(group['eez_ids'])} EEZs")
    
    print("\nExample individual countries:")
    for iso3, country in list(improved_structure['country_mappings'].items())[:5]:
        if len(country['eez_ids']) == 1:
            print(f"  {country['name']} ({iso3}): 1 EEZ")