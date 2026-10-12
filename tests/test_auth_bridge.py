import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from app.auth_store import SharedStore, dpapi
from app.auth_network import validate_request
from app.auth_gate import issue_permit, consume_permit, revoke_permits

ROOT = Path(__file__).resolve().parents[1]
class AuthBridgeTests(unittest.TestCase):
    def test_original_kit_hashes(self):
        hashes = json.loads((ROOT/'assets/auth/kit-sha256.json').read_text('utf-8'))
        for name, expected in hashes.items():
            self.assertEqual(hashlib.sha256((ROOT/'assets/auth'/name).read_bytes()).hexdigest(), expected)

    def test_dpapi_cas_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SharedStore(Path(temp)/'v4.bin')
            self.assertEqual(store.request({'op':'read'}), {'revision':0,'state':None})
            def write(_): return store.request({'op':'write','revision':0,'state':{'sample':'가나다'}})
            with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(write, range(2)))
            self.assertEqual(sum(r.get('revision')==1 for r in results),1)
            self.assertEqual(sum(r.get('bridgeError')=='STORE_CONFLICT' for r in results),1)
            self.assertEqual(store.request({'op':'read'})['state']['sample'],'가나다')
            store.path.write_bytes(b'corrupt')
            self.assertEqual(store.request({'op':'read'})['bridgeError'],'STORE_CORRUPT')
            self.assertEqual(store.path.read_bytes(),b'corrupt')

    def test_powershell_store_interoperability(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SharedStore(Path(temp)/'SsenSeries/Auth/v4.bin')
            env = dict(os.environ, LOCALAPPDATA=temp)
            def ps(request):
                result = subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(ROOT/'assets/auth/auth-store.ps1')],input=json.dumps(request).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)
                self.assertEqual(result.returncode,0)
                return json.loads(result.stdout.decode('utf-8-sig'))
            self.assertEqual(store.request({'op':'write','revision':0,'state':{'sample':'상호 호환'}}),{'revision':1})
            self.assertEqual(ps({'op':'read'})['state']['sample'],'상호 호환')
            self.assertEqual(ps({'op':'write','revision':1,'state':{'sample':'다른 앱'}}),{'revision':2})
            self.assertEqual(store.request({'op':'read'})['state']['sample'],'다른 앱')
            self.assertEqual(ps({'op':'write','revision':1,'state':{}})['bridgeError'],'STORE_CONFLICT')

    def test_fixed_api_and_raw_body(self):
        body = '{"한글": "가", "n":1}'
        self.assertEqual(validate_request({'path':'/challenge','method':'POST','body':body})[3],body.encode())
        for bad in [None, [], '//evil.invalid', '/keys?x=1', '/privacy', '/keys/../status']:
            with self.assertRaises(ValueError): validate_request({'path':bad,'method':'GET'})
        for headers in [{'Host':'evil.invalid'},{'Authorization':'secret\r\nHost: x'},{'X-Ssen-Spec':'0'}]:
            with self.assertRaises(ValueError): validate_request({'path':'/keys','method':'GET','headers':headers})
        with self.assertRaises(ValueError): validate_request({'path':'/keys','method':'POST'})

    def test_permits_fail_closed_and_are_scoped_one_use(self):
        revoke_permits()
        with self.assertRaises(PermissionError): issue_permit('clip')
        with patch('app.auth_gate.authorized', return_value=True):
            permit = issue_permit('clip')
        with self.assertRaises(PermissionError): consume_permit(permit,'capture')
        with self.assertRaises(PermissionError): consume_permit(permit,'clip')
        with patch('app.auth_gate.authorized', return_value=True): permit = issue_permit('clip')
        consume_permit(permit,'clip')
        with self.assertRaises(PermissionError): consume_permit(permit,'clip')
