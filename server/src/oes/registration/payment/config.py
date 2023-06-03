from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable, Optional

from importlib_metadata import entry_points
from loguru import logger
from oes.registration.models.config import PaymentConfig
from oes.registration.payment.base import PaymentService

PaymentServiceFactory = Callable[[dict[str, Any]], Optional[PaymentService]]
"""Factory function to configure and return a :class:`PaymentService`.

May return None if the service is not available.
"""

GROUP = "oes.registration.payment_services"


class PaymentServices:
    """Class for looking up/creating :class:`PaymentService` classes."""

    services: dict[str, PaymentService]
    entry_points: dict[str, Any]

    def __init__(self):
        self.services = {}
        self.entry_points = {}

    def get_service_exists(self, id: str) -> bool:
        """Get whether a service ID is installed."""
        return id in self.entry_points

    def load_service(self, id: str, config: dict[str, Any]):
        """Load a :class:`PaymentService`.

        Args:
            id: The payment service ID.
            config: The payment service configuration data.
        """
        ep = self.entry_points[id]
        factory: PaymentServiceFactory = ep.load()
        service = factory(config)
        if service is not None:
            self.services[id] = service
            logger.info(f"Loaded payment service {id}")

    def get_available_services(self) -> Iterable[str]:
        """Get an iterable of available service IDs."""
        return self.services.keys()

    def get_service(
        self,
        id: str,
    ) -> Optional[PaymentService]:
        """Get a :class:`PaymentService`.

        Args:
            id: The service ID.

        Returns:
            The service, or None if not available.
        """

        return self.services.get(id)


def load_services(config: PaymentConfig) -> PaymentServices:
    """Load :class:`PaymentService` classes."""
    services = PaymentServices()

    # TODO: get explicit enable/disable settings from somewhere?

    eps = entry_points(group=GROUP)
    for ep in eps:
        services.entry_points[ep.name] = ep

    for service_id, service_config in config.services.items():
        if not services.get_service_exists(service_id):
            logger.info(f"Payment service {service_id!r} not available")
            continue

        try:
            services.load_service(service_id, service_config)
        except Exception as e:
            logger.warning(f"Payment service {service_id} configuration failed: {e}")

    return services
