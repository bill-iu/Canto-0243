# alias_proposals 人手審核 r1

**Source:** `data/pos/alias_proposals.tsv`（`project_pos_alias propose`，n=64）  
**Policy:** A2+A4 — 機器提案、人手入帳；寧漏勿錯（ADR-0060）  
**Date:** 2026-07-19  

## 結論

| 判決 | n |
|------|--:|
| **ACCEPT 新 alias** | **1**（`侏→侏儒`） |
| REJECT（自由語素／假殘字） | 63 |
| 既有 alias（本輪未重提） | 6（曱甴／蘿蔔／骷髏） |

**唔接受** 全部 score=1.0 自動對：`優→優雅`、`功→功夫`、`創→創造`、`維→維護`、`悲→悲劇`… — 單字皆有獨立用法，alias 會毒自由語素。

## ACCEPT

| source | target | reason |
|--------|--------|--------|
| 侏 | 侏儒 | 罕單用；opaque 種子；完整詞補 `n` 後主表刪 `侏` |

**REJECT** `儒→侏儒`：`儒` 自由語素（儒家等）。

## 既有權威 alias（不變）

`曱/甴→曱甴` · `蘿/蔔→蘿蔔` · `骷/髏→骷髏`

## 跟進

- 真殘字靠白名單 + 偶爾人手加行；auto-pair 只作噪音雷達  
- 下輪若見 `尷/尬`、`蟑/螂` 等 bound pair 再入帳  
