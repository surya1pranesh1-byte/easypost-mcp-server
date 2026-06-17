from __future__ import annotations

from typing import Any


def map_rate(rate: Any) -> dict | None:
    if rate is None:
        return None
    return {
        "id": getattr(rate, "id", None),
        "carrier": getattr(rate, "carrier", None),
        "service": getattr(rate, "service", None),
        "rate": getattr(rate, "rate", None),
        "currency": getattr(rate, "currency", None) or "USD",
        "delivery_days": getattr(rate, "delivery_days", None),
        "delivery_date": getattr(rate, "delivery_date", None),
        "delivery_date_guaranteed": getattr(rate, "delivery_date_guaranteed", None),
    }


def map_address(address: Any) -> dict | None:
    if address is None:
        return None
    return {
        "id": getattr(address, "id", None),
        "street1": getattr(address, "street1", None),
        "street2": getattr(address, "street2", None),
        "city": getattr(address, "city", None),
        "state": getattr(address, "state", None),
        "zip": getattr(address, "zip", None),
        "country": getattr(address, "country", None),
        "residential": getattr(address, "residential", None),
        "verifications": getattr(address, "verifications", None),
    }


def map_tracker(tracker: Any) -> dict | None:
    if tracker is None:
        return None
    raw_details = getattr(tracker, "tracking_details", []) or []
    tracking_details = [
        {
            "message": getattr(d, "message", None),
            "status": getattr(d, "status", None),
            "status_detail": getattr(d, "status_detail", None),
            "datetime": getattr(d, "datetime", None),
            "source": getattr(d, "source", None),
            "tracking_location": (
                {
                    "city": getattr(d.tracking_location, "city", None),
                    "state": getattr(d.tracking_location, "state", None),
                    "country": getattr(d.tracking_location, "country", None),
                    "zip": getattr(d.tracking_location, "zip", None),
                }
                if getattr(d, "tracking_location", None) else None
            ),
        }
        for d in (raw_details if isinstance(raw_details, list) else [])
    ]
    return {
        "id": getattr(tracker, "id", None),
        "tracking_code": getattr(tracker, "tracking_code", None),
        "carrier": getattr(tracker, "carrier", None),
        "status": getattr(tracker, "status", None),
        "status_detail": getattr(tracker, "status_detail", None),
        "estimated_delivery_date": getattr(tracker, "est_delivery_date", None),
        "signed_by": getattr(tracker, "signed_by", None),
        "public_url": getattr(tracker, "public_url", None),
        "tracking_details": tracking_details,
    }


def map_shipment(shipment: Any) -> dict | None:
    if shipment is None:
        return None
    parcel = getattr(shipment, "parcel", None)
    postage_label = getattr(shipment, "postage_label", None)
    raw_rates = getattr(shipment, "rates", []) or []
    return {
        "id": getattr(shipment, "id", None),
        "mode": getattr(shipment, "mode", None),
        "status": getattr(shipment, "status", None),
        "tracking_code": getattr(shipment, "tracking_code", None),
        "reference": getattr(shipment, "reference", None),
        "from_address": map_address(getattr(shipment, "from_address", None)),
        "to_address": map_address(getattr(shipment, "to_address", None)),
        "parcel": {
            "id": getattr(parcel, "id", None),
            "length": getattr(parcel, "length", None),
            "width": getattr(parcel, "width", None),
            "height": getattr(parcel, "height", None),
            "weight": getattr(parcel, "weight", None),
        } if parcel else None,
        "selected_rate": map_rate(getattr(shipment, "selected_rate", None)),
        "rates": [map_rate(r) for r in (raw_rates if isinstance(raw_rates, list) else [])],
        "postage_label": {
            "label_url": getattr(postage_label, "label_url", None),
            "label_pdf_url": getattr(postage_label, "label_pdf_url", None),
            "label_zpl_url": getattr(postage_label, "label_zpl_url", None),
            "label_file_type": getattr(postage_label, "label_file_type", None),
        } if postage_label else None,
        "tracker": map_tracker(getattr(shipment, "tracker", None)),
    }


def map_collection(collection: Any, mapper: Any) -> dict[str, Any]:
    has_more = bool(getattr(collection, "has_more", False))
    raw_shipments = getattr(collection, "shipments", None)
    if isinstance(raw_shipments, list):
        items = [mapper(item) for item in raw_shipments]
    elif isinstance(collection, list):
        items = [mapper(item) for item in collection]
    else:
        items = []
    return {"has_more": has_more, "items": items}
