# 维护笔记

给维护者（和 AI 助手）看的：怎么加条目、页面怎么组织、图为什么这么画，以及历次更新与订正的留档。
**项目介绍在 [README.md](README.md)。**

姊妹项目 [`../llm-jailbreak-tracker`](../llm-jailbreak-tracker) 与
[`../llm-backdoor-tracker`](../llm-backdoor-tracker) 用的是**同一套 `build.py` 与 `template.html`**
（本项目从越狱那个复制而来，改了 schema、数据与文案）。
**backdoor 那边的 MAINTENANCE 仍然是这套管线的权威说明**，本文只写本项目自己的东西与差异。

---

## 本项目与两个姊妹项目最大的结构差异

**这张图近一半条目不是论文（98 条里 44 条）。** 这不是风格选择，是这个领域的形状决定的：

| 承重的东西 | 原始出处 |
|---|---|
| Dual LLM 模式（CaMeL 的前身） | 一篇个人博客，比论文早两年 |
| 指令层级被绕的第一份证据 | 一篇个人博客，比论文侧的确认早两年 |
| lethal trifecta（被 Meta 写进公司级框架） | 一篇个人博客 |
| 外泄通道（Markdown 图 / DNS / CSS 字体 / 搜索 query） | 全部是一手漏洞披露，论文侧几乎不记录 |
| 可用性攻击（持久 DoS）与完整性攻击（改记忆） | 只在一手披露里有，论文基准不测 |

**因此本项目的核验流程必须支持非论文条目**，见下面 §1。

---

## 每周更新流程

### 1. 扫新条目（两条并行的入口）

**沙箱网络实测（2026-08-24 本轮）：**

- **`curl` 出不去**（静默空返回）。和两个姊妹项目一样，别在 curl 上浪费时间。
- **`WebFetch` 走得通，可 4–5 路并行**，`arxiv.org/abs/<id>`、个人博客、厂商 blog 都能拉。
- **`export.arxiv.org/api/query` 没试**（越狱那轮实测被限流到 429，本轮直接走 abs 页，够用）。
- **`arstechnica.com` 被 WebFetch 拒绝**（`Claude Code is unable to fetch from`），
  **`genai.owasp.org` 返回 403**。遇到这两类直接换源，别重试。
- **`WebSearch` 好用**，而且**不限定域名时对博客/厂商公告的覆盖比限定 arxiv.org 好得多**。

**入口 A：论文。** `WebSearch` 限定 `allowed_domains: ["arxiv.org"]`，有效的查询角度：

- 按攻击族：`indirect prompt injection agent`、`chat template injection`、`RAG poisoning`
- 按防御族：`prompt injection defense adaptive`、`agent runtime provenance`、`instruction data separation`
- **按「谁打谁」**：`benchmark saturated prompt injection`、`adaptive attack defense framework`
- 按理论：`prompt injection impossibility`、`formal guarantee separation` ← **本领域这条线出人意料地厚，别跳过**
- 引用追踪：引用了 2302.12173、2404.13208、2406.13352、2503.18813、2510.09023 的新文

**入口 B：非论文（本项目独有，权重不低于 A）。** 按站点扫，效率远高于搜索：

| 源 | 怎么扫 | 本轮产出 |
|---|---|---|
| `embracethered.com/blog/tags/prompt-injection/` | **一次 WebFetch 就能拿到全部 53 篇的标题+日期+URL** | 图上 20 条 |
| `simonwillison.net/tags/prompt-injection/`、`/tags/lethal-trifecta/` | 同上，按标签翻 | 图上 12 条 |
| `monthofaibugs.com` / 其 wrap-up 帖 | 一帖索引 29 篇披露，含 CVE 与 URL | 图上 5 条 |
| 厂商：`ai.meta.com/blog`、`blog.google/security`、`help.openai.com` | 搜索找入口再 WebFetch | 图上 4 条 |
| 研究公司：Legit Security / Invariant Labs / Noma / PromptArmor / General Analysis / CodeIntegrity | 出事时按名字搜 | 图上 6 条 |

