# OCR → 危急值映射（第 2 步）

> 目标：让「拍一张化验单」能同时填好**原始数值**和**状态字段**，从而真正触发 `rule_engine.py` 的危急值报警。
>
> 范围：只改 `backend/ocr_map.py`。不改接口、不改前端（前端第 1 步已经加好 9 个数值框）。
>
> 前置：第 1 步已完成（`App.vue` 有「危急值数值」卡 + 结果页渲染 `critical`）。

---

## 0. 这一步解决什么

第 1 步之后，页面上虽然有了 9 个数值框，但 OCR 还不会填它们——`ocr_map.py` 只映射了状态型字段（`potassium_status / hb_low / plt_status` 等）。

结果就是：

```
拍化验单 → 血钾状态 = 高（有）
          血钾数值 = 空（没有）
                → 危急值 CV-01 永远不触发
```

这一步做完：

```
拍化验单 → 血钾数值 = 6.5  +  血钾状态 = 高
                → CV-01 触发
```

用 `backend/samples/critical_lab_demo.png` 实测，一次能回填 **18 个字段**，提交后命中 **8 条危急值**（CV-01/02/04/05/07/08/11/12）。

---

## 1. 核心难点：一条识别项要落两个字段

原来的 `map_items` 是「一条识别项 → 一个字段」：

```python
spec = _match_spec(name)          # 只返回一个 spec
entry = accum.setdefault(spec["field"], ...)
```

「钾」既对应 `potassium`（数值，给危急值用），又对应 `potassium_status`（状态，给用药规则用）。如果只是给两个 spec 都加 alias，`_match_spec` 只会返回其中一个——匹配分数相同时，**先出现在 `SPECS` 里的赢**。于是：

- 只填数值 → 危急值能报，但用药规则拿不到状态；
- 只填状态 → 用药规则正常，但危急值永远不报。

### 解决思路：数值字段做主字段，状态字段由它「派生」

```python
{
    "field": "potassium", "kind": "number", ...
    "derive": [
        {"field": "potassium_status", "kind": "status",
         "values": {"high": "高", "low": "低", "normal": "正常"}},
    ],
}
```

派生值只依赖 OCR 自己给出的 `flag`（相对这张化验单自己的参考范围是偏高/偏低/正常），**不做任何医学判断**。所以：

- 钾 6.5，参考 3.5-5.3 → `flag=high` → 数值 6.5 + 状态「高」；
- 血红蛋白 65，参考 130-175 → `flag=low` → 数值 65 + `hb_low=True`；
- 纤维蛋白原 0.6，参考 2.0-4.0 → `flag=low` → 数值 0.6 + `coag_abnormal=True`（低纤维蛋白原也算凝血异常）。

---

## 2. 数据流

```
OCR item: 钾 6.5 mmol/L ↑
        │
        ├─ 主字段：potassium = 6.5          → 进「危急值数值」卡
        └─ 派生：potassium_status = 高       → 进「电解质」卡
        │
        ▼  前端核对表（两行都默认勾选）
确认回填 → form.potassium = 6.5
           form.potassium_status = '高'
        │
        ▼  buildPayload()
POST /api/analyze { potassium: 6.5, potassium_status: '高', ... }
        │
        ▼  rule_engine.match()
CV-01 血钾危急值（critical 命中后 advices 被压制）
```

---

## 3. 代码改动（`backend/ocr_map.py`）

> 行号会随文件变化，按「原文」搜索定位。

### 3.1 卡片顺序加上「危急值数值」

**位置**：文件顶部 `CARD_ORDER`。

**原文**：

```python
CARD_ORDER = [
    "血常规", "尿常规", "肝功能", "肾功能", "凝血功能",
    "心肌酶谱", "肌钙蛋白", "电解质", "血脂",
    "空腹血糖和糖化", "超声心动图",
]
```

**改为**：

```python
CARD_ORDER = [
    "血常规", "尿常规", "肝功能", "肾功能", "凝血功能",
    "心肌酶谱", "肌钙蛋白", "电解质", "血脂",
    "空腹血糖和糖化", "超声心动图", "危急值数值",
]
```

作用：`fields` 最后会按 `CARD_ORDER` 排序，加上这一项，8 个可自动回填的数值字段会集中在核对表的最后，和前端那张「危急值数值」卡对应。

---

### 3.2 新增 8 条数值规格（注意插入位置）

**顺序很重要**：数值 spec 必须排在同名状态 spec 的前面，否则 `_match_spec` 会先命中状态，数值永远拿不到。

