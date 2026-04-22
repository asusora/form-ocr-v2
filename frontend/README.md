# Form OCR Frontend

前端基于 `Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus`，包含模板列表、模板编辑器和识别校对三个核心页面。

## 启动

```bash
cd frontend
npm install
npm run dev
```

默认访问 `http://localhost:5174`。开发服务器会把 `/api` 代理到 `http://localhost:8020`。

## 构建

```bash
npm run build
```

## 测试

```bash
npm run test
```

更详细的前端使用说明、测试配置、手工测试流程和验收步骤，请查看：

```bash
../docs/frontend-usage-and-testing-guide.md
```

## 环境变量

如需自定义 API 前缀或开发代理目标，可创建 `.env.local`：

```bash
VITE_API_BASE_URL=/api
VITE_API_PROXY_TARGET=http://localhost:8020
```

如果前端构建产物和后端不在同一个来源下部署，需要把 `VITE_API_BASE_URL` 改成完整地址，例如：

```bash
VITE_API_BASE_URL=http://localhost:8020/api
```

## 手工验收建议

1. 在模板列表页上传空白 PDF，新建模板后应自动跳转到模板编辑器。
2. 在模板编辑器切换到“画框新增字段”模式，拖拽生成字段框，再在右侧配置字段类型并保存。
3. 在模板列表页选择“去识别”，上传待识别 PDF 后应跳转到识别页，并在 `pending` 或 `processing` 状态下自动轮询。
4. 识别成功后，左侧应显示页图和字段框，拖框后右侧字段状态应变为 `manual_adjusted`。
5. 点击“重新识别”应触发单字段重跑，点击“保存结果”应调用批量保存接口。
6. 点击“下载 JSON”或“下载 Excel”应触发导出接口。
