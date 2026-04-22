# 表单 OCR 模板化识别系统 — 设计文档

- 日期：2026-04-22
- 状态：初稿（待用户确认后进入实现规划）
- 定位：单租户 demo 级配置化 Web 工具（先做 IRD WR1A 类表单，架构预留未来多业务 / 多租户扩展）

---

## 1. 背景与目标

### 1.1 问题

业务方（当前首批：IRD）有大量同类表单 PDF（如 WR1A 电业工程证明），需要从中提取结构化字段。传统方案：
- 纯坐标模板 → 同类表单因文本换行、条码、扫描偏移导致框选失效
- 纯端到端大模型 → 成本高、结果不稳定、无法复用已有校对习惯

### 1.2 目标

做一个 **配置化的 PDF 模板识别 Web 工具**，特性：
- 业务方自行上传空白模板 PDF、框选字段、定义类型，保存成"模板"
- 上传同类 PDF 即可按模板自动识别，即便格式有差异（换行、条码、轻微偏移、扫描件特征）也能容错
- 识别失败可以人工在界面上拖拽调整框 + 修正 OCR 文本
- 当前版本按"单团队内网 demo"设计，模板之间相互独立；后续如要扩展到多业务共享，再补租户与权限隔离

### 1.3 非目标（MVP 不做）

- 批量上传 / 异步队列（明确一次只处理一份 PDF）
- 审批流 / 多用户角色权限 / 租户隔离（demo 阶段默认单团队使用）
- OCR 结果反馈学习 / 模型微调
- 对外 REST API（仅作为 Web 工具使用；接口预留但不对外公布）

---

## 2. 核心用户流程

### 2.1 配置模板（一次性）

1. 业务人员进入系统，点"新建模板"
2. 上传空白模板 PDF（如 WR1A 空白表）
3. 系统渲染 PDF 每页成图片
4. 用户在图片上拖拽画框，为每个框配置：字段名、显示名、字段类型（text/date/checkbox/multiline_text/option_select/signature/table）
5. 保存 → 系统为每个框自动提取周围的稳定文本作为锚点

### 2.2 识别一份 PDF

1. 选择一个已有模板
2. 上传目标 PDF
3. 系统立即创建 recognition 任务并返回 `recognition_id`，前端进入识别页并显示 `processing`
4. 后端在进程内后台任务执行：转图 → 整页 OCR 缓存 → 页级粗对齐 → 字段级局部对齐 → 切图 → 按字段类型抽取
5. 前端轮询任务状态；成功后进入校对态：左侧 PDF + 对齐后的框，右侧字段列表 + OCR 结果
6. 对有问题的字段：拖拽框调整位置 → 点"重新识别"按钮 → 后端基于缓存页 OCR 和新 `aligned_bbox` 重跑单字段抽取 → 或直接修改右侧文本框
7. 确认无误，点"保存结果" → 导出 JSON 或 Excel

### 2.3 修改模板

允许修改已有模板的字段（增删改、调整位置、改类型、改锚点）。**改模板不影响已有历史识别结果**（历史结果已经人工校对过，不重跑）。

---

## 3. 系统架构

### 3.1 总体形态

单仓库 monorepo，前后端分离。

```
form-ocr-v2/
├── frontend/              # Vue 3 + TypeScript + Vite
│   ├── src/
│   │   ├── views/         # TemplateList / TemplateEditor / Recognize
│   │   ├── components/    # PdfCanvas / FieldPanel / TableConfig ...
│   │   ├── stores/        # Pinia
│   │   └── api/           # axios 封装
│   └── package.json
└── backend/               # FastAPI + Python 3.11
    ├── api/               # 路由层（FastAPI routers）
    ├── template/          # 模板 CRUD + 锚点自动提取
    ├── alignment/         # 对齐引擎（纯算法、无副作用）
    ├── ocr/               # OCR 引擎抽象 + PaddleOCR 实现
    ├── extractors/        # 字段类型插件（每种 field_type 一个类）
    ├── pipeline/          # 识别主流程 orchestrator
    ├── storage/           # 文件 / DB 访问封装
    ├── schemas/           # Pydantic 模型
    └── pyproject.toml
```

### 3.2 技术栈

**前端**
- Vue 3 + TypeScript + Vite + Pinia
- Element Plus（UI 组件库）
- `pdf.js`（PDF 渲染为 canvas）
- `fabric.js`（canvas 上层的框选/拖拽/resize）

