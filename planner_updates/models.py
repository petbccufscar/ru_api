from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework.authtoken.models import Token as RestToken
from base64 import urlsafe_b64encode
from mimetypes import guess_type
from uuid import uuid4
from secrets import token_hex
from hashlib import sha256
import json
import os


class Token(RestToken):
    pass


def hash_and_path(instance, path):
    ext = instance.file.file.ext or os.path.splitext(path)[1]
    hasher = sha256()
    instance.file.open()
    for chunk in instance.file.chunks():
        hasher.update(chunk)
    instance.hash = urlsafe_b64encode(hasher.digest()).rstrip(b'=').decode()
    return os.path.join('updates/', token_hex(16) + ext)


def validate_json(j):
    try:
        json.loads(j)
    except json.decoder.JSONDecodeError:
        raise ValidationError('Input string is not valid JSON')


class Asset(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to=hash_and_path)
    hash = models.CharField(max_length=43, editable=False)
    key = models.CharField(max_length=256)

    update = models.ForeignKey(
        'Update',
        related_name='assets',
        null=True,
        on_delete=models.CASCADE,
    )

    def file_extension(self):
        return os.path.splitext(self.file.path)[1]

    def content_type(self):
        return guess_type(self.file.path)[0]

    def url(self):
        domain = settings.BASE_URL
        return f'https://{domain}{self.file.url}'


class Update(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    runtime_version = models.CharField(max_length=64)
    extra_json = models.TextField(validators=[validate_json])
    channel = models.CharField(max_length=64)

    launch_asset = models.OneToOneField(
        Asset,
        on_delete=models.RESTRICT,
        related_name='launch_update'
    )

    def metadata(self):
        return {}

    def extra(self):
        return json.loads(self.extra_json)

    IOS = 'ios'
    ANDROID = 'android'
    platform = models.CharField(
        max_length=7,
        choices=[(IOS, IOS), (ANDROID, ANDROID)]
    )
