import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contact_verification_is_not_moved_into_primary_actions() -> None:
    app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")

    assert '.hero-shell .contact-verify' not in app
    assert "actions.append(verify)" not in app
    assert 'launcher.dataset.placement = "inline"' in app
    assert 'dock.className = "actions chat-launcher-dock"' in app
    assert "position:fixed;right:18px;bottom:18px;z-index:40" in app
    assert "dock.append(launcher);" in app
    assert "actions.append(launcher);" not in app


def test_desktop_hero_separates_contact_verification_from_actions() -> None:
    responsive = (ROOT / "frontend/styles/responsive.css").read_text(encoding="utf-8")

    assert '"contacts contacts verify photo"' in responsive
    assert '"actions actions actions photo"' in responsive
    assert ".contact-verify { align-self: center; justify-self: end; max-width: 220px; }" in responsive
    assert ".contact-reveal { width: auto; min-height: 40px;" in responsive


def test_assistant_footer_nudge_is_localized() -> None:
    app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")

    assert 'document.querySelector("#chatNudge").textContent = messages.chat_nudge;' in app
    assert 'document.querySelector(".footer-card")' in app
    assert "nudge.hidden = !entry.isIntersecting;" in app

    expected = {
        "en": "Questions? Ask me.",
        "de": "Fragen? Fragen Sie mich.",
        "lv": "Jautājumi? Jautā man.",
    }
    for language, value in expected.items():
        messages = json.loads(
            (ROOT / f"content/translations/{language}.json").read_text(encoding="utf-8")
        )
        assert messages["chat_nudge"] == value


def test_assistant_uses_secondary_action_visual_weight() -> None:
    chat = (ROOT / "frontend/styles/features/chat.css").read_text(encoding="utf-8")
    contact = (ROOT / "frontend/styles/features/contact.css").read_text(encoding="utf-8")

    assert "background: var(--surface); color: var(--text);" in chat
    assert "box-shadow: var(--shadow-sm);" in chat
    assert "0 12px 30px" not in chat
    assert ".contact-verify-status:empty { display: none; }" in contact
