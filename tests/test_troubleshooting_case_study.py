from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CASE_STUDY = ROOT / "docs/TROUBLESHOOTING_CASE_STUDY.md"
README = ROOT / "README.md"


def _case_study() -> str:
    return CASE_STUDY.read_text(encoding="utf-8")


def test_case_study_is_reachable_and_covers_the_incident_contract() -> None:
    text = _case_study()
    readme = README.read_text(encoding="utf-8")

    assert "docs/TROUBLESHOOTING_CASE_STUDY.md" in readme
    assert "Historical scope:" in text
    assert "not a statement about the current production" in text

    for section in range(1, 9):
        assert f"## {section}." in text

    required_evidence = (
        "https://github.com/rozkalnsandris/rozkalns-cv/pull/405",
        "https://github.com/rozkalnsandris/rozkalns-cv/issues/399",
        "../runner/release/rozkalns-cv-pull-deploy-main",
        "../tests/test_pull_deploy_public_redirect_contract.py",
    )
    for evidence in required_evidence:
        assert evidence in text


def test_every_case_study_section_has_an_explicit_evidence_anchor() -> None:
    text = _case_study()

    section_starts = [text.index(f"## {number}.") for number in range(1, 9)]
    section_starts.append(text.index("## Publication boundary"))

    for start, end in zip(section_starts, section_starts[1:]):
        section = text[start:end]
        assert "**Evidence:**" in section


def test_relative_case_study_evidence_paths_exist() -> None:
    text = _case_study()
    relative_links = re.findall(r"\]\((\.\./[^)]+)\)", text)

    assert relative_links
    for link in relative_links:
        target = (CASE_STUDY.parent / link).resolve()
        assert target.is_relative_to(ROOT)
        assert target.exists(), link


def test_case_study_keeps_publication_and_production_boundaries() -> None:
    text = _case_study()

    assert "/home/" not in text
    assert "private-user-images.githubusercontent.com" not in text
    assert not re.search(r"https://github\.com/[^\s)]+/commit/[0-9a-f]{40}", text)
    assert not re.search(
        r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b",
        text,
    )

    assert "source fix can be ready and validated without proving that it is currently live" in text
    assert "Repository evidence can prove the" in text
    assert "cannot by itself prove what is currently live" in text


def test_case_study_does_not_invent_operational_impact() -> None:
    text = _case_study().lower()

    for unsupported_claim in (
        "customer impact:",
        "users affected:",
        "outage duration:",
        "revenue impact:",
    ):
        assert unsupported_claim not in text
