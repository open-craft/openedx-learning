# Generated by Django 3.2.19 on 2023-06-22 07:37

import django.db.models.deletion
from django.db import migrations, models

import openedx_learning.lib.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Taxonomy",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "name",
                    openedx_learning.lib.fields.MultiCollationCharField(
                        db_collations={
                            "mysql": "utf8mb4_unicode_ci",
                            "sqlite": "NOCASE",
                        },
                        db_index=True,
                        help_text="User-facing label used when applying tags from this taxonomy to Open edX objects.",
                        max_length=255,
                    ),
                ),
                (
                    "description",
                    openedx_learning.lib.fields.MultiCollationTextField(
                        blank=True,
                        help_text="Provides extra information for the user when applying tags from this taxonomy to an object.",
                        null=True,
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Only enabled taxonomies will be shown to authors.",
                    ),
                ),
                (
                    "required",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates that one or more tags from this taxonomy must be added to an object.",
                    ),
                ),
                (
                    "allow_multiple",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates that multiple tags from this taxonomy may be added to an object.",
                    ),
                ),
                (
                    "allow_free_text",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates that tags in this taxonomy need not be predefined; authors may enter their own tag values.",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Taxonomies",
            },
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "value",
                    openedx_learning.lib.fields.MultiCollationCharField(
                        db_collations={
                            "mysql": "utf8mb4_unicode_ci",
                            "sqlite": "NOCASE",
                        },
                        help_text="Content of a given tag, occupying the 'value' part of the key:value pair.",
                        max_length=500,
                    ),
                ),
                (
                    "external_id",
                    openedx_learning.lib.fields.MultiCollationCharField(
                        blank=True,
                        db_collations={
                            "mysql": "utf8mb4_unicode_ci",
                            "sqlite": "NOCASE",
                        },
                        help_text="Used to link an Open edX Tag with a tag in an externally-defined taxonomy.",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        default=None,
                        help_text="Tag that lives one level up from the current tag, forming a hierarchy.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="oel_tagging.tag",
                    ),
                ),
                (
                    "taxonomy",
                    models.ForeignKey(
                        default=None,
                        help_text="Namespace and rules for using a given set of tags.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="oel_tagging.taxonomy",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ObjectTag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "object_id",
                    openedx_learning.lib.fields.MultiCollationCharField(
                        db_collations={
                            "mysql": "utf8mb4_unicode_ci",
                            "sqlite": "NOCASE",
                        },
                        help_text="Identifier for the object being tagged",
                        max_length=255,
                    ),
                ),
                (
                    "object_type",
                    openedx_learning.lib.fields.MultiCollationCharField(
                        db_collations={
                            "mysql": "utf8mb4_unicode_ci",
                            "sqlite": "NOCASE",
                        },
                        help_text="Type of object being tagged",
                        max_length=255,
                    ),
                ),
                (
                    "_name",
                    openedx_learning.lib.fields.MultiCollationCharField(
                        db_collations={
                            "mysql": "utf8mb4_unicode_ci",
                            "sqlite": "NOCASE",
                        },
                        help_text="User-facing label used for this tag, stored in case taxonomy is (or becomes) null. If the taxonomy field is set, then taxonomy.name takes precedence over this field.",
                        max_length=255,
                    ),
                ),
                (
                    "_value",
                    openedx_learning.lib.fields.MultiCollationCharField(
                        db_collations={
                            "mysql": "utf8mb4_unicode_ci",
                            "sqlite": "NOCASE",
                        },
                        help_text="User-facing value used for this tag, stored in case tag is null, e.g if taxonomy is free text, or if it becomes null (e.g. if the Tag is deleted). If the tag field is set, then tag.value takes precedence over this field.",
                        max_length=500,
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        default=None,
                        help_text="Tag associated with this object tag. Provides the tag's 'value' if set.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="oel_tagging.tag",
                    ),
                ),
                (
                    "taxonomy",
                    models.ForeignKey(
                        default=None,
                        help_text="Taxonomy that this object tag belongs to. Used for validating the tag and provides the tag's 'name' if set.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="oel_tagging.taxonomy",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(
                fields=["taxonomy", "value"], name="oel_tagging_taxonom_89e779_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(
                fields=["taxonomy", "external_id"],
                name="oel_tagging_taxonom_44e355_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="objecttag",
            index=models.Index(
                fields=["taxonomy", "_value"], name="oel_tagging_taxonom_3668ec_idx"
            ),
        ),
    ]
