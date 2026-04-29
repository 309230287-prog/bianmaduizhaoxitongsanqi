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

## 2026-04-28 新建对照任务 Failed to fetch 深挖修复

用户在“新建对照任务”页面上传客户 Excel 后仍看到 `Failed to fetch`。

进一步证据：

- 通过 WebView2 CDP 进入真实桌面窗口，确认页面来源为 `http://tauri.localhost/`。
- 同一窗口内 `GET /health` 和 `GET /config/status` 正常，说明后端不是整体不可达，CORS 也不是对所有请求失败。
- 同一窗口内 `POST /tasks` 文件上传失败为 `TypeError: Failed to fetch`。
- 后端数据库结构显示 `task_rows.task_row_id` 是全局主键，而客户行 ID 会反复生成 `row-2`、`row-3`。
- 回归测试复现：第一次创建 Excel 任务成功，第二次创建任务触发 `UNIQUE constraint failed: task_rows.task_row_id`。
- 手工单品任务也复现同类问题：每个独立手工任务都使用 `manual-1`，第二个任务会触发同样的唯一键冲突。

根因：

- `task_row_id` 的业务含义是“某个任务内部的客户行标识”，不是全系统全局唯一 ID。
- 数据库把它建成了全局主键，导致不同任务之间复用 `row-2` 或 `manual-1` 时崩溃。
- 崩溃是未处理 500，浏览器/WebView 无法读取异常响应，于是统一显示 `Failed to fetch`，掩盖了真实数据库错误。

修复：

- `task_rows` 主键改为 `(task_id, task_row_id)`，允许不同任务复用同一个行号标识。
- 增加旧库迁移：启动时自动把旧的 `task_row_id` 全局主键迁移为任务内复合主键。
- Excel 上传解析失败统一转成中文 400，而不是未处理 500。
- 人工审核回导 Excel 读取失败返回校验错误，不再炸成服务端异常。
- 手工追加商品的空商品名错误转成中文 400。

新增回归测试：

- 多个 Excel 任务可重复使用 `row-2`。
- 多个独立手工任务可重复使用 `manual-1`。
- 旧数据库结构会自动迁移到 `(task_id, task_row_id)`。
- 坏客户 Excel 上传返回中文 400 且保留 CORS 响应。

验证：

- 新增回归测试先失败后通过。
- 后端全量测试：`94 passed in 4.17s`。
- 重启后端后，通过真实 Tauri WebView2 验证：连续两次 `POST /tasks` 有效 Excel 上传均返回 200；坏文件上传返回 400 中文错误，不再是 `Failed to fetch`。

## 2026-04-28 三期隐藏 BUG 审计

用户要求继续深挖三期是否还有同类 BUG。

审计范围：

- 后端全量测试。
- 前端生产构建。
- Tauri 桌面构建。
- 静态扫描 `TODO/FIXME/Failed to fetch/未实现/占位` 等高风险文本。
- 人工复核任务创建、字段确认、运行看板、导出页、历史任务和配置保存链路。

新增确认 BUG：

- 已完成任务再次进入运行看板时，前端会自动调用 `/tasks/{task_id}/start`，后端原逻辑会把已完成任务重新置为 `running`，存在“只是查看却误重跑”的风险。
- 应用重启后，已完成任务可以按 ID 导出，但 `/config/status` 只返回内存任务，导致运行看板/导出页看不到历史已完成任务。
- 初始化配置页不回显 API Key 是正确的，但保存时会提交空字符串，后端原逻辑会把已保存的 API Key 清空。

修复：

- `start_task` 对 `completed/stopped/failed` 终态任务改为直接返回当前状态，不再误重跑。
- `TaskRepo.list_tasks` 从 SQLite 汇总历史任务、客户行数和是否有已完成结果。
- `/config/status` 改为合并 SQLite 历史任务和当前内存任务，重启后仍可列出可导出任务。
- 模型配置保存时，空 `api_key` 表示“不修改原 Key”，只有非空 Key 才替换。

新增回归测试：

- `test_completed_task_is_not_restarted_when_start_called_again`
- `test_config_status_lists_completed_tasks_after_app_restart`
- `test_blank_api_key_update_preserves_existing_secret`

验证：

- 后端全量测试：`97 passed in 4.45s`。
- 前端构建：`npm run build` 通过。
- Tauri 桌面构建：`npm run build` 通过，产物仍为 `phase3_app/desktop/src-tauri/target/release/product-code-mapper.exe`。

仍需后续产品化补强：

- 配置页的默认数据目录/导出目录已经保存，但当前后端运行目录仍由启动参数决定，后续应统一成真正可配置的运行目录。

## 2026-04-28 三期日志占位接口收口

用户追问“为什么还有占位接口”，按开发计划继续做 3.1 验收扫雷。

确认问题：

