#!/usr/bin/env python3
"""把 papers.json 的显示坐标 t 从真实坐标 t0 重新铺开,消除标签堆叠。

    python3 spread.py && python3 build.py

幂等:每次都从 t0 重算,连跑两次结果一致。新条目只需填对 t0(用下面的 T())。
"""
import json, bisect

YEARS = json.load(open("data/years.json"))
_ys = [y for y, _ in YEARS]; _ts = [t for _, t in YEARS]
def T(year, month):
    """(年, 月) → t0。2026 之后沿最后一段斜率外推。"""
    v = year + (month - 1) / 12.0
    if v <= _ys[0]: return _ts[0]
    i = bisect.bisect_right(_ys, v) - 1
    if i >= len(_ys) - 1: i = len(_ys) - 2
    return int(round(_ts[i] + (_ts[i+1] - _ts[i]) * (v - _ys[i]) / (_ys[i+1] - _ys[i])))

SCALE=1.30; MAXD=55
def tw(s,px=10.5): return sum((1 if ord(c)>0x2E80 else .6)*px for c in s)
P=json.load(open("data/papers.json"))
for p in P: p["t"]=p["t0"]                       # 幂等:每次从 t0 重算
NLANES = len(json.load(open("data/lanes.json")))
for lane in range(NLANES):
    ns=sorted([p for p in P if p["lane"]==lane], key=lambda p:p["t"])
    half=[(tw(p["label"])/2+9)/SCALE for p in ns]
    for _ in range(400):
        moved=0
        for i in range(len(ns)-1):
            need=half[i]+half[i+1]+3-(ns[i+1]["t"]-ns[i]["t"])
            if need>0:
                a,b=ns[i],ns[i+1]
                da=min(need/2, max(0, MAXD-(a["t0"]-a["t"])))
                db=min(need/2, max(0, MAXD-(b["t"]-b["t0"])))
                if da+db<=0: continue
                a["t"]-=da; b["t"]+=db; moved=1
        if not moved: break
for p in P: p["t"]=int(round(p["t"]))
P.sort(key=lambda p:(p["lane"],p["t"]))
json.dump(P,open("data/papers.json","w"),ensure_ascii=False,indent=1)
print("spread ok")
