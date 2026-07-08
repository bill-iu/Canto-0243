/** ponytail: keep in sync with app/services/ping_zak.is_ping_ze_serial_query */

const SLOT_RE = /^[PZ0-9]+$/i;
const HAS_PZ = /[PZ]/i;

export function isPingZeSerialQuery(q) {
  const n = (q || "").trim();
  if (!n || !HAS_PZ.test(n)) return false;
  return SLOT_RE.test(n);
}

/** @param {'zh' | 'en'} [lang] */
export function pingZeModeRedirectHint(lang = "zh") {
  if (lang === "en") {
    return "Ping–ze serial query switched to 02493 Mode (Strict)";
  }
  return "平仄串列查詢已切換至 02493模式（緊）";
}