> **标签索引页是本项目最高效的核验手段**：站点自己列出的标题与日期就是一手书目，
> 一次请求核实十几条。**先拉索引页，再决定哪几条值得单独 WebFetch 拿技术细节。**

### 2. 加条目 → `data/papers.json`

字段比姊妹项目多一个 `date`（精确到日），`kind` 的取值域也扩了：

```
id / label / lane / t0 / t / title / authors / year / date / venue / arxiv / url / kind / check / note
```

- `lane` 是 **0–11**（十二条），见 `lanes.json`
- **`date` 是 `YYYY-MM-DD`**，资料表里会显示。非论文的日期比 arXiv 脆弱，**必须从发布方页面抄**
- **`t0` 用 `spread.py` 里的 `T(year, month)` 算，`t` 交给 `spread.py` 生成**
- `kind` 取值：`paper` / `blogpost` / `writeup` / `talk` / `stance` / `competition` / `incident` / `spec` / `cluster`
  - **`writeup`** = 有可复现技术细节的漏洞披露（本项目最大的一类，26 条）
  - **`stance`** = 立场/设计法则，没有实验但被广泛当作约束引用（lethal trifecta、Rule of Two、MCP Colors）
  - **`blogpost`** = 一般博客（含转述他人研究的 link post，作者字段写「X（经 Y 转述）」）
  - **`spec`** = 厂商产品文档
  - 除 `paper` 外都会在资料表里显示徽章，图上画成**方形节点**
- **`check` 目前全部是 `confirmed`，保持这个状态**。新加的先写 `unchecked`，当轮清干净，别攒

### 3. 加边 → `data/edges.json`

| `type` | 用在什么情况 |
|---|---|
| `inherit` | 延续同一条方法线或同一个问题陈述 |
| `support` | 独立复现、同向证据、互相印证 |
| `refute` | **攻击打穿防御** 或 **防御把某个攻击的 ASR 打下去** 或 **划出对方结论的上限 / 反转它** |

**方向恒为 `from` → `to`，读作「from 对 to 做了这件事」。**

> **硬规矩一：边必须时间正向。** `from` 的 **`t0`** 必须 ≥ `to` 的 `t0`。查 `t0` 不是 `t`。
> `build.py` **不查**这一条，`mk_edges.py` 风格的校验脚本要单独跑（见 §5）。

> **硬规矩二：不要加没有边的条目。** `build.py` 会把孤儿节点判为错误并中止。

> **硬规矩三（本项目特有）：不要凭「这篇应该打了那篇」造 refute 边。**
> 大量论文写「打穿了 12 个近期防御」却**不点名**。本轮的处理是：
> **不点名就不连具体防御**，只连它明确指控的对象（评测流程、某个基准）。
> 本图 refute 边只有 31 条，比越狱那张图少得多，**这是纪律的结果，不是领域的和谐**。

### 4. 加战线 → `data/fronts.json`

三条硬规矩与姊妹项目相同（`build.py` 会 warn）。本项目额外约定：

- **每条 bullet 优先带 arXiv id；非论文条目靠粗体 label 精确匹配**（如 `**Rule of Two**`、`**IH 被绕**`）。
  `build.py` 的 `refs()` 会把粗体内容与 `papers.json` 的 `label` 精确比对，**label 改了战线就挂不上，会 warn**。
- `note` 第一句写 crux。本领域 crux 的形式高度固定，基本只有四种：
  **量词位置 / 攻击者预算 / 评测口径 / 「消除」与「限制后果」被混为一谈**。
- **允许 `edge_gap: true`。** 战线 11（注入 vs 越狱）两侧在图上没有任何边相连——
  **这本身是发现**：定义之争从没被正面打过。这种情况标 `edge_gap` 并在 note 里写明，别硬造边。

### 5. 构建 + 自检 + 验