#### 3.2.1 `hb`：插在 `hb_low` 之前

```python
{
    # 原始数值：进「危急值数值」卡，同时派生 hb_low 供人群标签/用药规则使用
    "field": "hb", "label": "血红蛋白 Hb", "kind": "number", "unit": "g/L",
    "card": "危急值数值",
    "aliases": ["血红蛋白", "血红蛋白浓度", "hgb", "hb"],
    "exclude": ["糖化", "尿", "胎儿", "血红蛋白a1c"],
    "expect_units": ["g/l"], "min": 10.0, "max": 250.0,
    "derive": [
        {"field": "hb_low", "kind": "bool",
         "values": {"low": True, "normal": False, "high": False}},
    ],
},
```

#### 3.2.2 `plt`：插在 `plt_status` 之前

```python
{
    # 原始数值进「危急值数值」卡，同时派生 plt_status
    "field": "plt", "label": "血小板 PLT", "kind": "number", "unit": "×10^9/L",
    "card": "危急值数值",
    "aliases": ["血小板计数", "血小板", "plt"],
    "exclude": ["压积", "体积", "分布", "抗体", "聚集", "相关", "比积"],
    "expect_units": ["109/l", "10e9/l"], "min": 1.0, "max": 2000.0,
    "derive": [
        {"field": "plt_status", "kind": "status",
         "values": {"low": "降低", "normal": "正常", "high": "正常"}},
    ],
},
```

> 注意 `expect_units` 写的是 `109/l`，不是 `10^9/l`。单位归一化会把 `×`、`*`、`^` 删掉，`×10^9/L`、`10^9/L`、`10*9/L` 都会变成 `109/l`。

#### 3.2.3 `inr` 和 `fibrinogen`：插在 `coag_abnormal` 之前

```python
{
    # INR 原始数值进「危急值数值」卡，同时派生 coag_abnormal
    "field": "inr", "label": "INR", "kind": "number", "unit": "",
    "card": "危急值数值",
    "aliases": ["国际标准化比值", "inr"],
    "exclude": ["活动度", "纠正"],
    "expect_units": ["比值", "ratio"], "min": 0.5, "max": 20.0,
    "derive": [
        {"field": "coag_abnormal", "kind": "bool",
         "values": {"high": True, "normal": False, "low": False}},
    ],
},
{
    # 纤维蛋白原原始数值进「危急值数值」卡；降低同样算凝血异常
    "field": "fibrinogen", "label": "纤维蛋白原 Fib", "kind": "number", "unit": "g/L",
    "card": "危急值数值",
    "aliases": ["纤维蛋白原", "fib"],
    "exclude": ["降解"],
    "expect_units": ["g/l"], "min": 0.1, "max": 15.0,
    "derive": [
        {"field": "coag_abnormal", "kind": "bool",
         "values": {"low": True, "normal": False, "high": False}},
    ],
},
```

#### 3.2.4 `hs_ctnt`：插在 `troponin_elevated` 之前

```python
{
    # 只认「高敏/超敏 T」的定量结果，单位必须 ng/mL；普通 cTnI/T 仍只走下面的开关
    "field": "hs_ctnt", "label": "高敏肌钙蛋白 T hs-cTnT", "kind": "number", "unit": "ng/mL",
    "card": "危急值数值",
    "aliases": ["高敏肌钙蛋白t", "超敏肌钙蛋白t", "hs-ctnt", "hsctnt"],
    "exclude": [],
    "expect_units": ["ng/ml"], "min": 0.0, "max": 100.0,
    "derive": [
        {"field": "troponin_elevated", "kind": "bool",
         "values": {"high": True, "normal": False, "low": False}},
    ],
},
```

#### 3.2.5 `potassium`、`sodium`、`co2cp`：插在 `potassium_status` 之前

