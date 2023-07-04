""" Tagging app data models """
from typing import List, Type

from django.db import models
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from model_utils.managers import InheritanceManager

from openedx_learning.lib.fields import MultiCollationTextField, case_insensitive_char_field

# Maximum depth allowed for a hierarchical taxonomy's tree of tags.
TAXONOMY_MAX_DEPTH = 3

# Ancestry of a given tag; the Tag.value fields of a given tag and its parents, starting from the root.
# Will contain 0...TAXONOMY_MAX_DEPTH elements.
Lineage = List[str]


class Tag(models.Model):
    """
    Represents a single value in a list or tree of values which can be applied to a particular Open edX object.

    Open edX tags are "name:value" pairs which can be applied to objects like content libraries, units, or people.
    Tag.taxonomy.name provides the "name" and the Tag.value provides the "value".
    (And an ObjectTag links a Tag with an object.)
    """

    id = models.BigAutoField(primary_key=True)
    taxonomy = models.ForeignKey(
        "Taxonomy",
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_("Namespace and rules for using a given set of tags."),
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="children",
        help_text=_(
            "Tag that lives one level up from the current tag, forming a hierarchy."
        ),
    )
    value = case_insensitive_char_field(
        max_length=500,
        help_text=_(
            "Content of a given tag, occupying the 'value' part of the key:value pair."
        ),
    )
    external_id = case_insensitive_char_field(
        max_length=255,
        null=True,
        blank=True,
        help_text=_(
            "Used to link an Open edX Tag with a tag in an externally-defined taxonomy."
        ),
    )

    class Meta:
        indexes = [
            models.Index(fields=["taxonomy", "value"]),
            models.Index(fields=["taxonomy", "external_id"]),
        ]

    def __repr__(self):
        """
        Developer-facing representation of a Tag.
        """
        return str(self)

    def __str__(self):
        """
        User-facing string representation of a Tag.
        """
        return f"<{self.__class__.__name__}> ({self.id}) {self.value}"

    def get_lineage(self) -> Lineage:
        """
        Queries and returns the lineage of the current tag as a list of Tag.value strings.

        The root Tag.value is first, followed by its child.value, and on down to self.value.

        Performance note: may perform as many as TAXONOMY_MAX_DEPTH select queries.
        """
        lineage: Lineage = []
        tag = self
        depth = TAXONOMY_MAX_DEPTH
        while tag and depth > 0:
            lineage.insert(0, tag.value)
            tag = tag.parent
            depth -= 1
        return lineage


class TaxonomyManager(InheritanceManager):
    """
    Base Taxonomy class uses InheritanceManager to help instantiate subclasses during queries.
    """


