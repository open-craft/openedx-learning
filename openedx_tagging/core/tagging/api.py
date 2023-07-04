""""
Tagging API

Anyone using the openedx_tagging app should use these APIs instead of creating
or modifying the models directly, since there might be other related model
changes that you may not know about.

No permissions/rules are enforced by these methods -- these must be enforced in the views.

Please look at the models.py file for more information about the kinds of data
are stored in this app.
"""
from typing import Generator, List, Type, Union

from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from .models import ObjectTag, Tag, Taxonomy


def create_taxonomy(
    name: str,
    description: str = None,
    enabled=True,
    required=False,
    allow_multiple=False,
    allow_free_text=False,
    object_tag_class: Type = None,
) -> Taxonomy:
    """
    Creates, saves, and returns a new Taxonomy with the given attributes.
    """
    taxonomy = Taxonomy(
        name=name,
        description=description,
        enabled=enabled,
        required=required,
        allow_multiple=allow_multiple,
        allow_free_text=allow_free_text,
    )
    if object_tag_class:
        taxonomy.object_tag_class = object_tag_class
    taxonomy.save()
    return taxonomy


def get_taxonomies(enabled=True) -> QuerySet:
    """
    Returns a queryset containing the enabled taxonomies, sorted by name.
    If you want the disabled taxonomies, pass enabled=False.
    If you want all taxonomies (both enabled and disabled), pass enabled=None.
    """
    queryset = Taxonomy.objects.order_by("name", "id").select_subclasses()
    if enabled is None:
        return queryset.all()
    return queryset.filter(enabled=enabled)


def get_taxonomy(id: int) -> Union[Taxonomy, None]:
    """
    Returns a Taxonomy of the appropriate subclass which has the given ID.
    """
    return Taxonomy.objects.filter(id=id).select_subclasses().first()


def get_tags(taxonomy: Taxonomy) -> List[Tag]:
    """
    Returns a list of predefined tags for the given taxonomy.

    Note that if the taxonomy allows free-text tags, then the returned list will be empty.
    """
    return taxonomy.get_tags()


def resync_object_tags(object_tags: QuerySet = None) -> int:
    """
    Reconciles ObjectTag entries with any changes made to their associated taxonomies and tags.

    By default, we iterate over all ObjectTags. Pass a filtered ObjectTags queryset to limit which tags are resynced.
    """
    if not object_tags:
        object_tags = ObjectTag.objects.all()

    num_changed = 0
    for object_tag in object_tags:
        changed = object_tag.resync()
        if changed:
            object_tag.save()
            num_changed += 1
    return num_changed


def get_object_tags(
    object_id: str, object_type: str = None, taxonomy: Taxonomy = None, valid_only=True
) -> Generator[ObjectTag, None, None]:
    """
    Generates a list of object tags for a given object.

    Pass taxonomy to limit the returned object_tags to a specific taxonomy.

    Pass valid_only=False when displaying tags to content authors, so they can see invalid tags too.
    Invalid tags will (probably) be hidden from learners.
    """
    tags = ObjectTag.objects.filter(
        object_id=object_id,
    ).order_by("id")
    if object_type:
        tags = tags.filter(object_type=object_type)
    if taxonomy:
        tags = tags.filter(_taxonomy=taxonomy)

    for tag in tags:
        # We can only validate tags with taxonomies, because we need the object_tag_class
        if valid_only:
            if tag._taxonomy_id:
                object_tag = tag.taxonomy.object_tag_class().copy(tag)
                if object_tag.is_valid():
                    yield object_tag
        else:
            yield tag


def tag_object(
    taxonomy: Taxonomy, tags: List, object_id: str, object_type: str
) -> List[ObjectTag]:
    """
    Replaces the existing ObjectTag entries for the given taxonomy + object_id with the given list of tags.

    If taxonomy.allows_free_text, then the list should be a list of tag values.
    Otherwise, it should be a list of existing Tag IDs.

    Raised ValueError if the proposed tags are invalid for this taxonomy.
    Preserves existing (valid) tags, adds new (valid) tags, and removes omitted (or invalid) tags.
    """

    return taxonomy.tag_object(tags, object_id, object_type)
