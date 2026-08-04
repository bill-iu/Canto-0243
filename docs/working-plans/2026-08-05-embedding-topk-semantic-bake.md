# 語意向量鄰居烘焙（bge-m3 top-K）— grill 決策稿

> 狀態：**v1 bake 已跑通**（A+C + 強制 GPU + S4 + T2）  
> 日期：2026-08-05  
> 領域詞：CONTEXT.md § **語意向量鄰居烘焙**、**語意鄰居 GPU 烘焙**、**語意相關**

## 已拍板

| # | 決策 | 說明 |
|---|---|---|
| Q1 | **A+C** | **A**：release 只 bake **語意相關**（`semantic_related` + `source=embedding_cosine`，rank=60）。**C**：全庫提案 TSV（可升 project_syn；**唔**自動 ant）。 |
| Q2 | **強制 GPU** | encode 必須 CUDA EP；無 CUDA → fail-closed。 |
| Q3 | **Runtime 零模型** | Desktop／PWA 只讀表。 |
| Q4 | **唔 bake 全庫向量入交貨庫** | sidecar：`.cache/embedding_topk/vectors_bge-m3.npz`（gitignore）。 |
| Q5 | **模型** | `F:\localAI\data\models\bge-m3-onnx`（1024-d）。 |
| Q6 | **範圍 S4** | Encode／C＝全 DISTINCT；**A 只寫直連 syn 度數 &lt; T**。 |
| Q7 | **T2 閾值** | T=5；A K′=10；A cosine≥0.50；C K=20（無 floor）。 |

## 實測結果（2026-08-05 本機 RTX 2080）

| 步驟 | 結果 |
|---|---|
| GPU encode 全庫 166058 | ~233s（~714 texts/s batch64；首次） |
| faiss IndexFlatIP top-K=20 | **117s**（CPU faiss） |
| C 提案 TSV | **3,321,160** 資料行 → `.cache/embedding_topk/embedding_syn_topk_proposals.tsv` |
| A 合格頭 | **135,622**（degree&lt;5） |
| A 入庫邊 | **1,129,483** `semantic_related`／`embedding_cosine` |
| lyrics.db | ~40MB → **~212MB**（本機產物；**唔**入 git） |
| integrity_check | ok |
| 抽樣「開心」embedding 鄰 | 開心顏／戥你開心／快樂幸福…；syn 仍以 cilin 等為前 |

## 命令（主理機）

```bash
# 專用 venv（gitignore）：.venv-embed-bake
# 一律 env -u PYTHONPATH

# 首次（GPU encode + top-K + A/C）
env -u PYTHONPATH PYTHONUNBUFFERED=1 .venv-embed-bake/Scripts/python.exe -m ingest bake-embedding-topk

# 向量已有：只重算 top-K／A／C
env -u PYTHONPATH PYTHONUNBUFFERED=1 .venv-embed-bake/Scripts/python.exe -m ingest bake-embedding-topk --skip-encode
```

重建 venv：

```bash
env -u PYTHONPATH python -m venv .venv-embed-bake
env -u PYTHONPATH .venv-embed-bake/Scripts/python.exe -m pip install \
  "onnxruntime-gpu[cuda,cudnn]==1.28.0" "numpy>=2" "tokenizers>=0.15" faiss-cpu -r requirements.txt
```

**PITFALL**：勿並行多個 bake（搶 `lyrics.db`）；`PYTHONPATH` 會串 Hermes venv。

## 產物契約

### A — release 邊
- `relation_type=semantic_related`，`source=embedding_cosine`，`score=cosine`
- 僅 head 直連 syn 度數 &lt; 5；每頭最多 10 邊且 score≥0.50
- 無向 canonical；`INSERT OR IGNORE`

### C — 提案 TSV（預設唔入 git）
- `.cache/embedding_topk/embedding_syn_topk_proposals.tsv`
- 欄位：`head tail score rank model_version`

### Sidecar
- `.cache/embedding_topk/vectors_bge-m3.npz`（chars + matrix float32）

## 明確不做
- cosine → ant；runtime 載 bge；交貨庫存全庫向量；CPU 正式 bake；C 無審灌 A

## 後續可選
- 近義橋模型 MiniLM → bge-m3
- 從 C TSV 抽樣 campaign 升 project_syn
- PWA 關係分包體積／gzip 策略（db ~200MB 級）
- bulk insert 進度 log
