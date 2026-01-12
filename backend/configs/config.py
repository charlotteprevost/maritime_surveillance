# Project Configuration
from datetime import datetime, timedelta
import os

# QGIS paths - only used for local development/automation
# These are optional and can be overridden via environment variables
QGIS_PATH = os.getenv("QGIS_PATH", "/Applications/QGIS-LTR.app/Contents/MacOS/QGIS")
PROJECT_PATH = os.getenv("PROJECT_PATH", "")

# Color Mapping for Layer Styling (used in QGIS or Web)
COLOR_MAPPING = {
    "FRA": "#0077FF",
    "USA": "#FF4444",
    "FRA-USA": "#AA00AA"
}

# Global API Base
GFW_BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"

# =============================
# GFW Dataset Identifiers
# =============================
DATASETS = {
    "sar": "public-global-sar-presence:latest",
    "fishing": "public-global-fishing-events:latest",
    "port_visits": "public-global-port-visits-events:latest",
    "encounters": "public-global-encounters-events:latest",
    "loitering": "public-global-loitering-events:latest",
    "gaps": "public-global-gaps-events:latest",
    "identity": "public-global-vessel-identity:latest",
    "eez": "public-eez-areas"
}

# =============================
# WINGS API (Map Raster & Reports)
# =============================
WINGS_API = {
    "report": f"{GFW_BASE_URL}/4wings/report",
    "generate_png": f"{GFW_BASE_URL}/4wings/generate-png",
    "bins": f"{GFW_BASE_URL}/4wings/bins",  # requires zoom level
    "tile": f"{GFW_BASE_URL}/4wings/tile/heatmap",  # /{z}/{x}/{y}
    "stats": f"{GFW_BASE_URL}/4wings/stats"
}

SAR_TILE_STYLE = {
    "url": "https://gateway.api.globalfishingwatch.org/v3/4wings/tile/heatmap/{z}/{x}/{y}?format=PNG&interval=DAY&datasets[0]=public-global-sar-presence:latest&style=eyJjb2xvciI6WzIyLDYzLDEzN10sInJhbXAiOlswLDg5MjksMzQxODEsNzIyMDMsMTIyNjA5LDE3NzQ3OSwyNjI0ODEsNDIxMTk2LDU2OTM5MF19",
    "id": "eyJjb2xvciI6WzIyLDYzLDEzN10sInJhbXAiOlswLDg5MjksMzQxODEsNzIyMDMsMTIyNjA5LDE3NzQ3OSwyNjI0ODEsNDIxMTk2LDU2OTM5MF19"
}

# =============================
# Events API
# =============================
EVENTS_API = {
    "base": f"{GFW_BASE_URL}/events",  # use GET or POST
    "datasets": {
        "fishing": DATASETS["fishing"],
        "port_visits": DATASETS["port_visits"],
        "encounters": DATASETS["encounters"],
        "loitering": DATASETS["loitering"],
        "gaps": DATASETS["gaps"]
    }
}

# =============================
# Vessel Identity & Tracking
# =============================
VESSELS_API = {
    "search": f"{GFW_BASE_URL}/vessels/search",
    "get_by_id": f"{GFW_BASE_URL}/vessels",  # /{vesselId}
    "batch_lookup": f"{GFW_BASE_URL}/vessels"  # ?ids[0]=...
}

# =============================
# Insights API (IUU, Gaps, Coverage)
# =============================
INSIGHTS_API = {
    "base": f"{GFW_BASE_URL}/insights/vessels"
}

# =============================
# Reference Boundaries (EEZ, RFMO, MPA)
# =============================
DATASETS_API = {
    "eez_regions": f"{GFW_BASE_URL}/datasets/public-eez-areas",
    "rfmo_regions": f"{GFW_BASE_URL}/datasets/public-rfmo-areas",
    "mpa_regions": f"{GFW_BASE_URL}/datasets/public-mpa-all"
}

# Defaults and UI/Backend Thresholds
DEFAULTS = {
    "max_days_range": 30,
    "throttle_delay_ms": 250
}

