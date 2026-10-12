"""Source QA only: fake entitlement for media regression, never bundled."""
from PySide6.QtCore import QObject, Signal
class GrantedAuth(QObject):
    changed = Signal(dict)
    snapshot = {'ready': True, 'canEdit': True, 'plan':'trial'}
    def authorize(self): return True
    def can_edit(self): return True
    def show(self): raise AssertionError('Unexpected authentication prompt in granted media test')
    def shutdown(self): pass

def test_player(settings=None):
    from app.player import Player
    return Player(settings, auth_factory=GrantedAuth)
