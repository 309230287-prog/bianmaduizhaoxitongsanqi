const steps = [
  {
    id: "home",
    flow: "首页入口",
    title: "首页工作台",
    nav: "首页",
    goals: ["让用户知道系统是否能用", "把基础资料和客户任务分开", "提供新建任务和继续下一轮入口"],
    risks: ["配置异常时不能直接进入智能对照", "业务人员不能看到一堆技术词", "首页不能变成杂乱仪表盘"],
    outputs: ["配置状态", "模型状态", "我司库状态", "任务入口"],
    render: () => `
      <div class="wireframe">
        <div class="hero-panel">
          <div class="panel">
            <div class="panel-title">
              <div>
                <p class="eyebrow">Workbench</p>
                <h3>今天要做什么？</h3>
              </div>
              <span class="tag green">配置正常</span>
            </div>
            <div class="flow-row">
              <button class="primary-button" type="button">新建对照任务</button>
              <button class="ghost-button" type="button">继续历史任务 / 开始下一轮</button>
              <button class="ghost-button" type="button">更新我司商品库</button>
              <button class="ghost-button" type="button">系统设置</button>
            </div>
          </div>
          <div class="panel">
            <p class="eyebrow">Status</p>
            <div class="status-grid">
              <div class="status-tile"><span class="tag green">模型</span><strong>DeepSeek 已配置</strong><p class="muted">用于中文解释和风险判断</p></div>
              <div class="status-tile"><span class="tag green">我司库</span><strong>11522 条</strong><p class="muted">基础资料已确认</p></div>
              <div class="status-tile"><span class="tag blue">最近任务</span><strong>客户食堂库</strong><p class="muted">第 1 轮已完成，可开始第 2 轮</p></div>
              <div class="status-tile"><span class="tag">导出</span><strong>默认目录可用</strong><p class="muted">文件导入导出自检通过</p></div>
            </div>
          </div>
        </div>
        <div class="panel tight">
          <div class="flow-row">
            <span class="flow-chip">初始化配置</span>
            <span class="flow-chip">更新我司库</span>
            <span class="flow-chip">新建任务</span>
            <span class="flow-chip">运行看板</span>
            <span class="flow-chip">导出 Excel</span>
            <span class="flow-chip">人工加工</span>
            <span class="flow-chip">开始下一轮</span>
          </div>
        </div>
      </div>
    `,
  },
  {
    id: "config",
    flow: "A. 首次启动和初始化配置",
    title: "初始化配置",
    nav: "初始化",
    goals: ["确认模型和目录可用", "让用户知道哪些能力已经准备好", "配置异常时阻止进入智能对照"],
    risks: ["API Key 不能明文暴露", "测试连接不发送真实客户数据", "中文文件名和导入导出必须提前检查"],
    outputs: ["模型配置状态", "目录配置状态", "连接测试结果"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title">
            <div>
              <p class="eyebrow">Setup</p>
              <h3>首次使用前，请完成基础配置</h3>
            </div>
            <span class="tag red">API Key 未测试</span>
          </div>
          <div class="form-grid">
            <label class="field"><span>模型提供方</span><div class="select-mock">DeepSeek</div></label>
            <label class="field"><span>模型名称</span><div class="input-mock">deepseek-chat</div></label>
            <label class="field"><span>Base URL</span><div class="input-mock">https://api.deepseek.com</div></label>
            <label class="field"><span>API Key</span><div class="input-mock">sk-**************</div></label>
            <label class="field"><span>默认数据目录</span><div class="input-mock">D:\\编码对照项目\\数据</div></label>
            <label class="field"><span>默认导出目录</span><div class="input-mock">D:\\编码对照项目\\导出</div></label>
          </div>
          <div class="flow-row" style="margin-top:18px">
            <button class="primary-button" type="button">测试模型连接</button>
            <button class="ghost-button" type="button">保存配置</button>
            <button class="mini-button" type="button">文件导入导出自检</button>
          </div>
        </div>
        <div class="split-2">
          <div class="panel tight"><p class="eyebrow">通过项</p><span class="tag green">默认目录可写</span><span class="tag green">日志目录可写</span><span class="tag green">中文文件名可用</span></div>
          <div class="panel tight"><p class="eyebrow">待处理</p><span class="tag red">模型连接未测试</span><span class="tag">我司商品库未导入</span></div>
        </div>
      </div>
    `,
  },
  {
    id: "company",
    flow: "系统基础资料",
    title: "更新我司商品库",
    nav: "我司库",
    goals: ["建立目标商品库", "把我司库作为系统基础资料管理", "识别编码、名称、单位、描述等关键字段"],
    risks: ["我司库不是纯标准词条", "缺少编码或名称时不能继续", "我司库更新后会影响下一轮对照"],
    outputs: ["我司商品库记录", "我司字段含义确认结果", "我司库版本或更新时间"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title">
            <div><p class="eyebrow">Company Catalog</p><h3>更新我司商品库</h3></div>
            <button class="primary-button" type="button">选择我司商品库 Excel</button>
          </div>
          <p class="muted">我司商品库是系统基础资料，不属于每次客户对照任务。客户人工加工后如果发现缺商品，应先补全我司库，再开始下一轮。</p>
          <table class="table-mock">
            <thead><tr><th>系统识别</th><th>Excel 列名</th><th>样例</th><th>状态</th></tr></thead>
            <tbody>
              <tr><td>我司商品编码</td><td>SPUID</td><td>100294</td><td><span class="tag green">必需</span></td></tr>
              <tr><td>我司商品名称</td><td>SPU名称（可修改）</td><td>海天金标生抽500ml</td><td><span class="tag green">必需</span></td></tr>
              <tr><td>我司单位</td><td>SPU基本单位</td><td>瓶</td><td><span class="tag blue">建议参与</span></td></tr>
              <tr><td>我司描述</td><td>SPU描述（可修改）</td><td>抄码/规格补充</td><td><span class="tag blue">建议参与</span></td></tr>
            </tbody>
          </table>
        </div>
        <div class="panel tight">
          <p class="eyebrow">导入摘要</p>
          <span class="tag green">11522 条商品</span>
          <span class="tag">22 列</span>
          <span class="tag green">基础字段已确认</span>
        </div>
      </div>
    `,
  },
  {
    id: "task",
    flow: "B. 日常商品编码对照",
    title: "新建对照任务",
    nav: "新建任务",
    goals: ["把客户库上传、字段确认、开始第一轮放在同一个任务页", "支持批量客户库和单条手工输入", "字段确认通过后才能开始第一轮对照"],
    risks: ["客户库上传页不要求人工做复杂判断", "AI 可以预判字段但不能完全黑箱跳过确认", "我司商品库更新不属于每次任务流程"],
    outputs: ["客户记录", "字段确认结果", "第一轮对照任务"],
    render: () => `
      <div class="wireframe">
        <div class="panel tight">
          <div class="task-steps" aria-label="新建任务步骤">
            <span class="task-step active">1 导入客户数据</span>
            <span class="task-step active">2 确认关键字段</span>
            <span class="task-step">3 开始第一轮对照</span>
          </div>
        </div>

        <div class="split-2">
          <div class="panel">
            <div class="panel-title">
              <div><p class="eyebrow">Step 1</p><h3>导入客户商品库</h3></div>
              <button class="primary-button" type="button">选择客户 Excel</button>
            </div>
            <p class="muted">这里只展示系统读到的列名、样例和异常提醒，不要求业务人员在这里完成字段判断。</p>
            <table class="table-mock">
              <thead><tr><th>客户库列名</th><th>样例</th><th>系统提醒</th></tr></thead>
              <tbody>
                <tr><td>商品名称</td><td>海天金标生抽</td><td><span class="tag green">可能是名称列</span></td></tr>
                <tr><td>规格</td><td>[1*500g]</td><td><span class="tag">格式需归一</span></td></tr>
                <tr><td>单位</td><td>瓶</td><td><span class="tag blue">建议参与判断</span></td></tr>
                <tr><td>商品名称</td><td>海天金标生抽</td><td><span class="tag red">重复列名</span></td></tr>
              </tbody>
            </table>
          </div>
          <div class="panel">
            <p class="eyebrow">Manual</p>
            <h3>或者手工输入单条商品</h3>
            <div class="form-grid" style="margin-top:16px">
              <label class="field"><span>商品名称</span><div class="input-mock">海天金标生抽</div></label>
              <label class="field"><span>规格</span><div class="input-mock">500ml</div></label>
              <label class="field"><span>单位</span><div class="input-mock">瓶</div></label>
              <label class="field"><span>备注</span><div class="input-mock">无</div></label>
            </div>
            <div class="flow-row" style="margin-top:18px"><button class="primary-button" type="button">加入本次任务</button></div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-title">
            <div>
              <p class="eyebrow">Step 2</p>
              <h3>确认关键字段</h3>
            </div>
            <span class="tag red">规格字段格式混杂</span>
          </div>
          <table class="table-mock">
            <thead><tr><th>业务含义</th><th>系统预判客户库列</th><th>是否需要你确认</th><th>提示</th></tr></thead>
            <tbody>
              <tr><td>商品名称</td><td>商品名称</td><td><span class="tag green">必须确认</span></td><td>主判断入口</td></tr>
              <tr><td>规格</td><td>规格</td><td><span class="tag blue">建议确认</span></td><td>可能影响包装和容量判断</td></tr>
              <tr><td>单位</td><td>单位</td><td><span class="tag blue">建议确认</span></td><td>可能影响结算单位</td></tr>
              <tr><td>备注</td><td>空白列</td><td><span class="tag">可跳过</span></td><td>发现空白列，默认不参与</td></tr>
            </tbody>
          </table>
        </div>

        <div class="panel">
          <div class="panel-title">
            <div>
              <p class="eyebrow">Step 3</p>
              <h3>开始第一轮对照</h3>
            </div>
            <button class="primary-button" type="button">开始第一轮对照</button>
          </div>
          <p class="muted">点击后进入对照进度看板。系统开始读取客户记录、召回我司候选，并准备写入导出 Excel 的解释和风险提示。</p>
          <span class="tag green">必需字段已确认</span>
          <span class="tag red">规格字段有风险</span>
          <span class="tag green">模型可用</span>
        </div>
      </div>
    `,
  },
  {
    id: "board",
    flow: "B. 日常商品编码对照",
    title: "对照进度看板",
    nav: "运行看板",
    goals: ["让用户明确知道系统什么时候开始计算", "展示本轮运行进度和结果分布", "本轮完成后允许导出 Excel"],
    risks: ["运行中不能导出正式结果", "停止后本轮不算完成", "统计框第一版只展示数量，不进入页面明细"],
    outputs: ["第 1 轮运行状态", "结果分类统计", "可导出的 Excel"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title">
            <div>
              <p class="eyebrow">Run Board</p>
              <h3>客户食堂库：第 1 轮对照</h3>
            </div>
            <span class="tag blue">运行中</span>
          </div>
          <div class="flow-row">
            <span class="tag">任务：客户商品库_20260425</span>
            <span class="tag">当前轮次：第 1 轮</span>
            <span class="tag">我司库版本：2026-04-25 09:30</span>
          </div>
        </div>

        <div class="status-grid">
          <div class="status-tile"><span class="tag green">我司商品库</span><strong>11522 条</strong><p class="muted">目标库总数</p></div>
          <div class="status-tile"><span class="tag green">客户商品库</span><strong>2581 条</strong><p class="muted">本轮待处理总数</p></div>
          <div class="status-tile"><span class="tag blue">已完成</span><strong>1600 条</strong><p class="muted">当前已处理记录</p></div>
          <div class="status-tile"><span class="tag green">自动落码无风险</span><strong>986 条</strong><p class="muted">可直接写入导出表</p></div>
          <div class="status-tile"><span class="tag blue">建议落码需复核</span><strong>532 条</strong><p class="muted">Excel 中标记待人工看</p></div>
          <div class="status-tile"><span class="tag red">必须人工干预</span><strong>82 条</strong><p class="muted">不伪造确定编码</p></div>
          <div class="status-tile"><span class="tag">未找到可靠匹配</span><strong>0 条</strong><p class="muted">继续等待本轮完成</p></div>
          <div class="status-tile"><span class="tag">本轮状态</span><strong>运行中</strong><p class="muted">本轮完成后才能导出</p></div>
        </div>

        <div class="panel">
          <div class="panel-title">
            <div>
              <p class="eyebrow">Controls</p>
              <h3>任务控制</h3>
            </div>
            <div class="flow-row">
              <button class="ghost-button" type="button">暂停</button>
              <button class="ghost-button" type="button">继续</button>
              <button class="ghost-button danger-button" type="button">停止</button>
            </div>
          </div>
          <div class="progress-track"><span style="width:62%"></span></div>
          <p class="muted">正在处理：第 1600 / 2581 条。已生成候选 1518 条，必须人工干预 82 条。</p>
          <div class="flow-row" style="margin-top:18px">
            <button class="primary-button" type="button" disabled>导出 Excel</button>
            <span class="tag">本轮完成后才能导出</span>
          </div>
        </div>

        <div class="panel tight">
          <p class="eyebrow">说明</p>
          <p class="muted">3.1 的统计框只展示数量，不进入页面明细。所有明细、候选解释、风险提示和人工审核列，都先进入导出的 Excel。</p>
        </div>
      </div>
    `,
  },
  {
    id: "export",
    flow: "B. 日常商品编码对照",
    title: "导出 Excel",
    nav: "导出",
    goals: ["本轮完成后导出可人工处理的 Excel", "避免一张超宽表拖垮使用体验", "支持人工加工后进入第二轮"],
    risks: ["不能覆盖客户原始文件", "必须人工干预不能伪造编码", "第二轮回导必须依赖任务行ID"],
    outputs: ["多工作表 Excel", "人工加工入口", "下一轮输入文件"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title">
            <div>
              <p class="eyebrow">Export</p>
              <h3>第 1 轮已完成，可以导出 Excel</h3>
            </div>
            <button class="primary-button" type="button">导出 Excel</button>
          </div>
          <div class="status-grid">
            <div class="status-tile"><span class="tag green">自动落码无风险</span><strong>1602 条</strong><p class="muted">总表中直接写入编码</p></div>
            <div class="status-tile"><span class="tag blue">建议落码需复核</span><strong>706 条</strong><p class="muted">人工在 Excel 中确认</p></div>
            <div class="status-tile"><span class="tag red">必须人工干预</span><strong>231 条</strong><p class="muted">不回填确定编码</p></div>
            <div class="status-tile"><span class="tag">未找到可靠匹配</span><strong>42 条</strong><p class="muted">等待人工或补全我司库</p></div>
          </div>
        </div>

        <div class="panel">
          <p class="eyebrow">Excel 工作表结构</p>
          <table class="table-mock">
            <thead><tr><th>工作表</th><th>用途</th><th>关键设计</th></tr></thead>
            <tbody>
              <tr><td>对照结果总表</td><td>业务人员主处理表</td><td>保留客户原始列，追加少量关键结果列</td></tr>
              <tr><td>详细证据表</td><td>查看解释和风险</td><td>总表“查看详细证据”可跳转到对应行</td></tr>
              <tr><td>统计汇总表</td><td>查看本轮整体结果</td><td>展示轮次、模型、我司库版本和分类数量</td></tr>
            </tbody>
          </table>
        </div>

        <div class="panel">
          <p class="eyebrow">第二轮闭环</p>
          <div class="flow-row">
            <span class="flow-chip">导出 Excel</span>
            <span class="flow-chip">人工加工</span>
            <span class="flow-chip">补全我司库</span>
            <span class="flow-chip">更新我司商品库</span>
            <span class="flow-chip">继续历史任务 / 开始下一轮</span>
            <span class="flow-chip">开始第 2 轮</span>
          </div>
          <p class="muted">人工加工后的 Excel 需要保留系统任务行ID。第二轮导入后，人工已确认的结果不被系统随意覆盖，人工指定编码会和最新我司库校验。</p>
        </div>
      </div>
    `,
  },
];

let currentIndex = 0;

const stepNav = document.querySelector("#stepNav");
const screen = document.querySelector("#screen");
const screenTitle = document.querySelector("#screenTitle");
const flowLabel = document.querySelector("#flowLabel");
const goalList = document.querySelector("#goalList");
const riskList = document.querySelector("#riskList");
const outputList = document.querySelector("#outputList");
const prevBtn = document.querySelector("#prevBtn");
const nextBtn = document.querySelector("#nextBtn");

function list(items) {
  return items.map((item) => `<li>${item}</li>`).join("");
}

function renderNav() {
  stepNav.innerHTML = steps
    .map(
      (step, index) => `
        <button class="step-button ${index === currentIndex ? "active" : ""}" type="button" data-step="${index}">
          <small>${String(index + 1).padStart(2, "0")}</small>
          ${step.nav}
        </button>
      `,
    )
    .join("");

  stepNav.querySelectorAll("[data-step]").forEach((button) => {
    button.addEventListener("click", () => {
      currentIndex = Number(button.dataset.step);
      render();
    });
  });
}

function render() {
  const step = steps[currentIndex];
  screenTitle.textContent = step.title;
  flowLabel.textContent = step.flow;
  screen.innerHTML = step.render();
  goalList.innerHTML = list(step.goals);
  riskList.innerHTML = list(step.risks);
  outputList.innerHTML = list(step.outputs);
  prevBtn.disabled = currentIndex === 0;
  nextBtn.disabled = currentIndex === steps.length - 1;
  renderNav();
}

prevBtn.addEventListener("click", () => {
  currentIndex = Math.max(0, currentIndex - 1);
  render();
});

nextBtn.addEventListener("click", () => {
  currentIndex = Math.min(steps.length - 1, currentIndex + 1);
  render();
});

render();