class Taxonomy(models.Model):
    """
    Represents a namespace and rules for a group of tags.
    """

    objects = TaxonomyManager()

    id = models.BigAutoField(primary_key=True)
    name = case_insensitive_char_field(
        null=False,
        max_length=255,
        db_index=True,
        help_text=_(
            "User-facing label used when applying tags from this taxonomy to Open edX objects."
        ),
    )
    description = MultiCollationTextField(
        null=True,
        blank=True,
        help_text=_(
            "Provides extra information for the user when applying tags from this taxonomy to an object."
        ),
    )
    enabled = models.BooleanField(
        default=True,
        help_text=_("Only enabled taxonomies will be shown to authors."),
    )
    required = models.BooleanField(
        default=False,
        help_text=_(
            "Indicates that one or more tags from this taxonomy must be added to an object."
        ),
    )
    allow_multiple = models.BooleanField(
        default=False,
        help_text=_(
            "Indicates that multiple tags from this taxonomy may be added to an object."
        ),
    )
    allow_free_text = models.BooleanField(
        default=False,
        help_text=_(
            "Indicates that tags in this taxonomy need not be predefined; authors may enter their own tag values."
        ),
    )
    _object_tag_class = models.CharField(
        null=True,
        max_length=255,
        help_text=_(
            "Overrides the default BaseObjectTag subclass associated with this taxonomy."
            "Must be a fully-qualified module and class name.",
        ),
    )

    class Meta:
        verbose_name_plural = "Taxonomies"

    def __repr__(self):
        """
        Developer-facing representation of a Taxonomy.
        """
        return str(self)

    def __str__(self):
        """
        User-facing string representation of a Taxonomy.
        """
        return f"<{self.__class__.__name__}> ({self.id}) {self.name}"

    @property
    def system_defined(self) -> bool:
        """
        Base taxonomies are user-defined, not system-defined.

        System-defined taxonomies cannot be edited by ordinary users.

        Subclasses should override this property as required.
        """
        return False

    @property
    def object_tag_class(self) -> Type:
        """
        Returns the BaseObjectTag subclass associated with this taxonomy.

        Can be overridden by setting this property.
        """
        if self._object_tag_class:
            ObjectTagClass = import_string(self._object_tag_class)
        elif self.allow_free_text:
            ObjectTagClass = OpenObjectTag
        else:
            ObjectTagClass = ClosedObjectTag

        return ObjectTagClass

    @object_tag_class.setter
    def object_tag_class(self, object_tag_class: Type):
        """
        Assigns the given object_tag_class's module path.class to the field.

        Raises ValueError if the given `object_tag_class` is a built-in class; it should be an ObjectTag-like class.
        """
        if object_tag_class.__module__ == "builtins":
            raise ValueError(
                f"object_tag_class {object_tag_class} must be class like ObjectTag"
            )

        # ref: https://stackoverflow.com/a/2020083
        self._object_tag_class = ".".join(
            [object_tag_class.__module__, object_tag_class.__qualname__]
        )

    def get_tags(self) -> List[Tag]:
        """
        Returns a list of all Tags in the current taxonomy, from the root(s) down to TAXONOMY_MAX_DEPTH tags, in tree order.

        Annotates each returned Tag with its ``depth`` in the tree (starting at 0).

        Performance note: may perform as many as TAXONOMY_MAX_DEPTH select queries.
        """
        tags = []
        if self.allow_free_text:
            return tags

        parents = None
        for depth in range(TAXONOMY_MAX_DEPTH):
            filtered_tags = self.tag_set.prefetch_related("parent")
            if parents is None:
                filtered_tags = filtered_tags.filter(parent=None)
            else:
                filtered_tags = filtered_tags.filter(parent__in=parents)
            next_parents = list(
                filtered_tags.annotate(
                    annotated_field=models.Value(
                        depth, output_field=models.IntegerField()
                    )
                )
                .order_by("parent__value", "value", "id")
                .all()
            )
            tags.extend(next_parents)
            parents = next_parents
            if not parents:
                break
        return tags

    def tag_object(
        self, tags: List, object_id: str, object_type: str
    ) -> List["ObjectTag"]:
        """
        Replaces the existing ObjectTag entries for the current taxonomy + object_id with the given list of tags.

        If self.allows_free_text, then the list should be a list of tag values.
        Otherwise, it should be a list of existing Tag IDs.

        Raised ValueError if the proposed tags are invalid for this taxonomy.
        Preserves existing (valid) tags, adds new (valid) tags, and removes omitted (or invalid) tags.
        """

        if not self.allow_multiple and len(tags) > 1:
            raise ValueError(_(f"Taxonomy ({self.id}) only allows one tag per object."))

        if self.required and len(tags) == 0:
            raise ValueError(
                _(f"Taxonomy ({self.id}) requires at least one tag per object.")
            )

        ObjectTagClass = self.object_tag_class
        current_tags = {
            tag.tag_ref: tag
            for tag in self.objecttag_set.filter(
                object_id=object_id, object_type=object_type
            )
        }
        updated_tags = []
        for tag_ref in tags:
            if tag_ref in current_tags:
                object_tag = current_tags.pop(tag_ref)
            else:
                object_tag = ObjectTagClass(
                    taxonomy=self,
                    object_id=object_id,
                    object_type=object_type,
                )

            try:
                object_tag.tag = self.tag_set.get(
                    id=tag_ref,
                )
            except (ValueError, Tag.DoesNotExist):
                # This might be ok, e.g. if self.allow_free_text.
                # We'll validate below before saving.
                object_tag.value = tag_ref

            object_tag.resync()
            if not object_tag.is_valid():
                raise ValueError(
                    _(f"Invalid object tag for taxonomy ({self.id}): {tag_ref}")
                )
            updated_tags.append(object_tag)

        # Save all updated tags at once to avoid partial updates
        for object_tag in updated_tags:
            object_tag.save()

        # ...and delete any omitted existing tags
        for old_tag in current_tags.values():
            old_tag.delete()

        return updated_tags


