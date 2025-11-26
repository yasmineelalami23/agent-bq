"""Utility modules."""

from .observability import configure_otel_resource, setup_opentelemetry

__all__ = [
    "configure_otel_resource",
    "setup_opentelemetry",
]
