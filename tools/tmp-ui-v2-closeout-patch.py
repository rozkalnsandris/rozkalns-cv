from pathlib import Path

smoke_path = Path("tests/browser-smoke.mjs")
smoke = smoke_path.read_text(encoding="utf-8")
old = '''    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 390,
      height: 844,
      deviceScaleFactor: 1,
      mobile: true
    });
    await cdp.navigate(`${baseUrl}/`);
    await cdp.waitFor(
      `document.documentElement.lang === "lv" && document.querySelector('#profileLocation')?.textContent === "Dortmund, Vācija"`,
      10_000,
      "mobile Latvian location restoration"
    );
    const mobileLocationLayout = await cdp.evaluate(`(() => {
      const row = document.querySelector('#profileLocation')?.closest('.contact-row');
      return row ? { clientWidth: row.clientWidth, scrollWidth: row.scrollWidth } : null;
    })()`);
    assert.ok(mobileLocationLayout);
    assert.ok(mobileLocationLayout.scrollWidth <= mobileLocationLayout.clientWidth);
'''
new = '''    const responsiveMatrix = [
      { width: 390, height: 844, mobile: true },
      { width: 430, height: 932, mobile: true },
      { width: 768, height: 1024, mobile: false },
      { width: 1280, height: 900, mobile: false },
      { width: 1440, height: 1000, mobile: false }
    ];
    for (const viewport of responsiveMatrix) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        ...viewport,
        deviceScaleFactor: 1
      });
      await cdp.navigate(`${baseUrl}/`);
      await cdp.waitFor(
        `document.documentElement.lang === "lv" && document.querySelector('#profileLocation')?.textContent === "Dortmund, Vācija"`,
        10_000,
        `responsive ${viewport.width}px Latvian restoration`
      );
      const layout = await cdp.evaluate(`(() => {
        const page = document.querySelector('#pageShell')?.getBoundingClientRect();
        const locationRow = document.querySelector('#profileLocation')?.closest('.contact-row');
        const primaryTargets = [...document.querySelectorAll(
          '.language-switcher button, .actions .button, #contactReveal, #chatLauncher'
        )].filter((element) => {
          const rect = element.getBoundingClientRect();
          return !element.hidden && rect.width > 0 && rect.height > 0;
        }).map((element) => {
          const rect = element.getBoundingClientRect();
          return {
            id: element.id || element.textContent.trim(),
            width: rect.width,
            height: rect.height
          };
        });
        return {
          innerWidth: window.innerWidth,
          documentClientWidth: document.documentElement.clientWidth,
          documentScrollWidth: document.documentElement.scrollWidth,
          bodyScrollWidth: document.body.scrollWidth,
          page: page ? { left: page.left, right: page.right, width: page.width } : null,
          location: locationRow ? {
            clientWidth: locationRow.clientWidth,
            scrollWidth: locationRow.scrollWidth
          } : null,
          primaryTargets
        };
      })()`);
      assert.equal(layout.innerWidth, viewport.width, `${viewport.width}px viewport width`);
      assert.ok(
        layout.documentScrollWidth <= layout.documentClientWidth,
        `${viewport.width}px document overflow: ${JSON.stringify(layout)}`
      );
      assert.ok(
        layout.bodyScrollWidth <= layout.documentClientWidth,
        `${viewport.width}px body overflow: ${JSON.stringify(layout)}`
      );
      assert.ok(layout.page, `${viewport.width}px page shell missing`);
      assert.ok(layout.page.left >= -0.5, `${viewport.width}px page left overflow`);
      assert.ok(layout.page.right <= viewport.width + 0.5, `${viewport.width}px page right overflow`);
      assert.ok(layout.location, `${viewport.width}px location row missing`);
      assert.ok(
        layout.location.scrollWidth <= layout.location.clientWidth,
        `${viewport.width}px location overflow: ${JSON.stringify(layout.location)}`
      );
      assert.ok(layout.primaryTargets.length >= 7, `${viewport.width}px primary targets missing`);
      for (const target of layout.primaryTargets) {
        assert.ok(
          target.height >= 48,
          `${viewport.width}px target below 48px: ${JSON.stringify(target)}`
        );
      }
    }
'''
if old not in smoke:
    raise SystemExit("expected single-view responsive smoke block missing")
smoke_path.write_text(smoke.replace(old, new, 1), encoding="utf-8")

doc_path = Path("docs/ui-v2/README.md")
doc = doc_path.read_text(encoding="utf-8")
needle = "- no production deploy without separate owner authorization\n"
replacement = '''- no production deploy without separate owner authorization

## Closeout status — 2026-08-15

The implementation slices are now represented by merged UI v2 work for the visual shell, recruiter-first hierarchy, hero, projects/skills/experience, live-homelab evidence and ProfilePage/metadata polish.

The multilingual URL migration is deliberately tracked separately in #251. The current EN/DE/LV client-side language switch remains supported in #243; crawlable `/en/`, `/de/`, `/lv/` variants and reciprocal `hreflang` belong to that dedicated routing/SEO change.

The real-Chromium validation matrix is enforced at 390, 430, 768, 1280 and 1440 CSS px. Each width must keep the document/page shell free of horizontal overflow, keep the localized location row contained and retain at least 48 CSS px height for the primary language/action/contact/chat controls.
'''
if needle not in doc:
    raise SystemExit("expected validation matrix tail missing")
doc_path.write_text(doc.replace(needle, replacement, 1), encoding="utf-8")
