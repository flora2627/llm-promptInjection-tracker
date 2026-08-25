#!/usr/bin/env python3
"""从 data/*.json + template.html 生成 index.html(LLM 提示注入立场图)。

    python3 build.py            # 生成并自检
    python3 build.py --open     # 顺便用浏览器打开

数据全部内联进 index.html —— 单文件、无外部请求,直接双击能开,
也满足 Artifact 的 CSP(禁止任何外部 host 请求)。
"""
import json, pathlib, re, sys, html, datetime, collections, webbrowser

ROOT = pathlib.Path(__file__).parent
D = ROOT / "data"
load = lambda n: json.loads((D / n).read_text())

lanes    = load("lanes.json")
years    = load("years.json")
papers   = load("papers.json")
edges    = load("edges.json")
fronts   = load("fronts.json")
misread  = load("misread.json")

# ------------------------------------------------------------------ 自检
def check():
    errs, warns = [], []
    ids = [p["id"] for p in papers]
    dup = [k for k, v in collections.Counter(ids).items() if v > 1]
    if dup: errs.append(f"papers.json 有重复 id: {dup}")
    ids = set(ids)

    for e in edges:
        if e["from"] not in ids: errs.append(f"边的起点不存在: {e['from']} -> {e['to']}")
        if e["to"] not in ids:   errs.append(f"边的终点不存在: {e['from']} -> {e['to']}")
        if e["type"] not in ("inherit", "support", "refute"):
            errs.append(f"未知边类型 {e['type']}: {e['from']}->{e['to']}")
        if e["from"] == e["to"]: errs.append(f"自环: {e['from']}")

    deg = collections.Counter()
    for e in edges:
        deg[e["from"]] += 1; deg[e["to"]] += 1
    orphan = sorted(ids - set(deg))
    if orphan:
        errs.append(f"孤儿节点(没有任何边,不该出现在图上): {orphan}")

    for p in papers:
        if not (0 <= p["lane"] < len(lanes)):
            errs.append(f"{p['id']}: lane 越界 {p['lane']}")
        if p["kind"] not in ("paper", "blogpost", "writeup", "talk", "stance",
                             "competition", "incident", "spec", "cluster"):
            errs.append(f"{p['id']}: 未知 kind {p['kind']}")
        if p["check"] not in ("confirmed", "unchecked", "none"):
            errs.append(f"{p['id']}: 未知 check {p['check']}")
        if p["check"] != "none" and not p.get("url"):
            warns.append(f"{p['id']}: 没有链接")
        if not p.get("title"):
            warns.append(f"{p['id']}: 没有标题")

    for k in misread:
        if k not in ids: errs.append(f"misread.json 里的 {k} 不在 papers.json")

    # 战线 ↔ 图 的同步:战线引的论文要在图上,双方的核心对立要真的有边
    byarx = {str(p["arxiv"]): p["id"] for p in papers if p.get("arxiv")}
    bydoi = {}
    for p in papers:
        m = re.search(r"10\.\d{4,5}/[^\s)]+", p.get("url", "") or "")
        if m: bydoi[m.group(0)] = p["id"]
    adj = collections.defaultdict(set)
    for e in edges:
        adj[e["from"]].add(e["to"]); adj[e["to"]].add(e["from"])
    bylabel = {p["label"]: p["id"] for p in papers}
    bytitle = {(p.get("title") or "").lower(): p["id"] for p in papers if p.get("title")}
    def refs(bullet):
        out = []
        for n in re.findall(r"\*\*(.+?)\*\*", bullet):     # 粗体名字与节点 label 精确同名也算引用
            n = n.strip(" —·:")
            if n in bylabel: out.append(bylabel[n])
            elif n.lower() in bytitle: out.append(bytitle[n.lower()])
        for x in re.findall(r"\b(\d{4}\.\d{4,5})\b", bullet):
            if x in byarx: out.append(byarx[x])
            else: out.append("?" + x)
        for x in re.findall(r"10\.\d{4,5}/[^\s*]+", bullet):
            x = x.rstrip(".,")
            if x in bydoi: out.append(bydoi[x])
            else: out.append("?" + x)
        return out
    for i, f in enumerate(fronts):
        pro = [refs(b) for b in f.get("pro", [])]
        con = [refs(b) for b in f.get("con", [])]
        bad = sorted({r[1:] for side in (pro, con) for rs in side for r in rs if r.startswith("?")})
        if bad:
            warns.append(f"战线 {i+1:02d}「{f['claim'][:18]}」引了图上没有的论文: {bad}")
        pi = {r for rs in pro for r in rs if not r.startswith("?")}
        ci = {r for rs in con for r in rs if not r.startswith("?")}
        if pi and ci and not f.get("edge_gap") and not any(b in adj[a] for a in pi for b in ci):
            warns.append(f"战线 {i+1:02d}「{f['claim'][:18]}」双方在图上没有任何一条边相连")
        for side, rs_list in (("pro", pro), ("con", con)):
            for b, rs in zip(f.get(side, []), rs_list):
                if not [r for r in rs if not r.startswith("?")] and "未入图" not in b:
                    warns.append(f"战线 {i+1:02d} {side} 有一条引用挂不到图上,也没标「未入图」: {b[:26]}…")
        if (not pi or not ci) and not f.get("edge_gap"):
            warns.append(f"战线 {i+1:02d}「{f['claim'][:18]}」有一侧没有任何可对应到图上的论文")

    # 标签横向重叠(与渲染同算法,提前发现拥挤)
    def tw(s, px): return sum((1 if ord(c) > 0x2E80 else .6) * px for c in s)
    for li in range(len(lanes)):
        ns = sorted([p for p in papers if p["lane"] == li], key=lambda p: p["t"])
        rows = []
        for p in ns:
            half = tw(p["label"], 10.5) / 2 + 9
            x = 200 + (p["t"] - 170) * 1.30
            lo, hi, t = x - half, x + half, 0
            while True:
                if t == len(rows): rows.append([])
                if all(hi < a or lo > b for a, b in rows[t]):
                    rows[t].append((lo, hi)); break
                t += 1
        if len(rows) > 3:
            warns.append(f"泳道「{lanes[li]['name']}」标签需要 {len(rows)} 层,考虑缩短 label 或调整 t")
    return errs, warns


