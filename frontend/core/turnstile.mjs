const TURNSTILE_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

export function turnstileLanguage(language) {
  return String(language ?? "").toLowerCase().startsWith("de") ? "de" : "en";
}

export function createTurnstileLoader() {
  let inFlight = null;

  return function loadTurnstile(root = globalThis.document, windowLike = globalThis.window) {
    if (windowLike?.turnstile) return Promise.resolve(windowLike.turnstile);
    if (inFlight) return inFlight;

    const pending = new Promise((resolve, reject) => {
      const script = root.createElement("script");
      script.src = TURNSTILE_SRC;
      script.async = true;
      script.defer = true;

      const fail = () => {
        script.remove();
        reject(new Error("turnstile unavailable"));
      };

      script.addEventListener(
        "load",
        () => windowLike?.turnstile ? resolve(windowLike.turnstile) : fail(),
        { once: true }
      );
      script.addEventListener("error", fail, { once: true });
      root.head.append(script);
    });

    inFlight = pending.finally(() => {
      inFlight = null;
    });
    return inFlight;
  };
}

export const loadTurnstile = createTurnstileLoader();
