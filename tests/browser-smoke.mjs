      `location.pathname === "/de/" && document.documentElement.lang === "de" && document.querySelector('#profileLocation')?.textContent === "Dortmund, Deutschland"`,
      10_000,
      "German localized URL"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#profileLocation')?.textContent`),
      "Dortmund, Deutschland"
    );

    const latvianLoaded = cdp.waitForEvent("Page.loadEventFired", 15_000);
    await cdp.evaluate(`document.querySelector('[data-lang="lv"]').click()`);
    await latvianLoaded;
    await cdp.waitFor(
      `location.pathname === "/lv/" && document.documentElement.lang === "lv" && document.title === "Andris Rožkalns · DevOps un Linux inženieris" && document.querySelector('#pdfLink')?.getAttribute('href') === "/cv-lv.pdf"`,
      10_000,
      "Latvian localized URL"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('[data-i18n="role"]').textContent`),
      "Junior DevOps un Linux inženieris"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#profileLocation')?.textContent`),
      "Dortmund, Vācija"
    );
    assert.deepEqual(
      await cdp.evaluate(`[...document.querySelectorAll('.language-switcher [data-lang]')].map((control) => [control.dataset.lang, control.getAttribute('aria-current')])`),
      [["en", null], ["de", null], ["lv", "page"]]
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('.focus-tags')`),
      null
    );
    assert.deepEqual(
      await cdp.evaluate(`(() => ({
        language: document.querySelector('.language-switcher')?.getAttribute('aria-label'),
        navigation: document.querySelector('.site-nav')?.getAttribute('aria-label'),
        profileListRole: document.querySelector('.profile-languages')?.getAttribute('role'),
        profileListLabel: document.querySelector('.profile-languages')?.getAttribute('aria-label'),
        profileListItems: [...document.querySelectorAll('.profile-languages .profile-language')].map((item) => item.getAttribute('role'))
      }))()`),
      {
        language: "Valodas",
        navigation: "CV",
        profileListRole: "list",
        profileListLabel: "Valodas",
        profileListItems: ["listitem", "listitem", "listitem"]
      }
    );

    await cdp.evaluate(`(() => {
      const launcher = document.querySelector('#chatLauncher');
      launcher.focus();