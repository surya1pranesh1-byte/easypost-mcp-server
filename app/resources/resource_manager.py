from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from app.resources.cache import ResourceCache
from app.resources.fuzzy import fuzzy_suggest, normalize_candidate
from app.resources.static_resources import (
    CARRIERS,
    COUNTRIES,
    PACKAGE_TYPES,
    PAYMENT_METHODS,
    SERVICES_BY_CARRIER,
    STATES_BY_COUNTRY,
)

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient

_CACHE_KEYS = {
    "carriers": "carriers",
    "services": "services",
    "package_types": "packageTypes",
    "countries": "countries",
    "carrier_accounts": "carrierAccounts",
    "warehouses": "warehouses",
    "states": "states",
    "payment_methods": "paymentMethods",
}


def _validation_result(
    *,
    valid: bool,
    confidence: float = 1.0,
    issues: list | None = None,
    suggestions: list | None = None,
    value: Any = None,
) -> dict[str, Any]:
    return {
        "valid": valid,
        "confidence": confidence,
        "issues": issues or [],
        "suggestions": suggestions or [],
        "value": value,
    }


class ResourceManager:
    def __init__(self, easypost_client: EasyPostClient, *, ttl_ms: int = 15 * 60 * 1000) -> None:
        self._easypost = easypost_client
        self._cache = ResourceCache(ttl_ms=ttl_ms)
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self, context: dict | None = None) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await self.refresh(context or {})
            self._initialized = True

    async def refresh(self, context: dict | None = None) -> None:
        ctx = context or {}
        self._cache.set(_CACHE_KEYS["carriers"], CARRIERS)
        self._cache.set(_CACHE_KEYS["services"], SERVICES_BY_CARRIER)
        self._cache.set(_CACHE_KEYS["package_types"], PACKAGE_TYPES)
        self._cache.set(_CACHE_KEYS["countries"], COUNTRIES)
        self._cache.set(_CACHE_KEYS["states"], STATES_BY_COUNTRY)
        self._cache.set(_CACHE_KEYS["payment_methods"], PAYMENT_METHODS)
        self._cache.set(_CACHE_KEYS["warehouses"], [])

        try:
            carrier_accounts = await self._easypost.execute(
                "carrier_accounts.list",
                lambda client: client.carrier_account.all(),
                ctx,
            )
            accounts = carrier_accounts if isinstance(carrier_accounts, list) else []
            self._cache.set(_CACHE_KEYS["carrier_accounts"], accounts)
        except Exception as exc:
            logger = ctx.get("logger")
            if logger:
                logger.warning(
                    "Carrier account resource refresh failed; continuing with static resources",
                    error_name=type(exc).__name__,
                    error_code=getattr(exc, "code", None),
                    error_message=str(exc),
                )
            self._cache.set(_CACHE_KEYS["carrier_accounts"], [])

    async def ensure_fresh(self, context: dict | None = None) -> None:
        if not self._initialized or not self._cache.has_fresh(_CACHE_KEYS["carriers"]):
            await self.initialize(context)

    def get_carriers(self) -> list[dict]:
        return self._cache.get(_CACHE_KEYS["carriers"]) or CARRIERS

    def get_services(self, carrier_code: str | None = None) -> dict | list:
        services = self._cache.get(_CACHE_KEYS["services"]) or SERVICES_BY_CARRIER
        if carrier_code:
            return services.get(carrier_code, [])
        return services

    def get_carrier_accounts(self) -> list:
        return self._cache.get(_CACHE_KEYS["carrier_accounts"]) or []

    def get_package_types(self) -> list[str]:
        return self._cache.get(_CACHE_KEYS["package_types"]) or PACKAGE_TYPES

    def get_countries(self) -> list[dict]:
        return self._cache.get(_CACHE_KEYS["countries"]) or COUNTRIES

    def get_states(self, country_code: str | None = None) -> dict | list:
        states = self._cache.get(_CACHE_KEYS["states"]) or STATES_BY_COUNTRY
        if country_code:
            return states.get(country_code, [])
        return states

    def get_payment_methods(self) -> list[str]:
        return self._cache.get(_CACHE_KEYS["payment_methods"]) or PAYMENT_METHODS

    def get_operational_context(self) -> dict[str, Any]:
        return {
            "resources": {
                "carriers_count": len(self.get_carriers()),
                "package_types_count": len(self._cache.get(_CACHE_KEYS["package_types"]) or []),
                "countries_count": len(self._cache.get(_CACHE_KEYS["countries"]) or []),
                "user_shipping_accounts_count": len(self.get_carrier_accounts()),
                "cache": {key: self._cache.metadata(key) for key in _CACHE_KEYS.values()},
            }
        }

    def validate_carrier(self, input_str: str) -> dict[str, Any]:
        carriers = self.get_carriers()
        normalized = normalize_candidate(input_str)
        for carrier in carriers:
            labels = [carrier.get("code"), carrier.get("name"), *(carrier.get("aliases") or [])]
            if any(normalize_candidate(lb) == normalized for lb in labels if lb):
                return _validation_result(valid=True, confidence=1.0, value=carrier["code"])
        return _validation_result(
            valid=False,
            confidence=0.0,
            issues=[{"code": "UNKNOWN_CARRIER", "message": f"Unsupported carrier: {input_str}"}],
            suggestions=fuzzy_suggest(input_str, carriers),
        )

    def validate_service(self, carrier_input: str, service_input: str) -> dict[str, Any]:
        carrier = self.validate_carrier(carrier_input)
        if not carrier["valid"]:
            return carrier
        services = self.get_services(carrier["value"])
        exact = next(
            (s for s in services if normalize_candidate(s) == normalize_candidate(service_input)),
            None,
        )
        if exact:
            return _validation_result(valid=True, confidence=1.0, value=exact)
        return _validation_result(
            valid=False,
            confidence=0.0,
            issues=[{
                "code": "UNSUPPORTED_SERVICE_FOR_CARRIER",
                "message": f"Unsupported service for {carrier['value']}: {service_input}",
            }],
            suggestions=fuzzy_suggest(
                service_input,
                [{"code": s, "name": s} for s in services],
                threshold=0.7,
            ),
        )

    def validate_carrier_account(self, input_str: str) -> dict[str, Any]:
        accounts = self.get_carrier_accounts()
        if not accounts:
            return _validation_result(valid=True, confidence=0.6, value=input_str)
        match = next((a for a in accounts if a.get("id") == input_str), None)
        if match:
            return _validation_result(valid=True, confidence=1.0, value=input_str)
        return _validation_result(
            valid=False,
            confidence=0.0,
            issues=[{"code": "UNKNOWN_CARRIER_ACCOUNT", "message": f"Unknown carrier account: {input_str}"}],
            suggestions=[
                {"id": a.get("id"), "carrier": a.get("carrier"), "description": a.get("description")}
                for a in accounts[:5]
            ],
        )

    def validate_package_type(self, input_str: str) -> dict[str, Any]:
        package_types = self.get_package_types()
        exact = next(
            (p for p in package_types if normalize_candidate(p) == normalize_candidate(input_str)),
            None,
        )
        if exact:
            return _validation_result(valid=True, confidence=1.0, value=exact)
        return _validation_result(
            valid=False,
            confidence=0.0,
            issues=[{"code": "UNKNOWN_PACKAGE_TYPE", "message": f"Unknown package type: {input_str}"}],
            suggestions=fuzzy_suggest(
                input_str,
                [{"code": p, "name": p} for p in package_types],
                threshold=0.72,
            ),
        )

    def validate_country(self, input_str: str) -> dict[str, Any]:
        countries = self.get_countries()
        normalized = normalize_candidate(input_str)
        for country in countries:
            labels = [country.get("code"), country.get("name")]
            if any(normalize_candidate(lb) == normalized for lb in labels if lb):
                return _validation_result(valid=True, confidence=1.0, value=country["code"])
        return _validation_result(
            valid=False,
            confidence=0.0,
            issues=[{"code": "UNKNOWN_COUNTRY", "message": f"Unknown country: {input_str}"}],
            suggestions=fuzzy_suggest(input_str, countries, threshold=0.72),
        )

    def validate_state(self, country_input: str, state_input: str) -> dict[str, Any]:
        country = self.validate_country(country_input)
        if not country["valid"]:
            return country
        states = self.get_states(country["value"])
        if not states:
            return _validation_result(valid=True, confidence=0.6, value=state_input)
        exact = next(
            (s for s in states if normalize_candidate(s) == normalize_candidate(state_input)),
            None,
        )
        if exact:
            return _validation_result(valid=True, confidence=1.0, value=exact)
        return _validation_result(
            valid=False,
            confidence=0.0,
            issues=[{
                "code": "UNKNOWN_STATE",
                "message": f"Unknown state/province for {country['value']}: {state_input}",
            }],
            suggestions=fuzzy_suggest(
                state_input,
                [{"code": s, "name": s} for s in states],
                threshold=0.7,
            ),
        )

    def validate_payment_method(self, input_str: str) -> dict[str, Any]:
        methods = self.get_payment_methods()
        exact = next(
            (m for m in methods if normalize_candidate(m) == normalize_candidate(input_str)),
            None,
        )
        if exact:
            return _validation_result(valid=True, confidence=1.0, value=exact)
        return _validation_result(
            valid=False,
            confidence=0.0,
            issues=[{"code": "UNKNOWN_PAYMENT_METHOD", "message": f"Unknown payment method: {input_str}"}],
            suggestions=fuzzy_suggest(
                input_str,
                [{"code": m, "name": m} for m in methods],
                threshold=0.7,
            ),
        )
