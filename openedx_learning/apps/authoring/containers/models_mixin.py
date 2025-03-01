"""
Mixins for models that implement containers
"""
from __future__ import annotations

from typing import ClassVar, Self

from django.db import models

from openedx_learning.apps.authoring.containers.models import Container, ContainerVersion
from openedx_learning.lib.managers import WithRelationsManager

__all__ = [
    "ContainerMixin",
    "ContainerVersionMixin",
]


class ContainerMixin(models.Model):
    """
    Convenience mixin to link your models against Container.

    Please see docstring for Container for more details.
    """

    # select these related entities by default for all queries
    objects: ClassVar[WithRelationsManager[Self]] = WithRelationsManager(  # type: ignore[assignment]
        "container",
        "container__publishable_entity",
        "container__publishable_entity__published",
        "container__publishable_entity__draft",
    )

    container = models.OneToOneField(
        Container,
        on_delete=models.CASCADE,
    )

    @property
    def uuid(self):
        return self.container.uuid

    @property
    def created(self):
        return self.container.created

    class Meta:
        abstract = True


class ContainerVersionMixin(models.Model):
    """
    Convenience mixin to link your models against ContainerVersion.

    Please see docstring for ContainerVersion for more details.
    """

    # select these related entities by default for all queries
    objects: ClassVar[WithRelationsManager[Self]] = WithRelationsManager(  # type: ignore[assignment]
        "container_version",
        "container_version__publishable_entity_version",
    )

    container_version = models.OneToOneField(
        ContainerVersion,
        on_delete=models.CASCADE,
    )

    @property
    def uuid(self):
        return self.container_version.uuid

    @property
    def title(self):
        return self.container_version.title

    @property
    def created(self):
        return self.container_version.created

    @property
    def version_num(self):
        return self.container_version.version_num

    class Meta:
        abstract = True
