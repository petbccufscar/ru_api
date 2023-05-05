from rest_framework import serializers
from .models import Update, Asset
from datetime import timezone


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = (
            'key',
            'hash',
            'content_type',
            'file_extension',
            'url',
        )


class LaunchAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = (
            'key',
            'hash',
            'content_type',
            'url',
        )


class UpdateSerializer(serializers.ModelSerializer):
    launch_asset = LaunchAssetSerializer(many=False, read_only=True)
    assets = AssetSerializer(many=True, read_only=True)

    created_at = serializers.DateTimeField(
        format='%Y-%m-%dT%H:%M:%S.000Z',
        default_timezone=timezone.utc,
    )

    class Meta:
        model = Update
        fields = (
            'id',
            'created_at',
            'runtime_version',
            'metadata',
            'extra',
            'launch_asset',
            'assets',
        )
