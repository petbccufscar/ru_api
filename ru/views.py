from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import RU
from .serializers import RUSerializer
from datetime import datetime


class RUView(APIView):
    @method_decorator(cache_page(60))
    def get(self, request):
        ru = RU.objects.all()
        serializer = RUSerializer(ru, many=True)
        return Response(serializer.data)
