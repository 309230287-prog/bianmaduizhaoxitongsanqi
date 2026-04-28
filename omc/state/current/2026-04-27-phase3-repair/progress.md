# 2026-04-27 三期代码检查与修复记录

## 范围

本次按三期 3.1 工程执行计划检查 `phase3_app`，重点修复会影响主线闭环的缺口：

- 003 多轮引擎入口。
- 运行看板状态接口。
- 暂停、继续、停止。
- Excel 导出和第二轮回导。
- 桌面启动方式。
- 构建产物忽略规则。

## 已修复

- 修复候选召回：入圈词只用于我司商品候选侧，避免客户词本身把无关我司商品拉进候选。
- 修复 `run_full` 与 `FakeModelClient` 接口不兼容，保证测试替身也走模型发令流程。
- 修复任务启动：由同步跑完改为后台运行，并改用 `run_full`。
- 接通任务状态机：运行中可暂停、继续、停止；停止后不能导出正式 Excel。
- 修复 `/tasks/{task_id}`、`/tasks/{task_id}/status` 和 `/config/status` 的状态返回，支撑前端看板。
- 修复配置自检目录：使用 `create_app(data_dir=...)` 指定目录，不再写到任意当前工作目录。
- 修复 Excel 导出：总表追加 `系统任务行ID` 和 `原始行号`，可被第二轮回导识别。
- 修复人工回导校验：人工确认行里的我司编码也必须存在于当前我司库。
- 修复第二轮回导：预览通过后保存人工审核结果，第二轮不覆盖人工已确认行。
- 修复启动脚本：优先启动 Tauri 桌面 exe，找不到 exe 时才回退浏览器开发模式。
- 修复 `.gitignore`：忽略 Tauri/Rust `target` 构建产物。
- 修复 Tauri identifier，消除 `.app` 结尾警告。

## 新增验证

- 后端全量测试：`79 passed in 2.30s`
- 前端构建：`npm run build` 通过
- Tauri 桌面构建：`npm run build` 通过
- PowerShell 启动脚本语法检查通过

## 仍需后续讨论或继续开发

- API Key 当前仍由本地 SQLite 配置承接，满足“不进代码、不进日志、不进 Git”，但正式桌面版最好接入系统安全凭据存储。
- 字段确认后端已有结构，但前端还没有完整字段确认页面，3.1 后续应补 UI。
- 第二轮回导已保护人工确认不被覆盖，但人工指定编码的状态表达还需要产品上再细化。
- 任务进度目前以任务状态和最终指标为主，逐行实时进度还可以继续加强。

## 2026-04-28 三期 3.1 缺口完善记录

本轮针对验收前缺口继续补强：

- 字段确认进入前端主流程，上传客户库后先进入字段确认，再允许启动对照。
- 后端启动任务增加字段确认和真实模型配置校验，未配置模型时不再静默使用 `FakeModelClient`。
- 手工输入单品可独立创建任务，不再依赖先上传客户 Excel。
- Excel 导出增加 `候选明细表`、总表内部链接和备选候选摘要。
- 已完成任务结果可从 SQLite 恢复，重启后仍可查看状态和导出。
- 小批量真实样本验证入口支持关键词抽样，例如 `--customer-keyword 生抽`。
- 用户运行说明、配置说明、常见错误说明、交付验收记录已补齐。

新增验证：

- 新增后端缺口测试先失败后通过。
- 后端全量测试：`86 passed in 3.17s`
- 前端构建：`npm run build` 通过
- Tauri 桌面构建：`npm run build` 通过，产物 `phase3_app/desktop/src-tauri/target/release/product-code-mapper.exe`
- 真实 DeepSeek 默认前 5 行验证：5 条均为未找到可靠匹配。
- 真实 DeepSeek `生抽` 关键词验证：5 条中 3 条必须人工审核，2 条未找到可靠匹配。

新增风险：

- 真实样本显示当前自动落码安全门偏保守，自动落码率为 0。
- 对“海天金标生抽 1*1.9L”这类接近命中的商品，系统仍可能因为候选分、品名包含关系、规格表达差异而转人工审核。
- 3.2 应优先优化规格归一、从商品名称中抽取品牌/品名/规格、候选排序和安全门策略。

## 2026-04-28 运行看板无实时动静修复

用户用真实 Excel 启动任务后，运行看板长时间显示 `running`，但自动落码、必须人工、未匹配等数字不变化。

根因：

- 后端原来只在整轮 `run_full` 完成后一次性写入 `task.result` 和运行指标。
- 运行中 `/tasks/{task_id}/status` 没有 `metrics`，前端只能显示 `- 条`。
- DeepSeek 串行调用加候选扫描耗时较长，导致用户看到的效果像卡死。

修复：

- `MatchRunEngine.run_full` 增加进度回调，每处理一条客户记录后回传当前 `row_results`。
- `TaskRecord` 增加 `partial_metrics`，运行中也能通过状态接口返回指标。
- `TaskRepo.update_run_progress` 同步更新数据库 `completed_count`。
- 新增集成测试 `test_running_task_status_exposes_live_metrics`，覆盖运行中指标可见。

验证：

- 后端全量测试：`87 passed in 3.50s`
- 前端构建：`npm run build` 通过

## 2026-04-28 桌面工作台 Failed to fetch 修复

用户在 Tauri 桌面工作台初始化配置页点击操作后，右上角提示 `Failed to fetch`。

根因：

- 本地后端服务正常，`/health`、`/settings/model`、`/config/status` 均可从命令行访问。
- 后端 CORS 只允许 `http://127.0.0.1:5173` 和 `http://localhost:5173`。
- Tauri 桌面壳页面来源为 `http://tauri.localhost`，未被允许，因此桌面窗口请求被浏览器安全策略拦截。

修复：

- 后端 CORS 增加 Tauri 桌面来源：`http://tauri.localhost`、`https://tauri.localhost`、`tauri://localhost`。
- 新增集成测试 `test_cors_allows_tauri_desktop_origin`。

验证：

- Tauri 来源预检请求返回 200，`Access-Control-Allow-Origin` 为 `http://tauri.localhost`。
- 后端全量测试：`88 passed in 3.63s`

## 2026-04-28 全局 Failed to fetch 继续修复

用户在“新建对照任务”页面继续看到 `Failed to fetch`。

进一步证据：

- 后端实际已经创建了多个任务，说明请求已经到达后端。
- 前端仍提示 `Failed to fetch`，说明失败发生在浏览器拿响应阶段。
- 对 `Origin: null` 的 CORS 预检请求返回 400。

根因：

- Tauri 打包桌面窗口在部分场景下会使用 `Origin: null`。
- 后端未允许 `null` 来源，导致响应被 WebView 拦截。

修复：

- CORS 允许来源增加 `null`。
- 新增集成测试 `test_cors_allows_packaged_desktop_null_origin`。

验证：

- `Origin: null` 访问 `/tasks` 预检返回 200，`Access-Control-Allow-Origin` 为 `null`。
- 后端全量测试：`89 passed in 3.53s`
