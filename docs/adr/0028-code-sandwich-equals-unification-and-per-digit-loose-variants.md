# 碼夾等號查詢統一與逐位鬆檔變體

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § **碼夾等號查詢**、**0243模式**、**等號（韻／聲）**、**參考字讀音解析**。延續 [ADR-0004](0004-reference-reading-query-normalize-position-match.md)、[ADR-0014](0014-serial-phoneme-anchor-and-prefix-wildcard-equals.md)。Grill 共識（2026-07）。

現況：`23就`（`HYBRID_CODE`）、`23就=`（實際被 **串列** `{碼}{字}=` 掃描攔截，非 `HYBRID_TAIL_EQUALS_ALIAS`）、`2=我3`（framed `EQUALS`）三條執行路徑並存；**0243模式**鬆檔 `get_code_variants` 用整段 `replaceAll` + 單格翻，漏交叉組合（例：查 `39` 無 `93`）。我們決定收斂為單一 **碼夾等號** 家族，並修正鬆檔變體為**逐位獨立後組合**。

## 決定

### 1. 領域範圍（碼夾等號查詢）

- **涵蓋**：`{碼}{字}`、`{碼}{字}=`、`{碼}={字}{碼}`（例 `23就`／`23就=`、`2=我3`）。
- **Normalize（A）**：於 **`normalizeQuery` 字串層**（與全形標點、`+` 別名同級）將 `{碼}{字}` 補尾 `=` → `{碼}{字}=`；`parse_query` 只見規範形。探針：`^(\d+)([一-龥]+)$` 且全串唔含 `=`（承接舊 `HYBRID_CODE` 邊界；漢字後唔可有尾碼）。例：`23就`→`23就=`、`32就起`→`32就起=`。與 **等號（韻／聲）** `字=`／`=字` 口訣統一。
- **唔包**：**整詞等號**（`香港=`）；**串列多錨**（`04困=49倒=`，仍 ADR-0014 串列家族）。
- **廢止獨立家族**：創作者語法層唔再分 **碼字查詢**／`HYBRID_CODE`；實作層刪 `QueryKind.HYBRID_CODE`、`HYBRID_TAIL_EQUALS_ALIAS`，單錨 `{碼}{字}=` **唔再**入串列掃描。

### 2. 分派與 MatchSpec（D）

- **單一 MatchSpec 形狀**：`build_equals_match_spec` / **equals span**（`equals_span`）為 SSOT。
- **QueryKind（甲）**：**沿用 `QueryKind.EQUALS`**（整詞等號 + 碼夾等號共用）；唔新增 `code_sandwich_equals` 等 kind。創作者文案靠 **`explain`**：`spec.code_prefix` 有值 → **碼夾等號查詢**；無 → **整詞等號查詢**（`whole_word` 等 span 輔助）。
- **比對策略分叉**（同一 family，唔再三套 filter）：
  - **尾韻**（`{碼}{字}=`，`dimension=final`）：保留今日 `23就` 語意——該格**字面或同韻**；參考字韻母用 **錨點選項（union）**。
  - **內嵌聲**（`{碼}={字}{碼}`，`dimension=initial`，`phoneme_anchor_only=true`）：保留今日 `2=我3`——**等號參考讀音（pron_rank 權威）**、精確聲母比對。

### 3. 0243 碼約束（逐位 B + 全域 A）

- **碼夾等號**與**所有 0243模式鬆檔比對**：每位 0243 碼獨立套用映射變體（`3↔9` 等），再取**笛卡爾組合**；查 `39` 須含 `93`。
- **全域修 `get_code_variants`**（Python `app/utils/jyutping_codec.py`、TS `client/src/db/code-variants.ts`）：多碼字串返回逐位組合全集；**02493模式**仍無鬆檔（單碼不變）。
- **MatchSpec 表達**：碼約束以 **`code_digit` slots**（逐位）為準；`code_prefix` 僅作候選池 hint／解釋，唔再單獨驅動舊整段變體算法。
- **候選池**：`code IN (...)` 等使用修後 `get_code_variants`，與逐位 filter 一致。

### 4. 與 ADR-0014 的關係

- **串列**保留 **≥2 參考字**（`04困=49倒=`）；**單錨** `{碼}{字}=` 改歸 **碼夾等號**，不再被 `parse_serial_phoneme_anchor_query` 的 `\d[一-龥]=` 子串攔截。
- ADR-0014 G2「單參考字碼夾仍走碼夾等號」以本 ADR 為準；現行「串列誤攔 `23就=`」視為待修 bug。