**后端**
- Python 3.11 + FastAPI + Pydantic v2
- SQLAlchemy 2 + PyMySQL（MySQL 8.0+）
- Alembic（迁移）
- PyMuPDF（PDF → 图像，无外部依赖，Windows 友好）
- PaddleOCR（默认 OCR 引擎，模型：`ch_PP-OCRv4`）
- OpenCV-Python（图像处理、对齐变换、checkbox/option_select 检测）
- Pillow（图像切图保存）
- rapidfuzz（锚点模糊匹配）

### 3.3 存储

- **数据库**：MySQL 8.0+，字符集 `utf8mb4`。JSON 字段用 MySQL 原生 JSON 类型
- **文件**：本地磁盘 `./data/`
  - 模板 PDF：`./data/templates/{template_id}/source.pdf`
  - 模板页图像缓存：`./data/templates/{template_id}/pages/{n}.png`
  - 模板页 OCR 缓存：`./data/templates/{template_id}/ocr/{n}.json`
  - 识别输入：`./data/recognitions/{recognition_id}/input.pdf`
  - 识别页图像缓存：`./data/recognitions/{recognition_id}/pages/{n}.png`
  - 识别页 OCR 缓存：`./data/recognitions/{recognition_id}/ocr/{n}.json`
  - 识别切图：`./data/recognitions/{recognition_id}/crops/{field_id}.png`
- **生产升级路径**：MySQL 保持，本地磁盘 → 对象存储（S3/OSS）。通过 `storage` 模块抽象，切换只改一个模块

### 3.4 模块职责

| 模块 | 职责 | 依赖 |
|---|---|---|
| `api` | 对外 REST 端点、请求校验、错误映射 | 所有业务模块 |
| `template` | 模板 CRUD；保存字段时自动提取锚点 | `ocr`, `storage` |
| `alignment` | 给定模板锚点 + 目标页 OCR 结果，返回每个字段的新坐标；纯算法 | 无（可单测） |
| `ocr` | 统一接口 `recognize(image) -> list[TextBlock]`；PaddleOCR 是默认实现 | 无 |
| `extractors` | 每种 `field_type` 一个 `FieldExtractor` 实现 | `ocr` |
| `pipeline` | 串起识别主流程 | `template`, `alignment`, `ocr`, `extractors`, `storage` |
| `storage` | 文件路径 / DB 访问封装 | 无 |

### 3.5 OCR 引擎抽象

```python
class OcrEngine(Protocol):
    def recognize(self, image: np.ndarray) -> list[TextBlock]:
        """整页 OCR。返回 TextBlock: {text, bbox:[x1,y1,x2,y2], confidence}"""
```

默认注册 `PaddleOcrEngine`。未来加 Azure/Google/阿里云 OCR 时，实现 Protocol 并注册到引擎工厂即可，上层业务不动。

### 3.6 FieldExtractor 插件架构

```python
class FieldExtractor(Protocol):
    field_type: str
    def extract(self, image: np.ndarray, bbox: BBox, context: ExtractContext) -> ExtractResult:
        """给定切图、bbox、上下文（含该页 OCR 结果），返回抽取结果"""
```

每种字段类型独立实现，不在主流程里 if-else 堆叠。加新类型（如金额 `amount`）= 写一个新类 + 注册。

---

## 4. 数据模型

### 4.1 `templates`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | CHAR(36) PK | UUID |
| name | VARCHAR(128) | 模板名，如 "WR1A" |
| description | TEXT | 备注 |
| source_pdf_path | VARCHAR(512) | 空白模板 PDF 路径 |
| page_count | INT | 页数 |
| render_dpi | INT | 转图 DPI（默认 200，所有坐标基于此） |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| deleted_at | DATETIME NULL | 软删除 |

### 4.2 `template_fields`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | CHAR(36) PK | |
| template_id | CHAR(36) FK | |
| page | INT | 页号（从 1 起） |
| name | VARCHAR(64) | 英文字段名 |
| label | VARCHAR(128) | 显示名 |
| field_type | ENUM | `text` / `multiline_text` / `date` / `checkbox` / `option_select` / `signature` / `table` |
| bbox | JSON | `{x1, y1, x2, y2}` 模板像素坐标 |
| anchors | JSON | `[{text, template_bbox, offset_from_field}]` |
| options | JSON NULL | `option_select` 专用：`[{value, labels[]}]` |
| columns | JSON NULL | `table` 专用：列定义 `[{name, label, type, x_ratio[]}]` |
| row_detection | JSON NULL | `table` 专用：`{"mode": "by_horizontal_lines" \| "by_text_rows" \| "fixed_count", "count": N}` |
| sort_order | INT | 右侧字段列表显示顺序 |

