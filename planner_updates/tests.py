from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITransactionTestCase
from .models import Token, Asset
from base64 import urlsafe_b64encode
from hashlib import sha256
import shutil


TEST_DIR = 'test_dir'
TEST_MEDIA_ROOT = TEST_DIR + '/assets'


def dummy_png():
    suf = SimpleUploadedFile(
        'image.png',
        b'content',
        content_type='image/png'
    )
    return {suf.name: suf}


def authentication_header():
    user = User.objects.get_or_create(username='user')[0]
    token = Token.objects.get_or_create(user=user)[0]
    return 'Bearer ' + token.key


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class UploadTests(APITransactionTestCase):
    def test_unauthenticated_returns_401(self):
        res = self.client.post(
            '/ru_api/updates/v1/upload',
            data=dummy_png()
        )
        self.assertEqual(res.status_code, 401)

    def test_authenticated_sets_and_returns_201(self):
        res = self.client.post(
            '/ru_api/updates/v1/upload',
            data=dummy_png(),
            HTTP_AUTHORIZATION=authentication_header()
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Asset.objects.all().count(), 1)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ManifestPostTests(APITransactionTestCase):
    def setUp(self):
        asset_res = self.client.post(
            '/ru_api/updates/v1/upload',
            data=dummy_png(),
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(asset_res.status_code, 201)
        self.dummy_png_objid = asset_res.data['id']

    def test_unauthenticated_returns_401(self):
        res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'platform': 'android',
                'runtimeVersion': '0',
                'launchAsset': 0,
                'assets': [],
                'extra': {},
            }
        )
        self.assertEqual(res.status_code, 401)

    def test_post_ok_returns_201(self):
        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'platform': 'android',
                'runtimeVersion': '0',
                'launchAsset': self.dummy_png_objid,
                'assets': [],
                'extra': {},
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 201)

    def test_post_missing_argument_returns_400(self):
        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'platform': 'android',
                'runtimeVersion': '0',
                'launchAsset': self.dummy_png_objid,
                'assets': [],
                'extra': {},
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 400)

        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'runtimeVersion': '0',
                'launchAsset': self.dummy_png_objid,
                'assets': [],
                'extra': {},
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 400)

        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'platform': 'android',
                'launchAsset': self.dummy_png_objid,
                'assets': [],
                'extra': {},
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 400)

        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'platform': 'android',
                'runtimeVersion': '0',
                'assets': [],
                'extra': {},
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 400)

        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'platform': 'android',
                'runtimeVersion': '0',
                'launchAsset': self.dummy_png_objid,
                'extra': {},
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 400)

        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'platform': 'android',
                'runtimeVersion': '0',
                'launchAsset': self.dummy_png_objid,
                'assets': [],
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 400)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ManifestGetTests(APITransactionTestCase):
    def setUp(self):
        asset_res = self.client.post(
            '/ru_api/updates/v1/upload',
            data=dummy_png(),
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(asset_res.status_code, 201)

        manifest_res = self.client.post(
            '/ru_api/updates/v1/manifest',
            format='json',
            data={
                'channel': 'testing',
                'platform': 'android',
                'runtimeVersion': '0',
                'launchAsset': asset_res.data['id'],
                'assets': [],
                'extra': {},
            },
            HTTP_AUTHORIZATION=authentication_header(),
        )
        self.assertEqual(manifest_res.status_code, 201)

    def test_get_ok_returns_200(self):
        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['runtimeVersion'], '0')

        fhash = res.data['launchAsset']['hash']
        self.assertEqual(
            fhash + '=',
            urlsafe_b64encode(sha256(b'content').digest()).decode(),
        )

    def test_get_ok_matches_hash(self):
        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 200)

    def test_unsupported_platform_returns_404(self):
        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'temple-os-mobile',
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 404)

    def test_unknown_channel_returns_404(self):
        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'reduction',
            }
        )
        self.assertEqual(res.status_code, 404)

    def test_unknown_runtime_version_returns_404(self):
        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_EXPO-RUNTIME-VERSION': 'exposdk:1530.0.0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 404)

    def test_unsupported_version_returns_400(self):
        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-PROTOCOL-VERSION': '45',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_header_returns_400(self):
        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 400)

        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 400)

        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_UFSCAR-PLANNER-CHANNEL': 'testing',
            }
        )
        self.assertEqual(res.status_code, 400)

        res = self.client.get(
            '/ru_api/updates/v1/manifest',
            **{
                'HTTP_EXPO-PLATFORM': 'android',
                'HTTP_EXPO-PROTOCOL-VERSION': '1',
                'HTTP_EXPO-RUNTIME-VERSION': '0',
            }
        )
        self.assertEqual(res.status_code, 400)


def tearDownModule():
    shutil.rmtree(TEST_DIR, ignore_errors=True)
