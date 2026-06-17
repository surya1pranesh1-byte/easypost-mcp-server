from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.clients.easypost_client import EasyPostClient
from app.resources.resource_manager import ResourceManager
from app.services.address_service import AddressService
from app.services.batch_service import BatchService
from app.services.confirmation_service import ConfirmationService
from app.services.elicitation_service import ElicitationService
from app.services.idempotency_store import IdempotencyStore
from app.services.order_service import OrderService
from app.services.pickup_service import PickupService
from app.services.return_service import ReturnService
from app.services.shipment_service import ShipmentService
from app.services.tracking_service import TrackingService
from app.services.workflow_state_store import WorkflowStateStore

if TYPE_CHECKING:
    from app.config.settings import AppConfig


@dataclass
class Services:
    resources: ResourceManager
    confirmations: ConfirmationService
    elicitation: ElicitationService
    idempotency: IdempotencyStore
    workflow_state: WorkflowStateStore
    shipments: ShipmentService
    addresses: AddressService
    tracking: TrackingService
    returns: ReturnService
    pickups: PickupService
    batches: BatchService
    orders: OrderService


def create_services(config: "AppConfig") -> Services:
    easypost_client = EasyPostClient(config)
    resources = ResourceManager(easypost_client)
    confirmations = ConfirmationService()
    elicitation = ElicitationService()
    idempotency = IdempotencyStore()
    workflow_state = WorkflowStateStore()

    return Services(
        resources=resources,
        confirmations=confirmations,
        elicitation=elicitation,
        idempotency=idempotency,
        workflow_state=workflow_state,
        shipments=ShipmentService(easypost_client, confirmations=confirmations, elicitation=elicitation, idempotency=idempotency),
        addresses=AddressService(easypost_client, confirmations=confirmations),
        tracking=TrackingService(easypost_client),
        returns=ReturnService(easypost_client, confirmations=confirmations, elicitation=elicitation),
        pickups=PickupService(easypost_client, confirmations=confirmations, idempotency=idempotency),
        batches=BatchService(easypost_client, confirmations=confirmations),
        orders=OrderService(easypost_client),
    )
