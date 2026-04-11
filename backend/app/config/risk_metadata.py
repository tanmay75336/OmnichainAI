import json
from pathlib import Path


RISK_METADATA_FILE = Path(__file__).with_name("risk_metadata.json")


def _load_metadata():
    with RISK_METADATA_FILE.open("r", encoding="utf-8") as file_pointer:
        return json.load(file_pointer)


_RISK_METADATA = _load_metadata()


def get_region_risk_metadata(region_type):
    normalized = region_type.lower().replace("-", "_").replace(" ", "_")
    metadata = _RISK_METADATA.get(normalized)
    if metadata:
        return metadata
    return _RISK_METADATA["tier_2"]


def get_all_region_risk_metadata():
    return dict(_RISK_METADATA)
