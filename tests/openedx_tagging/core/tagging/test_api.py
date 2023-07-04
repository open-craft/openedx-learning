""" Test the tagging APIs """

from unittest.mock import Mock, patch

from django.test.testcases import TestCase

import openedx_tagging.core.tagging.api as tagging_api
from openedx_tagging.core.tagging.models import ObjectTag, Tag

from .test_models import TestTagTaxonomyMixin


class TestApiTagging(TestTagTaxonomyMixin, TestCase):
    """
    Test the Tagging API methods.
    """

    def test_create_taxonomy(self):
        params = {
            "name": "Difficulty",
            "description": "This taxonomy contains tags describing the difficulty of an activity",
            "enabled": False,
            "required": True,
            "allow_multiple": True,
            "allow_free_text": True,
        }
        taxonomy = tagging_api.create_taxonomy(**params)
        for param, value in params.items():
            assert getattr(taxonomy, param) == value

    def test_create_taxonomy_bad_object_tag_class(self):
        with self.assertRaises(ValueError) as exc:
            tagging_api.create_taxonomy(
                name="invalid",
                object_tag_class=str,
            )
        assert "object_tag_class <class 'str'> must be class like ObjectTag" in str(
            exc.exception
        )

    def test_get_taxonomies(self):
        tax1 = tagging_api.create_taxonomy("Enabled")
        tax2 = tagging_api.create_taxonomy("Disabled", enabled=False)
        with self.assertNumQueries(1):
            enabled = list(tagging_api.get_taxonomies())
        assert enabled == [tax1, self.taxonomy, self.system_taxonomy]
        assert str(enabled[0]) == "<Taxonomy> (3) Enabled"
        assert str(enabled[1]) == "<Taxonomy> (1) Life on Earth"
        assert str(enabled[2]) == "<SystemTaxonomy> (2) System Languages"

        with self.assertNumQueries(1):
            disabled = list(tagging_api.get_taxonomies(enabled=False))
        assert disabled == [tax2]
        assert str(disabled[0]) == "<Taxonomy> (4) Disabled"

        with self.assertNumQueries(1):
            both = list(tagging_api.get_taxonomies(enabled=None))
        assert both == [tax2, tax1, self.taxonomy, self.system_taxonomy]

    def test_get_tags(self):
        self.setup_tag_depths()
        assert tagging_api.get_tags(self.taxonomy) == [
            *self.domain_tags,
            *self.kingdom_tags,
            *self.phylum_tags,
        ]

    def check_object_tag(self, object_tag, taxonomy, tag, name, value):
        """
        Verifies that the properties of the given object_tag (once refreshed from the database) match those given.
        """
        object_tag.refresh_from_db()
        assert object_tag.taxonomy == taxonomy
        assert object_tag.tag == tag
        assert object_tag.name == name
        assert object_tag.value == value

    def test_resync_object_tags(self):
        missing_links = ObjectTag(object_id="abc", object_type="alpha")
        missing_links.name = self.taxonomy.name
        missing_links.value = self.mammalia.value
        missing_links.save()
        changed_links = self.taxonomy.object_tag_class(
            object_id="def",
            object_type="alpha",
            taxonomy=self.taxonomy,
            tag=self.mammalia,
        )
        changed_links.name = "Life"
        changed_links.value = "Animals"
        changed_links.save()
        no_changes = self.taxonomy.object_tag_class(
            object_id="ghi",
            object_type="beta",
            taxonomy=self.taxonomy,
            tag=self.mammalia,
        )
        no_changes.name = self.taxonomy.name
        no_changes.value = self.mammalia.value
        no_changes.save()

        changed = tagging_api.resync_object_tags()
        assert changed == 2
        for object_tag in (missing_links, changed_links, no_changes):
            self.check_object_tag(
                object_tag, self.taxonomy, self.mammalia, "Life on Earth", "Mammalia"
            )

        # Once all tags are resynced, they stay that way
        changed = tagging_api.resync_object_tags()
        assert changed == 0

        # ObjectTag value preserved even if linked tag is deleted
        self.mammalia.delete()
        for object_tag in (missing_links, changed_links, no_changes):
            self.check_object_tag(
                object_tag, self.taxonomy, None, "Life on Earth", "Mammalia"
            )

        # ObjectTag name preserved even if linked taxonomy is deleted
        self.taxonomy.delete()
        for object_tag in (missing_links, changed_links, no_changes):
            self.check_object_tag(object_tag, None, None, "Life on Earth", "Mammalia")

        # Resyncing the tags for code coverage
        changed = tagging_api.resync_object_tags()
        assert changed == 0

        # Recreate the taxonomy with a custom tag class and resync some tags
        first_taxonomy = tagging_api.create_taxonomy(
            "Life on Earth", object_tag_class=ObjectTag
        )
        second_taxonomy = tagging_api.create_taxonomy(
            "Life on Earth", object_tag_class=ObjectTag
        )
        new_tag = Tag.objects.create(
            value="Mammalia",
            taxonomy=second_taxonomy,
        )

        # Use our mock object tag class here
        MockObjectClass = Mock()
        MockObjectClass.return_value = Mock(spec=ObjectTag)
        MockObjectClass.return_value.is_valid.side_effect = [False, True, False, True]
        with patch(
            "openedx_tagging.core.tagging.models.import_string",
            return_value=MockObjectClass,
        ):
            changed = tagging_api.resync_object_tags(
                ObjectTag.objects.filter(object_type="alpha")
            )
            assert changed == 2

        for object_tag in (missing_links, changed_links):
            self.check_object_tag(
                object_tag, second_taxonomy, new_tag, "Life on Earth", "Mammalia"
            )

        # Ensure the omitted tag was not updated
        self.check_object_tag(no_changes, None, None, "Life on Earth", "Mammalia")

        # Update that one too (without the patching)
        changed = tagging_api.resync_object_tags(
            ObjectTag.objects.filter(object_type="beta")
        )
        assert changed == 1
        self.check_object_tag(
            no_changes, first_taxonomy, None, "Life on Earth", "Mammalia"
        )

    def test_tag_object(self):
        self.taxonomy.allow_multiple = True
        test_tags = [
            [
                self.archaea.id,
                self.eubacteria.id,
                self.chordata.id,
            ],
            [
                self.chordata.id,
                self.archaebacteria.id,
            ],
            [
                self.archaebacteria.id,
                self.archaea.id,
            ],
        ]

        # Tag and re-tag the object, checking that the expected tags are returned and deleted
        for tag_list in test_tags:
            object_tags = tagging_api.tag_object(
                self.taxonomy,
                tag_list,
                "biology101",
                "course",
            )

            # Ensure the expected number of tags exist in the database
            assert (
                list(
                    tagging_api.get_object_tags(
                        taxonomy=self.taxonomy,
                        object_id="biology101",
                        object_type="course",
                    )
                )
                == object_tags
            )
            # And the expected number of tags were returned
            assert len(object_tags) == len(tag_list)
            for index, object_tag in enumerate(object_tags):
                assert object_tag.tag_id == tag_list[index]
                assert object_tag.is_valid()
                assert object_tag.taxonomy == self.taxonomy
                assert object_tag.name == self.taxonomy.name
                assert object_tag.object_id == "biology101"
                assert object_tag.object_type == "course"

    def test_get_object_tags(self):
        # Alpha tag has no taxonomy
        alpha = ObjectTag(object_id="abc", object_type="alpha")
        alpha.name = self.taxonomy.name
        alpha.value = self.mammalia.value
        alpha.save()
        # Beta tag has a closed taxonomy
        beta = self.taxonomy.object_tag_class.objects.create(
            object_id="abc",
            object_type="beta",
            taxonomy=self.taxonomy,
        )

        # Fetch all the tags for a given object ID
        assert list(
            tagging_api.get_object_tags(
                object_id="abc",
                valid_only=False,
            )
        ) == [
            alpha,
            beta,
        ]

        # No valid tags for this object yet..
        assert not list(
            tagging_api.get_object_tags(
                object_id="abc",
                valid_only=True,
            )
        )
        # ...until we make beta valid
        beta.tag = self.mammalia
        beta.save()
        assert list(
            tagging_api.get_object_tags(
                object_id="abc",
                valid_only=True,
            )
        ) == [
            beta,
        ]

        # Fetch all the tags for alpha-type objects
        assert list(
            tagging_api.get_object_tags(
                object_id="abc",
                object_type="alpha",
                valid_only=False,
            )
        ) == [
            alpha,
        ]

        # Fetch all the tags for a given object ID + taxonomy
        assert list(
            tagging_api.get_object_tags(
                object_id="abc",
                taxonomy=self.taxonomy,
                valid_only=False,
            )
        ) == [
            beta,
        ]