```python
{
    # 血钾原始数值进「危急值数值」卡，同时派生 potassium_status 供用药规则使用
    "field": "potassium", "label": "血钾 K⁺", "kind": "number", "unit": "mmol/L",
    "card": "危急值数值",
    "aliases": ["血钾", "钾离子", "钾", "k", "k+"],
    "exclude": ["尿钾", "钠钾"],
    "expect_units": ["mmol/l"], "min": 1.0, "max": 10.0,
    "derive": [
        {"field": "potassium_status", "kind": "status",
         "values": {"high": "高", "low": "低", "normal": "正常"}},
    ],
},
{
    "field": "sodium", "label": "血钠 Na⁺", "kind": "number", "unit": "mmol/L",
    "card": "危急值数值",
    "aliases": ["血钠", "钠离子", "钠", "na", "na+"],
    "exclude": ["尿钠", "脑钠", "利钠"],
    "expect_units": ["mmol/l"], "min": 90.0, "max": 200.0,
},
{
    "field": "co2cp", "label": "二氧化碳结合率 CO₂CP", "kind": "number", "unit": "mmol/L",
    "card": "危急值数值",
    "aliases": ["二氧化碳结合率", "二氧化碳结合力", "co2cp", "co2-cp"],
    "exclude": ["分压"],
    "expect_units": ["mmol/l"], "min": 1.0, "max": 50.0,
},
```

---

### 3.3 加字段索引

**位置**：`SPECS` 结束之后。

```python
SPEC_BY_FIELD = {s["field"]: s for s in SPECS}
```

`_apply_derives` 要靠它按字段名找到目标 spec。

---

### 3.4 单字别名只允许精确命中

**位置**：`_alias_score`。

**原文**：

```python
    if norm == a:
        return 1000 + len(a)
    # 2~3 个字母的缩写只允许精确命中，避免 "ck" 误吃 "ckmb"、"pt" 误吃 "aptt"
    if a.isascii() and len(a) <= 3:
        return 0
```

**改为**：

```python
    if norm == a:
        return 1000 + len(a)
    # 单字（钾/钠）只允许精确命中，避免「脑钠肽」误吃「钠」
    if len(a) <= 1:
        return 0
    # 2~3 个字母的缩写只允许精确命中，避免 "ck" 误吃 "ckmb"、"pt" 误吃 "aptt"
    if a.isascii() and len(a) <= 3:
        return 0
```

为什么：`sodium` 的别名里有单字「钠」。原逻辑对中文单字走 `a in norm`，于是「脑钠肽」也会命中钠，把 BNP 当血钠回填。加这一条后，单字只接受「钠」这一整项，`血钠/钠离子` 走完整别名。

---

### 3.5 单位归一化支持 `×10^9/L`

**位置**：`_norm_unit`。

**原文**：

```python
def _norm_unit(unit: str) -> str:
    s = unicodedata.normalize("NFKC", str(unit or "")).lower()
    s = s.replace("μ", "u").replace("µ", "u").replace("²", "2")
    return re.sub(r"\s+", "", s)
```

**改为**：

```python
def _norm_unit(unit: str) -> str:
    s = unicodedata.normalize("NFKC", str(unit or "")).lower()
    s = s.replace("μ", "u").replace("µ", "u").replace("²", "2")
    # ×10^9/L、10*9/L、10^9/L 统一成 109/l
    s = s.replace("×", "").replace("*", "").replace("^", "")
    return re.sub(r"\s+", "", s)
```

为什么：血小板单位在化验单上可能是 `×10^9/L`、`10^9/L`、`10*9/L`，三种写法都必须通过校验，否则血小板数值会被“单位不一致”挡掉，CV-05 就永远不报。

---

### 3.6 文字型高低也能识别

**位置**：`_flag_of` 最后几行。

**原文**：

```python
    t = unicodedata.normalize("NFKC", str(value or ""))
    if any(k in t for k in ("↑", "阳性", "(+)", "＋")):
        return "high"
    if "↓" in t:
        return "low"
    return "normal"
```

**改为**：

```python
    t = unicodedata.normalize("NFKC", str(value or "")).strip()
    if t in ("高", "低"):
        return "high" if t == "高" else "low"
    if any(k in t for k in ("↑", "阳性", "(+)", "＋", "升高", "偏高", "增高")):
        return "high"
    if any(k in t for k in ("↓", "降低", "偏低", "减低")):
        return "low"
    return "normal"
```

为什么：有些单子结果栏写「升高/降低」而不是箭头；没有参考范围时，只能靠文字兜底。

---

### 3.7 新增派生函数

**位置**：`# ================= 主入口 =================` 之后、`def map_items` 之前。

```python
def _apply_derives(accum, spec, source, flag):
    """把一条识别项派生到附加字段（例如 钾 6.5 → potassium + potassium_status）。

    派生只依赖 OCR 自己给出的 flag（相对参考范围的高/低），不做任何医学判断。
    """
    for derive in spec.get("derive", []):
        target = SPEC_BY_FIELD.get(derive["field"])
        if target is None:
            continue
        value = derive["values"].get(flag)
        if value is None:
            continue
        entry = accum.setdefault(target["field"], {"spec": target, "rows": []})
        entry["rows"].append({
            "source": source,
            "number": None,
            "flag": flag,
            "ref_range": source["ref_range"],
            "derived_value": value,
            "derived_from": spec["field"],
            "derived_item": source["item"],
            "derived_source_value": source["value"],
        })
```

