from django.shortcuts import render
# Create api view 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import RU
from .serializers import RUSerializer
from datetime import datetime

def updateInfo():
    # RU.objects.all().delete()
    pass


# Create your views here.
class RUView(APIView):

    def get(self, request):

        ru = RU.objects.all()
        if len(ru) == 0 or ru[len(ru)-1].created_at.date() != datetime.date.today():
            updateInfo()
            ru = RU.objects.all()

        serializer = RUSerializer(ru, many=True)
        return Response(serializer.data)