## Considered Options

- **整段 `code_prefix` + 舊 `get_code_variants`**：實作簡單，但漏 `93` 等交叉組合；與「每位一音節一碼」直覺不符；**拒絕**。
- **僅碼夾等號逐位、全域 `get_code_variants` 不動**：兩套鬆檔規則並存；**拒絕**（Grill 選 **A 全域**）。
- **合併到純 equals span + 全走 pron_rank**：`字=`／`=字` 語法統一但 `飛機` 類尾韻結果會變；**拒絕**（Grill 選 **D + 尾韻 union**）。
- **保留 `HYBRID_CODE` 執行、只改 parse 別名**：QueryKind 仍分裂；**拒絕**。

## Consequences

- **行為變更（鬆檔）**：凡依賴舊整段變體集合的查詢（純數字 `39`、`23就` 候選池等）可能**新增** `93`、`69` 等碼的命中；須更新 golden queries 與 `code-variants` self-check。
- **行為收斂（分派）**：`23就` 與 `23就=` normalize 後**同一** QueryKind／spec／策略；消除 hybrid vs 串列分歧。
- **實作順序（建議）**：
  1. **P0**：`get_code_variants` 逐位笛卡爾積 + 雙端 self-check／smoke。
  2. **P1**：`normalizeQuery`（或等價層）補 `{碼}{字}` → `{碼}{字}=`；分派：單錨脫離串列；`build_equals_match_spec` + 碼夾 strategy fork。
  3. **P2**：刪 `HYBRID_CODE`／`HYBRID_TAIL_EQUALS_ALIAS`／`specHybridCode`／`filterHybridRefCandidates`；`query-explain`：`code_prefix` 有無分整詞／碼夾文案。
  4. **P3**：golden journey（`23就`、`39起`、`2=我3`、`飛機`／`飛起`）與 `test_code_sandwich_candidate_pool` 對齊碼夾等號家族。
- **Explain**：`query-explain` 唔再單靠 `whole_word` 標「整詞」；有 `code_prefix` 嘅 `32就起=` 等須出**碼夾等號**文案，唔誤標整詞等號。

## Status

`implemented`（P0–P3 已落地於 Python + PWA）

### PR-A amend（執行層：禁止以 `code_prefix` 做比對）

Grill 2026-07：在 P0–P3 之上，**所有執行／比對路徑**唔再以 `MatchSpec.code_prefix` 全碼字串驅動約束。

1. **約束 SSOT**：`mask` 內 digit + `code_digit` slots → `required_codes_from_spec`／`buildRequiredCodes`；逐格 `matches_code_positions`（`get_code_variants(單 digit)`）。
2. **Dense 候選池**：僅當每位皆有 digit 時 `dense_code_from_spec` 合成全碼，再 `get_code_variants` 笛卡爾 + `code IN (...)`（加速，語意與逐格等價）。
3. **仍可暫存 `code_prefix` 欄**：builder／explain／golden 可填；**filter／engine／equals／compound／relation seed 比對忽略**（PR-C 再停寫／刪欄）。
4. **前綴碼**（compound 短於詞碼）：前 N 格逐格鬆檔，保留 `startsWith` 等價語意。

### PR-C amend（停寫／退役 MatchSpec.code_prefix）

1. **Builders**（`query_match_spec_registry`／equals／TS 對照）**唔再寫** `MatchSpec.code_prefix`；碼約束只經 **`code_digit` slots**（`append_code_digit_slots`）。
2. **Explain／hint／golden**：用 `code_digit_string_from_spec`／`has_code_digit_constraints`（slots／mask），唔讀欄位。
3. **ParsedQuery** 仍可有 `code_prefix`（創作者輸入語法，如 `33!開心`、compound 前綴碼）——僅 parse 產物，唔再抄入 MatchSpec。
4. **欄位**：dataclass／TS interface 暫留 optional deprecated，**禁止再依賴**；PR 後新 code 唔賦值。

### Cleanup（刪 MatchSpec.code_prefix）

`MatchSpec` **已移除** `code_prefix` 欄位。碼串只由 slots／mask 還原（`code_digit_string_from_spec`）。**ParsedQuery**／compound／relation 輸入上的 `code_prefix` 仍係創作者語法欄位，唔屬 MatchSpec。