> **小白解释**：`accum` 是「字段名 → 这个字段的所有来源」的字典。派生不是重新匹配项目名，而是直接往目标字段的来源列表里追加一行，并打上 `derived_value` 标记。后面输出时，带这个标记的行直接用 `derived_value`，不再重新推导。

---

### 3.8 `map_items`：数值失败也要派生状态

**位置**：`map_items` 里处理 `spec["kind"] == "number"` 的那段。

**原文**：

```python
        if spec["kind"] == "number":
            issue = _unit_issue(spec, unit)
            if issue:
                unmatched.append({**source, "reason": issue})
                warnings.append("%s：%s" % (name, issue))
                continue
            if number is None:
                unmatched.append({**source, "reason": "结果不是数值"})
                warnings.append("%s：结果「%s」不是数值，未回填" % (name, value))
                continue
            if number < spec.get("min", -1e9) or number > spec.get("max", 1e9):
                reason = "数值超出合理范围（%s ~ %s）" % (spec.get("min"), spec.get("max"))
                unmatched.append({**source, "reason": reason})
                warnings.append("%s：%s，请人工录入" % (name, reason))
                continue

        entry = accum.setdefault(spec["field"], {"spec": spec, "rows": []})
        entry["rows"].append({
            "source": source,
            "number": number,
            "flag": flag,
            "ref_range": ref_range,
        })
```

**改为**：

```python
        primary_ok = True
        if spec["kind"] == "number":
            issue = _unit_issue(spec, unit)
            if issue:
                unmatched.append({**source, "reason": issue})
                warnings.append("%s：%s" % (name, issue))
                primary_ok = False
            elif number is None:
                unmatched.append({**source, "reason": "结果不是数值"})
                warnings.append("%s：结果「%s」不是数值，未回填" % (name, value))
                primary_ok = False
            elif number < spec.get("min", -1e9) or number > spec.get("max", 1e9):
                reason = "数值超出合理范围（%s ~ %s）" % (spec.get("min"), spec.get("max"))
                unmatched.append({**source, "reason": reason})
                warnings.append("%s：%s，请人工录入" % (name, reason))
                primary_ok = False

        if primary_ok:
            entry = accum.setdefault(spec["field"], {"spec": spec, "rows": []})
            entry["rows"].append({
                "source": source,
                "number": number,
                "flag": flag,
                "ref_range": ref_range,
            })

        # 数值回填失败（单位不对 / 不是数值 / 超范围）时仍从箭头派生状态或开关，
        # 保证「血红蛋白 8 g/dL」这类情况至少不会丢掉异常状态
        if spec.get("derive"):
            _apply_derives(accum, spec, source, flag)
```

**关键点**：原来的 `continue` 会让整条 item 直接结束；现在改成 `primary_ok = False`，只跳过数值本身，派生照常执行。

举例：血红蛋白 8 g/dL（参考 13-17）。单位不是 g/L → 数值 `hb` 不回填（避免把 8 g/dL 当成 8 g/L 误报 CV-04），但 `flag=low` → `hb_low=True` 仍会回填，贫血标签不丢。

---

### 3.9 输出时合并派生值

**位置**：`map_items` 末尾的 `for spec in SPECS:` 循环。

**A. 数值字段只统计主行**（派生行没有数值）：

```python
        if spec["kind"] == "number":
            primary_rows = [r for r in rows if "derived_value" not in r]
            if not primary_rows:
                continue
            value = primary_rows[0]["number"]
            if len(primary_rows) > 1:
                notes.append("多处出现（%s），取第一条" % "、".join(r["source"]["item"] for r in primary_rows))
            if not any(r["source"]["unit"] for r in primary_rows):
                notes.append("化验单未印单位，已按表单单位回填")
```

**B. 状态字段取最重，派生行直接用 `derived_value`**：

