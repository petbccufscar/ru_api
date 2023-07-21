"""ru_api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path
from ru import views as ru_views
from planner_updates import views as updates_views
from django.conf.urls.static import static

urlpatterns = [
    path('ru_api/admin/', admin.site.urls),
    path('ru_api/notice/', ru_views.NoticeView.as_view()),
    path('ru_api/', ru_views.RUView.as_view()),
    path('ru_api/menu/<str:campus>/', ru_views.menu_view),
    path('ru_api/index.html', ru_views.campus_view),
    path('ru_api/updates/v1/manifest', updates_views.ManifestView.as_view()),
    path('ru_api/updates/v1/upload', updates_views.UploadAssetView.as_view()),
    path('ru_api/updates/v1/sign', updates_views.AttachSignatureView.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