唯一约束：`(template_id, name)`。

### 4.3 `recognitions`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | CHAR(36) PK | |
| template_id | CHAR(36) FK | 来源模板 ID；模板软删除后仍可读取（改模板不影响历史识别） |
| template_snapshot | JSON | 创建时冻结的模板定义快照。结构：`{name, render_dpi, page_count, fields: [<完整 template_field 定义, 含 bbox/anchors/options/columns/row_detection>]}`。识别后续任何操作（重算字段、导出）都以此为准，不读 `template_fields` 表 |
| input_pdf_path | VARCHAR(512) | |
| page_count | INT | |
| status | ENUM | `pending` / `processing` / `success` / `failed` |
| error_message | TEXT NULL | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 4.4 `recognition_fields`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | CHAR(36) PK | |
| recognition_id | CHAR(36) FK | FK 到 `recognitions.id`，ON DELETE CASCADE |
| template_field_id | CHAR(36) | 仅记录来源字段 ID 的普通列，**不设 FK 约束**（模板字段删除后，历史识别结果保持完整，字段定义仍可从 `recognitions.template_snapshot` 还原） |
| field_name | VARCHAR(64) | 冗余存字段名，方便查询与导出 |
| aligned_bbox | JSON | 对齐后坐标 |
| raw_value | JSON | OCR 原始结果（text 存字符串，table 存二维数组，option_select 存选中 value 等） |
| edited_value | JSON NULL | 用户编辑后；null 表示未编辑 |
| confidence | FLOAT NULL | |
| crop_path | VARCHAR(512) | 切图路径 |
| alignment_status | ENUM | `auto` / `manual_adjusted` / `alignment_failed` |

---

## 5. 核心流程

### 5.1 建模板

```
用户上传空白 PDF
  ↓
后端 PyMuPDF 按 render_dpi 转图（每页一张 PNG）缓存
  ↓
对每页做整页 OCR，缓存结果到 `./data/templates/{template_id}/ocr/{n}.json`（用于后续锚点提取）
  ↓
前端显示 PDF 图片，用户拖拽画框、填字段名/类型
  ↓
用户点保存 → POST /api/templates/{id}/fields
  ↓
后端对每个字段自动提取锚点：
  - 从该页整页 OCR 结果里找"稳定文本"候选
    - 排除：落在任何字段框内的 OCR 块（overlap > 0.3）
    - 排除：长度 < 2 字符 或 纯数字
  - 为每个字段挑 2-3 个锚点，方位分散（左/上/右分布，避免共线）
  - 记录 {text, template_bbox, offset_from_field}
  ↓
写入 templates + template_fields
```

**关键点**：锚点在"保存字段时"提取，而非上传 PDF 时，因为必须等到用户画完所有框才知道哪些 OCR 块是"变量"（落在框内）、哪些是"固定文本"（可当锚点）。

### 5.2 识别

``` 
用户选模板 + 上传目标 PDF → POST /api/recognitions
  ↓
后端创建 recognition（status=pending），冻结 template_snapshot，并立即返回 `202 Accepted + recognition_id`
  ↓
后台任务启动，status=processing
  ↓
PyMuPDF 转图（同 render_dpi），缓存 `./data/recognitions/{recognition_id}/pages/{n}.png`
  ↓
每页做整页 OCR，得到 `List[TextBlock]` 并缓存到 `./data/recognitions/{recognition_id}/ocr/{n}.json`
  ↓
按 page 聚合该页所有字段锚点，先做页级粗匹配，生成 `global_matrix`（见 §6）
  ↓
对每个 template_field（按 page 分组）：
  ├─ 从页级已匹配锚点中挑离该字段最近的 2-3 个，计算字段局部矩阵
  ├─ 投射 bbox → aligned_bbox
  ├─ 按 aligned_bbox 切图，存为 crop_path
  └─ 按 field_type 调用对应 FieldExtractor：
      - text: 直接使用缓存的整页 OCR 结果筛在 aligned_bbox 内的文本块拼接 + strip
      - multiline_text: 同 text，但按行合并（y 坐标聚类）
      - date: 基于 text 结果正则提取日期并标准化（DD/MM/YYYY）
      - checkbox: 对切图做 OpenCV 前景像素密度阈值判定 → bool
      - option_select: 先用切图视觉检测；必要时对切图局部 OCR，再做三级 fallback（见 §5.4）
      - signature: 不识别，仅保留切图；raw_value = null
      - table: 行列拆分时优先复用整页 OCR；单元格缺失时才对局部切图补 OCR（见 §5.5）
  ↓
status=success 或 failed；前端通过 GET /api/recognitions/{id} 拉取结果
```

