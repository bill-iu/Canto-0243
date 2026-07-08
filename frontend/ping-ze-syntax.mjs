/** ponytail: keep in sync with app/services/ping_zak.py */

const SLOT_RE = /^[PZ0-9]+$/i;
const HAS_PZ = /[PZ]/i;

const MATRIX_394052_MODE = "m3";

function isPingZeSerialQuery(q) {
  const n = (q || "").trim();
  if (!n || !HAS_PZ.test(n)) return false;
  return SLOT_RE.test(n);
}

function pingZeEffectiveMode() {
  return MATRIX_394052_MODE || "m2";
}

/** @param {'zh' | 'en'} [lang] */
function pingZeModeRedirectHint(lang = "zh") {
  if (MATRIX_394052_MODE && pingZeEffectiveMode() === MATRIX_394052_MODE) {
    return null;
  }
  if (lang === "en") {
    return "Ping–ze serial query switched to 02493 Mode (Strict)";
  }
  return "平仄串列查詢已切換至 02493模式（緊）";
}

export { MATRIX_394052_MODE, isPingZeSerialQuery, pingZeEffectiveMode, pingZeModeRedirectHint };