- `/logs/recent` 是生产路由，但仍返回空数组。
- `action_logs` 表和 `TaskRepo.log_action` 已经存在，任务创建、导入、导出等动作会写日志。
- 前端当前没有调用 `/logs/recent`，所以它不影响主流程，但和“基础日志和异常提示已完成”的验收口径不一致。

修复：

- 增加 `TaskRepo.list_action_logs(limit=100)`，从 SQLite 读取最近操作日志。
- `/logs/recent` 改为返回真实 `action_logs` 记录。

新增回归测试：

- `test_recent_logs_endpoint_returns_persisted_actions`

验证：

- 回归测试先失败，确认旧接口确实返回空日志。
- 修复后单条回归测试通过。
- 后端全量测试：`98 passed in 5.43s`。
- 前端生产构建：`npm run build` 通过。
- Tauri 桌面构建：`npm run build` 通过，产物仍为 `phase3_app/desktop/src-tauri/target/release/product-code-mapper.exe`。

## 2026-04-29 停止状态导出问题修复

用户真实运行 312 条样本时发现：进度条已满、任务进入 `stopped`，但“导出 Excel”按钮仍不可用。

根因证据：

- 后端状态接口返回：`task_status=stopped`、`can_export=false`。
- 数据库 `task_runs` 显示同一任务 `total_count=312`、`completed_count=312`。
- 数据库 `run_results` 已有 312 条结果。
- 导出接口旧逻辑按状态机 `stopped` 一刀切禁止导出，返回 409。

判断：

- 这不是“没有结果不能导出”。
- 这是停止状态、结束条件和导出条件之间打架。
- 业务上只要已经生成可复核结果，就应允许导出 Excel，尤其要支持用户停止后检查当前结果。

修复：

- 导出权限从“必须 completed”调整为“不是 failed 且已有结果”。
- 重启恢复时允许加载 stopped 但已有结果的最新运行结果。
- 保留 running/paused 且尚无结果时禁止导出。

新增回归测试：

- `test_stopped_after_all_rows_processed_can_still_export_excel`
- 同步调整 `test_api_can_pause_and_stop_running_task`，停止后已有结果应可导出。

验证：

- 两条关键回归测试通过。
- 后端全量测试：`99 passed in 4.98s`。
- 当前真实任务 `341d351c2d5a4e11aaebcca66a5bf6b1` 状态接口已返回 `can_export=true`。
- 当前真实任务导出接口返回 200，并生成 Excel：`runtime_data/debug/task-341d351c-export-check.xlsx`。
- 导出 Excel 验证：包含 `对照结果总表`、`详细证据表`、`候选明细表`、`统计汇总表`；总表 313 行，候选明细表 6241 行。

## 2026-04-29 看板进度和桌面交付边界修订

用户补充三条要求：

1. 进度条必须显示百分比。
2. 前端和后端必须真正连成桌面版，不要再停留在 Web/脚本启动体验。
3. 中断之后也要允许下载，哪怕是不完整的当前结果。

本轮完成：

- 运行看板增加 `处理进度：xx%` 和 `已处理 / 总数`。
- 将“总轮次”改为“系统内部匹配轮次”，避免和人工第二轮混淆。
- 将右侧“第二轮”改为“人工复核后 / 开始下一轮对照”，明确只有上传人工加工 Excel 后才进入业务第 2 轮。
- 停止后如已有结果，导出按钮显示为“导出当前结果 Excel”，并提示“文件可能不是完整最终结果”。
- 抽出 `runBoardProgress` 进度计算函数，并增加前端检查文件。

仍未完成，进入下一阶段：

- Python 后端作为 Tauri sidecar 内置到桌面程序。
- Windows 安装包。
- 安装后开始菜单入口、桌面快捷方式和卸载验证。

验证：

- 前端进度计算检查：`npx tsc src/pages/runBoardProgress.test.ts ...` 后执行 `node runtime_data/frontend-tests/runBoardProgress.test.js`，通过。
- 前端构建：`npm run build` 通过。
- 后端全量测试：`99 passed in 5.21s`。
- 当前真实任务 `341d351c2d5a4e11aaebcca66a5bf6b1` 状态接口返回 `can_export=true`。
- Tauri 桌面构建：`npm run build` 通过，产物仍为 `phase3_app/desktop/src-tauri/target/release/product-code-mapper.exe`。

## 2026-04-29 桌面壳自动拉起后端

根因确认：

- `phase3_app/desktop/src-tauri/src/main.rs` 原本只有 `tauri::Builder::default().run(...)`。
- 这意味着桌面端只负责开窗口，不负责启动 Python 后端。
- 因此前端和后端没有真正由桌面壳打通，仍依赖外部脚本或已有 8000 服务。

本轮完成：