```python
        elif spec["kind"] == "status":
            best, best_note = "正常", None
            for r in rows:
                if "derived_value" in r:
                    v = r["derived_value"]
                    note = "由「%s %s」数值派生" % (r["derived_item"], r["derived_source_value"])
                else:
                    v, note = _status_value(spec, r["source"]["value"], r["flag"], r["ref_range"])
                if STATUS_RANK.get(spec["field"], {}).get(v, 0) > STATUS_RANK.get(spec["field"], {}).get(best, 0):
                    best, best_note = v, note
            value = best
            if best_note:
                notes.append(best_note)
            if len(rows) > 1:
                notes.append("合并 %d 条结果取最重" % len(rows))
```

**C. 开关字段任一为真**：

```python
        else:
            def _row_bool(r):
                if "derived_value" in r:
                    return bool(r["derived_value"])
                return _bool_value(spec, r["source"]["value"], r["flag"])

            value = any(_row_bool(r) for r in rows)
            derived = [r for r in rows if "derived_value" in r]
            if derived:
                notes.append("由「%s」数值派生" % "、".join(
                    "%s %s" % (r["derived_item"], r["derived_source_value"]) for r in derived
                ))
            if len(rows) > 1:
                notes.append("合并 %d 条结果（任一阳性即为是）" % len(rows))
```

**D. 字段级备注**（不是全局 warning）：

```python
        extra_note = FIELD_NOTE.get(spec["field"])
        if extra_note:
            notes.append(extra_note)
```

并在文件上部加：

```python
# 只写进该字段备注、不升级为全局 warning 的提示
FIELD_NOTE = {
    "inr": "CV-07 还需在用药页选择「华法林」。",
    "hs_ctnt": "CV-11 还需在症状页勾选「胸痛」。",
}
```

同时把 `FIELD_CAUTION["coag_abnormal"]` 的措辞从“是否高于参考范围”改成“PT/APTT/INR 是否升高、纤维蛋白原是否降低”，因为现在低纤维蛋白原也会派生 `coag_abnormal=True`。

---

## 4. 单位防线（为什么有些项“不自动填”）

危急值的阈值是按固定单位写的，最怕“数值对、单位错”导致的假报警/漏报警。所以数值字段一律做单位校验，**不做自动换算**：

| 字段 | 接受单位 | 拒绝示例 | 拒绝后行为 |
|---|---|---|---|
| `hb` | `g/L` | `g/dL`（13 g/dL ≈ 130 g/L） | 不填数值，但仍按箭头派生 `hb_low` |
| `plt` | `×10^9/L`、`10^9/L`、`10*9/L` | `10^12/L` | 不填数值 |
| `potassium`/`sodium`/`co2cp` | `mmol/L` | `mEq/L` | 不填数值 |
| `inr` | 空、`比值`、`ratio` | `%`（PT 活动度） | 不填数值 |
| `fibrinogen` | `g/L` | `mg/dL` | 不填数值 |
| `hs_ctnt` | `ng/mL` | `ng/L`（100 ng/L = 0.1 ng/mL） | 不填数值 |
| `baseline_ldl` | `mmol/L` | `mg/dL` | 不填数值 |

拒绝时会在 `unmatched` 里写明原因，并在 `warnings` 里提示“请手动录入”。这比“悄悄换算”安全：医生能看到哪一项没填、为什么没填。

---

## 5. 验收

