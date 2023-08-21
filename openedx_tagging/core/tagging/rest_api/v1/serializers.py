"""
API Serializers for taxonomies
"""

from rest_framework import serializers

from openedx_tagging.core.tagging.models import Taxonomy, ObjectTag


class TaxonomyListQueryParamsSerializer(serializers.Serializer):
    """
    Serializer for the query params for the GET view
    """

    enabled = serializers.BooleanField(required=False)


class TaxonomySerializer(serializers.ModelSerializer):
    class Meta:
        model = Taxonomy
        fields = [
            "id",
            "name",
            "description",
            "enabled",
            "required",
            "allow_multiple",
            "allow_free_text",
            "system_defined",
            "visible_to_authors",
        ]


class ObjectTagListQueryParamsSerializer(serializers.Serializer):
    """
    Serializer for the query params for the ObjectTag GET view
    """

    taxonomy = serializers.PrimaryKeyRelatedField(
        queryset=Taxonomy.objects.all(), required=False
    )


class ObjectTagSerializer(serializers.ModelSerializer):
    """
    Serializer for the ObjectTag model.
    """

    class Meta:
        model = ObjectTag
        fields = [
            "name",
            "value",
            "taxonomy_id",
            "tag_ref",
            "is_valid",
        ]

# ToDo: Remove
# class ObjectTagUpdateItemSerializer(serializers.Serializer):
#     """
#     Serialize for a single ObjectTag item
#     """
#     id = serializers.CharField(required=False)
#     value = serializers.CharField(required=False)

#     def validate(self, attrs):
#         if attrs['id'] and attrs['value']:
#             raise serializers.ValidationError('A tag should be referenced by either id or value, not both')
#         if not (attrs['id'] or attrs['value']):
#             raise serializers.ValidationError('A tag should be referenced by either id or value')

#         return attrs

class ObjectTagUpdateBodySerializer(serializers.Serializer):
    """
    Serializer of the body for the ObjectTag UPDATE view
    """
    tags = serializers.ListField(child=serializers.CharField(), required=True)

class ObjectTagUpdateQueryParamsSerializer(serializers.Serializer):
    """
    Serializer of the query params for the ObjectTag UPDATE view
    """

    taxonomy = serializers.PrimaryKeyRelatedField( queryset=Taxonomy.objects.all(), required=True)
