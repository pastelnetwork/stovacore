import base64
import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from core.models import client
from core_modules.blackbox_modules.crypto import get_Ed521


def restore_bytes_from_string(pk_string):
    bytes_encoded = pk_string.encode()
    return base64.b64decode(bytes_encoded)


def bytes_to_string(pk_bytes):
    return base64.encodebytes(pk_bytes).decode('ascii')


class SignUserDataView(View):
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(SignUserDataView, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        try:
            json_data = json.loads(request.body)
            raw_data = json.dumps(json_data).encode()
            public_key = client.get_pubkey()
            private_key = client.get_privkey()
            pub_key_as_string = bytes_to_string(public_key)
            ed_521 = get_Ed521()
            signature = bytes(ed_521.sign(private_key, public_key, raw_data))
            json_data['public_key'] = pub_key_as_string
            json_data['signature'] = bytes_to_string(signature)
        except Exception as ex:
            return JsonResponse({'error': '{}'.format(ex)}, status=400)
        return JsonResponse(json_data)
