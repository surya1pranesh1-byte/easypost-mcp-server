from __future__ import annotations

CARRIERS: list[dict] = [
    {"code": "USPS", "name": "USPS", "aliases": ["united states postal service"]},
    {"code": "FedEx", "name": "FedEx", "aliases": ["federal express"]},
    {"code": "UPS", "name": "UPS", "aliases": ["united parcel service"]},
    {"code": "DHLExpress", "name": "DHL Express", "aliases": ["dhl"]},
    {"code": "CanadaPost", "name": "Canada Post", "aliases": ["canadapost"]},
]

SERVICES_BY_CARRIER: dict[str, list[str]] = {
    "USPS": [
        "GroundAdvantage",
        "First",
        "Priority",
        "Express",
        "ParcelSelect",
        "MediaMail",
        "LibraryMail",
    ],
    "FedEx": [
        "FEDEX_GROUND",
        "FEDEX_2_DAY",
        "FEDEX_2_DAY_AM",
        "STANDARD_OVERNIGHT",
        "PRIORITY_OVERNIGHT",
        "FIRST_OVERNIGHT",
        "GROUND_HOME_DELIVERY",
        "INTERNATIONAL_PRIORITY",
        "INTERNATIONAL_ECONOMY",
    ],
    "UPS": [
        "Ground",
        "UPSStandard",
        "UPSSaver",
        "NextDayAir",
        "NextDayAirSaver",
        "2ndDayAir",
        "3DaySelect",
        "WorldwideExpress",
        "WorldwideExpedited",
    ],
    "DHLExpress": [
        "ExpressWorldwide",
        "ExpressEasy",
        "ExpressEnvelope",
        "MedicalExpress",
    ],
    "CanadaPost": [
        "RegularParcel",
        "ExpeditedParcel",
        "Xpresspost",
        "Priority",
    ],
}

PACKAGE_TYPES: list[str] = [
    "Parcel",
    "FlatRateEnvelope",
    "FlatRateLegalEnvelope",
    "FlatRatePaddedEnvelope",
    "FlatRateSmallBox",
    "FlatRateMediumBox",
    "FlatRateLargeBox",
]

COUNTRIES: list[dict[str, str]] = [
    {"code": "US", "name": "United States"},
    {"code": "CA", "name": "Canada"},
    {"code": "GB", "name": "United Kingdom"},
    {"code": "AU", "name": "Australia"},
    {"code": "DE", "name": "Germany"},
    {"code": "FR", "name": "France"},
    {"code": "IN", "name": "India"},
]

STATES_BY_COUNTRY: dict[str, list[str]] = {
    "US": [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
    ],
    "CA": ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"],
}

PAYMENT_METHODS: list[str] = ["SENDER", "THIRD_PARTY", "RECEIVER"]
