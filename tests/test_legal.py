import unittest
from pathlib import Path
from scripts.prepare_legal import prepare

ROOT = Path(__file__).resolve().parent.parent


class LegalTests(unittest.TestCase):
    def test_terms_preserve_third_party_rights(self):
        text = (ROOT/'LICENSE').read_text('utf-8')
        self.assertIn('이 약관은 그 라이선스가 허락하는 권리를 제한하지 않습니다.', text)
        self.assertIn('1.0.0 및 그 이후', text)
        self.assertIn('상명초 김승현, 등촌중 김형훈', text)
        self.assertNotIn('{', text)
        self.assertIn('YouTube 검색·재생·구간 저장', text)

    def test_installer_terms_match_canonical_terms(self):
        prepare()
        self.assertEqual((ROOT/'LICENSE').read_text('utf-8'), (ROOT/'build/LICENSE.txt').read_text('utf-16'))
        self.assertTrue((ROOT/'build/LICENSE.txt').read_bytes().startswith(b'\xff\xfe'))
