import hashlib,io,json,unittest
from unittest.mock import patch
from constitution_distance.api import API

class TransportTests(unittest.TestCase):
 def test_transport_hash_and_header_allowlist_never_persist_credentials(self):
  class Response(io.BytesIO):
   status=200
   headers={'Date':'today','X-Request-ID':'public-id','Authorization':'secret','Set-Cookie':'private'}
  payload={'messages':[{'role':'user','content':'0 or 1'}]}
  with patch('urllib.request.urlopen',return_value=Response(b'{"ok": true}')) as call:
   result=API('https://example.com','secret').request('/test',payload)
  self.assertEqual(result['_transport']['request_body_sha256'],hashlib.sha256(json.dumps(payload).encode()).hexdigest())
  self.assertEqual(result['_http_headers'],{'date':'today','x-request-id':'public-id'})
  self.assertNotIn('secret',json.dumps(result));self.assertNotIn('private',json.dumps(result))
  self.assertEqual(call.call_args.args[0].get_header('Authorization'),'Bearer secret')
