"""Regression tests for text input embedded in Nova's existing voice conversation."""
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "static" / "index.html"


class InlineChatFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML.read_text(encoding="utf-8")
        cls.app = (ROOT / "app.py").read_text(encoding="utf-8")
        cls.launcher = (ROOT / "run.bat").read_text(encoding="utf-8")

    def test_input_is_inside_existing_conversation_panel_not_an_extra_tab(self):
        conversation_start = self.html.index('<div class="card-title">Conversation</div>')
        messages_start = self.html.index('id="messages"', conversation_start)
        composer_start = self.html.index('id="chatForm"', messages_start)
        clear_start = self.html.index('id="clearChat"', composer_start)
        booking_panel_start = self.html.index('<section class="panel" id="panel-booking">')
        self.assertLess(conversation_start, messages_start)
        self.assertLess(messages_start, composer_start)
        self.assertLess(composer_start, clear_start)
        self.assertLess(clear_start, booking_panel_start)
        self.assertIn('data-tab="booking"', self.html)
        self.assertIn('data-tab="manage"', self.html)

    def test_voice_and_conversation_panel_are_visible_on_initial_load(self):
        self.assertIn('<section class="panel active" id="panel-voice">', self.html)
        self.assertIn('<section class="panel active" id="panel-menu">', self.html)
        voice = self.html.index('<section class="panel active" id="panel-voice">')
        menu = self.html.index('<section class="panel active" id="panel-menu">')
        self.assertLess(voice, menu)
        self.assertNotIn('data-tab="chat"', self.html)

    def test_fallback_is_visibly_labeled_and_styled(self):
        self.assertIn("Mic not working? Type your message here", self.html)
        self.assertIn('placeholder="Type your booking or cancellation request…"', self.html)
        self.assertIn('.chat-composer{display:flex', self.html)
        self.assertIn('.chat-composer textarea{display:block', self.html)
        self.assertIn('VOICE OPTIONAL', self.html)

    def test_typed_messages_use_same_chat_backend_and_context(self):
        self.assertIn("$('chatForm').addEventListener('submit', sendTextMessage)", self.html)
        self.assertIn("fetch('/api/chat', { method: 'POST', body: form })", self.html)
        self.assertIn("form.append('history', JSON.stringify(sessionHistory.slice(-40)))", self.html)
        self.assertIn("form.append('mode', activeMode)", self.html)
        self.assertIn('function sendTextMessage(event)', self.html)

    def test_chat_history_is_memory_only_and_legacy_storage_is_cleared(self):
        self.assertIn('let audioContext = null', self.html)
        self.assertIn('voicedFrames = 0, sessionHistory = []', self.html)
        self.assertIn('localStorage.removeItem(key)', self.html)
        self.assertNotIn('localStorage.setItem', self.html)
        self.assertNotIn('function loadModeHistory', self.html)
        self.assertNotIn('function persistHistory', self.html)

    def test_enter_submits_and_shift_enter_keeps_newline(self):
        self.assertIn("event.key === 'Enter' && !event.shiftKey", self.html)
        self.assertIn("$('chatForm').requestSubmit()", self.html)


    def test_booking_ui_uses_name_and_mobile_not_email(self):
        self.assertIn('id="guestName"', self.html)
        self.assertIn('id="guestPhone"', self.html)
        self.assertIn('id="lookupName"', self.html)
        self.assertIn('id="lookupPhone"', self.html)
        self.assertNotIn('guestEmail', self.html)
        self.assertNotIn('lookupEmail', self.html)
        self.assertIn("guest_name: $('guestName').value.trim(), phone: $('guestPhone').value.trim()", self.html)

    def test_home_html_cannot_be_reused_from_browser_cache(self):
        self.assertIn('Cache-Control": "no-store, no-cache, must-revalidate"', self.app)
        self.assertIn('Pragma": "no-cache"', self.app)

    def test_launcher_chooses_free_port_and_waits_for_updated_frontend(self):
        self.assertIn('scripts\\find_port.py', self.launcher)
        self.assertIn('scripts\\open_browser_when_ready.py', self.launcher)
        self.assertIn('context-aware-room-followup-20261026', self.launcher)
        self.assertIn('--port %NOVA_PORT%', self.launcher)
        self.assertNotIn('--port 8000', self.launcher)

    def test_port_picker_runs_and_returns_local_port_range(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "find_port.py")],
            check=True, capture_output=True, text=True, timeout=5,
        )
        port = int(result.stdout.strip())
        self.assertGreaterEqual(port, 8000)
        self.assertLessEqual(port, 8099)


if __name__ == "__main__":
    unittest.main()
