import { $ } from "./app-context.mjs";

function relationPayloadFromForm() {
  const data = new FormData($.relationForm);
  return {
    seed_char: String(data.get("seed_char") || "").trim(),
    opposite_char: String(data.get("opposite_char") || "").trim(),
    relation_type: String(data.get("relation_type") || "syn"),
  };
}

function applyRelationForm(relation) {
  if (!$.seedChar || !$.oppositeChar) return;
  $.seedChar.value = relation.seed_char || "";
  $.oppositeChar.value = relation.opposite_char || "";
  const type = relation.relation_type === "ant" ? "ant" : "syn";
  $.relationForm.querySelectorAll('input[name="relation_type"]').forEach((input) => {
    input.checked = input.value === type;
  });
}

function showRelationOk(text) {
  $.relationOkStatus.textContent = text;
  $.relationOkStatus.hidden = false;
  $.relationErrStatus.hidden = true;
}

function showRelationErr(text) {
  $.relationErrStatus.textContent = text;
  $.relationErrStatus.hidden = false;
  $.relationOkStatus.hidden = true;
}

async function postRelation(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  return { response, body };
}
