# GM Table Configurations
GM_FILTER_DROPDOWN_MENU_OPTIONS = [
    {"label": "GCF ID", "value": "GCF_ID"},
    {"label": "BGC Class", "value": "BGC_CLASS"},
]

# BGC class options for different MIBiG versions
MIBIG_VERSIONS = [
    {"label": "MIBiG < 4.0", "value": "pre_v4"},
    {"label": "MIBiG ≥ 4.0", "value": "v4_plus"},
]

GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_PRE_V4 = [
    {"label": "Alkaloid", "value": "ALKALOID"},
    {"label": "NRP", "value": "NRP"},
    {"label": "Polyketide", "value": "POLYKETIDE"},
    {"label": "RiPP", "value": "RIPP"},
    {"label": "Saccharide", "value": "SACCHARIDE"},
    {"label": "Terpene", "value": "TERPENE"},
    {"label": "Other", "value": "OTHER"},
    {"label": "Unknown", "value": "UNKNOWN"},
]

GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS_V4 = [
    {"label": "NRPS", "value": "NRPS"},
    {"label": "PKS", "value": "PKS"},
    {"label": "Ribosomal", "value": "RIBOSOMAL"},
    {"label": "Saccharide", "value": "SACCHARIDE"},
    {"label": "Terpene", "value": "TERPENE"},
    {"label": "Other", "value": "OTHER"},
    {"label": "Unknown", "value": "UNKNOWN"},
]

GM_RESULTS_TABLE_MANDATORY_COLUMNS = [
    {"name": "GCF ID", "id": "GCF ID", "type": "numeric"},
    {"name": "# Links", "id": "# Links", "type": "numeric"},
    {"name": "Average Score", "id": "Average Score", "type": "numeric"},
]

GM_RESULTS_TABLE_OPTIONAL_COLUMNS = [
    {"name": "Top Spectrum ID", "id": "Top Spectrum ID", "type": "numeric"},
    {"name": "Top Spectrum MF ID", "id": "Top Spectrum MF ID", "type": "numeric"},
    {"name": "Top Spectrum Precursor m/z", "id": "Top Spectrum Precursor m/z", "type": "numeric"},
    {"name": "Top Spectrum GNPS ID", "id": "Top Spectrum GNPS ID", "type": "text"},
    {"name": "Top Spectrum Score", "id": "Top Spectrum Score", "type": "numeric"},
    {"name": "MiBIG IDs", "id": "MiBIG IDs", "type": "text"},
    {"name": "BGC Classes", "id": "BGC Classes", "type": "text"},
]

GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS = [
    "Top Spectrum ID",
    "Top Spectrum MF ID",
    "Top Spectrum Precursor m/z",
    "Top Spectrum GNPS ID",
    "Top Spectrum Score",
    "MiBIG IDs",
    "BGC Classes",
]

# MG Table Configurations
MG_FILTER_DROPDOWN_MENU_OPTIONS = [
    {"label": "MF ID", "value": "MF_ID"},
    {"label": "Spectrum ID", "value": "SPECTRUM_ID"},
]

MG_RESULTS_TABLE_MANDATORY_COLUMNS = [
    {"name": "MF ID", "id": "MF ID", "type": "numeric"},
    {"name": "# Links", "id": "# Links", "type": "numeric"},
    {"name": "Average Score", "id": "Average Score", "type": "numeric"},
]

MG_RESULTS_TABLE_OPTIONAL_COLUMNS = [
    {"name": "Top GCF ID", "id": "Top GCF ID", "type": "numeric"},
    {"name": "Top GCF # BGCs", "id": "Top GCF # BGCs", "type": "numeric"},
    {"name": "Top GCF BGC IDs", "id": "Top GCF BGC IDs", "type": "text"},
    {"name": "Top GCF BGC Classes", "id": "Top GCF BGC Classes", "type": "text"},
    {"name": "Top GCF Score", "id": "Top GCF Score", "type": "numeric"},
]

MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS = [
    "Top GCF ID",
    "Top GCF # BGCs",
    "Top GCF BGC IDs",
    "Top GCF BGC Classes",
    "Top GCF Score",
]

# Scoring Configurations
SCORING_DROPDOWN_MENU_OPTIONS = [{"label": "Metcalf", "value": "METCALF"}]

MAX_TOOLTIP_ROWS = 500
