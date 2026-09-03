from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contact_verification_is_not_moved_into_primary_actions() -> None:
    app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")

    assert '.hero-shell .contact-verify' not in app
    assert "actions.append(verify)" not in app
    assert 'launcher.dataset.placement = rail ? "rail" : "inline"' in app
    assert "else actions.append(launcher);" in app


def test_desktop_hero_separates_contact_verification_from_actions() -> None:
    responsive = (ROOT / "frontend/styles/responsive.css").read_text(encoding="utf-8")

    assert '"contacts contacts verify photo"' in responsive
    assert '"actions actions actions photo"' in responsive
    assert ".contact-verify { align-self: center; justify-self: end; max-width: 220px; }" in responsive
    assert ".contact-reveal { width: auto; min-height: 40px;" in responsive


def test_inline_assistant_uses_secondary_action_visual_weight() -> None:
    chat = (ROOT / "frontend/styles/features/chat.css").read_text(encoding="utf-8")
    contact = (ROOT / "frontend/styles/features/contact.css").read_text(encoding="utf-8")

    assert '.chat-launcher[data-placement="inline"] {' in chat
    assert "box-shadow: none;" in chat
    assert '.chat-launcher[data-placement="inline"]:hover {' in chat
    assert ".contact-verify-status:empty { display: none; }" in contact
