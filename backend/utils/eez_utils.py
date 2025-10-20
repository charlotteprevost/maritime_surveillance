def classify_eez(label):
    """
    Classifies an EEZ label based on naming conventions.
    Returns: 'overlapping' | 'joint' | 'sovereign' | 'unknown'
    """
    l = label.lower()
    if "overlapping claim" in l:
        return "overlapping"
    if "joint regime" in l:
        return "joint"
    if "sovereign" in l:
        return "sovereign"
    return "unknown"


def get_eez_data(config):
    """
    Returns the full list of EEZs from the Flask app config.
    """
    return config.get("EEZ_DATA", [])


def get_deduplicated_eez_labels(config):
    """
    Returns one EEZ per ISO3 code (for UI optgroups).
    """
    seen = {}
    for e in get_eez_data(config):
        if e["iso3"] not in seen:
            seen[e["iso3"]] = e["label"]
    return [{"iso3": iso3, "label": label} for iso3, label in sorted(seen.items())]

def resolve_iso3_to_country(eez_data):
    """
    Build a mapping from ISO3 code to a readable country name
    using the most common or canonical EEZ label.

    Args:
        eez_data: List of EEZ entries with 'label' and 'iso3'

    Returns:
        dict: { "USA": "United States", ... }
    """
    from collections import defaultdict, Counter

    label_counts = defaultdict(Counter)

    for eez in eez_data:
        label = eez["label"]
        iso3 = eez["iso3"]

        # Exclude overlapping or joint regime claims from canonical name
        if "overlapping" in label.lower() or "joint" in label.lower():
            continue

        label_counts[iso3][label] += 1

    return {iso3: labels.most_common(1)[0][0] for iso3, labels in label_counts.items()}


def resolve_label_to_iso3(label, config):
    """
    Resolves a single EEZ label to its ISO3 code.
    """
    for e in get_eez_data(config):
        if e["label"].lower() == label.lower():
            return e["iso3"]
    return None


def resolve_country_names_to_iso3(names, config):
    """
    Resolves a list of EEZ labels to a unique list of ISO3 codes.
    """
    iso3s = set()
    for name in names:
        iso3 = resolve_label_to_iso3(name, config)
        if iso3:
            iso3s.add(iso3)
    return list(iso3s)


def resolve_label_to_eez_ids(label, config):
    """
    Resolves a country label to one or more EEZ IDs.
    """
    eezs = get_eez_data(config)


# I want the dropdown to look something like this:
# - Australia (All EEZs)
#      - Australia (Only)
#      - Christmas Island
#      - Cocos Islands
#      - Heard and McDonald Islands
#      - Macquarie Island
#      - Norfolk Island
# - Benin
# - Canada (All EEZs)
#      - Canada (Only)
#      - Overlapping claim: Canada / USA
# - Denmark (All EEZs)
#      - Denmark (Only)
#      - Faeroe
#      - Greenland
#      - Joint regime area Iceland / Denmark (Faeroe Islands)
# ...
# - Russia (All EEZs)
#      - Russia (Only)
#      - Joint regime area United States / Russia
# - United States of America (All EEZs)
#      - Alaska
#      - American Samoa
#      - Guam
#      - Hawaii
#      - Howland and Baker islands
#      - Jarvis Island
#      - Johnston Atoll
#      - Northern Mariana Islands
#      - Palmyra Atoll
#      - Puerto Rico
#      - United States (Only)
#      - United States Virgin Islands
#      - Wake Island
#      - Joint regime area United States / Russia
#      - Overlapping claim: Canada / USA
#      - Overlapping claim: Puerto Rico / Dominican Republic

# Examples: 
# - When a user selects Hawaii, I want to get the EEZ ID for Hawaii only.
# - When a user selects United States, I want to get the EEZ ID for the United States only.
# - When a user selects United States (All EEZs), I want to get the EEZ IDs for the all the eez entries that have the iso3 of the United States.

    if label.endswith("ALL"):
        base = label.replace(" ALL", "").strip()
        # Get all EEZs that include the country iso3
        iso3 = resolve_label_to_iso3(base, config)
        return [e["id"] for e in eezs if iso3 in e["iso3"]]
    # Get the EEZ that matches the label
    return [e["id"] for e in eezs if e["label"].lower() == label.lower()]
            









