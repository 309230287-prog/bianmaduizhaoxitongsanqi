# OMC Project State - 商品编码对照二期

## Current Stage

二期需求、执行路书、技术规格已形成。

当前进入：

**Phase 2：模型输入输出契约与候选池离线验证。**

## Active Direction

大模型主导商品语义翻译与证据对齐。

一期产品逻辑不再作为二期产品基线。

## Core Principle

大模型负责理解和判断，程序负责流程和留痕。

## Key Documents

- `docs/project-memory.md`
- `docs/requirements/商品编码对照系统-需求文档-二期语义翻译-v0.1.md`
- `docs/route-map/商品编码对照系统-二期语义翻译实施路书-v0.1.md`
- `docs/planning/商品编码对照系统-二期技术执行规格-v0.1.md`
- `docs/superpowers/plans/2026-04-18-phase2-semantic-translation-implementation-plan.md`
- `docs/tasks/二期第一阶段-验证样本与模型验证任务书-v0.1.md`

## Next Action

通过产品内“二期语义工作台”执行小批模型试跑，先修正模型输出契约和 JSON 解析稳定性，再扩大到 10 条金样本。

## Latest Progress - 2026-04-18

- 已建立二期独立包：`src/product_matcher_phase2/`。
- 已建立 30 条金样本：`samples/phase2/golden_samples_v0.1.xlsx`。
- 已实现模型输入构造和模型输出 JSON 解析。
- 已实现客户库 / 我司库 Excel 读取，保留重复中文表头和原始字段。
- 已实现候选池基础召回与覆盖率评估。
- 当前金样本候选池覆盖率：Top10 100.00%，Top20 100.00%。
- 已准备 10 条模型试跑输入：`samples/phase2/model_trial_inputs_v0.1.jsonl`。
- 已准备模型试跑脚本：`scripts/phase2_run_model_trial.py`。
- 当前环境未读取到 `DASHSCOPE_API_KEY`，真实模型试跑尚未执行。
- 已新增模型选择框架：`src/product_matcher/services/model_catalog.py`。
- 已记录模型选择框架文档：`docs/planning/模型选择框架-v0.1.md`。
- 已用 DeepSeek 做过连接测试，连接成功。
- 已通过脚本级二期试跑调用 DeepSeek 10 条样本，但 10 条均未通过 JSON/schema 校验，不能视为模型验证成功。
- 已新增产品内“二期语义工作台”骨架：页面可触发 `/phase2/trial` 后台任务，读取 `samples/phase2/model_trial_inputs_v0.1.jsonl`，保存试跑结果并提供下载。
- 已明确工程复用边界：允许复用一期 FastAPI/Jinja2、后台任务、日志和下载基础设施；二期语义链路必须保持在 `src/product_matcher_phase2/`，不得把一期匹配结果包装成二期语义判断。
- 当前自动落码准确率尚未评估，因为真实大模型输出契约尚未通过。
