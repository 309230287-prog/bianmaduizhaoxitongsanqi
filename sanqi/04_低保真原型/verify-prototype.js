const fs = require("fs");
const path = require("path");

const root = __dirname;
const projectRoot = path.resolve(root, "..");
const files = {
  app: fs.readFileSync(path.join(root, "app.js"), "utf8"),
  index: fs.readFileSync(path.join(root, "index.html"), "utf8"),
  readme: fs.readFileSync(path.join(root, "README.md"), "utf8"),
  reviewDoc: fs.readFileSync(path.join(root, "三期3.1-DEMO评审修改文档-v0.1.md"), "utf8"),
  flowDoc: fs.readFileSync(
    path.join(projectRoot, "03_业务流程文档", "商品编码对照系统-三期3.1业务流程文档-v0.1.md"),
    "utf8",
  ),
  requirementsDoc: fs.readFileSync(
    path.join(projectRoot, "02_需求文档", "商品编码对照系统-三期需求文档-v0.2.md"),
    "utf8",
  ),
};

const checks = [
  ["原型标题应收缩为新建任务、运行看板、导出", files.index.includes("新建对照任务、对照进度看板、导出")],
  ["左侧主线应包含运行看板", files.app.includes('nav: "运行看板"')],
  ["3.1 主线不应保留候选解释页面", !files.app.includes('nav: "候选解释"')],
  ["3.1 主线不应保留人工审核页面", !files.app.includes('nav: "人工审核"')],
  ["运行看板应显示当前轮次", files.app.includes("第 1 轮")],
  ["运行看板应有暂停按钮", files.app.includes("暂停")],
  ["运行看板应有继续按钮", files.app.includes("继续")],
  ["运行看板应有停止按钮", files.app.includes("停止")],
  ["导出按钮应表达本轮完成后才能点击", files.app.includes("本轮完成后才能导出")],
  ["README 应记录 3.1 收缩后的主线", files.readme.includes("对照进度看板")],
  ["评审修改文档应记录第二轮闭环", files.reviewDoc.includes("继续历史任务 / 开始下一轮")],
  ["业务流程文档应记录运行看板和下一轮闭环", files.flowDoc.includes("对照进度看板 -> 导出 Excel -> 人工加工 -> 开始下一轮")],
  ["需求文档应包含对照进度看板需求", files.requirementsDoc.includes("FR-12A 对照进度看板")],
  ["需求文档应包含第二轮闭环需求", files.requirementsDoc.includes("FR-12B 第二轮闭环")],
];

const failed = checks.filter(([, passed]) => !passed);

if (failed.length > 0) {
  console.error("Prototype verification failed:");
  failed.forEach(([name]) => console.error(`- ${name}`));
  process.exit(1);
}

console.log(`Prototype verification passed: ${checks.length}/${checks.length} checks.`);