- 桌面入口增加 `start_backend_if_needed`。
- 启动桌面程序时先检测 `127.0.0.1:8000` 是否已有后端。
- 如没有后端，则自动定位项目内 `phase3_app/backend`，设置 `PYTHONPATH`，启动 `uvicorn product_code_mapper.api.app:create_app --factory`。
- 等待本地 8000 端口可用后再继续打开桌面窗口。
- 后端子进程由桌面进程托管，桌面进程退出时尝试关闭子进程。

边界说明：

- 当前已实现“项目目录内的桌面 exe 自动拉起后端”。
- Windows 安装包和真正分发形态仍需下一阶段完成：需要把 Python 后端、依赖和运行时一起纳入安装包或 sidecar 方案。

验证：

- 新增桌面桥接护栏测试：`tests/integration/test_desktop_backend_bridge.py`。
- 红灯：测试确认旧 `main.rs` 不包含后端启动逻辑，失败。
- 绿灯：补齐桌面入口后该测试通过。
- 后端全量测试：`100 passed in 5.83s`。
- 前端构建：`npm run build` 通过。
- Tauri 桌面构建：`npm run build` 通过，产物为 `phase3_app/desktop/src-tauri/target/release/product-code-mapper.exe`。

## 2026-04-29 用户入口收口为桌面客户端

用户明确目标：

- 使用体验要像 Codex：打开桌面客户端，就在客户端窗口里运行。
- 不要从用户入口打开浏览器页面。

本轮调整：

- `phase3_app/scripts/start_workbench.ps1` 改为纯桌面入口。
- 找到 `product-code-mapper.exe` 时，只启动桌面客户端。
- 找不到桌面客户端时，只提示先构建桌面客户端，不再启动浏览器开发模式。
- 后端启动职责继续放在 Tauri 桌面壳 `main.rs`。

仍未处理：

- 端口仍暂时保留 `127.0.0.1:8000`，按用户要求稍后再处理。

验证：

- 启动脚本回归测试先失败，证明旧脚本仍包含浏览器/后端开发模式。
- 删除用户入口中的浏览器/脚本后端兜底后，`tests/integration/test_start_scripts.py` 通过。

## 2026-04-29 用户入口和开发调试入口分离

用户确认目标：

- 日常使用入口要像 Codex 一样，只打开桌面客户端。
- Debug 能力不能丢，后期仍需要能单独启动前端、后端、浏览器调试。

本轮完成：

- `启动三期工作台.bat` 继续作为用户入口，只打开 Tauri 桌面客户端。
- `phase3_app/scripts/start_workbench.ps1` 不再启动浏览器、不再启动前端 dev server、不再直接启动 uvicorn。
- 新增 `开发调试启动.bat`。
- 新增 `phase3_app/scripts/开发调试启动.bat`。
- 新增 `phase3_app/scripts/start_dev_debug.ps1`，保留开发调试链路：启动后端、启动前端 dev server、打开 `http://127.0.0.1:5173`。

验证：

- 先新增测试，确认开发调试入口缺失时失败。
- 补齐脚本后，`tests/integration/test_start_scripts.py` 通过，5 个启动脚本检查全部通过。

## 2026-04-29 修复 bat 双击一闪而过

用户反馈：

- `启动三期工作台.bat` 和 `开发调试启动.bat` 双击后一闪而过。

根因确认：

- 使用 `cmd /c` 真实运行两个 bat 后复现失败。
- bat 调用的是 Windows 自带 `powershell.exe`。
- `.ps1` 文件为 UTF-8 无 BOM，包含中文字符串。
- Windows PowerShell 5.1 按系统 ANSI/GBK 读取脚本，导致中文字符串乱码，并引发解析错误，例如 `&&` 被误认为语法符号、大括号被误判缺失。

本轮修复：

- 两个 PowerShell 脚本改为 ASCII 文本，避免 Windows PowerShell 编码误读。
- 四个 bat 入口增加 `-NoProfile`。
- 四个 bat 入口增加 `if errorlevel 1 pause`，出错时窗口停住，不再一闪而过。
- 启动脚本测试增加 ASCII 兼容性检查。

验证：

- `tests/integration/test_start_scripts.py`：6 个脚本检查通过。
- Windows PowerShell Parser API 检查 `start_workbench.ps1` 通过。
- Windows PowerShell Parser API 检查 `start_dev_debug.ps1` 通过。
- `cmd /c "D:\bianmaduizhaoxiangmu\sanqi_publish_clean\启动三期工作台.bat"` 返回 0，并输出 `Phase 3 desktop client started...`。
- `cmd /c "D:\bianmaduizhaoxiangmu\sanqi_publish_clean\开发调试启动.bat"` 返回 0，并输出开发调试地址和后端地址。
- 后端全量测试：`104 passed in 4.88s`。
- 前端构建：`npm run build` 通过。
- Tauri 桌面构建：首次因刚验证启动的 `product-code-mapper.exe` 正在运行而无法覆盖；关闭该进程后重跑 `npm run build` 通过。