### 5.3 校对与修正

``` 
前端打开 /recognitions/{id}
  ↓
若 status=processing：显示处理中占位并轮询详情接口
  ↓
若 status=success：加载目标 PDF 页图像 + recognition_fields（含 aligned_bbox 和 raw_value）
  ↓
左侧画布叠加所有 bbox：
  - 默认灰色边框
  - alignment_status=alignment_failed 的红色
  ↓
用户操作：
  (a) 拖拽某个框 → 前端更新本地 bbox state → 出现"重新识别"按钮
      → 点按钮 → POST /api/recognitions/{id}/re-extract/{field_id} body:{aligned_bbox}
      → 后端优先复用该页 OCR 缓存；若字段类型需要，再对新 bbox 做局部 OCR / 图像分析
      → 返回新 raw_value
      → 前端更新显示
  (b) 修改右侧文本框 → 本地 state 更新（不立即提交）
  (c) 点"保存结果" → PUT /api/recognitions/{id}/fields
      → 批量写回 edited_value + aligned_bbox + alignment_status=manual_adjusted
  (d) 点"下载 JSON" / "下载 Excel" → GET .../export?format=
```

### 5.4 `option_select` 的三级识别策略

1. **圈选检测**（`cv2.HoughCircles`）：在 bbox 图像里找圆圈；用每个选项文本的坐标和圆心比对，找被圈中的选项
2. **划除检测**：形态学（`cv2.morphologyEx` + `HoughLinesP`）找横线穿过的字符；被划掉的选项排除，剩下的就是选中项
3. **手写匹配**：对 bbox 做 OCR，把识别到的文字与 `options[].labels` 做模糊匹配（rapidfuzz），命中返回对应 `value`

任何一级命中则停止，输出选中的 `value`。三级都失败返回 `null`，前端在字段高亮提示人工确认。

### 5.5 `table` 拆分

```
表格对齐 → 得到表格整体 aligned_bbox
  ↓
按 row_detection 拆行：
  - by_horizontal_lines: cv2.HoughLinesP 检测水平线
  - by_text_rows: 整页 OCR 结果里落在 bbox 内的文本按 y 坐标聚类（DBSCAN/简单阈值）
  - fixed_count: 均分为 N 行
  ↓
对每行：按 columns[].x_ratio 切出每个单元格的 sub_bbox
  ↓
对每个单元格：按列的 type 递归调用对应 FieldExtractor（text/date/checkbox/...）
  ↓
聚合：raw_value = [{col1: val, col2: val, ...}, ...]
```

注意：表格的单元格不单独存切图（存太多），只在前端校对时 on-demand 切。

---

## 6. 对齐算法详细设计

### 6.1 锚点自动提取（建模板时）

```python
def extract_anchors_for_field(field_bbox, page_ocr_blocks, all_field_bboxes, n=3):
    candidates = []
    for block in page_ocr_blocks:
        if any(iou(block.bbox, f) > 0.3 for f in all_field_bboxes):
            continue
        if len(block.text.strip()) < 2 or block.text.strip().isdigit():
            continue
        distance = bbox_distance(block.bbox, field_bbox)
        candidates.append((distance, block))
    candidates.sort(key=lambda x: x[0])
    return pick_diverse_anchors(candidates, n)  # 方位分散（左/上/右）
```

`pick_diverse_anchors`：把候选按相对字段的方位（上/下/左/右 四象限）分桶，每桶挑最近的一个，再不够数量再从最近的里补。目的是避免锚点共线（共线会让仿射矩阵退化）。

### 6.2 锚点匹配（识别时）