ISO3_TO_COUNTRY = {
    'ALB': 'Albania',
    'DZA': 'Algeria',
    'AGO': 'Angola',
    'ATA': 'Antarctica',
    'ATG': 'Antigua and Barbuda',
    'ARG': 'Argentina',
    'AUS': 'Australia',
    'AZE': 'Azerbaijan',
    'BHS': 'Bahamas',
    'BHR': 'Bahrain',
    'BGD': 'Bangladesh',
    'BEL': 'Belgium',
    'BLZ': 'Belize',
    'BEN': 'Benin',
    'BIH': 'Bosnia and Herzegovina',
    'BRA': 'Brazil',
    'BRN': 'Brunei',
    'BGR': 'Bulgaria',
    'KHM': 'Cambodia',
    'CMR': 'Cameroon',
    'CAN': 'Canada',
    'CPV': 'Cape Verde',
    'CHL': 'Chile',
    'CHN': 'China',
    'COL': 'Colombia',
    'COM': 'Comoros',
    'CRI': 'Costa Rica',
    'CUB': 'Cuba',
    'CYP': 'Cyprus',
    'COD': 'Democratic Republic of the Congo',
    'DJI': 'Djibouti',
    'DMA': 'Dominica',
    'DOM': 'Dominican Republic',
    'ECU': 'Ecuador',
    'EGY': 'Egypt',
    'SLV': 'El Salvador',
    'GNQ': 'Equatorial Guinea',
    'ERI': 'Eritrea',
    'EST': 'Estonia',
    'FJI': 'Fiji',
    'FIN': 'Finland',
    'GAB': 'Gabon',
    'GMB': 'Gambia',
    'GEO': 'Georgia',
    'DEU': 'Germany',
    'GHA': 'Ghana',
    'GIB': 'Gibraltar',
    'GRC': 'Greece',
    'GRD': 'Grenada',
    'GTM': 'Guatemala',
    'GIN': 'Guinea',
    'GNB': 'Guinea-Bissau',
    'HTI': 'Haiti',
    'HND': 'Honduras',
    'ISL': 'Iceland',
    'IND': 'India',
    'IDN': 'Indonesia',
    'IRN': 'Iran',
    'IRQ': 'Iraq',
    'IRL': 'Ireland',
    'ISR': 'Israel',
    'ITA': 'Italy',
    'CIV': 'Ivory Coast',
    'JAM': 'Jamaica',
    'JPN': 'Japan',
    'HRV': 'Croatia',
    'BRB': 'Barbados',
    'DNK': 'Denmark (Faeroe Islands)',
    'FRA': 'France',
    'NOR': 'Norway',
    'JOR': 'Jordan',
    'KAZ': 'Kazakhstan',
    'KEN': 'Kenya',
    'KIR': 'Kiribati',
    'KWT': 'Kuwait',
    'LVA': 'Latvia',
    'LBN': 'Lebanon',
    'LBR': 'Liberia',
    'LBY': 'Libya',
    'LTU': 'Lithuania',
    'MDG': 'Madagascar',
    'MYS': 'Malaysia',
    'MDV': 'Maldives',
    'MLT': 'Malta',
    'MHL': 'Marshall Islands',
    'MRT': 'Mauritania',
    'MEX': 'Mexico',
    'FSM': 'Micronesia',
    'MCO': 'Monaco',
    'MNE': 'Montenegro',
    'MAR': 'Morocco',
    'MOZ': 'Mozambique',
    'MMR': 'Myanmar',
    'NAM': 'Namibia',
    'NRU': 'Nauru',
    'NLD': 'Netherlands',
    'NZL': 'New Zealand',
    'NIC': 'Nicaragua',
    'NGA': 'Nigeria',
    'PRK': 'North Korea',
    'OMN': 'Oman',
    'GUY': 'Guyana',
    'PAK': 'Pakistan',
    'PLW': 'Palau',
    'PSE': 'Palestine',
    'PAN': 'Panama',
    'PNG': 'Papua New Guinea',
    'PER': 'Peru',
    'PHL': 'Philippines',
    'POL': 'Poland',
    'PRT': 'Portugal',
    'QAT': 'Qatar',
    'MUS': 'Republic of Mauritius',
    'COG': 'Republic of the Congo',
    'ROU': 'Romania',
    'RUS': 'Russia',
    'KNA': 'Saint Kitts and Nevis',
    'LCA': 'Saint Lucia',
    'VCT': 'Saint Vincent and the Grenadines',
    'WSM': 'Samoa',
    'STP': 'Sao Tome and Principe',
    'SAU': 'Saudi Arabia',
    'SEN': 'Senegal',
    'SYC': 'Seychelles',
    'SLE': 'Sierra Leone',
    'SGP': 'Singapore',
    'SVN': 'Slovenia',
    'SLB': 'Solomon Islands',
    'SOM': 'Somalia',
    'ZAF': 'South Africa',
    'KOR': 'South Korea',
    'ESP': 'Spain',
    'LKA': 'Sri Lanka',
    'SDN': 'Sudan',
    'SUR': 'Suriname',
    'SWE': 'Sweden',
    'SYR': 'Syria',
    'TWN': 'Taiwan',
    'TZA': 'Tanzania',
    'THA': 'Thailand',
    'TLS': 'Timor-Leste',
    'TGO': 'Togo',
    'TON': 'Tonga',
    'TTO': 'Trinidad and Tobago',
    'TUN': 'Tunisia',
    'TUR': 'Turkey',
    'TKM': 'Turkmenistan',
    'TUV': 'Tuvalu',
    'UKR': 'Ukraine',
    'ARE': 'United Arab Emirates',
    'GBR': 'United Kingdom',
    'USA': 'United States',
    'URY': 'Uruguay',
    'VUT': 'Vanuatu',
    'VEN': 'Venezuela',
    'VNM': 'Vietnam',
    'ESH': 'Western Sahara',
    'YEM': 'Yemen'
 };

# Config loaded successfully (logging handled by app.py)
