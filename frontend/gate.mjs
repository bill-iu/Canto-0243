import {
  $,
  shell,
  setAppSearchReady,
  applyAppTitle,
  REDUCED_MOTION,
  LANDING_VARIANT,
  LANDING_SESSION_KEY,
  LANDING_REVEAL_MS,
  LANDING_HANDOFF_MS,
  GATE_BRAND_INTRO_MS,
  GATE_NEAR_DONE_PCT,
  GATE_INK_CLIP_MAX,
  WARMUP_DONE_HOLD_MS,
  WARMUP_DONE_FADE_MS,
} from "./app-context.mjs";

let lastReadySnapshot = null;
let warmupDoneShown = false;
let warmupTailShown = false;
let warmupPollTimer = null;
let warmupDismissTimer = null;

function wordCacheProgress(data) {
  const wc = data?.phases?.word_cache;
  if (!wc) return 0;
  return typeof data?.word_cache_progress === "number"
    ? data.word_cache_progress
    : (wc.progress ?? 0);
}

/** Prefer server tail_progress (includes weighted word_cache — ADR-0055). */
function tailPreloadProgress(data) {
  if (typeof data?.tail_progress === "number" && Number.isFinite(data.tail_progress)) {
    return Math.max(0, Math.min(1, data.tail_progress));
  }
  const phases = data?.phases || {};
  const wc = wordCacheProgress(data);
  const sr = phases.static_resources?.progress ?? 0;
  const cs = phases.compound_syn?.progress ?? 0;
  const ca = phases.compound_ant?.progress ?? 0;
  const other = (sr + cs + ca) / 3;
  // Client-side fallback weights match server honesty
  if (phases.word_cache?.status === "ready" || phases.word_cache?.status === "failed") {
    return Math.max(wc, other);
  }
  return 0.72 * wc + 0.28 * other;
}

function formatGateStatusLabel(data, { connecting = false } = {}) {
  if (connecting || !data) return "開緊字庫…";
  if (data.degraded) return "字庫執唔切，照用得，可能慢啲";
  if (data.gate_ready) return "開得工！";
  // Pre-gate: DB probe only — no fake word_cache %
  if (data.db_ready === false) return "連緊字庫…";
  return "開緊字庫…";
}

function clearWarmupDismissTimer() {
  if (warmupDismissTimer) {
    window.clearTimeout(warmupDismissTimer);
    warmupDismissTimer = null;
  }
}

function hideWarmupBadge() {
  if (!$.warmupBadge) return;
  clearWarmupDismissTimer();
  $.warmupBadge.hidden = true;
  $.warmupBadge.classList.remove("is-done", "is-exiting");
  if ($.warmupBadgePct) $.warmupBadgePct.hidden = false;
}

function dismissWarmupBadgeWithFade() {
  if (!$.warmupBadge || $.warmupBadge.hidden) return;
  if (REDUCED_MOTION) {
    hideWarmupBadge();
    return;
  }
  $.warmupBadge.classList.add("is-exiting");
  warmupDismissTimer = window.setTimeout(() => {
    hideWarmupBadge();
    warmupDismissTimer = null;
  }, WARMUP_DONE_FADE_MS);
}

function warmupPctFromProgress(progress01) {
  return Math.max(0, Math.min(100, Math.round((progress01 || 0) * 100)));
}

function setWarmupInkProgress(progress01) {
  const w = (Math.max(0, Math.min(1, progress01)) * GATE_INK_CLIP_MAX).toFixed(1);
  if ($.warmupInkClipRect) $.warmupInkClipRect.setAttribute("width", w);
}

function setWarmupBadgeTail(progress01) {
  if (!$.warmupBadge || warmupDoneShown) return;
  warmupTailShown = true;
  const pct = warmupPctFromProgress(progress01);
  if ($.warmupBadgeLabel) $.warmupBadgeLabel.textContent = "執埋啲手尾";
  if ($.warmupBadgePct) {
    $.warmupBadgePct.textContent = `${pct}%`;
    $.warmupBadgePct.hidden = false;
  }
  setWarmupInkProgress(progress01);
  $.warmupBadge.setAttribute("aria-label", `背景預載 ${pct}%`);
  $.warmupBadge.hidden = false;
  $.warmupBadge.classList.remove("is-done");
}

