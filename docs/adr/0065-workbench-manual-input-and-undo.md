# ADR-0065: Workbench manual slot/span input + undo placement

創作者除鎖定＋候選外，需要直接手改句面；既有單層 `draft.undo` 已覆蓋套用／放寬，但復原掣藏在候選區底部，手改亦未入 undo。

## Decision

1. **單擊**＝鎖定／解鎖（標定替換段）；**雙擊**（或焦點格 Enter／F2）＝單格手改。
2. 單格：只收**一個漢字**或**一位 `0–9`**；Enter／blur 確認，Esc 取消；空／非法不改。
3. **段手打**：句格畫布右上角 **✎** 展開（無鎖定不可點；唔進條件列）；規則同工作台起句；長度＝段寬；確認後 resolve 讀音／碼並推 undo。
4. 本階段手改**唔收 `?`**（通配仍走指定碼）。
5. **句稿復原**掣移入「本次替換條件」；覆蓋套用候選、確認放寬、段手打、單格手改；**唔**為鎖定切換或只改讀音寫 undo。

## Considered

| Option | Result |
|--------|--------|
| 手改放進條件列 | Rejected — 條件唔改句面 |
| 單擊即編輯 | Rejected — 與標定衝突 |
| 新手打也收 `?` | Deferred — 下期；指定碼已有通配 |
| 新建多層 undo | Rejected — 強化既有單層 |

## Consequences

- `line-draft` 加 `set_slot_manual`／`apply_span_input`；`LastApplied.kind` 含 `manual`。
- CONTEXT：**字位鎖定**／**替換段**／**句稿復原**。
- Self-check 覆蓋手改＋條件列復原掣位置。
