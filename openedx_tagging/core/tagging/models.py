""" Tagging app data models """
import logging
from typing import Any, List, Type, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from openedx_learning.lib.fields import MultiCollationTextField, case_insensitive_char_field

log = logging.getLogger(__name__)


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
        on_delete=models.CASCADE,
        help_text=_("Namespace and rules for using a given set of tags."),
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        default=None,
        on_delete=models.CASCADE,
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


class Taxonomy(models.Model):
    """
    Represents a namespace and rules for a group of tags.
    """

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
    system_defined = models.BooleanField(
        default=False,
        editable=False,
        help_text=_(
            "Indicates that tags and metadata for this taxonomy are maintained by the system;"
            " taxonomy admins will not be permitted to modify them.",
        ),
    )
    visible_to_authors = models.BooleanField(
        default=True,
        editable=False,
        help_text=_(
            "Indicates whether this taxonomy should be visible to object authors."
        ),
    )
    _taxonomy_class = models.CharField(
        null=True,
        max_length=255,
        help_text=_(
            "Taxonomy subclass used to instantiate this instance; must be a fully-qualified module and class name."
            " If the module/class cannot be imported, an error is logged and the base Taxonomy class is used instead."
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
    def taxonomy_class(self) -> Type:
        """
        Returns the Taxonomy subclass associated with this instance, or None if none supplied.

        May raise ImportError if a custom taxonomy_class cannot be imported.
        """
        if self._taxonomy_class:
            return import_string(self._taxonomy_class)
        return None

    @taxonomy_class.setter
    def taxonomy_class(self, taxonomy_class: Union[Type, None]):
        """
        Assigns the given taxonomy_class's module path.class to the field.

        Must be a subclass of Taxonomy, or raises a ValueError.
        """
        if taxonomy_class:
            if not issubclass(taxonomy_class, Taxonomy):
                raise ValueError(
                    f"Unable to assign taxonomy_class for {self}: {taxonomy_class} must be a subclass of Taxonomy"
                )

            # ref: https://stackoverflow.com/a/2020083
            self._taxonomy_class = ".".join(
                [taxonomy_class.__module__, taxonomy_class.__qualname__]
            )
        else:
            self._taxonomy_class = None

    def cast(self):
        """
        Returns the current Taxonomy instance cast into its taxonomy_class.

        If no taxonomy_class is set, or if we're unable to import it, then just returns self.
        """
        try:
            TaxonomyClass = self.taxonomy_class
            if TaxonomyClass and not isinstance(self, TaxonomyClass):
                return TaxonomyClass().copy(self)
        except ImportError:
            # Log error and continue
            log.exception(
                f"Unable to import taxonomy_class for {self}: {self._taxonomy_class}"
            )

        return self

    def copy(self, taxonomy: "Taxonomy") -> "Taxonomy":
        """
        Copy the fields from the given Taxonomy into the current instance.
        """
        self.id = taxonomy.id
        self.name = taxonomy.name
        self.description = taxonomy.description
        self.enabled = taxonomy.enabled
        self.required = taxonomy.required
        self.allow_multiple = taxonomy.allow_multiple
        self.allow_free_text = taxonomy.allow_free_text
        self.system_defined = taxonomy.system_defined
        self.visible_to_authors = taxonomy.visible_to_authors
        self._taxonomy_class = taxonomy._taxonomy_class
        return self

    def _get_tags_query_set(self) -> models.QuerySet:
        """
        Base query set for used on `get_tags()`
        """
        return self.tag_set

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
            filtered_tags = self._get_tags_query_set().prefetch_related("parent")
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

    def validate_object_tag(
        self,
        object_tag: "ObjectTag",
        check_taxonomy=True,
        check_tag=True,
        check_object=True,
    ) -> bool:
        """
        Returns True if the given object tag is valid for the current Taxonomy.

        Subclasses should override the internal _validate* methods to perform their own validation checks, e.g. against
        dynamically generated tag lists.

        If `check_taxonomy` is False, then we skip validating the object tag's taxonomy reference.
        If `check_tag` is False, then we skip validating the object tag's tag reference.
        If `check_object` is False, then we skip validating the object ID/type.
        """
        if check_taxonomy and not self._check_taxonomy(object_tag):
            return False

        if check_tag and not self._check_tag(object_tag):
            return False

        if check_object and not self._check_object(object_tag):
            return False

        return True

    def _check_taxonomy(
        self,
        object_tag: "ObjectTag",
    ) -> bool:
        """
        Returns True if the given object tag is valid for the current Taxonomy.

        Subclasses can override this method to perform their own taxonomy validation checks.
        """
        # Must be linked to this taxonomy
        return object_tag.taxonomy_id and object_tag.taxonomy_id == self.id

    def _check_tag(
        self,
        object_tag: "ObjectTag",
    ) -> bool:
        """
        Returns True if the given object tag's value is valid for the current Taxonomy.

        Subclasses can override this method to perform their own taxonomy validation checks.
        """
        # Open taxonomies only need a value.
        if self.allow_free_text:
            return bool(object_tag.value)

        # Closed taxonomies need an associated tag in this taxonomy
        return object_tag.tag_id and object_tag.tag.taxonomy_id == self.id

    def _check_object(
        self,
        object_tag: "ObjectTag",
    ) -> bool:
        """
        Returns True if the given object tag's object is valid for the current Taxonomy.

        Subclasses can override this method to perform their own taxonomy validation checks.
        """
        return bool(object_tag.object_id)

    def _set_tag(
        self,
        tag_ref,
        object_tag: "ObjectTag",
    ) -> "ObjectTag":
        """
        Set a tag on `object_tag` and run a resync

        Subclasses can override this method to perform their own set tag process.
        """
        try:
            object_tag.tag = self.tag_set.get(
                id=tag_ref,
            )
        except (ValueError, Tag.DoesNotExist):
            # This might be ok, e.g. if self.allow_free_text.
            # We'll validate below before saving.
            object_tag.value = tag_ref

        object_tag.resync()
        return object_tag

    def tag_object(
        self,
        tags: List,
        object_id: str,
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

        current_tags = {
            tag.tag_ref: tag
            for tag in ObjectTag.objects.filter(
                taxonomy=self,
                object_id=object_id,
            )
        }
        updated_tags = []
        for tag_ref in tags:
            if tag_ref in current_tags:
                object_tag = current_tags.pop(tag_ref)
            else:
                object_tag = ObjectTag(
                    taxonomy=self,
                    object_id=object_id,
                )

            object_tag = self._set_tag(tag_ref, object_tag)

            if not object_tag or not self.validate_object_tag(object_tag):
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
        editable=False,
        help_text=_("Identifier for the object being tagged"),
    )
    taxonomy = models.ForeignKey(
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
            models.Index(fields=["taxonomy", "_value"]),
        ]

    def __repr__(self):
        """
        Developer-facing representation of an ObjectTag.
        """
        return str(self)

    def __str__(self):
        """
        User-facing string representation of an ObjectTag.
        """
        return f"<{self.__class__.__name__}> {self.object_id}: {self.name}={self.value}"

    @property
    def name(self) -> str:
        """
        Returns this tag's name/label.

        If taxonomy is set, then returns its name.
        Otherwise, returns the cached _name field.
        """
        return self.taxonomy.name if self.taxonomy_id else self._name

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

    def is_valid(self) -> bool:
        """
        Returns True if this ObjectTag represents a valid taxonomy tag.

        A valid ObjectTag must be linked to a Taxonomy, and be a valid tag in that taxonomy.
        """
        return self.taxonomy_id and self.taxonomy.validate_object_tag(self)

    def get_lineage(self) -> Lineage:
        """
        Returns the lineage of the current tag as a list of value strings.

        If linked to a Tag, returns its lineage.
        Otherwise, returns an array containing its value string.
        """
        return self.tag.get_lineage() if self.tag_id else [self._value]

    def resync(self) -> bool:
        """
        Reconciles the stored ObjectTag properties with any changes made to its associated taxonomy or tag.

        This method is useful to propagate changes to a Taxonomy name or Tag value.

        It's also useful for a set of ObjectTags are imported from an external source prior to when a Taxonomy exists to
        validate or store its available Tags.

        Returns True if anything was changed, False otherwise.
        """
        changed = False

        # Locate an enabled taxonomy matching _name, and maybe a tag matching _value
        if not self.taxonomy_id:
            # Use the linked tag's taxonomy if there is one.
            if self.tag_id:
                self.taxonomy_id = self.tag.taxonomy_id
                changed = True
            else:
                for taxonomy in Taxonomy.objects.filter(
                    name=self.name, enabled=True
                ).order_by("allow_free_text", "id"):
                    # Cast to the subclass to preserve custom validation
                    taxonomy = taxonomy.cast()

                    # Closed taxonomies require a tag matching _value,
                    # and we'd rather match a closed taxonomy than an open one.
                    # So see if there's a matching tag available in this taxonomy.
                    tag = taxonomy.tag_set.filter(value=self.value).first()

                    # Make sure this taxonomy will accept object tags like this.
                    self.taxonomy = taxonomy
                    self.tag = tag
                    if taxonomy.validate_object_tag(self):
                        changed = True
                        break
                    # If not, undo those changes and try the next one
                    else:
                        self.taxonomy = None
                        self.tag = None

        # Sync the stored _name with the taxonomy.name
        if self.taxonomy_id and self._name != self.taxonomy.name:
            self.name = self.taxonomy.name
            changed = True

        # Closed taxonomies require a tag matching _value
        if self.taxonomy and not self.taxonomy.allow_free_text and not self.tag_id:
            tag = self.taxonomy.tag_set.filter(value=self.value).first()
            if tag:
                self.tag = tag
                changed = True

        # Sync the stored _value with the tag.name
        elif self.tag and self._value != self.tag.value:
            self.value = self.tag.value
            changed = True

        return changed

    @classmethod
    def cast(cls, object_tag: "ObjectTag") -> "ObjectTag":
        """
        Returns a cls instance with the same properties as the given ObjectTag.
        """
        return cls().copy(object_tag)

    def copy(self, object_tag: "ObjectTag") -> "ObjectTag":
        """
        Copy the fields from the given ObjectTag into the current instance.
        """
        self.id = object_tag.id
        self.tag = object_tag.tag
        self.taxonomy = object_tag.taxonomy
        self.object_id = object_tag.object_id
        self._value = object_tag._value
        self._name = object_tag._name
        return self


class SystemDefinedTaxonomy(Taxonomy):
    class Meta:
        proxy = True

    def _check_taxonomy(self, object_tag: ObjectTag) -> bool:
        """
        Returns True if this is a system defined taxonomy
        """
        return super()._check_taxonomy(object_tag) and self.system_defined


class ModelSystemDefinedTaxonomy(SystemDefinedTaxonomy):
    """
    Model based system taxonomy abstract class.

    This type of taxonomies has an associated Django model in `tag_class_model()`.
    Are designed to create a Tag when an ObjectTags with a new Tag.
    The Tags are representations of the instances of the associated model.

    On Tag.external_id stores an identifier from the instance (`pk` as default)
    and on Tag.value stores an human readable representation of the instance
    (e.g. `username`).
    The subclasses can override this behavior, to choose the right field.

    When an ObjectTag is created with an existing Tag,
    the Tag is re-synchronized with its instance.
    """

    class Meta:
        proxy = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Checks if the `tag_class_model` is correct
        """
        assert issubclass(self.tag_class_model, models.Model)
        super().__init__(*args, **kwargs)

    @property
    def tag_class_model(self) -> Type:
        """
        Subclasses must implement this method to return the Django.model
        class referenced by these object tags.
        """
        raise NotImplementedError

    def _check_instance(self, object_tag: ObjectTag) -> bool:
        """
        Returns True if the instance exists

        Subclasses can override this method to perform their own instance validation checks.
        """
        intance_id = object_tag.tag.external_id
        return self.tag_class_model.objects.filter(pk=intance_id).exists()

    def _check_tag(self, object_tag: ObjectTag) -> bool:
        """
        Returns True if pass the instance validation checks
        """
        return super()._check_tag(object_tag) and self._check_instance(object_tag)

    def _get_external_id_from_instance(self, instance) -> str:
        """
        Returns the tag external id from the instance

        Subclasses can override this method to get the external id from their own models.
        """
        return str(instance.pk)

    def _get_value_from_instance(self, instance) -> str:
        """
        Returns the tag value from the instance

        Subclasses can override this method to get the value from their own models.
        """
        return str(instance.pk)

    def _get_instance(self, pk):
        """
        Gets the instance from `pk`
        """
        try:
            return self.tag_class_model.objects.get(pk=pk)
        except self.tag_class_model.DoesNotExist:
            return None

    def _resync_tag(self, tag: Tag) -> Tag:
        """
        Resync the tag value with the value from the instance
        """
        instance = self._get_instance(tag.external_id)
        if instance:
            value = self._get_value_from_instance(instance)
            if tag.value != value:
                tag.value = value
                tag.save()
        return tag

    def _set_tag(self, tag_ref, object_tag: ObjectTag) -> ObjectTag:
        """
        Set or create the respective Tag on `object_tag`

        This function is used on `tag_object`.
        For this to work it is necessary that `tag_ref`
        is always the `pk` of the model to which you want
        to associate it.
        """
        try:
            tag = self.tag_set.get(
                external_id=tag_ref,
            )
            # Run a resync of the tag
            tag = self._resync_tag(tag)
            object_tag.tag = tag
        except (ValueError, Tag.DoesNotExist):
            # Creates a new tag with the instance
            instance = self._get_instance(tag_ref)
            if not instance:
                return None
            new_tag = Tag(
                taxonomy=self,
                value=self._get_value_from_instance(instance),
                external_id=self._get_external_id_from_instance(instance),
            )
            new_tag.save()
            object_tag.tag = new_tag

        return object_tag


class UserSystemDefinedTaxonomy(ModelSystemDefinedTaxonomy):
    """
    User based system taxonomy class.
    """

    class Meta:
        proxy = True

    @property
    def tag_class_model(self) -> Type:
        """
        Associate the user model
        """
        return get_user_model()

    def _get_value_from_instance(self, instance) -> str:
        """
        Returns the username as tag value
        """
        return instance.get_username()


class LanguageTaxonomy(SystemDefinedTaxonomy):
    """
    Language System-defined taxonomy

    The tags are filtered and validated taking into account the
    languages available in Django LANGUAGES settings var
    """

    class Meta:
        proxy = True

    def _get_tags_query_set(self) -> models.QuerySet:
        """
        Returns a query set of available languages tags.
        """
        available_langs = self._get_available_languages()
        return self.tag_set.filter(external_id__in=available_langs)

    def _get_available_languages(cls) -> List[str]:
        """
        Get available languages from Django LANGUAGE.
        """
        langs = set()
        for django_lang in settings.LANGUAGES:
            # Split to get the language part
            langs.add(django_lang[0].split("-")[0])
        return langs

    def _check_valid_language(self, object_tag: ObjectTag) -> bool:
        """
        Returns True if the tag is on the available languages
        """
        available_langs = self._get_available_languages()
        return object_tag.tag.external_id in available_langs

    def _check_tag(self, object_tag: ObjectTag) -> bool:
        """
        Returns True if the tag is on the available languages
        """
        return super()._check_tag(object_tag) and self._check_valid_language(object_tag)
