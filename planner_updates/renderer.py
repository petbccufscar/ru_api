from rest_framework.renderers import BaseRenderer
from rest_framework.utils import encoders, json

class CanonicalJSONRenderer(BaseRenderer):
    """
    Renderer which serializes to Canonical JSON.
    """
    media_type = 'application/json'
    format = 'json'
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into Canonical JSON, returning a bytestring.
        """
        del accepted_media_type, renderer_context
        if data is None:
            return b''

        return json.dumps(
            data,
            cls=encoders.JSONEncoder,
            separators=(',', ':'),
            sort_keys=True,
        ).encode()
