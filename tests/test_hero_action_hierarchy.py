import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contact_verification_is_not_moved_into_primary_actions() -> None:
    app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert '.hero-shell .contact-verify' not in app
    assert "actions.append(verify)" not in app
    assert "chatLauncher" not in app
    assert 'id="chatLauncher"' not in html
    assert 'id="contactReveal"' in html


def test_desktop_hero_separates_contact_verification_from_actions() -> None:
    responsive = (ROOT / "frontend/styles/v2/responsive.css").read_text(encoding="utf-8")

    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    assert html.index('id="contact"') < html.index('class="contact-verify"')
    assert '"actions actions photo"' in responsive
    assert '.hero-shell .actions { display: flex;' in responsive



def test_deferred_assistant_does_not_nudge_from_footer() -> None:
    app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")
    assert "chat_nudge" not in app
    assert "chatLauncher" not in app


def test_assistant_css_is_not_imported() -> None:
    css = (ROOT / "frontend/styles/index.css").read_text(encoding="utf-8")
    assert "features/chat.css" not in css
    contact = (ROOT / "frontend/styles/v2/features/contact.css").read_text(encoding="utf-8")
    assert ".contact-verify-status:empty { display: none; }" in contact