function showWarmupBadgeDone() {
  if (!$.warmupBadge || warmupDoneShown || !warmupTailShown) {
    hideWarmupBadge();
    warmupDoneShown = true;
    return;
  }
  warmupDoneShown = true;
  if ($.warmupBadgeLabel) $.warmupBadgeLabel.textContent = "搞掂！";
  if ($.warmupBadgePct) $.warmupBadgePct.hidden = true;
  setWarmupInkProgress(1);
  $.warmupBadge.setAttribute("aria-label", "背景預載完成");
  $.warmupBadge.classList.add("is-done");
  $.warmupBadge.classList.remove("is-exiting");
  $.warmupBadge.hidden = false;
  clearWarmupDismissTimer();
  warmupDismissTimer = window.setTimeout(() => {
    warmupDismissTimer = null;
    dismissWarmupBadgeWithFade();
  }, WARMUP_DONE_HOLD_MS);
}

function applyWarmupBadgeFromReady(data) {
  if (!data || !shell.appSearchReady || warmupDoneShown) return;
  if (data.startup_complete) {
    if (warmupTailShown) showWarmupBadgeDone();
    else hideWarmupBadge();
    stopWarmupBadgePoll();
    return;
  }
  setWarmupBadgeTail(tailPreloadProgress(data));
}

async function syncWarmupBadgeAfterSearchVisible() {
  if (!$.warmupBadge) return;
  try {
    const res = await fetch("/ready", { cache: "no-store" });
    if (!res.ok) {
      hideWarmupBadge();
      return;
    }
    const data = await res.json();
    if (data.startup_complete) {
      hideWarmupBadge();
      return;
    }
    setWarmupBadgeTail(tailPreloadProgress(data));
    startWarmupBadgePoll();
  } catch {
    hideWarmupBadge();
  }
}

function stopWarmupBadgePoll() {
  if (warmupPollTimer) {
    window.clearInterval(warmupPollTimer);
    warmupPollTimer = null;
  }
}

function startWarmupBadgePoll() {
  if (warmupPollTimer) return;
  warmupPollTimer = window.setInterval(async () => {
    if (warmupDoneShown) {
      stopWarmupBadgePoll();
      return;
    }
    try {
      const res = await fetch("/ready", { cache: "no-store" });
      if (!res.ok) return;
      applyWarmupBadgeFromReady(await res.json());
      if (warmupDoneShown) stopWarmupBadgePoll();
    } catch {
      /* retry */
    }
  }, 400);
}

function setGateInkProgress(progress01) {
  const p = Math.max(0, Math.min(1, progress01));
  // Gate logo may use cropped viewBox (e.g. 148); don't force full 200 wordmark frame
  if ($.gateInkClipRect) {
    const svg = $.gateInkClipRect.ownerSVGElement;
    const max =
      (svg && (Number(svg.viewBox?.baseVal?.width) || Number(svg.getAttribute("width")))) ||
      GATE_INK_CLIP_MAX;
    $.gateInkClipRect.setAttribute("width", (p * max).toFixed(1));
  }
  if ($.gateInkClipRectMini) {
    $.gateInkClipRectMini.setAttribute(
      "width",
      (p * GATE_INK_CLIP_MAX).toFixed(1),
    );
  }
}

function shouldPlayLanding() {
  return !sessionStorage.getItem(LANDING_SESSION_KEY) && !REDUCED_MOTION;
}

