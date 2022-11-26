from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import RU, Notice
from .serializers import RUSerializer, NoticeSerializer


class RUView(APIView):
    @method_decorator(cache_page(60))
    def get(self, _):
        ru = RU.objects.all()
        serializer = RUSerializer(ru, many=True)
        return Response(serializer.data)


class NoticeView(APIView):
    @method_decorator(cache_page(60))
    def get(self, _):
        notice = Notice.objects.last()
        if notice:
            serializer = NoticeSerializer(notice, allow_null=True)
            return Response(serializer.data)
        else:
            return Response(False)
