# P1 audit — stratum `low|u` (pos=u undetermined)

**Sample:** `data/pos/audit/p1_sample_low_u.tsv`  
**Universe:** 2962 · **Sample n:** 149 · seed 20260718  
**Question:** Is `u` (未定) justified, or is there a clear formal POS?

POS codes: `n` 名 · `v` 動 · `a` 形 · `r` 副 · `x` 虛 · `u` 未定（可多標）

## Counts

| verdict | n | share | meaning |
|---------|---|-------|---------|
| OK | 14 | 9.4% | truly hard / rare / multi-class unclear → `u` correct |
| SOFT | 15 | 10.1% | borderline; `u` acceptable |
| BAD | 120 | 80.5% | clear POS exists → `fix_pos` set |
| **ok_rate (OK+SOFT)** | **29/149** | **0.1946** | `u`-justified rate |

**Note:** Low ok_rate is expected and useful for this stratum: `no-source;fallback` mass-`u` is mostly **under-tagging**, not true indeterminacy. Soft counts as acceptable for gate-rate (`project_pos_audit apply`).

## Verdict policy (this pass)

- **OK:** tokenization fragments / multi-token glue (e.g. 你在、是個、都很); rare/opaque (住部、依句、林布); not a coherent POS unit.
- **SOFT:** high multi-class monosyllables or fixed dual use where primary set is debatable (可、安、著、約、部、晒…); `u` still OK until multi-tag review.
- **BAD:** clear one or few formal classes → fill `fix_pos` (comma-sorted `a,n,r,v,x`); leave family/voice empty unless needed.

## BAD by fix_pos family (primary patterns)

| fix_pos | count (approx) | examples |
|---------|----------------|----------|
| `n` | many | 下身、傻妹、功夫、功課、卡通片、大師、女子、床、殭屍、熊仔、舖頭、麪… |
| `v` | many | 不敢、中意、出嚟、到手、大嗌、失戀、成爲、打人、換衫、收埋、識、識得、行路… |
| `a` | many | 單純、大膽、奇、好奇、心急、慢、淡、淺、熱、熱鬧、老土、聰明、自私… |
| `r` | several | 不禁、愈來愈、成晚、梗係、正在、的確、真係、而家、遲早… |
| `x` | several | 一群、之內、乎、依間、哼、噼、某、者、邊個、我度… |
| multi (`a,r` / `a,v` / `n,v` / `r,v` / `n,x` / …) | several | 主要、出名、好象、得閒、施工、突破、紅、組、迅速、這裡… |

### High-confidence easy BADs (clear single class)

專名／實體：嵐嵐、阿南、阿嘉、小雪、幼稚園、礦場、插件、符紙、班長、爽身粉  
粵語常用：出嚟、屋企人、得閒、是但、梗係、真係、而家、邊個、新抱、舖頭、老土、睇見、等陣、收埋  
書面常用：不禁、正在、的確、愈來愈、遲早、聰明、自私、突破、施工

### OK (u justified) — 14

| literal | reason |
|---------|--------|
| 也能 | 副+能願截斷 |
| 住部 | 疑截斷／罕 |
| 你在 | 人稱+在截斷 |
| 依句 | 罕／不明 |
| 我怕 | 主+動截斷 |
| 我攬 | 主+動截斷 |
| 是個 | 係+量截斷 |
| 有了 | 動+助截斷 |
| 林布 | 罕／疑專名 |
| 歲的 | 碎片 |
| 的事 | 的+事截斷 |
| 知有 | 截斷 |
| 都很 | 副連用截斷 |
| 都能 | 副+能截斷 |

### SOFT (u acceptable) — 15

一摸、也是、共、可、單、埋個、安、就在、應、晒、約、著、部、陳、魔風

## Implications

1. **P1 `low|u` is mostly recoverable:** ~80% of sample has an obvious formal tag; fallback `u` should not be treated as stable SSOT for these heads.
2. **Fragment noise:** ~9% OK are multi-char glue from Essay/segmenter boundaries — keep `u` or drop from gate body later; do not invent POS.
3. **Apply path:** when ready,  
   `python -m ingest.project_pos_audit apply --verdicts data/pos/audit/p1_sample_low_u.tsv --dry-run`  
   then without `--dry-run` to upsert BAD rows (`fix_pos` → SSOT with `p1-audit;review`). Soft/OK left as `u`.
4. **Not applied this pass** — audit-only; no SSOT/carrier write.

## Files

| path | role |
|------|------|
| `data/pos/audit/p1_sample_low_u.tsv` | filled verdicts |
| `data/pos/audit/p1_audit_low_u_summary.md` | this summary |
| `data/pos/audit/p1_sample.meta.json` | sample meta (universe 2962, n=149) |