errs, warns = check()
for w in warns: print(f"  [warn] {w}")
if errs:
    for e in errs: print(f"  [ERR ] {e}", file=sys.stderr)
    sys.exit(f"\n构建中止:{len(errs)} 个错误")

# ------------------------------------------------------------------ 渲染战线卡片
def md(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    # [文字](url) -> 链接;裸 arXiv id -> 链接
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"(?<![\w/.])(\d{4}\.\d{4,5})(?![\w.])",
               r'<span class="aid"><a href="https://arxiv.org/abs/\1">\1</a></span>', s)
    return s.replace("\n", "<br>")

def render_front(i, f):
    def side(kind, label, items):
        lis = "\n".join(f"        <li>{md(x)}</li>" for x in items)
        return (f'      <div class="side {kind}"><div class="side-label"><span class="tick"></span>'
                f'{html.escape(label)}</div><ul>\n{lis}\n      </ul></div>')
    return f"""  <div class="front">
    <div class="front-top"><span class="front-no">{i:02d}</span>
      <span class="front-claim">{md(f['claim'])}</span>
      <span class="verdict {f['verdict_class']}">{html.escape(f['verdict'])}</span></div>
    <div class="sides">
{side('pro', f['pro_label'], f['pro'])}
      <div class="divider"></div>
{side('con', f['con_label'], f['con'])}
    </div>
    <div class="front-note">{md(f['note'])}</div>
  </div>"""

fronts_html = "\n".join(render_front(i, f) for i, f in enumerate(fronts, 1))

# ------------------------------------------------------------------ 渲染资料表
KIND_CN = {"paper": None, "blogpost": "博客", "writeup": "漏洞披露", "talk": "议题",
           "stance": "立场", "competition": "竞赛/靶场", "incident": "事件",
           "spec": "厂商文档", "cluster": "条目簇"}
CHECK_CN = {"confirmed": ("b-confirmed", "confirmed"),
            "unchecked": ("b-unchecked", "待核"),
            "none": ("b-none", "无 arXiv")}
deg = collections.Counter()
for e in edges:
    deg[e["from"]] += 1; deg[e["to"]] += 1

