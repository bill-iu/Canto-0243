# Canto-0243

<p align="center">
  <a href="../README.md">繁體中文</a> · <b>简体中文</b> · <a href="README.en.md">English</a>
</p>

填写粤语歌词时，常见困难一是不知道有哪些字可用，二是需要在**同音、押韵、近义**之间快速换字，同时又要符合 0243 与粤拼读音。传统做法是在词典、韵书、近义表之间反复查阅，手动尝试「这一位置能否换成另一个字」——效率低，且容易遗漏许多可用字。[0243.hk](https://0243.hk) 已是近年来较好用的粤语填词检索网站，但偶尔会出现 502 Bad Gateway 无法访问；检索时也可能长时间加载；或缺少所需功能——这些情况都会拖慢创作进度。

**Canto-0243**（**ONE·揾·韵**）是我在多种 AI Agent（Cursor、Codex、Grok Build、GitHub Copilot）协助下开发的离线粤语填词检索工作台：依据 **394052／02493 数字码**、**粤拼**、**韵母／声母规则**与 **近义／反义关系**，在数秒内列出符合条件的**词条**。顶栏 **0243搜索模式** 有三档：**0243模式**（松）、**02493模式**（紧）、**394052模式**（六声，三声 `4`／五声 `5` 分明）。例如输入 `23就` 可查找同调且与「就」押韵的尾字；输入 `香港=` 可查找与「香港」押韵的候选词；输入 `~开心` 或切换**近反义模式**可查找近义／反义词；输入 `~~`／`!!` 可查找填词常用的二字近义／反义复合词。套件解压即可使用，词库与近反义资料均存于本地，无需联网。

**授权**：整包（程序、`lyrics.db`、`words-lexicon.json`）依 [Canto-0243 License](../LICENSE)（CC BY-NC-SA 4.0 + 附加条款；**开源**）。第三方上游资料见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。  
**技术栈**：FastAPI · SQLAlchemy · SQLite（离线单机）· PWA 前端（Service Worker / Web App Manifest；Vite + 纯 HTML/JS，离线数据库以 OPFS / wa-sqlite 提供）  
**领域词汇**：见 [`CONTEXT.md`](../CONTEXT.md) · 贡献指南 [`docs/CONTRIBUTING.md`](CONTRIBUTING.md)

---

## 最新版本

<!-- version:zh-Hans -->
目前版本：**v1.1.0**
<!-- /version:zh-Hans -->

<!-- words-count:zh-Hans -->
目前总词条列数：**171,082**（`lyrics.db` · `words` 表）
<!-- /words-count:zh-Hans -->

**立即开始使用（两种方式，同等重要）**

**Canto-0243 手机版**（浏览器直接开启，无需安装，支持「添加到主屏幕」，完全离线）  
👉 https://bill-iu.github.io/Canto-0243/

**离线 portable 版本**（Windows / macOS 免安装，解压即用）  
下载最新版：[canto-0243-portable.zip](https://github.com/bill-iu/Canto-0243/releases) / macOS tar  
完整 Releases 与词库文件请到 [GitHub Releases](https://github.com/bill-iu/Canto-0243/releases)

问题与建议欢迎 [GitHub Issues](https://github.com/bill-iu/Canto-0243/issues)。

---

## 功能

* **0243搜索三档**：**0243模式** `mode=m1`（松档等价）· **02493模式** `mode=m2`（仅 `4↔5` 松档）· **394052模式** `mode=m3`（六声码逐位精确；词库存储用 394052，三声 `4`、五声 `5` 分明）。
* **多种查询语法**：纯汉字 · 纯数字 · **粤拼查询** · **加号锚**（`23+好=`）· **韵／声锚**（`就=`）· **串列韵／声锚** · **四字部分韵／声锚**（`穷?潦倒=`）· **前缀通配等号** · 整词等号／码夹。
* **近反义**：**近反义模式** `mode=syn` 全栏 UI（不接受粤拼）；或在 0243搜索模式下 `~词`／`!词`、反义复合 `!!`、近义复合 `~~`。

---

## 快速开始

**选一种开始使用**：

- **Canto-0243 手机版**：直接开启 https://bill-iu.github.io/Canto-0243/ ，添加到主屏幕后完全离线可用。顶栏有「搜索教学」。

- **Desktop 离线版**：从 [Releases](https://github.com/bill-iu/Canto-0243/releases) 下载解压。Windows 仅双击 `Canto-0243.exe`（不附 `.bat`）；macOS 双击 `Canto-0243.command`。

开发者 clone 需准备 `lyrics.db`（详见 [`docs/CONTRIBUTING.md`](CONTRIBUTING.md)）。

---

## 常用语法示例

| 输入示例 | 说明 |
|----------|------|
| `就` | 查这个字的所有读音 |
| `你好` | 查这个词语 |
| `23` | 找同音字 |
| `就=` | 同「就」韵 |
| `23就` | 码 + 尾字同韵 |
| `香??` | 缺字查询 |
| `香港=` | 整词同韵 |
| `?+就=` | 尾格同韵 |
| `~开心` | 近义词 |
| `!!` / `~~` | 反义／近义复合词 |

完整例子与所有语法，请在 App 内点击顶栏「搜索教学」查看。

---

## 维护者提示

词库重建、发布等详见 [`docs/CONTRIBUTING.md`](CONTRIBUTING.md) 及 [`docs/release.md`](release.md)。

---

## 关于开发者

**Bill IU（姚程驭）** — 演员，粤语音乐剧填词人，超级业余的程序设计师。

---

## Canto-0243 授权与使用

您可将本工具用于任何您想做的事，包括协助粤语填词、查韵、换字，以及作为**商业创作**（例如歌曲、剧本、已发表歌词）的组成部分——前提是遵守下列限制：

* **不得**将本工具重新打包、转售，或作为竞争性产品单独发布。
* **不得**将本工具提供为**付费 API**、订阅或按量计费的查询／推理服务（免费自托管或免费公开访问另论，但仍须遵守署名等条款）。
* 任何公开发布的 fork、改进或衍生版本须**沿用同一授权**（或实质等同条款），并在合理显眼位置保留 **Canto-0243** 名称。若您运营公开网站、网页 app 或 API（包括免费），须显示例如「Powered by Canto-0243」并链接至官方仓库。
* 若您运营**商业软件**或**付费推理服务**，希望将本工具整合入产品，请先与版权人联络或于官方 repo 开 Issue 商议书面授权。

除上述条款外，本授权在实务上等效于 [Creative Commons Attribution-NonCommercial-ShareAlike 4.0（CC BY-NC-SA 4.0）](https://creativecommons.org/licenses/by-nc-sa/4.0/) 加上附加限制。完整法律文本见 [`LICENSE`](../LICENSE)。

请在任何未来 fork 或发布中保留 **Canto-0243** 名称！

---

## 致谢与第三方授权

### 项目致谢

本项目在作者几乎无编程基础的起步阶段，得益于 [ivorhoulker（艾浩家）](https://github.com/ivorhoulker) 担任顾问，在设计与实施上给予许多指导与宝贵建议。

亦感谢 **「0243 理论」发明人黄志华老师**（很荣幸得到他的支持），奠定粤语填词数字化的理论基础。感谢 [0243.hk](https://0243.hk) 开发者 **Daniel Tam** 先生开发该网站，解决许多填词难题，并启发本工具的开发。

### 资料与语料致谢

本应用程序得以实现，全赖语言学家、开源维护者及社群贡献者的出色工作。我们十分荣幸能整合以下项目的数据（与产品「关于」页一致；再分发前请阅读各上游完整条款）：

* [words.hk（粤典）](https://words.hk/)：采用**非商业开放授权**（详见 [words.hk /hoifong](https://words.hk/base/hoifong/)）。
* [Rime 粤语词典补缺来源](https://github.com/CanCLID/rime-cantonese-upstream)：采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。
* [HSK 3.0 词表](https://github.com/elkmovie/hsk30)：采用 [MIT](https://opensource.org/licenses/MIT) 授权。
* [开放词典 · 粤语词典（Kaifangcidian）](https://kaifangcidian.com/xiazai/)：采用 [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)。
* [词林同义词（Cilin）](https://github.com/yaleimeng/Final_word_Similarity)：采用 [MIT](https://opensource.org/licenses/MIT) 授权。
* [国语辞典近义／反义（guotong）](https://github.com/guotong1988/chinese_dictionary)：采用 [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE)。
* [自建反义词库](../LICENSE)：大模型辅助生成，采用 [Canto-0243 License](../LICENSE)。

完整第三方授权清单见 [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)。

---

## 相关文件

| 文件 | 内容 |
|------|------|
| [`README.md`](../README.md) | 繁体中文（GitHub 首页） |
| [`docs/README.zh-Hans.md`](README.zh-Hans.md) | 本文件（简体中文书面语） |
| [`docs/README.en.md`](README.en.md) | English documentation |
| [`LICENSE`](../LICENSE) | Canto-0243 License（程序与词条库交付） |
| [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | 第三方资料授权 |
| [`docs/CONTRIBUTING.md`](CONTRIBUTING.md) | 贡献与 PR · 源码根目录约定 |
| [`CONTEXT.md`](../CONTEXT.md) | 领域词汇表 |
| [`WORKLOG.md`](../WORKLOG.md) | 变更记录 |

---

**最后更新**：2026-07-17（README／关于页资料致谢对齐；贡献指引不再规定 agent 文件）
