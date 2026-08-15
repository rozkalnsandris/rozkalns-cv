from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOG_MARKUP = 'id="chatLog" class="chat-log" role="log" aria-live="polite" aria-relevant="additions" aria-atomic="false"'


class ChatLogSemanticsTest(unittest.TestCase):
    def test_source_and_generated_transcript_keep_log_semantics_without_listitems(self):
        for relative in ("frontend/index.html", "html/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(html.count(LOG_MARKUP), 1, relative)
            self.assertNotIn('class="message bot" role="listitem"', html, relative)
            self.assertNotIn('class="message user" role="listitem"', html, relative)

    def test_dynamic_messages_do_not_assign_listitem_role(self):
        source = (ROOT / "frontend/features/chat.mjs").read_text(encoding="utf-8")
        self.assertIn('message.className = `message ${role}`;', source)
        self.assertIn('log.append(message);', source)
        self.assertNotIn('message.setAttribute("role", "listitem")', source)


if __name__ == "__main__":
    unittest.main()
