# -*- coding: utf-8 -*-
"""测 /api/analyze 接口：不用浏览器、不依赖 /docs 页面。
前提：另一个窗口里 uvicorn api:app --reload 正在跑（别关）。
运行：python test_api.py
"""
import json
import urllib.request

url = "http://127.0.0.1:8000/api/analyze"
payload = {
    "scenario": "ACS",
    "post_pci": True,
    "post_pci_months": 1,
    "age": 62,
    "sex": "男",
    "af": True,
    "cha2ds2_vasc": 3,
    "has_bled": 2,
    "diabetes": True,
    "ascvd_risk": "超高危",
    "on_dapt": True,
    "surgery_date": "2026-09-10",
    "stent_type": "药物洗脱支架×2",
    "discharge_plan": "DAPT 12个月",
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))

print("标签：", data["tags"])
if data["redlines"]:
    print("红线命中：")
    for x in data["redlines"]:
        print(f"  [{x['id']}] {x['name']} → {x['action']}")
else:
    print("红线：无")
    print("常规建议：")
    for a in data["advices"]:
        print(f"  [{a['id']}｜{a['level']}] {a['action']}  （出处 {a['source']}）")