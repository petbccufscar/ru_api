from django.shortcuts import render
# Create api view 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import RU
from .serializers import RUSerializer
from datetime import datetime


# Create your views here.
class RUView(APIView):

    def get(self, request):

        ru = RU.objects.all()
        serializer = RUSerializer(ru, many=True)
        return Response(serializer.data)