```python
def build_global_alignment(page_anchors, target_ocr_blocks):
    candidate_pairs = []
    for anchor in page_anchors:
        topk = rapidfuzz.process.extract(
            anchor.text,
            [b.text for b in target_ocr_blocks],
            scorer=rapidfuzz.fuzz.ratio,
            limit=3,
        )
        for text, score, index in topk:
            if score < 70:
                continue
            block = target_ocr_blocks[index]
            candidate_pairs.append(CandidatePair(
                template_point=center(anchor.template_bbox),
                target_point=center(block.bbox),
                score=score,
                anchor_text=anchor.text,
            ))
    return estimate_best_transform(candidate_pairs)
```

这里不在锚点匹配阶段直接用"离模板坐标最近"做去重，因为此时目标页还未完成对齐，模板坐标与目标页坐标不可直接比较。正确做法是：

1. 先为每个锚点保留 `top-k` 候选，而不是立刻选唯一命中
2. 在页级范围内用 RANSAC / 最小二乘求一个粗 `global_matrix`
3. 再把模板锚点投影到目标页，用投影点和候选点的距离做二次消歧

### 6.3 页级消歧 + 变换矩阵

```python
def finalize_anchor_match(anchor, candidate_blocks, global_matrix):
    predicted = apply_matrix(center(anchor.template_bbox), global_matrix)
    chosen = min(candidate_blocks, key=lambda b: dist(center(b.bbox), predicted))
    return AnchorMatch(
        template_point=center(anchor.template_bbox),
        target_point=center(chosen.bbox),
        score=chosen.score,
    )
```

| 匹配锚点数 N | 变换类型 | 参数 | 实现 |
|---|---|---|---|
| ≥ 3 | 仿射变换 | 6 | `cv2.estimateAffinePartial2D` 或最小二乘 |
| 2 | 相似变换 | 4 | 平移 + 缩放 + 旋转 |
| 1 | 纯平移 | 2 | dx, dy |
| 0 | 无变换 | — | 直接用模板坐标 + `alignment_status=alignment_failed` |

≥ 4 锚点时用 RANSAC 剔除 outlier。

`global_matrix` 的求解对象是"整页锚点集合"。字段级局部矩阵必须建立在这个页级结果之上，而不是每个字段各自重新从零匹配一遍锚点。

### 6.4 局部对齐（关键）

为应对"某段多一行导致后续字段整体下推"这类差异，**每个字段独立用离自己最近的锚点计算局部矩阵**，而非全页一个矩阵：

```python
def align_field(field, page_anchor_matches, global_matrix):
    nearest = sorted(
        page_anchor_matches,
        key=lambda a: dist(a.template_point, center(field.bbox))
    )[:3]
    if len(nearest) >= 2:
        local_matrix = compute_transform(nearest)
        return apply_matrix(field.bbox, local_matrix), "auto"
    if global_matrix is not None:
        return apply_matrix(field.bbox, global_matrix), "auto"
    return field.bbox, "alignment_failed"
```

### 6.5 Fallback 策略

| 情况 | 处理 |
|---|---|
| 某字段局部锚点不足 2 个 | 用全页 `global_matrix` |
| 整页只有 1 个有效锚点 | 只做平移 |
| 整页所有锚点都失败 | 直接用模板 bbox + `alignment_status=alignment_failed` |
| 变换后 bbox 超出页面 | Clamp 到页面边界 |
| 匹配分数 60-69 | 作为低置信候选参与 RANSAC，但不会单独直接命中 |

**核心原则**：算法层永远不抛异常阻塞流程，失败当成一种"结果"返回，让用户在校对界面手工调整。

---

## 7. 前端 UI 设计

### 7.1 模板列表页（`/`）

- 卡片或表格显示所有模板：名称、字段数、更新时间、操作（编辑/删除）
- 顶部"新建模板"按钮 → 弹窗上传 PDF → 跳转模板编辑器
- 每行"去识别"按钮 → 弹窗上传 PDF → 创建 recognition → 跳识别页

### 7.2 模板编辑器（`/templates/:id`）

- 布局：左 70%（PDF 画布）+ 右 30%（字段列表 + 选中字段配置 + 锚点预览）
- PDF 渲染：pdf.js → canvas；fabric.js 覆盖层支持画矩形、选中、拖拽、resize、右键删除
- 多页切换：底部页码
- 右侧选中字段时显示类型专属配置面板：
  - `text/multiline_text/date/checkbox/signature`：只需 name + label + type
  - `option_select`：追加选项编辑器（可增删选项，每项含 value + labels[]）
  - `table`：追加列定义表格 + 行检测模式选择；有"按视觉分割"按钮，自动检测横竖线帮用户初始化列/行