```bash
python3 spread.py     # 只在 build.py warn「标签需要 >3 层」时跑；幂等
python3 build.py      # 自检 + 生成

# build.py 不查的两项，单独跑
python3 - <<'EOF'
import json, collections
P=json.load(open("data/papers.json")); E=json.load(open("data/edges.json"))
t={p["id"]:p["t0"] for p in P}          # ← 用 t0，不是 t
print("时间倒挂:", [(e["from"],e["to"],e["label"]) for e in E if t[e["from"]]<t[e["to"]]])
print("重复边:", [k for k,v in collections.Counter((e["from"],e["to"]) for e in E).items() if v>1])
EOF

# markdown 强调是否配对（写坏了会产出不平衡的 HTML）
python3 - <<'EOF'
import json,re
for f in ("papers","fronts","misread"):
    d=json.load(open(f"data/{f}.json")); items=d if isinstance(d,list) else list(d.values())
    for it in items:
        for v in ([it] if isinstance(it,str) else [x for x in it.values() if isinstance(x,str)]
                  + [y for x in it.values() if isinstance(x,list) for y in x if isinstance(y,str)]):
            if re.sub(r'\*\*(.+?)\*\*','',v).count('*')%2: print("单星不配对:", v[:60])
EOF

# 生成的 JS 语法检查
node --check <(python3 -c "import re;s=open('index.html').read();print(re.search(r'<script>(.*)</script>',s,re.S).group(1))")

# HTML 标签平衡（md() 写坏时靠它抓）
python3 -c "
from html.parser import HTMLParser
VOID={'br','img','input','meta','link','hr','line','circle','rect','path','use','stop','polygon','ellipse','source'}
class P(HTMLParser):
    def __init__(s): super().__init__(); s.stack=[]; s.err=[]
    def handle_starttag(s,t,a):
        if t not in VOID: s.stack.append(t)
    def handle_endtag(s,t):
        if s.stack and s.stack[-1]==t: s.stack.pop()
        elif t in s.stack:
            s.err.append((t,s.stack[-1]))
            while s.stack and s.stack.pop()!=t: pass
p=P(); p.feed(open('index.html').read()); print('残留:',p.stack,'错误:',p.err[:5])"

# 无头截图（#graph / #brief / #fronts / #refs / #method 各一张）
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --virtual-time-budget=5000 --window-size=1440,1100 --screenshot=/tmp/shot.png \
  "file://$PWD/index.html#graph"
```

---

## 图的设计约定（改数据前先看）

- **十二条泳道，顺序是排过的，不要随手改。** 当前顺序：

  `概念与起源 | 直接注入·提示窃取 | 投毒与持久化 | 外泄通道与野外事故 | 间接注入 | Agent 劫持 | 评测·竞赛·基建 | 检测与运行时监控 | 架构与能力控制 | 提示级防御 | 训练期防御 | 理论与立场`

  这个顺序是**在「攻击块（5 条）相邻 + 防御块（4 条）相邻 + 起源在首 + 理论在尾」的约束下，
  枚举全部 17,280 种合法排列、最小化 Σ(边数 × 跨泳道距离)** 选出来的：
  **cost 409**，而按叙事直觉排是 **509**（无约束的全局最优是 399，只好 10，不值得牺牲语义）。
  布线算法把每条边放进 `floor((laneA+laneB)/2)` 的通道，**跨度越长，中间泳道的轨道越挤**，
  所以泳道顺序直接决定图有多高。**改顺序前先重跑这个优化**，脚本：

  ```python
  # 约束下穷举，17,280 种，秒级
  import itertools, json
  ATK=[1,2,3,4,5]; DEF=[6,7,8,9]; EVAL=[10]   # ← 用原始编号，见下面「原始编号」注
  for blocks in itertools.permutations(['A','D','E']):
      for pa in itertools.permutations(ATK):
          for pd in itertools.permutations(DEF):
              order=[0]+sum(([list(pa),list(pd),EVAL][{'A':0,'D':1,'E':2}[b]] for b in blocks),[])+[11]
              ...  # cost(order) = Σ 边数 × |pos[a]-pos[b]|
  ```

  > **原始编号**：数据是按「概念0 / 直接1 / 间接2 / 投毒3 / Agent4 / 外泄5 / 提示级6 / 训练期7 / 检测8 / 架构9 / 评测10 / 理论11」
  > 写出来的，然后整体 remap 成上面的展示顺序。重跑优化时用原始编号定义 ATK/DEF/EVAL。

