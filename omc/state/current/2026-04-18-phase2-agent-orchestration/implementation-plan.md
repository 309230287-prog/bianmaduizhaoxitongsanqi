# Implementation Plan

## Goal

建立二期多智能体并行开发的组织骨架，并启动第一轮并行任务。

## Current Context

- 当前目录：`D:\编码对照项目\编码对照项目_主线`
- 父级 git 根目录：`D:\编码对照项目`
- 当前目录尚无独立 `.git`
- 父级仓库有大量无关变更，不适合直接作为二期并行开发仓库
- 已新增二期语义试跑控制台骨架，并通过 `python -m unittest discover -s tests -v`

## Files And Areas

- Project boundary: `.git`, `.gitignore`, `.worktrees/`
- OMC task: `omc/state/current/2026-04-18-phase2-agent-orchestration/`
- Phase2 core: `src/product_matcher_phase2/`
- Product shell: `src/product_matcher/app.py`, `src/product_matcher/templates/index.html`, `src/product_matcher/static/app.css`
- Tests: `tests/phase2/`, `tests/test_app_flow.py`

## Steps

1. 建立独立本地 git 仓库或等价隔离边界。
2. 增加项目级 `.gitignore`，确保 `.worktrees/`、运行数据、缓存、构建产物不进入版本控制。
3. 创建基线提交或至少建立可分支的 clean baseline。
4. 创建主开发分支 `phase2/orchestrated-prototype`。
5. 为 agents 建立互不重叠的文件所有权。
6. 派发只读审查 agent：检查路书、OMC、边界、验收。
7. 派发实现/诊断 agent：诊断 DeepSeek 输出失败并提出 schema/prompt 修正方案。
8. 总管集成结果，先跑针对性测试，再跑全量测试。

## Risks

- 嵌套 git 仓库会让父级仓库看到整个项目目录为未跟踪或特殊目录，但这是为了让本项目独立。
- 如果 agents 同时修改 `app.py` 或模板，会产生冲突；第一轮只允许一个 agent 改产品壳。
- 模型试跑可能产生费用和较长等待，默认先做离线诊断，不直接重复调用 10 条。

## Verification

- `git status --short` 在独立项目中可读、范围干净。
- `git check-ignore -q .worktrees` 返回成功。
- `python -m unittest discover -s tests -v` 通过。
- OMC task brief 和 implementation plan 已记录架构。

## Done Means

项目进入可并行开发状态，agents 有明确职责，总管能安全集成，且没有把一期逻辑混入二期语义判断。