- 锚点预览：选中字段时显示系统提取的锚点，允许用户勾选/反选/手动添加（都是 optional，全自动为默认）

### 7.3 识别校对页（`/recognitions/:id`）

- 布局：左 60%（PDF + 框）+ 右 40%（字段结果）
- `status=processing` 时显示处理中骨架屏 + 轮询状态
- `status=success` 时左侧显示目标 PDF 渲染 + 所有字段的对齐框
  - 灰色框 = 默认
  - 绿色框 = 已人工确认（edited_value 非空 或 alignment_status=manual_adjusted）
  - 红色框 = alignment_status=alignment_failed 或类型校验失败（如 date 字段识别不出日期格式）
  - 点击框 ↔ 右侧字段同步高亮
  - 拖拽框 → 字段行出现"🔄 重新识别"按钮
- 右侧：字段卡片列表，按 sort_order 排序
  - `text/multiline_text/date`：文本输入框（可编辑）
  - `checkbox`：勾选框
  - `option_select`：单选按钮组 + 原始选项高亮
  - `signature`：切图展示（不可编辑）
  - `table`：可编辑表格组件（Element Plus ElTable，每格输入框 + 整行"🔄"按钮）
- 底部：保存结果 + 下载 JSON + 下载 Excel

### 7.4 上传识别 PDF 的入口

模板列表页点"去识别"→ 弹窗（选模板 + 拖拽上传）→ 创建 recognition → 跳识别页。

---

## 8. API 清单

```
# 模板
POST   /api/templates                       上传空白 PDF，创建模板
GET    /api/templates                       列表
GET    /api/templates/{id}                  详情（含所有字段）
PUT    /api/templates/{id}                  改模板元信息（name/description）
DELETE /api/templates/{id}                  软删
GET    /api/templates/{id}/pages/{n}        模板页图像 PNG
POST   /api/templates/{id}/fields           批量保存字段（触发锚点提取）
PUT    /api/templates/{id}/fields/{fid}     改单个字段
DELETE /api/templates/{id}/fields/{fid}

# 识别
POST   /api/recognitions                    multipart: pdf + template_id，创建任务并返回 {id, status}
GET    /api/recognitions/{id}               返回状态；success 时附带完整字段结果
GET    /api/recognitions/{id}/pages/{n}     目标 PDF 页图像
GET    /api/recognitions/{id}/crops/{fid}   单字段切图
POST   /api/recognitions/{id}/re-extract/{fid}   body: {aligned_bbox}，重算单字段
PUT    /api/recognitions/{id}/fields        批量保存 edited_value / aligned_bbox
GET    /api/recognitions/{id}/export?format=json|xlsx
```

元数据类接口统一 JSON 响应，错误格式：`{"detail": "message", "code": "ERROR_CODE"}`；页图 / 切图 / 导出接口返回文件流。

---

## 9. 错误处理

| 错误 | HTTP | 前端行为 |
|---|---|---|
| 上传非 PDF | 400 | 提示文件类型错误 |
| PDF 损坏 / 加密 | 400 | 提示建议重新导出 |
| OCR 处理超时（默认 90s，可配置） | 200 / 202 后续查询为 `failed` | `recognition.status=failed`，显示 error_message，建议重传 |
| 对齐全失败 | 200（非错） | `alignment_status=alignment_failed`，红框提示 |
| 字段类型校验失败（如 date 无法解析） | 200 | 字段红色高亮，但仍返回 raw_value |
| DB 连接失败 | 500 | 通用错误页 |

**核心原则**：算法失败不是异常，而是一种返回值。仅在"无法完成整个流程"（PDF 损坏、OCR 超时）时才返回错误状态。

---

## 10. 测试策略

### 10.1 单元测试（pytest）

- `alignment/`：构造模板锚点 + 模拟变形的 OCR 结果，断言变换矩阵和投射坐标
- `extractors/`：每种 FieldExtractor 独立测试
  - `text`: 简单拼接 + 去空格
  - `date`: 各种日期格式 → 标准化
  - `checkbox`: 黑/白样例图 + 阈值边界
  - `option_select`: 圈选/划除/手写三级策略各自构造样例
  - `table`: 构造 mock 行列切分 + 递归 extractor