- **横轴 `t` 是像素坐标，不是年份。** 对照 `years.json`：2022→200，2023→420，2024→760，2025→1180，2026→1620。
  每年约 420–440 个 t 单位，比越狱那张图均匀（那边刻意拉宽了 2023–2025）。

- **`t` 上做过「有上限的横向铺开」，基准是 `t0`。** `t0` 由 `T(year, month)` 算出，判定边的先后与写注记以它为准；
  `t` 是排版用的显示坐标。**单条相对 `t0` 的位移上限 55 个 t 单位**，顺序不变，脚本幂等（每次从 `t0` 重算）。
  **2025 年 8–9 月是全图最挤的一段**（Month of AI Bugs 那批 + EchoLeak + ForcedLeak + Notion 全挤在两个月里），
  加新条目后如果 `build.py` warn「标签需要 >3 层」，跑一次 `python3 spread.py` 再 build。

- **label 要短。** 中文字符按 1.0 计宽、拉丁按 0.6，**中文 label 尽量 ≤5 字**。
  本项目的非论文条目用产品名做 label（`GitLab Duo`、`Cowork 外泄`、`Copilot RCE`），比论文名短，这是优势。

- 其余（节点大小=边数、琥珀描边=做过反驳、虚线描边=常被误读、方形=非单篇论文、正交通道布线）与姊妹项目相同。

---

## 本项目的内容纪律（在姊妹项目那几条之外）

1. **书目字段必须当场从原始页面抄。** 论文抄 abs 页，非论文抄发布方自己的页面。
   **本轮 98 条全部这样做的，没有一条是凭记忆填的**（越狱那轮凭记忆填 id 抓出过两处错号）。
2. **摘要/正文里没给的数字就不写。**
3. **跨基准、跨年份的 ASR 不可比。** 注入的判定器、任务集、载荷形状三处都不同。
   注记里出现 ASR 必须带基准名。
4. **不能在 `data/*.json` 里写 HTML。** `md()` 先 `html.escape` 再套 markdown。
   只能用 `**粗**` / `*斜*` / `` `代码` `` / `[文字](url)`，裸 arXiv id 自动成链接。
   **特别注意 `***三星***` 与 `**...*...**` 这类嵌套**——本轮踩过，会产出不平衡的 `<b>/<i>`（见 §5 的校验脚本）。
5. **防御条目默认按「未面对自适应攻击」打折**（2510.09023 的口径）。
6. **厂商自评数字必须标注「无法独立验证」**（`geminidefend`、`automode`、`googlelayer` 三条都这么写的）。
7. **收录漏洞披露不等于认可其严重程度评级。** 本图对 CVE 有无、CVSS 高低不加权——
   **在这个领域拿没拿到 CVE 与技术上开没开辟新面基本无关**（Month of AI Bugs 的 29 篇里只有少数有 CVE）。
8. **转述型 link post 的作者字段要写成「原作者（经 X 转述）」**，并在注记里点明技术细节来自谁。
   本轮有 5 条这样处理（Antigravity、Cowork 外泄、Word 蠕虫、Notion 3.0、auto mode）。

---

## 历史留档

### 2026-08-24 · 建库（第一轮）

从 `../llm-jailbreak-tracker` 复制 `build.py` / `spread.py` / `template.html` / `LICENSE` / `.gitignore`，
扩了 schema、重写全部数据与文案。产出：**98 条目 · 208 边 · 11 战线 · 31 条误读标记 · 12 泳道**。

**核验方式：**98 条**逐条 WebFetch 拉原始页面**。论文核对标题、完整作者、v1 日期、comments 与摘要正文；
非论文核对标题、作者、发表日期，并用站点自身的标签索引交叉验证。

**对 `build.py` 的改动（都很小）：**
- `kind` 白名单扩到 9 种，`KIND_CN` 加了对应中文徽章
- 资料表的链接列：非 arXiv 条目显示**来源域名**而不是「链接」
- 作者行加显示 `date`（精确到日）
- `aria` 描述重写，并加了「论文 N 篇 / 非论文 M 条」