### 5.1 纯映射单元测试（不联网、不装依赖）

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest test_ocr_critical -v
```

实测：

```
Ran 13 tests in 0.017s
OK
```

覆盖：

- spec 一致性（字段名不重复、派生目标都存在）
- 一条识别项派生多个字段（钾→`potassium`+`potassium_status`，Hb→`hb`+`hb_low`）
- 真实凝血单写法（「活化部分凝血酶时间 (CP3000)」、TT/APTT 比值）→ `coag_abnormal`
- PT 活动度是逆向指标，**不**自动映射（避免正常/异常颠倒）
- 心电图：QT/QTc 420/520 取 QTc=520；心率 35/QTc 520 触发 CV-09/10；结论「窦性心动过缓」→窦性心律
- 映射结果喂给 `rule_engine` 能命中 CV-01/02/04/05/07/08/11/12
- 正常钾 4.2 不产生危急值
- `hb 8 g/dL` 不误填 `hb`，但 `hb_low=True`
- `LDL 124 mg/dL` 不被静默回填
- 「脑钠肽」不会被当成「钠」
- 「白细胞计数」不会被当成「血小板」

### 5.2 真实 OCR（合成化验单）

样例图：[backend/samples/critical_lab_demo.png](backend/samples/critical_lab_demo.png)

实测识别 16 项，映射 18 个字段：

| 字段 | 值 | 来源 |
|---|---|---|
| `hb` | 65 | 血红蛋白 65 g/L ↓ |
| `hb_low` | 是 | 由 Hb 派生 |
| `plt` | 15 | 血小板计数 15 ×10^9/L ↓ |
| `plt_status` | 降低 | 由 PLT 派生 |
| `potassium` | 6.5 | 钾 6.5 mmol/L ↑ |
| `potassium_status` | 高 | 由 K 派生 |
| `sodium` | 118 | 钠 118 mmol/L ↓ |
| `inr` | 4.8 | INR 4.8 ↑ |
| `coag_abnormal` | 是 | 由 INR + 纤维蛋白原派生 |
| `fibrinogen` | 0.6 | 纤维蛋白原 0.6 g/L ↓ |
| `hs_ctnt` | 0.12 | 高敏肌钙蛋白T 0.12 ng/mL ↑ |
| `troponin_elevated` | 是 | 由 hs-cTnT 派生 |
| `co2cp` | 12 | 二氧化碳结合率 12 mmol/L ↓ |
| `scr` | 150 | 肌酐 150 μmol/L ↑ |
| `baseline_ldl` | 3.21 | LDL-C |
| `hba1c` | 6.2 | 糖化血红蛋白 |
| `fbg_status` | 高 | 葡萄糖 6.4 |
| `alt_ast_status` | 轻度升高 | ALT 68 / AST 42 |

提交后（勾上华法林 + 胸痛）：

```
critical = ['CV-01','CV-02','CV-04','CV-05','CV-07','CV-08','CV-11','CV-12']
```

未回填：总胆红素（仅提示黄疸）、白细胞计数（不映射血小板）。

### 5.3 浏览器端到端

1. 后端 `uvicorn api:app --reload`，前端 `npm run dev`。
2. 辅助检查 → 「上传整张化验单」→ 选 `backend/samples/critical_lab_demo.png`。
3. 核对表应出现 18 行，数值行在「危急值数值」分组，派生的状态行带“由「…」数值派生”备注。
4. 确认回填 → 第 3 步对应输入框有值。
5. 用药页选「华法林」，症状页勾「胸痛」，提交。
6. 结果页顶部应出现 8 张深红危急值卡。

---

## 6. 别人怎么复现

### 6.1 只验映射（最快）

需要 Python 3.8+，**不需要** FastAPI / 向量库 / API Key：

```powershell
cd pci-med/backend
python -m unittest test_ocr_critical -v
```

### 6.2 验完整 OCR

1. 后端 venv 里要有 `openai`，`backend/.env` 配好 `DASHSCOPE_API_KEY`。
2. 启动 `uvicorn api:app --reload`。
3. 用 `backend/samples/critical_lab_demo.png` 走一遍页面（见 5.3）。
4. 这一步会真实调用 qwen3-vl-plus，产生少量费用。

### 6.3 文件清单

- 改：`backend/ocr_map.py`
- 新增：`backend/test_ocr_critical.py`（纯映射回归）
- 新增：`backend/samples/critical_lab_demo.png` + `README.md`（合成样例）
- 不改：`api.py`、`ocr.py`、前端（第 1 步已就绪）

---

## 7. 边界

1. **危急值数值字段分两处**：8 个在「危急值数值」卡（Hb/PLT/K/Na/INR/Fib/hs-cTnT/CO₂CP），心电图卡另有 `heart_rate / qtc / qtc_baseline`；`baseline_scr` 与 `qtc_baseline` 必须手工填。CV-03 校正钙仍缺 `calcium_corrected`，这是 12 条里唯一没接的。
2. **药物和症状不会从化验单读**：CV-07 需要手工选「华法林」，CV-11 需要手工勾「胸痛」。字段备注里已经提示。
3. **状态派生只做“高/低/正常”**：ALT/AST 的“轻度/重度”、CK 的“中度/重度”仍由原来的状态 spec + 倍数逻辑处理，不受影响。
4. **普通 cTnI/T 不填数值**：只置 `troponin_elevated=True`。`hs_ctnt` 只认高敏/超敏 T + `ng/mL`，因为危急值阈值 0.07 是 hs-cTnT 的 ng/mL 阈值。
5. **单位不一致不自动换算**：宁可让医生手填，也不把 `g/dL` 当 `g/L`。
6. **OCR 可能看错**：所以前端核对表必须逐项确认；这里做的是“确定性映射”，不是“确定性读图”。
