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

    @property
    def unit(self):
        """ Convenience accessor to the Unit this version is associated with """
        return self.container_version.container.unit  # pylint: disable=no-member

    # Note: the 'publishable_entity_version' field is inherited and will appear on this model, but does not exist
    # in the underlying database table. It only exists in the ContainerVersion table.
    # You can verify this by running 'python manage.py sqlmigrate oel_units 0001_initial'
