"""
Models that implement units
"""
from django.db import models

from ..publishing.models import Container, ContainerVersion

__all__ = [
    "Unit",
    "UnitVersion",
]


class Unit(Container):
    """
    A Unit is Container, which is a PublishableEntity.
    """
    container = models.OneToOneField(
        Container,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )

    @property
    def versioning(self):
        return self.container.versioning


class UnitVersion(ContainerVersion):
    """
    A UnitVersion is a ContainerVersion, which is a PublishableEntityVersion.
    """
    container_version = models.OneToOneField(
        ContainerVersion,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )
