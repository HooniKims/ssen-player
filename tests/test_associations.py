import unittest
from pathlib import Path
from app.file_associations import registration_entries, EXTENSIONS, PROG_ID, CAPABILITIES
from scripts.render_associations import render


class AssociationTests(unittest.TestCase):
    def test_registers_candidates_without_overwriting_defaults(self):
        exe = r'C:\수업 자료\쎈player\SsenPlayer.exe'
        entries = registration_entries(exe)
        command = next(value for path, name, value in entries if path.endswith(r'\shell\open\command'))
        self.assertEqual(command, f'"{exe}" "%1"')
        self.assertFalse(any('UserChoice' in path for path, _, _ in entries))
        for ext in EXTENSIONS:
            self.assertIn((CAPABILITIES + r'\FileAssociations', ext, PROG_ID), entries)
            self.assertIn((rf'Software\Classes\{ext}\OpenWithProgids', PROG_ID, ''), entries)
            self.assertFalse(any(path == rf'Software\Classes\{ext}' for path, _, _ in entries))

    def test_installer_registration_matches_runtime(self):
        root = Path(__file__).resolve().parent.parent
        self.assertEqual((root/'build/associations.iss').read_text('utf-8-sig'), render())
