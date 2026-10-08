from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SimpleFirstAssistantDeferredTests(unittest.TestCase):
    def test_public_assistant_endpoints_denied(self):
        config=(ROOT/"deploy/simple-deploy/nginx.conf").read_text()
        for path in ("/api/chat", "/api/chat-config", "/api/chat-admission"):
            self.assertIn(f"location = {path} {{ return 404; }}",config)
        self.assertIn("location /api/ {",config)
        self.assertIn("proxy_pass http://127.0.0.1:5000/;",config)

    def test_localized_assistant_deferral_notice(self):
        import json
        messages=json.loads((ROOT/"content/ui-v2.json").read_text(encoding="utf-8"))
        for language in ("en","de","lv"):
            message=messages["i18n"][language]["v2_assistant_deferred"]
            assert message
            html=(ROOT/f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(f'data-ui-i18n="v2_assistant_deferred">{message}</p>',html)
            self.assertNotIn('id="chatLauncher"',html)
            self.assertIn('id="contactReveal"',html)

    def test_chat_not_in_home_source(self):
        html=(ROOT/"frontend/index.html").read_text()
        app=(ROOT/"frontend/app.mjs").read_text()
        for marker in ("chatLauncher","chatDialog","chatBackdrop","chatForm"):
            self.assertNotIn(marker,html)
        self.assertNotIn("chatLauncher",app)
        self.assertNotIn("features/chat.mjs",app)
        self.assertIn('id="contactReveal"',html)
        self.assertIn("features/contact.mjs",app)

if __name__=="__main__":unittest.main()
