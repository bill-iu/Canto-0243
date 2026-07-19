# 五批 Essay top-N 全體抽樣審核

**Date:** 2026-07-19  
**Seed:** 99  
**Threshold:** (OK+SOFT)/n ≥ 0.90  
**Universe:** 五批 formal 晉升（`u-inlex-nf2k`…`nf5`），共 ~9704 條  
**Sample:** 每批 min(n, max(50, ⌈5%⌉)) → **合計 486**

## 總成績

| verdict | n | % |
|---------|--:|---:|
| OK | 461 | 94.9% |
| SOFT | 9 | 1.9% |
| BAD | 16 | 3.3% |
| **total** | **486** | 100% |

**ok_rate = 470/486 = 0.9671**

**PASS**（≥ 0.90）

## 分批

| batch | sample | OK | SOFT | BAD | ok_rate | 初閘 | 本輪 |
|-------|-------:|---:|-----:|----:|--------:|------|------|
| nf2k | 100 | 93 | 2 | 5 | **0.95** | 0.98 | re-audit |
| nf2b | 100 | 95 | 2 | 3 | **0.97** | 0.99 | re-audit |
| nf3 | 100 | 97 | 2 | 1 | **0.99** | 1.00 | re-audit |
| nf4 | 100 | 97 | 1 | 2 | **0.98** | 0.99 | re-audit |
| nf5 | 86 | 79 | 2 | 5 | **0.942** | 1.00 | re-audit |

各批均 **≥ 0.90**。

## BAD 修正（16，已 apply）

| batch | literal | was | fix_pos | 摘要 |
|-------|---------|-----|---------|------|
| nf2k | 個別 | a,n,r | a,r | n 假陽 |
| nf2k | 倒後 | n,r,v | r | 粵副 |
| nf2k | 嘩嘩 | a,r,x | r,x | a 假陽 |
| nf2k | 見點 | v | r | 粵「差點」 |
| nf2k | 飲得 | v | **u** | V+得殘片 → fragment |
| nf2b | 乜料 | n,x | n | x 假陽 |
| nf2b | 援手 | n,v | n | v 假陽 |
| nf2b | 由來已久 | a,r | a | r 假陽 |
| nf3 | 隨時歡迎 | a,v | v | a 假陽 |
| nf4 | 大有文章 | a,n | a | n 假陽 |
| nf4 | 音訊全無 | a,v | a | v 假陽 |
| nf5 | 一枕黃粱 | n,v | n | v 假陽 |
| nf5 | 久病成醫 | a,x | v | 謂語成語 |
| nf5 | 互有勝負 | a,v | v | a 假陽 |
| nf5 | 同工異曲 | a,n | a | n 假陽 |
| nf5 | 白日見鬼 | v,x | v | x 假陽 |

## 覆蓋（修後）

| metric | value |
|--------|------:|
| formal/all | ~0.999 |
| formal/(all−fragment) | **1.0** |
| SSOT `u` | 26（全 fragment） |

## 檔案

- `full_sample.tsv` / `full_sample.meta.json`
- `audit_part1..5.tsv` + `*_summary.md`
- 本報告

## 結論

五批 Essay 戰役抽樣品質 **穩定 >90%**（全體 96.7%）。主要錯誤類型：多標假陽（a/n/v 亂加）、粵語副詞標成 v、少數殘片誤 formal。已全部修入 SSOT。
