from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from .serializers import UpdateSerializer
from .models import Asset, Token, Update
from datetime import timedelta
import mimetypes
import json
import os


VALID_PLATFORMS = ['android', 'ios']


# Add extra extension to MIME type mappings.
mimetypes.add_type('font/ttf', '.ttf')


class BearerAuthentication(TokenAuthentication):
    model = Token
    keyword = 'Bearer'


class UploadAssetView(APIView):
    authentication_classes = [BearerAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request):
        # Prune dangling assets older than a minute.
        Asset.objects.filter(
            update=None,
            launch_update=None,
            uploaded_at__lt=timezone.now() - timedelta(minutes=1),
        ).delete()

        filenames = list(request.FILES.keys())
        if len(filenames) != 1:
            return Response({'error': 'must send one file'}, status=400)
        filename = filenames[0]
        request.FILES[filename].ext = os.path.splitext(filename)[1]

        if mimetypes.guess_type(filename)[0] == None:
            emsg = (
                'could not map MIME type from the file extension, please '
                'change the source to add the correct mapping'
            )
            return Response({'error': emsg}, status=422)

        asset = Asset(
            key=os.path.splitext(filename)[0],
            file=request.FILES[filename],
        )
        asset.save()
        return Response({'id': asset.id}, status=201)


def map_manifest(man):
    return {
        'id': man['id'],
        'createdAt': man['created_at'],
        'runtimeVersion': man['runtime_version'],
        'launchAsset': {
            'hash': man['launch_asset']['hash'],
            'key': man['launch_asset']['key'],
            'contentType': man['launch_asset']['content_type'],
            'url': man['launch_asset']['url'],
        },
        'assets': [
            {
                'hash': asset['hash'],
                'key': asset['key'],
                'contentType': asset['content_type'],
                'fileExtension': asset['file_extension'],
                'url': asset['url'],
            }
            for asset in man['assets']
        ],
        'metadata': man['metadata'],
        'extra': man['extra'],
    }


class ManifestView(APIView):
    authentication_classes = [BearerAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        res = Response()
        res['Expo-Protocol-Version'] = 1
        res['Expo-Sfv-Version'] = 0

        protocol_version = request.headers.get('Expo-Protocol-Version')
        if protocol_version == None:
            res.data = {'error': 'the protocol version header is missing'}
            res.status_code = 400
            return res

        platform = request.headers.get('Expo-Platform')
        if platform == None:
            res.data = {'error': 'the platform header is missing'}
            res.status_code = 400
            return res

        runtime_version = request.headers.get('Expo-Runtime-Version')
        if runtime_version == None:
            res.data = {'error': 'the runtime version header is missing'}
            res.status_code = 400
            return res

        channel = request.headers.get('Ufscar-Planner-Channel')
        if channel == None:
            res.daata = {'error': 'the channel name header is missing'}
            res.status_code = 400
            return res

        if protocol_version != "1":
            res.data = {'error': 'protocol version not supported'}
            res.status_code = 400
            return res

        if platform not in VALID_PLATFORMS:
            res.data = {'error': 'the provided platform is not supported'}
            res.status_code = 404
            return res

        if 'Expo-Expect-Signature' in request.headers:
            res.data = {'error': 'signatures are not supported yet'}
            res.status_code = 422
            return res

        try:
            latest_update = Update.objects.filter(
                runtime_version=runtime_version,
                channel=channel,
                platform=platform,
            ).latest('created_at')
            res.data = map_manifest(UpdateSerializer(latest_update).data)
            res['Cache-Control'] = 'private, max-age=0'
            return res
        except Update.DoesNotExist:
            del res['Content-Type']
            res.status_code = 404
            return res

    def post(self, request):
        res = Response()

        if not isinstance(request.data, dict):
            res.data = {'error': 'invalid request body, expected an object'}
            res.status_code = 400
            return res

        runtime_version = request.data.get('runtimeVersion')
        if not isinstance(runtime_version, str):
            res.data = {'error': 'invalid runtime version, expected a string'}
            res.status_code = 400
            return res

        req_platform = request.data.get('platform')
        if req_platform not in VALID_PLATFORMS:
            res.data = {'error': 'the given platform is not valid'}
            res.status_code = 400
            return res

        req_channel = request.data.get('channel')
        if not isinstance(req_channel, str):
            res.data = {'error': 'invalid channel name, expected a string'}
            res.status_code = 400
            return res

        req_launch = request.data.get('launchAsset')
        if not isinstance(req_launch, int):
            res.data = {'error': 'invalid launch asset, expected an integer'}
            res.status_code = 400
            return res

        req_extra = request.data.get('extra')
        if not isinstance(req_extra, dict):
            res.data = {'error': 'invalid extra field, expected an object'}
            res.status_code = 400
            return res

        update = None
        with transaction.atomic():
            launch = None
            try:
                launch = Asset.objects.get(id=req_launch)
            except Asset.DoesNotExist:
                res.data = {'error': 'the launch asset was not found'}
                res.status_code = 404
                return res

            request_assets = request.data.get('assets')
            if not isinstance(request_assets, list):
                res.data = {'error': 'invalid assets, expected an array'}
                res.status_code = 400
                return res

            assets = []
            for request_asset in request_assets:
                if not isinstance(request_asset, int):
                    res.data = {'error': 'invalid asset, expected an integer'}
                    res.status_code = 400
                    return res

                try:
                    assets.append(Asset.objects.get(id=request_asset))
                except Asset.DoesNotExist:
                    res.data = {'error': f'asset id {request_asset} not found'}
                    res.status_code = 404
                    return res

            update = Update(
                runtime_version=runtime_version,
                extra_json=json.dumps(req_extra),
                channel=req_channel,
                launch_asset=launch,
                platform=req_platform,
            )
            update.save()

            for request_asset in assets:
                request_asset.update = update
                request_asset.save()

        res.data = map_manifest(UpdateSerializer(update).data)
        res.status_code = 201
        return res
