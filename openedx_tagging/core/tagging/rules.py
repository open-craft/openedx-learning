"""Django rules-based permissions for tagging"""

import rules
from django.contrib.auth import get_user_model

from .models import ObjectTag, Tag, Taxonomy

User = get_user_model()


# Global staff are taxonomy admins.
# (Superusers can already do anything)
is_taxonomy_admin = rules.is_staff


@rules.predicate
def can_view_taxonomy(user: User, taxonomy: Taxonomy = None) -> bool:
    """
    Anyone can view an enabled taxonomy or list all taxonomies,
    but only taxonomy admins can view a disabled taxonomy.
    """
    return not taxonomy or taxonomy.cast().enabled or is_taxonomy_admin(user)


@rules.predicate
def can_change_taxonomy(user: User, taxonomy: Taxonomy = None) -> bool:
    """
    Even taxonomy admins cannot change system taxonomies.
    """
    return is_taxonomy_admin(user) and (
        not taxonomy or (taxonomy and not taxonomy.cast().system_defined)
    )


@rules.predicate
def can_change_tag(user: User, tag: Tag = None) -> bool:
    """
    Even taxonomy admins cannot add tags to system taxonomies (their tags are system-defined), or free-text taxonomies
    (these don't have predefined tags).
    """
    taxonomy = tag.taxonomy.cast() if (tag and tag.taxonomy_id) else None
    return is_taxonomy_admin(user) and (
        not tag
        or not taxonomy
        or (taxonomy and not taxonomy.allow_free_text and not taxonomy.system_defined)
    )


@rules.predicate
def can_change_object_tag(user: User, taxonomy: Taxonomy = None) -> bool:
    """
    Everyone can potentially create/edit object tags (taxonomy=None). The object permission must be checked
    to determine if the user can create/edit a object_tag for a specific taxonomy.

    Everyone can create or modify object tags on enabled taxonomies.
    Only taxonomy admins can create or modify object tags on disabled taxonomies.
    """
    if not taxonomy:
        return True

    taxonomy = taxonomy.cast()

    return taxonomy.enabled or is_taxonomy_admin(user)

# Taxonomy
rules.add_perm("oel_tagging.add_taxonomy", can_change_taxonomy)
rules.add_perm("oel_tagging.change_taxonomy", can_change_taxonomy)
rules.add_perm("oel_tagging.delete_taxonomy", can_change_taxonomy)
rules.add_perm("oel_tagging.view_taxonomy", can_view_taxonomy)

# Tag
rules.add_perm("oel_tagging.add_tag", can_change_tag)
rules.add_perm("oel_tagging.change_tag", can_change_tag)
rules.add_perm("oel_tagging.delete_tag", is_taxonomy_admin)
rules.add_perm("oel_tagging.view_tag", rules.always_allow)

# ObjectTag
rules.add_perm("oel_tagging.add_objecttag", can_change_object_tag)
rules.add_perm("oel_tagging.change_objecttag", can_change_object_tag)
rules.add_perm("oel_tagging.delete_objecttag", is_taxonomy_admin)
rules.add_perm("oel_tagging.view_objecttag", rules.always_allow)
