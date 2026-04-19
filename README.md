# 编码对照项目

先读 [docs/project-memory.md](docs/project-memory.md)。

## 当前阶段

- 已进入第一版 MVP 方案收敛阶段
- 当前主线以单模型生产方案为准
- 当前正式文档基线：
  - [需求文档 v0.3](docs/requirements/商品智能匹配系统-需求文档-v0.3.md)
  - [实施路书 v0.3](docs/route-map/商品智能匹配系统-实施路书-v0.3.md)
  - [单模型配置与调用契约 v0.1](docs/planning/单模型配置与调用契约-v0.1.md)

## 当前技术路线

- 本地 Web 界面：FastAPI + Jinja2
- Excel 读取与回写：openpyxl
- 当前生产主链路：
  - 上传
  - 字段对照
  - 单模型标准化
  - 本地候选召回
  - 单模型裁决
  - 分级导出
- 默认推荐模型：阿里云百炼 `qwen-plus`
- 重要边界：
  - 生产模型是配置项，不在代码中写死
  - API Key 只从本地配置或环境变量读取，不写入源码和仓库
  - 第一版生产主链路不依赖多模型
  - 第一版生产主链路不依赖向量召回
- 当前模板复用：按 Excel 表头结构自动保存和复用字段对照
- 桌面客户端：Electron 桌面壳 + Python 本地服务
- Windows 打包：PyInstaller + electron-builder
- 后续增强：人工审核回流、历史关系沉淀、向量增强、challenger 模型实验

## 当前已实现能力

当前版本已覆盖：
- 双 Excel 上传入口
- 读取第一张工作表
- 表头提取
- 样例行预览
- 固定字段对照表页面
- 字段自动建议映射
- 字段模板自动复用
- 标准化样例输出
- 初版匹配样例输出
- 匹配候选展示与结果分级
- 匹配汇总统计
- 匹配结果 Excel 导出
- 运行日志与操作日志落地
- 外置品牌词库加载
- 外置商品词库加载
- 浏览器自动打开本地页面
- 桌面客户端开发启动入口
- Windows 安装包构建脚本

## 当前版本边界

当前版本已经能让你：
- 看系统如何拆品牌、规格、单位和商品名称
- 看系统如何从我司商品库缩小候选范围
- 看系统如何对候选做分级判断
- 复用已确认过的字段对照模板
- 导出带追加列的结果 Excel
- 生成 Windows 安装包和桌面客户端可执行文件

当前版本还没有完成：
- 单模型生产链路的完整配置化落地
- 人工审核结果保存
- 历史匹配关系沉淀
- 审核回流
- 更强的本地候选召回策略
- 更完整的技术配置文档与验收样本

## 文档说明

- `docs/requirements`：正式需求文档
- `docs/route-map`：实施路书
- `docs/planning`：技术说明、历史规划和配置契约

说明：
- `v0.3` 是当前有效主线
- `docs/planning` 下的部分 `v0.1` 规则文档属于历史方案，不应覆盖当前单模型路线

## 运行方式

### 最简单方式

在项目根目录双击：

```text
启动商品匹配系统.bat
```

它会自动完成：
- 切换到 UTF-8 中文环境
- 设置 Python 模块路径
- 首次启动时安装缺失依赖
- 启动本地服务
- 自动打开二期工作台

打开后的默认页面：

```text
http://127.0.0.1:8000/phase2
```

关闭启动窗口，系统服务就会停止。

### 命令行方式

如果不想双击，也可以在项目根目录执行：

```bat
run_local.cmd
```

或者：

```bat
python scripts\start_app.py
```

浏览器访问：

```text
http://127.0.0.1:8000/phase2
```

## 运行期文件

- 模型配置样例：`config/model_settings.example.json`
- 品牌词库：`config/dictionaries/brands.txt`
- 商品词库：`config/dictionaries/product_keywords.txt`
- 运行日志：`runtime_data/logs/app.log`
- 操作日志：`runtime_data/logs/actions.jsonl`
- 字段模板：`runtime_data/mapping_templates.json`

说明：
- `model_settings.example.json` 只放默认推荐值和占位符，不放真实 API Key
- `brands.txt` 和 `product_keywords.txt` 都是外置文件，后续维护不依赖改源码
- `actions.jsonl` 会记录上传、字段选择、点击按钮、导出等动作
- `app.log` 会记录接口请求、耗时和异常

### 桌面客户端开发模式

在项目根目录执行：

```bat
run_desktop.cmd
```

它会：
- 自动拉起本地 Python 服务
- 用 Electron 打开桌面窗口

## 打包方式

构建 Windows 安装包：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_client.ps1
```

构建产物默认在：

```text
dist\windows-client\product-matcher-desktop-setup-0.1.0.exe
dist\windows-client\win-unpacked\product-matcher-desktop.exe
```

## 测试方式

```bat
D:\Users\weis\Documents\New project\tools\runtime\python314\python.exe -m unittest discover -s tests -v
```

## 目录说明

- `docs/requirements`：需求文档
- `docs/planning`：技术文档、规划、历史规则说明
- `docs/route-map`：实施路书
- `src/product_matcher`：当前应用代码
- `desktop-shell`：Electron 桌面客户端壳
- `scripts`：构建和打包脚本
- `runtime_data`：本地上传缓存、字段模板和运行期数据
- `tests`：基础测试

## 当前已有原始资料

- 商品智能匹配系统需求规格说明书 - 四维AND逻辑.pdf
- 商品智能匹配系统 - 技术方案文档（四维AND逻辑）.pdf
- 客户商品库.xlsx
- 我司商品库.xlsx
