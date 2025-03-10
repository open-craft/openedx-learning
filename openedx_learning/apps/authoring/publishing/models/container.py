"""
Container and ContainerVersion models
"""
from typing import ClassVar, Self, TypeVar

from django.core.exceptions import ValidationError
from django.db import models

from openedx_learning.lib.fields import case_sensitive_char_field
from openedx_learning.lib.managers import WithRelationsManager

from ..model_mixins.publishable_entity import PublishableEntityMixin, PublishableEntityVersionMixin
from .entity_list import EntityList

M = TypeVar('M', bound="Container")


class ContainerManager(WithRelationsManager[M]):
    """
    A custom manager used for Container and its subclasses.
    """
    def __init__(self):
        """
        Initialize the manager for Container / a Container subclass
        """
        super().__init__(
            # Select these related entities by default:
            "publishable_entity",
            "publishable_entity__published",
            "publishable_entity__draft",
        )

    def get_queryset(self) -> models.QuerySet:
        """
        Apply filter() and select_related() to all querysets.
        """
        qs = super().get_queryset()
        if self.model.CONTAINER_TYPE:
            qs = qs.filter(container_type=self.model.CONTAINER_TYPE)
        return qs

    def create(self, **kwargs) -> M:
        """
        Apply the values from our filter when creating new instances.
        """
        if self.model.CONTAINER_TYPE:
            # Don't allow creating via a subclass, like Unit.objects.create().
            # Instead use create_container() which calls Container.objects.create(..., container_type=...)
            raise ValidationError("Container instances should only be created via APIs like create_container()")
        return super().create(**kwargs)


class Container(PublishableEntityMixin):
    """
    A Container is a type of PublishableEntity that holds other
    PublishableEntities. For example, a "Unit" Container might hold several
    Components.

    For now, all containers have a static "entity list" that defines which
    containers/components/enities they hold. As we complete the Containers API,
    we will also add support for dynamic containers which may contain different
    entities for different learners or at different times.

    NOTE: We're going to want to eventually have some association between the
    PublishLog and Containers that were affected in a publish because their
    child elements were published.
    """
    # Subclasses (django proxy classes) should override this
    CONTAINER_TYPE = ""

    objects: ClassVar[ContainerManager[Self]] = ContainerManager()  # type: ignore[assignment]

    container_type = case_sensitive_char_field(max_length=500)

    def save(self, *args, **kwargs):
        if not self.container_type:
            raise ValidationError("Container instances should only be created via APIs like create_container()")
        return super().save(*args, **kwargs)

    def clean(self):
        """
        Validate this container subclass
        """
        if self.container_type and self.CONTAINER_TYPE:
            if self.container_type != self.CONTAINER_TYPE:
                raise ValidationError("container type field mismatch with model.")
        super().clean()

    @classmethod
    def cast_from(cls, instance: "Container") -> Self:
        """
        Create a new copy of a Container object, with a different subclass
        """
        assert instance.container_type == cls.CONTAINER_TYPE
        new_instance = cls(
            pk=instance.pk,
            container_type=instance.container_type,
        )
        # Copy Django's internal cache of related objects
        new_instance._state.fields_cache.update(instance._state.fields_cache)  # pylint: disable=protected-access
        return new_instance


class ContainerVersion(PublishableEntityVersionMixin):
    """
    A version of a Container.

    By convention, we would only want to create new versions when the Container
    itself changes, and not when the Container's child elements change. For
    example:

    * Something was added to the Container.
    * We re-ordered the rows in the container.
    * Something was removed to the container.
    * The Container's metadata changed, e.g. the title.
    * We pin to different versions of the Container.

    The last looks a bit odd, but it's because *how we've defined the Unit* has
    changed if we decide to explicitly pin a set of versions for the children,
    and then later change our minds and move to a different set. It also just
    makes things easier to reason about if we say that entity_list never
    changes for a given ContainerVersion.
    """

    container = models.ForeignKey(
        Container,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    # The list of entities (frozen and/or unfrozen) in this container
    entity_list = models.ForeignKey(
        EntityList,
        on_delete=models.RESTRICT,
        null=False,
        related_name="container_versions",
    )

    @classmethod
    def cast_from(cls, instance: "ContainerVersion") -> Self:
        """
        Create a new copy of a Container object, with a different subclass
        """
        new_instance = cls(
            pk=instance.pk,
            container_id=instance.container_id,
            entity_list_id=instance.entity_list_id,
        )
        # Copy Django's internal cache of related objects
        new_instance._state.fields_cache.update(instance._state.fields_cache)  # pylint: disable=protected-access
        return new_instance
