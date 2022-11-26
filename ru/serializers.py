from rest_framework import serializers
from .models import RU, Notice


class RUSerializer(serializers.ModelSerializer):
    class Meta:
        model = RU
        fields = '__all__'


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = '__all__'
