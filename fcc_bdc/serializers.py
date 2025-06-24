from rest_framework import serializers

class BoundingBoxRequestSerializer(serializers.Serializer):
    state = serializers.CharField(max_length=2)
    bbox = serializers.ListField(
        child=serializers.FloatField(),
        min_length=4,
        max_length=4,
        help_text="Bounding box [xmin, ymin, xmax, ymax]"
    )