from rest_framework import serializers
from .models import RU

class RUSerializer(serializers.ModelSerializer):
    class Meta:
        model = RU
        fields = '__all__'