**对 `spread.py` 的改动：** `range(11)` 改成从 `lanes.json` 读泳道数。

**本轮的两处书目困难（已处理）：**

| 条目 | 问题 | 处理 |
|---|---|---|
| Bing Chat / Sydney（2023-02-09） | 一手推文抓不到 | 改按 **OECD AI 事件库**记录核实（该记录援引 9 家媒体报道），注记里写明细节来自二手 |
| Supabase MCP 外泄 | 发布方页面现显示 **2026 年复审日期**，与首次广泛报道（2025-07）不符 | 按**首次报道**定位，注记里标注歧义 |

**这两处说明一件事：非论文条目的日期比 arXiv 脆弱得多**——博客会被重写、重新发布、改版丢日期。
这是收录非论文必须付的成本，也是为什么 §1 强调**优先用站点自己的标签索引交叉验证**。

**本轮修过的建模错误：**
- 一处 markdown 嵌套写坏（`**作者自己的评价是 *This solution is pretty bad!***`）
  导致生成的 HTML 里 `<b>`/`<i>` 交叉不闭合。**`build.py` 不查这个**，靠 §5 的 HTML 平衡脚本抓到的。
- 战线 11 两侧无边相连，最初想硬造一条 refute 边，改成标 `edge_gap` 并把「没有边」写成结论。

### 本轮看过、判定超范围、故意不入图

- **越狱** —— 归 `llm-jailbreak-tracker`。横跨条目（2510.09023）**两图各取一半**，双方注记都写明了。
- **训练期权重后门** —— 归 `llm-backdoor-tracker`。**边界个案：记忆/检索库投毒本图收**
  （AgentPoison 自称 backdoor，但载体是检索库不是权重，触发路径是检索相似度不是模型参数）。
- **纯营销性质的厂商安全博客**（无可核实技术内容）。
- **OWASP LLM Top 10 的 LLM01 条目** —— 想收，但 `genai.owasp.org` 返回 **403** 抓不到，本轮不收。

---

## 待办

### 最大的单一缺口

**厂商安全公告与 CVE 库从未系统扫过。**
本图的野外事故条目主要来自**少数几位研究者的个人博客**——这意味着**覆盖面被他们的兴趣塑造**：
编码 agent 多、企业 SaaS 少、非英语生态为零。
扫法：CVE 按 `prompt injection` 关键词逐年检索、MSRC 安全更新、GitHub Security Advisory、
以及各家的 AI bug bounty 页面（注意 Google 已把这类标为「已知问题不计赏金」，**这类政策变化本身值得作为条目**）。

### 其余

- **多模态注入只有几条，没有成线。** 图片里的隐藏指令、语音、文档版式——与本图文本线共享威胁模型，理应收。
- **LessWrong / Alignment Forum 从未扫过。**
- **安全顶会的纯论文集条目基本没进来**（CCS / NDSS / USENIX Sec / S&P 里只在 arXiv 有预印本的才被捞到）。
- **Sydney 那条需要一手来源**：推文存档或 2023-02 的一手报道，拿到后把注记里的「按二手记录写」去掉。
- **OWASP LLM01 需要换一个能抓的镜像源。**
- **中文与非英文文献未覆盖。**
- **一条值得单独做的实验（战线 04 指出的空洞）：**
  内部信号派（Attention Tracker → PIShield）押的赌注是「残差流比文本更难被优化欺骗」，
  而**这个赌注至今没有被一次正面的自适应攻击检验过**。谁做了这个实验，就会成为战线 04 的裁定者。

---

## 附：`spread.py`

加新条目后 `build.py` warn「标签需要 >3 层」时跑一次：

```bash
python3 spread.py && python3 build.py
```

它从每条记录的 `t0` 重新计算 `t`，**幂等**（连跑两次 `papers.json` 的 md5 不变）。
新条目必须带 `t0`；`t` 可以先随便填，`spread.py` 会覆盖它。
`t0` 由 `T(year, month)` 按 `years.json` 插值算出——直接复用 `spread.py` 顶部的同名函数。
