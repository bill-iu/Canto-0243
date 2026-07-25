/** Portable host: POST /shutdown then close tab (Desktop keep-alive menu path). */
import { getPortableExitCopy } from '../../shared/portable-exit-i18n.mjs';

export async function exitPortable(lang: "zh" | "zh-Hans" | "en" = "zh"): Promise<void> {
  const copy = getPortableExitCopy(lang);
  if (!window.confirm(copy.confirm)) return;
  try {
    const response = await fetch("/shutdown", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delay_ms: 0 }),
    });
    if (!response.ok) throw new Error("shutdown failed");
    window.close();
    window.setTimeout(() => {
      if (document.visibilityState !== "visible") return;
      document.body.replaceChildren();
      const note = document.createElement("p");
      note.className = "portable-exit-note";
      note.textContent = copy.done;
      document.body.appendChild(note);
    }, 400);
  } catch {
    window.alert(copy.fail);
  }
}
