# Canto-0243

<p align="center">
  <a href="../README.md">繁體中文</a> · <b>简体中文</b> · <a href="README.en.md">English</a>
</p>

填写粤语歌词时，常见困难一是不知道有哪些字可用，二是需要在**同音、押韵、近义**之间快速换字，同时又要符合 0243 与粤拼读音。传统做法是在词典、韵书、近义表之间反复查阅，手动尝试「这一位置能否换成另一个字」——效率低，且容易遗漏许多可用字。[0243.hk](https://0243.hk) 已是近年来较好用的粤语填词检索网站，但偶尔会出现 502 Bad Gateway 无法访问；检索时也可能长时间加载；或缺少所需功能——这些情况都会拖慢创作进度。

**Canto-0243**（**ONE·揾·韵**）是由多种 AI Agent 协助开发的离线粤语填词检索工作台：依据 **0243／02493 数字码**、**粤拼**、**韵母／声母规则**与 **近义／反义关系**，在数秒内列出可替换的**词条**。输入 `23就` 可查找同调且与「就」押韵的尾字；输入 `香港=` 可查找与「香港」押韵的候选词；输入 `~开心` 或切换**近反义模式**可查找近义／反义词；输入 `~~`／`!!` 可查找填词常用的二字近义／反义复合词。套件解压即可使用，词库与近反义资料均存于本地，无需常驻云端。

**授权**：程序代码依 [Canto-0243 License](../LICENSE)（CC BY-NC-SA 4.0 + 附加条款；**非 OSI 开源**）。第三方资料见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。  
**技术栈**：FastAPI · SQLAlchemy · SQLite（离线单机）· 纯 HTML/JS 前端  
**领域词汇**：见 [`CONTEXT.md`](../CONTEXT.md) · 贡献指南 [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## 最新版本

<!-- words-count:zh-Hans -->
目前总词条列数：**193,278**（`lyrics.db` · `words` 表）
<!-- /words-count:zh-Hans -->

官方离线资料包：**[Canto-0243 v1.4.0](https://github.com/bill-iu/Canto-0243/releases/tag/v1.4.0)**（`canto-0243-portable.zip`、macOS `tar.gz`、`lyrics.db`、`words-lexicon.json`）。问题与建议欢迎提交 [GitHub Issues](https://github.com/ICE-U-code/Canto-0243/issues)。

---

## 功能

* **0243／02493 编码搜索**：**0243模式** `mode=m1`（0243 等价变体）与 **02493模式** `mode=m2`（含 9 键声调、区分二声）。
* **多种查询语法**：纯汉字 · 纯数字（分页 + 总数 header）· **粤拼查询**（`syut`／`nei hou`／`ming4 baak6`）· **粤拼锚**（`?yut?`、`23o`、`3hon4` 等粤拼锚，见速查）· 混合码字（`23就`）· wildcard（`3_`、`23?`）· 等号韵／声（`香港=`、`2=我3`）· 韵／声锚（`?就=`、`?港=?`）。
* **近反义**：**近反义模式** `mode=syn` 全栏 UI（不接受粤拼）；或在 0243搜索模式下 `~词`／`!词`、反义复合 `!!`、近义复合 `~~`。
* **词库与收录**：**词库埠** raw lookup + **收录决策**；多字词级标音或音节拼接读音。
* **近反义资料**：**静态词林埠**（cilin／国语辞典近义／反义语料）；运行时与 ingest 共用同一规则。
* **结果排序**：同一 match tier 内 **纯汉字** → **essay 词频** → **curated** → **pron_rank** → 字面（详见 [`CONTEXT.md`](../CONTEXT.md) § 搜索结果排序）。

---

## 快速开始

### 1. 下载与安装（一般用户）

完整离线体验请用官方 portable 套件，**无需** clone 源码或自行导入词库。

1. 从 [GitHub Releases](https://github.com/ICE-U-code/Canto-0243/releases) 下载 **`canto-0243-portable.zip`**（建议对照 [`Canto-0243 v1.4.0`](https://github.com/bill-iu/Canto-0243/releases/tag/v1.4.0)）。
2. 解压缩整个文件夹（例如 `canto-0243-portable`）。
3. 按平台启动：
   * **Windows**：解压后双击 **`START.bat`**（无需安装 Python）。
   * **macOS**：下载 `canto-0243-portable-macos.tar.gz`，解压后双击 **`Canto-0243.app`**。
   * **Linux**：`chmod +x START.sh && ./START.sh`（须本机 Python 3.10+）。

**环境要求**：Windows／macOS **免安装**（套件已内建 Python）；Linux 仍须 Python 3.10+。

| 入口 | URL |
|------|-----|
| 前端（搜索教学位于顶栏） | http://127.0.0.1:8000/frontend/index.html |
| API 文档 | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |

套件内已含 `lyrics.db` 与静态近反义资料。疑难排解见解压后文件夹内 `README.txt`。

### 2. 如何使用

**三种模式**（顶栏 segmented control）：

| 模式 | `mode` | 用途 |
|------|--------|------|
| **0243模式**（松） | `m1` | 0243 码等价变体 |
| **02493模式**（紧） | `m2` | 02493 码，区分二声 |
| **近反义** | `syn` | 输入汉字列出近义／反义栏（不接受粤拼） |

**语法族**（皆可在 **0243搜索模式** 使用，除非另有说明）：

* **字面／数字／粤拼**：直接输入「你好」、`23`、`nei hou`。
* **位置与通配符**：`香??`、`?你?`、`3_`、`23?`。
* **数字 + 尾字**：`23就`（尾字与「就」押韵）、`23@就`（尾字字面固定）、`23*就`（延长位置约束）。
* **等号锚点**：`=` 在锚字**后**比较韵母（`?就=`）、在锚字**前**比较声母（`?=就`）；整词与「香港」押韵 `香港=`、码夹 `2我=3`。
* **粤拼锚**：缺字查询内用粤拼取代汉字参考字（`?syut?` 中格音节、`23o` 码后**末格**韵母、`3hon4` 首格音节等）；**并非**整段粤拼查询；**近反义模式**不接受。
* **近反义关系查询**：`~开心`、`!你`、`33!开心`。
* **反义复合词**：`!!`、`33!!`、`!!你`、`33!!你`（如生死、是非）。
* **近义复合词**：`~~`、`33~~`、`~~你`、`33~~你`（如朋友、恐惧）；**不适用近反义模式**。

应用内 **「搜索教学」** 提供完整可点击示例；下方「查询语法速查」与教学页一致，供离线查阅。

### 3. 从 Git clone（开发者）

clone 所得源码**不包含**完整 `lyrics.db`。若要在本机运行 `python main.py`，请先从 Releases 下载 `lyrics.db` 置于项目根目录，或按下方 Maintainer 流程自行构建。

```bash
pip install -r requirements.txt
python main.py
```

亦可使用 `./start.sh`（创建 venv 并打开浏览器；仍需自备 `lyrics.db`）。

**随仓库提供**（第 1 层，见「资料来源」）：essay 词频、curated 常用词、反义／近义复合列表，以及 bundled 近反义 静态文件。**单字 rime `char.csv` 与 antisem 不在 git 中**——clone 后请先执行 `python scripts/bootstrap_data.py`（第 2 层）。

---

## Maintainer：重建词条库与近反义

产物均为本地／gitignore 文件，**请勿** commit。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
pip install -r requirements-dev.txt
python scripts/bootstrap_data.py
# 1. 自上游词表整理多字词级标音（见 THIRD_PARTY_NOTICES § 多字词级标音）
# 2. 导入 words 表（会同步更新 README 词条列数）：
python scripts/ingest/import_data.py
# 3. 近反义 ingest：
python -m ingest report
python -m ingest normalize --source current_static
python -m ingest build-relations
```

可选近反义来源（默认关闭）见 `data/syn_ant/sources.yaml`。

### 官方资料 Release（四件套）

再分发前核对 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。**勿**将大文件 commit 至 git。  
**全量发布**与**词库发布**分层、手动／CI checklist 见 [release.md](release.md)（[ADR-0008](adr/0008-release-publishing-tiers.md)）。

| 资产 | 用途 |
|------|------|
| `lyrics.db` | 完整**词条库**（`words` + `word_relations`） |
| `canto-0243-portable.zip` | Windows 免安装套件（内建 venv + `START.bat`） |
| `canto-0243-portable-macos.tar.gz` | macOS 免安装 **`Canto-0243.app`** |
| `words-lexicon.json` | **词级标音**附件 |

```bash
python scripts/export_words_lexicon.py -o dist/words-lexicon.json
python scripts/update_readme_words_count.py
# Windows（含内建 venv zip）:
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
# macOS（含 Canto-0243.app tar.gz）:
bash scripts/build-portable.sh
# 上传四件套至 GitHub Release
```

---

## 查询语法速查

与前端「搜索教学」可点击例子一致。

### 基本查询

| 输入示例 | 说明 |
|----------|------|
| `就` | 查询该字的所有读音 |
| `你好` | 查询该词语 |
| `syut` | 粤拼查询（无声调） |
| `nei hou` | 粤拼查询（无声调） |
| `ming4 baak6` | 粤拼查询（有声调） |

### 0243／02493 数字

| 输入示例 | 说明 | 模式 |
|----------|------|------|
| `23` | 找同音字 | 0243模式 |
| `93` | 02493 增加数字 9 | 02493模式 |

**标点等价**（查询分派自动正规化）：全形 `？` 与 `?` 等价；全形 `～`／`！` 与 `~`／`!` 等价；`~~`／`!!` 与 `～～`／`！！` 及混合写法（如 `~～`）等价。

### 缺字／音查询（遮罩）

| 输入示例 | 说明 |
|----------|------|
| `香??` | 三字词，首字为「香」 |
| `?你?` | 三字词，中间字为「你」 |
| `_识_` | 三字词，中间字为「识」 |
| `3_` | 二字：首字和 3 同音，尾字不限 |
| `23?` | 三字：前两字 23 同音，第三个字不限 |
| `门0` | 二字：首字字面「门」＋尾格码 0 |

### 星号锚（`*`）— 指定某一格的「字面／同韵／同声」

用 `*` 把「码」和「锚字」连接起来。**`=` 永远紧贴锚字后面**，表示该格和锚字**同韵母**；没有 `=` 则表示该格**字面固定**为锚字。`*=`（锚字在右侧）表示该格和锚字**同声母**（旧语法保留）。

**三种形状，一眼看出格位：**

- **尾格**：`{code}*{汉字}{可选 '='}` / `{code}*= {汉字}`  
  例：`23*好`、`23*好=`、`23*=好`
- **中格**：`{左码}*{汉字}{可选 '='}{右码}`  
  例：`2*好3`（中格字面「好」）、`2*好=3`（中格与「好」押韵母）
- **头格**：`*{汉字}{可选 '='}{右码}`  
  例：`*门0`（首字字面「门」）、`*门=0`（首字与「门」押韵母）

> `门0` 仍可用，但属 **deprecated** alias；新教学请用 `*门0`。

（补充）同韵／同声也可用 `=` 语法：`香=?`、`?就=`、`=香?`、`?=就`。

### 粤拼锚

缺字查询家族内以粤拼标读音约束，**不是**整段粤拼查询（`syut` 查词 ≠ `?syut?` 锚中格）。**近反义模式**不支援粤拼锚；无效韵母片段会拒绝并提示。

**通配符位置**

| 输入示例 | 说明 |
|----------|------|
| `?港=?` | 三字，**中格**与「港」押韵（三格韵锚） |
| `?yut?` | 三字，**中格**韵母片段 `yut` |
| `?syut?` | 三字，**中格**完整音节 `syut` |
| `?hon` | 二字，**末格**完整音节 `hon` |

**码 + 粤拼**

| 输入示例 | 说明 |
|----------|------|
| `3hon4` | 二字，码 `34`，**首格**完整音节 `hon` |
| `3?hon4` | 三字，`{首码}?{音节}{末码}`，中格音节 |
| `3h4` | 二字，码 `34`，**首格**声母 `h` |
| `23ngo` | 二字，码 `23`，**末格**完整音节 `ngo` |
| `23o` | 二字，码 `23`，**末格**韵母 `o`（比 `23ngo` 阔） |
| `23ei0` | 三字，码 `230`，**中格**韵母 `ei`（同 `23你=0` 类） |

`3hon4` 音节在**首格**；`23ngo`／`23o` 粤拼在码后、锚**末格**——两者格式不同，勿混。

### 右 `=` 查韵母（整词／码夹）

| 输入示例 | 说明 |
|----------|------|
| `香港=` | 二字，整词与「香港」押韵 |
| `大蛋糕=` | 三字，整词与「大蛋糕」押韵 |
| `34英皇=` | 五字，前码 34＋整词与「英皇」押韵 |
| `2我=3` | 二字，23 同音，首字与「我」押韵 |
| `23就=` | 二字，23 同音＋尾字与「就」押韵（同 `23就`） |

### 左 `=` 查声母

| 输入示例 | 说明 |
|----------|------|
| `=香港` | 二字，整词与「香港」同声 |
| `2=我3` | 二字，23 同音，首字与「我」同声 |

### 近义／反义

| 输入示例 | 说明 |
|----------|------|
| `~开心` | 近义于「开心」 |
| `!你` | 反义于「你」（含镜像近义） |
| `33!开心` | 33 同音＋反义于「开心」 |
| `mode=syn`＋`开心` | 近反义模式（两栏 UI） |

### 反义复合词

| 输入示例 | 说明 |
|----------|------|
| `!!` | 二字反义复合（如生死、是非） |
| `33!!` | 33 同音＋反义复合 |
| `!!你` | 反义复合，尾字与「你」押韵 |
| `33!!你` | 33 同音＋反义复合＋尾字与「你」押韵 |

### 近义复合词

| 输入示例 | 说明 |
|----------|------|
| `~~` | 二字近义复合（如朋友、恐惧） |
| `33~~` | 33 同音＋近义复合 |
| `~~你` | 近义复合，尾字与「你」押韵 |
| `33~~你` | 33 同音＋近义复合＋尾字与「你」押韵 |

```http
GET /words/search/?q=你好&mode=m1
GET /words/search/?q=23就&mode=m1
GET /words/search/?q=香港=&mode=m1
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=nei%20hou&mode=m1
GET /words/search/?q=?syut?&mode=m1
GET /words/search/?q=23o&mode=m1
GET /words/search/?q=3hon4&mode=m1
GET /words/search/?q=!你&mode=m1
GET /words/search/?q=~~&mode=m1
GET /words/search/?q=开心&mode=syn
```

---

## 进阶：架构与部署

### 架构概览

```text
查询字符串 → query_parse（语法分类 · ParsedQuery · build_match_spec）
         → query_dispatch（优先序 registry → executors）
                ↓
    position_match · word_lookup_executor · relation_syntax_executor
                ↓
    domain/lexicon（收录决策）· domain/thesaurus（静态词林）· domain/relations（近反义池／关系图）
                ↓
         words 表 · word_cache（短词 preload）
                ↓
         essay_sort · JSON 结果（纯数字含 X-Search-Total）
```

| 层 | 路径 | 职责 |
|----|------|------|
| 领域 | `app/domain/lexicon/` | 词库埠 · **收录决策** |
| 领域 | `app/domain/thesaurus/` | **静态词林埠** |
| 领域 | `app/domain/relations/` | **近反义池** · **关系图** · ranking |
| 服务 | `app/services/query_parse.py` | `parse_query` · `build_match_spec` |
| 服务 | `app/services/query_dispatch.py` | `search_words` registry |
| 服务 | `app/services/position_match.py` | 位置比对 · 等号／码夹 |
| 服务 | `app/services/*_executor.py` | lookup · `~`/`!` · `!!` · `~~` |

设计原则：领域规则位于 `app/domain/`；ingest 与运行时共用同一埠与池规则。

### 部署与资料库

**产品保证路径**：离线单机 + **SQLite**（`lyrics.db`）。新 schema 仅透过 SQLite bootstrap／`scripts/db/init_db.py` 维护。

**PostgreSQL**：冻结中的 scaffold，**非**主要交付目标。实验用见 `requirements-postgres.txt` 与 [`CONTEXT.md`](../CONTEXT.md) § 产品边界。

### 项目结构

```text
Canto-0243/
├── app/                    # API · domain · services · models
├── frontend/               # index.html（查韵首屏）· relation-entry.html
├── portable/               # START.bat · START.sh · env.portable
├── data/                   # 见「资料来源」三层模型
├── ingest/                 # python -m ingest
├── scripts/                # bootstrap · build-portable · import_data
├── tests/
├── docs/                   # CONTRIBUTING · README.* · release
├── main.py · start.sh      # 开发入口
├── README.md               # 繁中（GitHub 首页）
├── LICENSE · THIRD_PARTY_NOTICES.md
├── CONTEXT.md · WORKLOG.md · AGENTS.md · skills-lock.json
└── requirements*.txt
```

### 资料来源与授权

再分发前请核对 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。收录与排序见 [`CONTEXT.md`](../CONTEXT.md) § 词库与排序。

| 层级 | 说明 | 例子 |
|------|------|------|
| **1 · 随仓库** | clone 即可得 | `data/essay/`、`data/lexicon/`、`data/syn_ant/`、bundled cilin／thesaurus |
| **2 · bootstrap** | `python scripts/bootstrap_data.py` | rime `char.csv`、antisem |
| **3 · maintainer 自建** | gitignore | `lyrics.db`、词级标音 JSON |

近义／反义默认管线：`data/syn_ant/sources.yaml`（cilin、guotong、antisem、compound 列表）。详表见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

---

## 测试

目前 **225** 个 unittest。

```bash
python -m unittest discover -s tests -q
```

关键回归：纯汉字 strict code、wildcard、`mode=syn`、等号／码夹、粤拼、粤拼锚、`~~`／`!!` 复合词。

---

## 依赖

| 层 | 文件 | 用途 |
|----|------|------|
| Runtime | `requirements.txt` | FastAPI + SQLAlchemy + SQLite |
| Ingest / dev | `requirements-dev.txt` | ingest 与 legacy 脚本 |
| PostgreSQL（冻结） | `requirements-postgres.txt` | 实验用 |

---

## Canto-0243 授权与使用

您可将本工具用于粤语填词、查韵、换字等用途，并作为**商业创作**（例如歌曲、剧本、已发表歌词）的组成部分——前提是遵守下列限制：

* **不得**将本工具重新打包、转售，或作为竞争性产品单独发布。
* **不得**将本工具提供为**付费 API**、订阅或按量计费的查询／推理服务（免费自托管或免费公开访问另论，但仍须遵守署名等条款）。
* 任何公开发布的 fork、改进或衍生版本须**沿用同一授权**（或实质等同条款），并在合理显眼位置保留 **Canto-0243** 名称。若您运营公开网站、网页 app 或 API（包括免费），须显示例如「Powered by Canto-0243」并链接至官方仓库。
* 若您运营**商业软件**或**付费推理服务**，希望将本工具整合入产品，请先与版权人联络或于官方 repo 开 Issue 商议书面授权。

除上述条款外，本授权在实务上等效于 [Creative Commons Attribution-NonCommercial-ShareAlike 4.0（CC BY-NC-SA 4.0）](https://creativecommons.org/licenses/by-nc-sa/4.0/) 加上附加限制。完整法律文本见 [`LICENSE`](../LICENSE)。

请在任何未来 fork 或发布中保留 **Canto-0243** 名称！

---

## 致谢与第三方授权

### 项目致谢

本项目在作者几乎无编程基础的起步阶段，得益于 **[ivorhoulker](https://github.com/ivorhoulker)** 担任顾问：在设计与实施上提供了大量意见与指导，并提出许多宝贵的修改建议。若无这些协助，**Canto-0243** 不会出现。

亦感谢 **「0243理论」发明人黄志华老师**，奠定粤语填词数字化的理论基础。感谢 [0243.hk](https://0243.hk) 开发者 **Daniel Tam** 先生开发该网站，解决了许多人的填词问题，并启发作者开发本工具。

### 资料与语料致谢

Canto-0243 整合多个开源词典、语料与近反义资源。我们明确感谢以下团队与专案（再分发前请阅读各上游完整条款；授权总表见 [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)）：

* **Rime 粤语（单字读音 `char.csv`、essay 词频）**：来自 [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) 与 [rime/rime-cantonese](https://github.com/rime/rime-cantonese)，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。欢迎为上述项目点 star。
* **词林同义词（Cilin）**：经 [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity)／[liao961120/cilin](https://github.com/liao961120/cilin) 汇出，采用 **MIT** 授权。
* **国语辞典近义／反义（guotong）**：来自 [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary)，采用 [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE)。
* **ChineseAntiword（antisem）**：来自 [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword)；上游**未明示授权**，本地使用须署名，再分发前请自行核对条款。
* **words.hk 粤典词表**：来自 [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/)，**公有领域**（致谢 [words.hk](https://words.hk/)）。
* **多字词级标音上游**（maintainer 自建 `lyrics.db` 时）：[CC-Canto](https://cantonese.org/download.html)（[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)）、[开放词典 · 粤语词典](https://kaifangcidian.com/xiazai/)（[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)）。

使用上述资料构建或再分发词库时，您同意遵守各自授权；部分来源含**非商业**或**署名**要求。可选近反义来源（如 COW）默认关闭，见 `data/syn_ant/sources.yaml`。

---

## 相关文件

| 文件 | 内容 |
|------|------|
| [`README.md`](../README.md) | 繁体中文（GitHub 首页） |
| [`README.zh-Hans.md`](README.zh-Hans.md) | 本文件（简体中文书面语） |
| [`README.en.md`](README.en.md) | English documentation |
| [`LICENSE`](../LICENSE) | Canto-0243 License |
| [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | 第三方资料授权 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 贡献与 PR · 源码根目录约定 |
| [`CONTEXT.md`](../CONTEXT.md) | 领域词汇表 |
| [`WORKLOG.md`](../WORKLOG.md) | 变更记录 |
| [`AGENTS.md`](../AGENTS.md) | Agent 协作指引 |

---

**最后更新**：2026-06-17（v1.4.0 · 全形查询符号等价 · favicon · ADR-0010）
