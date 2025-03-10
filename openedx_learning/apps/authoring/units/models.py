"""
Models that implement units
"""

from ..publishing.models import Container, ContainerVersion

__all__ = [
    "Unit",
    "UnitVersion",
]


class Unit(Container):
    """
    A Unit is Container, which is a PublishableEntity.
    """
    CONTAINER_TYPE = "unit"

    class Meta:
        proxy = True


class UnitVersion(ContainerVersion):
    """
    A UnitVersion is a ContainerVersion, which is a PublishableEntityVersion.
    """

    @property
    def unit(self):
        return Unit.objects.get(pk=self.container_id)

    class Meta:
        proxy = True
