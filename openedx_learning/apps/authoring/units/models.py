"""
Models that implement units
"""

from ..containers.models_mixin import ContainerMixin, ContainerVersionMixin

__all__ = [
    "Unit",
    "UnitVersion",
]


class Unit(ContainerMixin):
    """
    A Unit is Container, which is a PublishableEntity.

    The only purpose of this table at the moment is to distinguish units from
    other container types at the database level, and to provide a target for
    foreign keys that need to apply only to units (if any?).
    """


class UnitVersion(ContainerVersionMixin):
    """
    A UnitVersion has a ContainerVersion, which is a PublishableEntityVersion.
    """

    # Not sure what other metadata goes here, but we want to try to separate things
    # like scheduling information and such into different models.

    @property
    def unit(self):
        return self.container_version.container.unit  # pylint: disable=no-member