class ObjectTag(models.Model):
    """
    Represents the association between a tag and an Open edX object.

    Tagging content in Open edX involves linking the object to a particular name:value "tag", where the "name" is the
    tag's label, and the value is the content of the tag itself.

    Tagging objects can be time-consuming for users, and so we guard against the deletion of Taxonomies and Tags by
    providing fields to cache the name:value stored for an object.

    However, sometimes Taxonomy names or Tag values change (e.g if there's a typo, or a policy change about how a label
    is used), and so we still store a link to the original Taxonomy and Tag, so that these changes will take precedence
    over the original name:value used.

    Also, if an ObjectTag is associated with free-text Taxonomy, then the tag's value won't be stored as a standalone
    Tag in the database -- it'll be stored here.
    """

    id = models.BigAutoField(primary_key=True)
    object_id = case_insensitive_char_field(
        max_length=255,
        help_text=_("Identifier for the object being tagged"),
    )
    object_type = case_insensitive_char_field(
        max_length=255,
        help_text=_("Type of object being tagged"),
    )
    _taxonomy = models.ForeignKey(
        Taxonomy,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_(
            "Taxonomy that this object tag belongs to. Used for validating the tag and provides the tag's 'name' if set."
        ),
    )
    tag = models.ForeignKey(
        Tag,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_(
            "Tag associated with this object tag. Provides the tag's 'value' if set."
        ),
    )
    _name = case_insensitive_char_field(
        null=False,
        max_length=255,
        help_text=_(
            "User-facing label used for this tag, stored in case taxonomy is (or becomes) null."
            " If the taxonomy field is set, then taxonomy.name takes precedence over this field."
        ),
    )
    _value = case_insensitive_char_field(
        null=False,
        max_length=500,
        help_text=_(
            "User-facing value used for this tag, stored in case tag is null, e.g if taxonomy is free text, or if it"
            " becomes null (e.g. if the Tag is deleted)."
            " If the tag field is set, then tag.value takes precedence over this field."
        ),
    )

    class Meta:
        indexes = [
            models.Index(fields=["_taxonomy", "_value"]),
        ]

    def __init__(self, *args, **kwargs):
        """
        Initializes the cached taxonomy instance.
        """
        super().__init__(*args, **kwargs)
        self._cached_taxonomy = None

    def __repr__(self):
        """
        Developer-facing representation of an ObjectTag.
        """
        return str(self)

    def __str__(self):
        """
        User-facing string representation of an ObjectTag.
        """
        return f"<{self.__class__.__name__}> {self.object_id} ({self.object_type}): {self.name}={self.value}"

    @property
    def taxonomy(self) -> str:
        """
        Returns this tag's taxonomy object, instantiated as the correct Taxonomy subclass.

        This instance is cached so that subsequent calls to self.taxonomy don't re-fetch the value.

        Returns None if taxonomy_id is not set.
        """
        if not self._taxonomy_id:
            self._cached_taxonomy = None

        elif not self._cached_taxonomy:
            self._cached_taxonomy = (
                Taxonomy.objects.filter(id=self._taxonomy_id)
                .select_subclasses()
                .first()
            )

        return self._cached_taxonomy

    @taxonomy.setter
    def taxonomy(self, taxonomy: Taxonomy):
        """
        Stores to the _taxonomy field.
        """
        self._taxonomy = taxonomy
        self._cached_taxonomy = taxonomy

    def copy(self, object_tag: "ObjectTag") -> "ObjectTag":
        """
        Copy the fields from the given ObjectTag into the current instance.
        """
        self.id = object_tag.id
        self.object_id = object_tag.object_id
        self.object_type = object_tag.object_type
        self._taxonomy_id = object_tag._taxonomy_id
        self.tag_id = object_tag.tag_id
        self._name = object_tag.name
        self._value = object_tag.value
        return self

    @property
    def name(self) -> str:
        """
        Returns this tag's name/label.

        If taxonomy is set, then returns its name.
        Otherwise, returns the cached _name field.
        """
        return self.taxonomy.name if self._taxonomy_id else self._name

    @name.setter
    def name(self, name: str):
        """
        Stores to the _name field.
        """
        self._name = name

    @property
    def value(self) -> str:
        """
        Returns this tag's value.

        If tag is set, then returns its value.
        Otherwise, returns the cached _value field.
        """
        return self.tag.value if self.tag_id else self._value

    @value.setter
    def value(self, value: str):
        """
        Stores to the _value field.
        """
        self._value = value

    @property
    def tag_ref(self) -> str:
        """
        Returns this tag's reference string.

        If tag is set, then returns its id.
        Otherwise, returns the cached _value field.
        """
        return self.tag.id if self.tag_id else self._value

    def get_lineage(self) -> Lineage:
        """
        Returns the lineage of the current tag as a list of value strings.

        If linked to a Tag, returns its lineage.
        Otherwise, returns an array containing its value string.
        """
        return self.tag.get_lineage() if self.tag_id else [self._value]

    def is_valid(self, check_taxonomy=True, check_tag=True, check_object=True) -> bool:
        """
        Returns True if this ObjectTag is valid for the linked taxonomy and/or tag.

        Subclasses must override this method to perform the proper validation checks, e.g. closed vs open taxonomies,
        dynamically generated tag lists or object definitions.

        If `check_taxonomy` is False, then we skip validating the object tag's taxonomy reference.
        If `check_tag` is False, then we skip validating the object tag's tag reference.
        If `check_object` is False, then we skip validating the object ID/type.
        """
        # Must be linked to a taxonomy
        if check_taxonomy and not self._taxonomy_id:
            return False

        # Open taxonomies don't have an associated tag, but we need a value.
        if check_tag and not self.value:
            return False

        # Must have a valid object id/type:
        if check_object and (not self.object_id or not self.object_type):
            return False

        return True

    def resync(self) -> bool:
        """
        Reconciles the stored ObjectTag properties with any changes made to its associated taxonomy or tag.

        This method is useful to propagate changes to a Taxonomy name or Tag value.

        It's also useful for a set of ObjectTags are imported from an external source prior to when a Taxonomy exists to
        validate or store its available Tags.

        Subclasses must override this method to perform any additional syncing for the particular type of object tag.

        Returns True if anything was changed, False otherwise.
        """
        changed = False

        # Locate a taxonomy matching _name
        if not self._taxonomy_id:
            for taxonomy in Taxonomy.objects.filter(
                name=self.name, enabled=True
            ).select_subclasses():
                # Make sure this taxonomy will accept object tags like this.
                object_tag = taxonomy.object_tag_class(
                    id=self.id,
                    taxonomy=taxonomy,
                    _name=self._name,
                    _value=self._value,
                )
                if object_tag.is_valid(check_tag=False, check_object=False):
                    self.taxonomy = taxonomy
                    changed = True
                    break
                # If not, try the next one

        # Sync the stored _name with the taxonomy.name
        if self._taxonomy_id and self._name != self.taxonomy.name:
            self.name = self.taxonomy.name
            changed = True

        # Closed taxonomies require a tag matching _value
        if self.taxonomy and not self.tag_id:
            tag = self.taxonomy.tag_set.filter(value=self.value).first()
            if tag:
                self.tag = tag
                changed = True

        # Sync the stored _value with the tag.name
        elif self.tag and self._value != self.tag.value:
            self.value = self.tag.value
            changed = True

        return changed


