from __future__ import annotations

from typing import Any

FIELD_CATALOG: dict[str, dict[str, Any]] = {
    "carrier": {
        "title": "Carrier",
        "description": "Exact supported carrier code or name. Do not use abbreviations unless listed.",
        "examples": ["USPS", "FedEx", "UPS"],
        "validation_rules": ["Must match an authoritative carrier exactly."],
        "formatting_hints": ["Use the value returned by get_carriers or validate_carrier."],
    },
    "service": {
        "title": "Service level",
        "description": "Exact carrier service level returned by carrier resources or shipment rates.",
        "examples": ["GroundAdvantage", "FEDEX_GROUND", "Priority"],
        "validation_rules": ["Must be valid for the selected carrier."],
        "formatting_hints": ["Do not use vague terms like ground unless that exact service exists."],
    },
    "predefined_package": {
        "title": "Package type",
        "description": "Carrier/package predefined package type.",
        "examples": ["Parcel", "FlatRateEnvelope", "FlatRateSmallBox"],
        "validation_rules": ["Must match a known package type exactly."],
    },
    "country": {
        "title": "Country",
        "description": "ISO 3166-1 alpha-2 country code.",
        "examples": ["US", "CA", "GB"],
        "validation_rules": ["Two-letter country code."],
        "formatting_hints": ["Use uppercase country codes."],
    },
    "state": {
        "title": "State or province",
        "description": "State, province, or region code appropriate for the destination country.",
        "examples": ["CA", "NY", "ON"],
        "validation_rules": ["Use country-specific state/province format where required."],
    },
    "zip": {
        "title": "Postal code",
        "description": "Country-specific postal or ZIP code.",
        "examples": ["94104", "10001", "M5V 2T6"],
        "validation_rules": ["Must match the destination country postal format."],
        "formatting_hints": ["For US addresses use 5-digit or ZIP+4 format."],
    },
    "street1": {
        "title": "Street address",
        "description": "Primary street address line.",
        "examples": ["417 Montgomery St"],
        "validation_rules": ["Must be a real operational shipping address, not a placeholder."],
    },
    "city": {
        "title": "City",
        "description": "Destination or origin city.",
        "examples": ["San Francisco", "New York"],
        "validation_rules": ["Required for address creation and shipment workflows."],
    },
    "weight": {
        "title": "Weight",
        "description": "Parcel weight in ounces.",
        "examples": [16, 32.5],
        "validation_rules": ["Must be greater than 0 and at most 1120 ounces."],
        "formatting_hints": ["EasyPost parcel weight is in ounces."],
    },
    "length": {
        "title": "Length",
        "description": "Parcel length in inches.",
        "examples": [10],
        "validation_rules": ["Must be greater than 0 and at most 120 inches."],
    },
    "width": {
        "title": "Width",
        "description": "Parcel width in inches.",
        "examples": [8],
        "validation_rules": ["Must be greater than 0 and at most 120 inches."],
    },
    "height": {
        "title": "Height",
        "description": "Parcel height in inches.",
        "examples": [4],
        "validation_rules": ["Must be greater than 0 and at most 120 inches."],
    },
    "rate_option": {
        "title": "Rate option",
        "description": "Numbered option from the shipment's actual returned rates.",
        "examples": [1, 2],
        "validation_rules": ["Must refer to one of the returned rate options for the shipment."],
    },
    "confirm": {
        "title": "Confirmation",
        "description": "Explicit approval for high-risk or irreversible operations.",
        "examples": [True],
        "validation_rules": ["Must be true before execution continues."],
    },
    "insurance_amount": {
        "title": "Insurance amount",
        "description": "Shipment insurance amount in USD unless otherwise specified.",
        "examples": ["100.00", "250.00"],
        "validation_rules": ["Must be non-negative currency with at most two decimals."],
    },
    "tracking_code": {
        "title": "Tracking code",
        "description": "Carrier tracking number.",
        "examples": ["EZ1000000001"],
        "validation_rules": ["Must be supplied by the carrier or EasyPost."],
    },
    "min_datetime": {
        "title": "Pickup start",
        "description": "Earliest pickup datetime.",
        "examples": ["2026-05-25T10:00:00-07:00"],
        "validation_rules": ["Must be an operational pickup datetime accepted by the carrier."],
    },
    "max_datetime": {
        "title": "Pickup end",
        "description": "Latest pickup datetime.",
        "examples": ["2026-05-25T14:00:00-07:00"],
        "validation_rules": ["Must be after pickup start."],
    },
}


def get_field_metadata(path: str) -> dict[str, Any]:
    parts = str(path or "").split(".")
    last = parts[-1] if parts else ""
    if last == "zip":
        return FIELD_CATALOG["zip"]
    if last == "country":
        return FIELD_CATALOG["country"]
    if last == "state":
        return FIELD_CATALOG["state"]
    if last == "predefined_package":
        return FIELD_CATALOG["predefined_package"]
    if last == "amount":
        return FIELD_CATALOG["insurance_amount"]
    return FIELD_CATALOG.get(last) or {
        "title": last or "Field",
        "description": f"Required field: {path}",
        "examples": [],
        "validation_rules": [],
    }


def schema_for_field(path: str) -> dict[str, Any]:
    metadata = get_field_metadata(path)
    last = path.split(".")[-1]

    numeric_fields = {"length", "width", "height", "weight", "rate_option"}
    if last in numeric_fields:
        return {
            "type": "integer" if last == "rate_option" else "number",
            "title": metadata["title"],
            "description": metadata["description"],
            "minimum": 1 if last == "rate_option" else 0.01,
            **({"maximum": 1120 if last == "weight" else 120} if last != "rate_option" else {}),
        }

    if last == "confirm":
        return {
            "type": "boolean",
            "title": metadata["title"],
            "description": metadata["description"],
            "default": False,
        }

    return {
        "type": "string",
        "title": metadata["title"],
        "description": metadata["description"],
        "minLength": 1,
        "maxLength": 255,
    }


def examples_for_fields(paths: list[str]) -> dict[str, list]:
    return {path: get_field_metadata(path).get("examples", []) for path in paths}