rows = []
for p in sorted(papers, key=lambda p: (p["year"], p["lane"], p["label"])):
    cls, txt = CHECK_CN[p["check"]]
    kind = KIND_CN.get(p["kind"])
    badges = f'<span class="badge {cls}">{txt}</span>'
    if kind: badges += f'<span class="badge b-kind">{kind}</span>'
    if p["id"] in misread: badges += '<span class="badge b-kind">常被误读</span>'
    if p.get("url"):
        src = p["arxiv"] or re.sub(r"^www\.", "", (p["url"].split("/")[2] if "//" in p["url"] else "链接"))
        link = f'<a href="{p["url"]}">{html.escape(src)}</a>'
    else:
        link = f'<span style="color:var(--muted)">{html.escape(p["venue"] or "—")}</span>'
    note = f'<div class="nt">{md(p["note"])}</div>' if p.get("note") else ""
    rows.append(
        f'<tr id="ref-{p["id"]}" data-id="{p["id"]}" data-check="{p["check"]}" data-kind="{p["kind"]}">'
        f'<td class="yr">{p["year"]}</td>'
        f'<td><div class="ti">{html.escape(p["title"] or p["label"])}</div>'
        f'<div class="au">{html.escape(p["authors"])} · {html.escape(p["venue"] or "")}'
        f' · {html.escape(p.get("date") or str(p["year"]))}'
        f' · 图上标为「{html.escape(p["label"])}」· {deg[p["id"]]} 条边</div>{note}</td>'
        f'<td class="au">{html.escape(lanes[p["lane"]]["name"])}</td>'
        f'<td>{badges}</td><td class="ln">{link}</td></tr>')

# ------------------------------------------------------------------ 注入
D_ = "零一二三四五六七八九"
def cn_num(n):
    if n < 10: return D_[n]
    if n < 20: return "十" + (D_[n % 10] if n % 10 else "")
    if n < 100: return D_[n // 10] + "十" + (D_[n % 10] if n % 10 else "")
    return str(n)
n_fronts = len(fronts)
n_fronts_cn = cn_num(n_fronts)

et = collections.Counter(e["type"] for e in edges)
kinds = collections.Counter(p["kind"] for p in papers)
date = datetime.date.today().isoformat()
aria = (f"LLM 提示注入(prompt injection)研究领域 2022 至 2026 的时间线森林图:{len(lanes)} 条研究主干泳道上分布 "
        f"{len(papers)} 个条目,以 {len(edges)} 条签名边连接——灰实线为继承 {et['inherit']} 条、"
        f"青色佐证 {et['support']} 条、琥珀虚线反驳证伪 {et['refute']} 条。"
        f"条目不限于论文:另含漏洞披露、博客、议题、竞赛靶场与厂商文档,"
        f"其中论文 {kinds['paper']} 篇、非论文 {len(papers)-kinds['paper']} 条。"
        f"泳道从上到下依次是概念与起源、直接注入与提示窃取、间接注入、投毒与持久化、Agent 劫持、"
        f"外泄通道与野外事故、提示级防御、训练期防御、检测与运行时监控、架构与能力控制、"
        f"评测竞赛与基建、理论与立场。"
        f"另有 {len(misread)} 个条目被标为常被系统性误读。方形节点表示该条目不是单篇论文。")

data = {"lanes": lanes, "years": years, "papers": papers, "edges": edges, "misread": misread}

out = (ROOT / "template.html").read_text()
for k, v in {
    "{{DATA}}":        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
    "{{FRONTS}}":      fronts_html,
    "{{REFS}}":        "\n".join(rows),
    "{{N_PAPERS}}":    str(len(papers)),
    "{{N_EDGES}}":     str(len(edges)),
    "{{N_INHERIT}}":   str(et["inherit"]),
    "{{N_SUPPORT}}":   str(et["support"]),
    "{{N_REFUTE}}":    str(et["refute"]),
    "{{N_MISREAD}}":   str(len(misread)),
    "{{N_UNCHECKED}}": str(sum(1 for p in papers if p["check"] == "unchecked")),
    "{{N_FRONTS_CN}}": n_fronts_cn,
    "{{ARIA}}":        html.escape(aria),
    "{{DATE}}":        date,
}.items():
    out = out.replace(k, v)

left = re.findall(r"\{\{[A-Z_]+\}\}", out)
if left: sys.exit(f"模板占位符未替换: {sorted(set(left))}")

(ROOT / "index.html").write_text(out)
kc = collections.Counter(p["kind"] for p in papers)
cc = collections.Counter(p["check"] for p in papers)
print(f"\n✓ index.html  {len(out)//1024} KB")
print(f"  条目 {len(papers)}  {dict(kc)}")
print(f"  核验 {dict(cc)}")
print(f"  边   {len(edges)}  {dict(et)}")
print(f"  战线 {n_fronts} · 误读标记 {len(misread)}")
print(f"  边数最多: {deg.most_common(5)}")
if "--open" in sys.argv:
    webbrowser.open((ROOT / "index.html").as_uri())