function markLandingDone() {
  sessionStorage.setItem(LANDING_SESSION_KEY, "1");
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function awaitGateBrandBeat(playLanding) {
  if (!playLanding) return;
  try {
    if (document.fonts && document.fonts.ready) {
      await Promise.race([document.fonts.ready, sleep(2400)]);
    }
  } catch {
    /* use timeout fallback below */
  }
  if (!document.documentElement.classList.contains("fonts-ready")) {
    document.documentElement.classList.add("fonts-ready");
    window.__gateBrandShownAt = performance.now();
  }
  const shownAt = window.__gateBrandShownAt ?? performance.now();
  const remain = GATE_BRAND_INTRO_MS - (performance.now() - shownAt);
  if (remain > 0) await sleep(remain);
}

function setSearchControlsEnabled(enabled) {
  $.searchInput.disabled = !enabled;
  $.searchBtn.disabled = !enabled || shell.isSearching;
  if ($.shuffleBtn) $.shuffleBtn.disabled = !enabled;
}

async function revealFromGate({ playLanding }) {
  // 就緒閘解鎖：與 PWA 共用 ready-gate.css 的 shell 露出 class（唔用 pwa- 前綴）
  document.documentElement.classList.add("shell-revealed");
  document.body.classList.remove("landing-a-pending", "landing-b-pending");
  if (playLanding) {
    markLandingDone();
    if (LANDING_VARIANT === "b") {
      $.preloadOverlay.classList.add("is-handoff");
      $.appShell?.classList.remove("is-gated");
      $.appShell?.classList.add("is-revealing", "landing-b-revealed");
      $.searchForm?.classList.add("is-landing-in");
      await sleep(LANDING_HANDOFF_MS);
      $.preloadOverlay.classList.add("is-exiting");
      await sleep(280);
    } else {
      $.preloadOverlay.classList.add("is-exiting");
      $.appShell?.classList.remove("is-gated");
      $.appShell?.classList.add("is-revealing");
      await sleep(LANDING_REVEAL_MS);
    }
  }
  $.preloadOverlay.classList.add("is-hidden");
  $.preloadOverlay.classList.remove("is-exiting", "is-handoff");
  $.preloadOverlay.setAttribute("aria-busy", "false");
  setAppSearchReady(true);
  setSearchControlsEnabled(true);
  if (playLanding && !REDUCED_MOTION) {
    await sleep(80);
  }
  $.searchInput.focus({ preventScroll: true });
}

async function waitForPreloadReady() {
  const playLanding = shouldPlayLanding();
  setSearchControlsEnabled(false);
  hideWarmupBadge();
  lastReadySnapshot = null;
  if (playLanding) {
    $.appShell?.classList.add("is-gated");
    document.body.classList.add(`landing-${LANDING_VARIANT}-pending`);
  } else {
    $.preloadOverlay.classList.add("preload-overlay--minimal");
  }
  while (true) {
    try {
      const res = await fetch("/ready", { cache: "no-store" });
      if (!res.ok) throw new Error(`ready ${res.status}`);
      const data = await res.json();
      lastReadySnapshot = data;
      if (typeof data.portable === "boolean") {
        applyAppTitle(data.portable);
      }
      if (data.gate_ready) {
        setGateInkProgress(1);
        $.preloadLabel.textContent = formatGateStatusLabel(data);
        $.preloadOverlay.classList.toggle("is-degraded", Boolean(data.degraded));
        await awaitGateBrandBeat(playLanding);
        await revealFromGate({ playLanding });
        await syncWarmupBadgeAfterSearchVisible();
        return;
      }
      // Short gate: indeterminate-ish ink until DB probe passes
      setGateInkProgress(data.db_ready ? 0.85 : 0.2);
      $.preloadLabel.textContent = formatGateStatusLabel(data);
    } catch {
      if (lastReadySnapshot) {
        setGateInkProgress(lastReadySnapshot.db_ready ? 0.85 : 0.2);
        $.preloadLabel.textContent = formatGateStatusLabel(lastReadySnapshot);
      } else {
        $.preloadLabel.textContent = formatGateStatusLabel(null, { connecting: true });
      }
    }
    await sleep(220);
  }
}

export {
  setGateInkProgress,
  waitForPreloadReady,
  wordCacheProgress,
};
