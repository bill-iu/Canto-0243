/** Portable host: POST /shutdown then close tab (legacy shared/main.mjs). */

const CONFIRM_ZH =
  "\u5c07\u95dc\u9589\u672c\u6a5f\u670d\u52d9\uff0c\u672a\u5132\u5b58\u5de5\u4f5c\u5514\u6703\u907a\u5931\u3002\u78ba\u5b9a\u9000\u51fa Canto-0243\uff1f";
const CONFIRM_EN =
  "This will stop the local server. Unsaved work is already on disk. Exit Canto-0243?";
const FAIL_ZH =
  "\u7121\u6cd5\u95dc\u9589\u672c\u6a5f\u670d\u52d9\u3002\u8acb\u7a0d\u5f8c\u518d\u8a66\uff0c\u6216\u4f7f\u7528\u5de5\u4f5c\u7ba1\u7406\u54e1\u7d50\u675f pythonw.exe\u3002";
const FAIL_EN =
  "Could not stop the local server. Try again, or end pythonw.exe in Task Manager.";
const DONE_ZH =
  "Canto-0243 \u5df2\u9000\u51fa\u3002\u4f60\u53ef\u4ee5\u95dc\u9589\u6b64\u5206\u9801\u3002";
const DONE_EN = "Canto-0243 has exited. You can close this tab.";

export async function exitPortable(lang: "zh" | "en" = "zh"): Promise<void> {
  if (!window.confirm(lang === "en" ? CONFIRM_EN : CONFIRM_ZH)) return;
  try {
    const response = await fetch("/shutdown", { method: "POST" });
    if (!response.ok) throw new Error("shutdown failed");
    window.close();
    window.setTimeout(() => {
      if (document.visibilityState !== "visible") return;
      document.body.replaceChildren();
      const note = document.createElement("p");
      note.className = "portable-exit-note";
      note.textContent = lang === "en" ? DONE_EN : DONE_ZH;
      document.body.appendChild(note);
    }, 400);
  } catch {
    window.alert(lang === "en" ? FAIL_EN : FAIL_ZH);
  }
}
