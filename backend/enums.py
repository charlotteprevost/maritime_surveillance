from enum import Enum

# For the /4wings/generate-png endpoint
# For the /4wings/tile/heatmap/{z}/{x}/{y} endpoint
# For the /4wings/interaction/{z}/{x}/{y}/{cell} endpoint
class Dataset(str, Enum):
    SAR = "public-global-sar-presence:latest"
    AIS = "public-global-fishing-effort:latest"

# For the /4wings/generate-png endpoint
# For the /4wings/tile/heatmap/{z}/{x}/{y} endpoint
class Interval(str, Enum):
    DAY = "DAY"
    HOUR = "HOUR"
    TEN_DAYS = "10DAYS"
    MONTH = "MONTH"
    YEAR = "YEAR"

# For the /4wings/generate-png endpoint
# For the /4wings/tile/heatmap/{z}/{x}/{y} endpoint
# For the /4wings/interaction/{z}/{x}/{y}/{cell} endpoint
class NeuralVesselType(str, Enum):
    LIKELY_FISHING = "Likely Fishing"
    LIKELY_NON_FISHING = "Likely non-fishing"
    UNKNOWN = "Unknown"

# For the /4wings/generate-png endpoint
# For the /4wings/tile/heatmap/{z}/{x}/{y} endpoint
# For the /4wings/interaction/{z}/{x}/{y}/{cell} endpoint
class GearType(str, Enum):
    TUNA_PURSE_SEINES = "tuna_purse_seines"
    DRIFTNETS = "driftnets"
    TROLLERS = "trollers"
    SET_LONGLINES = "set_longlines"
    PURSE_SEINES = "purse_seines"
    POTS_AND_TRAPS = "pots_and_traps"
    OTHER_FISHING = "other_fishing"
    DREDGE_FISHING = "dredge_fishing"
    SET_GILLNETS = "set_gillnets"
    FIXED_GEAR = "fixed_gear"
    TRAWLERS = "trawlers"
    FISHING = "fishing"
    SEINERS = "seiners"
    SQUID_JIGGER = "squid_jigger"
    POLE_AND_LINE = "pole_and_line"
    DRIFTING_LONGLINES = "drifting_longlines"

# For the /4wings/generate-png endpoint
# For the /4wings/tile/heatmap/{z}/{x}/{y} endpoint
# For the /4wings/interaction/{z}/{x}/{y}/{cell} endpoint
class ShipType(str, Enum):
    CARRIER = "carrier"
    SEISMIC_VESSEL = "seismic_vessel"
    PASSENGER = "passenger"
    OTHER = "other"
    SUPPORT = "support"
    BUNKER = "bunker"
    GEAR = "gear"
    CARGO = "cargo"
    FISHING = "fishing"
    DISCREPANCY = "discrepancy"

# For the /v3/vessels/{vesselId} endpoint
class VesselRegistryMatch(str, Enum):
    SEVERAL_FIELDS = "SEVERAL_FIELDS"
    NO_MATCH = "NO_MATCH"
    ALL = "ALL"

# For the /v3/vessels/{vesselId} endpoint
class RegistryInfoDetail(str, Enum):
    NONE = "NONE"
    DELTA = "DELTA"
    ALL = "ALL"

# For the /api/insights/vessels endpoint
class InsightType(str, Enum):
    FISHING = "FISHING"
    GAP = "GAP"
    COVERAGE = "COVERAGE"
    VESSEL_IDENTITY_IUU_VESSEL_LIST = "VESSEL-IDENTITY-IUU-VESSEL-LIST"
