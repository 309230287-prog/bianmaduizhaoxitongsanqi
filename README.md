# 商品编码对照系统三期

这是三期独立仓库，只保留三期文档、三期工作台代码和必要运行记录。

不包含一期/旧二期代码。

## 目录

- `phase3_app/backend`：Python/FastAPI 本地服务和业务引擎。
- `phase3_app/frontend`：React + Vite 前端工作台。
- `phase3_app/desktop`：Tauri 桌面壳。
- `phase3_app/scripts`：本地启动脚本。
- `sanqi`：三期需求、业务流程、技术方案、执行计划和原型文档。
- `omc`：本轮修复和验证记录。

## 快速启动

已构建过桌面程序时，双击根目录：

```text
启动三期工作台.bat
```

脚本会先启动 Python 本地服务，然后优先打开 Tauri 桌面程序。

如果桌面程序还没有构建，脚本会回退到浏览器开发模式。

## 开发验证

后端测试：

```powershell
cd phase3_app/backend
python -m pytest -q
```

前端构建：

```powershell
cd phase3_app/frontend
npm install
npm run build
```

桌面构建：

```powershell
cd phase3_app/desktop
npm install
npm run build
```

## 当前验证记录

最近一次本地验证：

- 后端测试：`87 passed`
- 前端构建：通过
- Tauri 桌面构建：通过
- 真实 DeepSeek 小样本验证：已跑通默认前 5 行和 `生抽` 关键词 5 行，结果见 `sanqi/07_交付说明/三期3.1交付验收记录-v0.1.md`

详细记录见：

```text
omc/state/current/2026-04-27-phase3-repair/progress.md
```
