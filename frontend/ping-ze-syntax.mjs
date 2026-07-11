/** Thin re-export — detect SSOT: query-mode-detect.mjs (Phase B). */
import { isPingZeSerialQuery } from "./query-mode-detect.mjs";

const MATRIX_394052_MODE = "pz";

function pingZeEffectiveMode() {
  return MATRIX_394052_MODE;
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