- `template/anchors`：给定 OCR 结果和字段框，验证挑出的锚点符合规则（方位分散、排除变量）

### 10.2 集成测试

- 准备 3-5 张真实 WR1A 样例 PDF 作为固定测试集（含空白、填写件、不同格式变种）
- 配置一个"黄金模板"+ 对应"期望输出"JSON
- 端到端跑完整识别流水线，断言结果与期望 JSON 差异（字段级编辑距离）在阈值内

### 10.3 前端测试（MVP 低优先级）

- Vitest 单测关键组件：`PdfCanvas` 的框选逻辑、坐标转换
- 不做 E2E（人工验收）

---

## 11. 非功能性约束

- **性能**：单份 2 页 PDF 端到端识别 ≤ 10 秒（PaddleOCR 冷启动除外）
- **并发**：单进程单 worker + 进程内后台任务（Demo 够用，不引入外部消息队列）
- **PaddleOCR 模型**：`ch_PP-OCRv4`，启动时预加载避免首请求冷启动
- **字符集**：UTF-8 / `utf8mb4`
- **文件大小**：上传 PDF ≤ 20MB
- **Python 版本**：3.11（PaddleOCR 兼容性考虑，避开 3.12）

---

## 12. 范围边界与未来扩展

### MVP 范围（本设计覆盖）

- 单团队单租户 demo 使用
- 单份 PDF 识别
- 7 种字段类型（含 table）
- 模板 CRUD + 锚点自动提取
- 校对界面（拖拽调整 + 文本编辑）
- JSON / Excel 导出
- MySQL 持久化

### 明确不在本版本（后续迭代）

- 批量上传 + 异步队列 + 置信度分拣
- 多用户权限 / 组织隔离
- 云 OCR 引擎实现（抽象已留，实现待需求）
- 视觉特征全局对齐（Hybrid 方案 2 的前置步骤）
- 反馈学习 / 模板自优化
- 对外开放 REST API（现在只服务于自己的前端）

### 扩展路径

- **性能不够**：把 `pipeline` 改成 Celery 异步，`status=processing` 时前端轮询
- **对齐精度不够**：加视觉粗对齐层（OpenCV ORB + 单应性）到 `alignment` 模块最前面
- **字段类型不够**：新增 `FieldExtractor` 实现 + 枚举即可
- **多租户**：在所有表加 `tenant_id`；前端加登录 + 模板按租户隔离

---

## 附录 A：关键数据结构（Pydantic）

```python
class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class Anchor(BaseModel):
    text: str
    template_bbox: BBox
    offset_from_field: tuple[float, float]  # (dx, dy) 从字段中心到锚点中心

class OptionDef(BaseModel):
    value: str                 # 归一化输出值，如 "yes"
    labels: list[str]          # 匹配用的原文，如 ["是", "Y"]

class ColumnDef(BaseModel):
    name: str                  # 列英文名
    label: str                 # 列显示名
    type: Literal["text","multiline_text","date","checkbox"]  # 表格单元格允许的子类型
    x_ratio: tuple[float, float]  # (start, end) 相对表格宽度 0-1

class RowDetectionConfig(BaseModel):
    mode: Literal["by_horizontal_lines","by_text_rows","fixed_count"]
    count: int | None = None   # 仅 mode=fixed_count 时必填

class TemplateField(BaseModel):
    id: UUID
    template_id: UUID
    page: int
    name: str
    label: str
    field_type: Literal["text","multiline_text","date","checkbox","option_select","signature","table"]
    bbox: BBox
    anchors: list[Anchor]
    options: list[OptionDef] | None = None          # 仅 option_select
    columns: list[ColumnDef] | None = None          # 仅 table
    row_detection: RowDetectionConfig | None = None # 仅 table
    sort_order: int

class TextBlock(BaseModel):
    text: str
    bbox: BBox
    confidence: float

class ExtractResult(BaseModel):
    raw_value: Any                    # 类型随 field_type 变化：
                                      # text/multiline_text/date → str
                                      # checkbox → bool
                                      # option_select → str (OptionDef.value) | None
                                      # signature → None
                                      # table → list[dict[str, Any]]
    confidence: float | None
    crop_path: str | None
```