class SystemTaxonomy(Taxonomy):
    """
    System-defined taxonomies are not editable by normal users; they're defined by fixtures/migrations, and may have
    dynamically-determined Tags and ObjectTags.
    """

    @property
    def system_defined(self) -> bool:
        """
        This is a system-defined taxonomy.
        """
        return True


class OpenObjectTag(ObjectTag):
    """
    Free-text object tag.

    Only needs a taxonomy and a value to be valid.
    """

    class Meta:
        proxy = True


class ClosedObjectTag(OpenObjectTag):
    """
    Object tags linked to a closed taxonomy, where all the tag options are known.
    """

    class Meta:
        proxy = True

    def is_valid(self, check_taxonomy=True, check_tag=True, check_object=True) -> bool:
        """
        Returns True if this ObjectTag is linked to a known tag, and it's parent classes are valid.

        If `check_taxonomy` is False, then we skip validating the object tag's taxonomy reference.
        If `check_tag` is False, then we skip validating the object tag's tag reference.
        If `check_object` is False, then we skip validating the object ID/type.
        """
        # Must be linked to a Tag
        if check_tag and not self.tag_id:
            return False

        return super().is_valid(
            check_taxonomy=check_taxonomy,
            check_tag=check_tag,
            check_object=check_object,
        )
