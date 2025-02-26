GM_FILTER_DROPDOWN_MENU_OPTIONS = [
    {"label": "GCF ID", "value": "GCF_ID"},
    {"label": "BGC Class", "value": "BGC_CLASS"},
]

GM_FILTER_DROPDOWN_BGC_CLASS_OPTIONS = [
    {"label": "Alkaloid", "value": "ALKALOID"},
    {"label": "NRP", "value": "NRP"},
    {"label": "Polyketide", "value": "POLYKETIDE"},
    {"label": "RiPP", "value": "RIPP"},
    {"label": "Saccharide", "value": "SAACCHARIDE"},
    {"label": "Terpene", "value": "TERPENE"},
    {"label": "Other", "value": "OTHER"},
    {"label": "Unknown", "value": "UNKNOWN"},
]

GM_SCORING_DROPDOWN_MENU_OPTIONS = [{"label": "Metcalf", "value": "METCALF"}]

GM_RESULTS_TABLE_MANDATORY_COLUMNS = [
    {"name": "GCF ID", "id": "GCF ID", "type": "numeric"},
    {"name": "# Links", "id": "# Links", "type": "numeric"},
    {"name": "Average Score", "id": "Average Score", "type": "numeric"},
]

GM_RESULTS_TABLE_OPTIONAL_COLUMNS = [
    {"name": "Top Spectrum ID", "id": "Top Spectrum ID", "type": "numeric"},
    {"name": "Top Spectrum Precursor m/z", "id": "Top Spectrum Precursor m/z", "type": "numeric"},
    {"name": "Top Spectrum GNPS ID", "id": "Top Spectrum GNPS ID", "type": "text"},
    {"name": "Top Spectrum Score", "id": "Top Spectrum Score", "type": "numeric"},
    {"name": "MiBIG IDs", "id": "MiBIG IDs", "type": "text"},
    {"name": "BGC Classes", "id": "BGC Classes", "type": "text"},
]

GM_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS = [
    "Top Spectrum ID",
    "Top Spectrum Precursor m/z",
    "Top Spectrum GNPS ID",
    "Top Spectrum Score",
    "MiBIG IDs",
    "BGC Classes",
]

MG_RESULTS_TABLE_MANDATORY_COLUMNS = [
    {"name": "MF ID", "id": "MF ID", "type": "numeric"},
    {"name": "Spectrum ID", "id": "Spectrum ID", "type": "numeric"},
    {"name": "# Links", "id": "# Links", "type": "numeric"},
    {"name": "Average Score", "id": "Average Score", "type": "numeric"},
]

MG_RESULTS_TABLE_OPTIONAL_COLUMNS = [
    {"name": "Top GCF ID", "id": "Top GCF ID", "type": "numeric"},
    {"name": "Top GCF Score", "id": "Top GCF Score", "type": "numeric"},
    {"name": "Top GCF MiBIG IDs", "id": "Top GCF MiBIG IDs", "type": "text"},
    {"name": "Top GCF BGC Classes", "id": "Top GCF BGC Classes", "type": "text"},
    {"name": "Spectrum Precursor m/z", "id": "Spectrum Precursor m/z", "type": "numeric"},
    {"name": "Spectrum GNPS ID", "id": "Spectrum GNPS ID", "type": "numeric"},
]

MG_RESULTS_TABLE_CHECKL_OPTIONAL_COLUMNS = [
    "Top GCF ID",
    "Top GCF Score",
    "Top GCF MiBIG IDs",
    "Top GCF BGC Classes",
    "Spectrum Precursor m/z",
    "Spectrum GNPS ID",
]
