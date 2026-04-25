const steps = [
  {
    id: "home",
    flow: "首页入口",
    title: "首页工作台",
    nav: "首页",
    goals: ["让用户知道系统是否能用", "把初始化和业务入口分开", "显示我司库、模型、最近任务状态"],
    risks: ["配置异常时不能直接进入智能对照", "业务人员不能看到一堆技术词", "首页不能变成杂乱仪表盘"],
    outputs: ["配置状态", "模型状态", "我司库状态", "主要入口"],
    render: () => `
      <div class="wireframe">
        <div class="hero-panel">
          <div class="panel">
            <div class="panel-title">
              <div>
                <p class="eyebrow">Workbench</p>
                <h3>今天要做哪类编码对照？</h3>
              </div>
              <span class="tag green">配置正常</span>
            </div>
            <div class="flow-row">
              <button class="primary-button" type="button">开始商品对照</button>
              <button class="ghost-button" type="button">更新我司商品库</button>
              <button class="ghost-button" type="button">手工输入商品</button>
              <button class="ghost-button" type="button">系统设置</button>
            </div>
          </div>
          <div class="panel">
            <p class="eyebrow">Status</p>
            <div class="status-grid">
              <div class="status-tile"><span class="tag green">模型</span><strong>DeepSeek 已配置</strong><p class="muted">用于候选解释和风险判断</p></div>
              <div class="status-tile"><span class="tag warn">我司库</span><strong>11522 条</strong><p class="muted">字段待复核 2 项</p></div>
              <div class="status-tile"><span class="tag blue">最近任务</span><strong>客户食堂库</strong><p class="muted">2581 条记录</p></div>
              <div class="status-tile"><span class="tag">导出</span><strong>默认目录可用</strong><p class="muted">中文路径检查通过</p></div>
            </div>
          </div>
        </div>
        <div class="panel tight">
          <div class="flow-row">
            <span class="flow-chip">初始化配置</span>
            <span class="flow-chip">我司库</span>
            <span class="flow-chip">客户库</span>
            <span class="flow-chip">字段确认</span>
            <span class="flow-chip">候选解释</span>
            <span class="flow-chip">人工确认</span>
            <span class="flow-chip">导出</span>
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
    risks: ["API Key 不能明文暴露", "测试连接不发送真实客户数据", "中文路径必须提前检查"],
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
            <button class="mini-button" type="button">检查中文路径</button>
          </div>
        </div>
        <div class="split-2">
          <div class="panel tight"><p class="eyebrow">通过项</p><span class="tag green">默认目录可写</span><span class="tag green">日志目录可写</span><span class="tag green">中文路径通过</span></div>
          <div class="panel tight"><p class="eyebrow">待处理</p><span class="tag red">模型连接未测试</span><span class="tag">我司商品库未导入</span></div>
        </div>
      </div>
    `,
  },
  {
    id: "company",
    flow: "B. 日常商品编码对照",
    title: "导入我司商品库",
    nav: "我司库",
    goals: ["建立目标商品库", "确认编码和名称字段", "识别描述、别名、分类等辅助字段"],
    risks: ["我司库不是纯标准词条", "缺少编码或名称时不能继续", "重复列和空白列要提示"],
    outputs: ["我司商品库记录", "我司字段含义确认结果"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title">
            <div><p class="eyebrow">Company Catalog</p><h3>更新我司商品库</h3></div>
            <button class="primary-button" type="button">选择 Excel</button>
          </div>
          <table class="table-mock">
            <thead><tr><th>系统识别</th><th>Excel 列名</th><th>样例</th><th>用户确认</th></tr></thead>
            <tbody>
              <tr><td>我司商品编码</td><td>SPUID</td><td>100294</td><td><span class="tag green">必需</span></td></tr>
              <tr><td>我司商品名称</td><td>SPU名称（可修改）</td><td>海天金标生抽500ml</td><td><span class="tag green">必需</span></td></tr>
              <tr><td>我司单位</td><td>SPU基本单位</td><td>瓶</td><td><span class="tag blue">强建议</span></td></tr>
              <tr><td>我司描述</td><td>SPU描述（可修改）</td><td>抄码/规格补充</td><td><span class="tag blue">强建议</span></td></tr>
            </tbody>
          </table>
        </div>
        <div class="panel tight">
          <p class="eyebrow">导入摘要</p>
          <span class="tag green">11522 条商品</span>
          <span class="tag">22 列</span>
          <span class="tag red">2 个字段需确认</span>
        </div>
      </div>
    `,
  },
  {
    id: "customer",
    flow: "B. 日常商品编码对照",
    title: "上传客户商品库 / 手工输入",
    nav: "客户库",
    goals: ["支持批量客户库", "支持单条手工查询", "提前暴露重复列、空白列和缺失字段"],
    risks: ["客户库带加工痕迹", "商品名称可能重复列", "规格可能藏在名称里"],
    outputs: ["客户记录", "客户字段含义确认结果"],
    render: () => `
      <div class="wireframe">
        <div class="split-2">
          <div class="panel">
            <div class="panel-title"><div><p class="eyebrow">Batch</p><h3>上传客户商品库</h3></div><button class="primary-button" type="button">选择客户 Excel</button></div>
            <table class="table-mock">
              <thead><tr><th>列名</th><th>样例</th><th>提醒</th></tr></thead>
              <tbody>
                <tr><td>商品名称</td><td>海天金标生抽</td><td><span class="tag green">名称字段</span></td></tr>
                <tr><td>规格</td><td>[1*500g]</td><td><span class="tag">格式需归一</span></td></tr>
                <tr><td>单位</td><td>瓶</td><td><span class="tag blue">强建议</span></td></tr>
                <tr><td>商品名称</td><td>海天金标生抽</td><td><span class="tag red">重复列名</span></td></tr>
              </tbody>
            </table>
          </div>
          <div class="panel">
            <p class="eyebrow">Manual</p>
            <h3>手工输入单条商品</h3>
            <div class="form-grid" style="margin-top:16px">
              <label class="field"><span>商品名称</span><div class="input-mock">海天金标生抽</div></label>
              <label class="field"><span>规格</span><div class="input-mock">500ml</div></label>
              <label class="field"><span>单位</span><div class="input-mock">瓶</div></label>
              <label class="field"><span>备注</span><div class="input-mock">无</div></label>
            </div>
            <div class="flow-row" style="margin-top:18px"><button class="primary-button" type="button">加入对照任务</button></div>
          </div>
        </div>
      </div>
    `,
  },
  {
    id: "fields",
    flow: "B. 日常商品编码对照",
    title: "字段含义确认",
    nav: "字段确认",
    goals: ["把字段分成必需、强建议、可选、不参与", "缺失字段给业务风险提示", "让用户修正系统误判"],
    risks: ["不能机械套固定字段", "缺少必需字段要阻止继续", "强建议字段缺失要降低自动落码等级"],
    outputs: ["字段确认结果", "字段风险提示", "可复用模板"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title"><div><p class="eyebrow">Field Mapping</p><h3>请确认字段含义</h3></div><span class="tag red">规格字段格式混杂</span></div>
          <table class="table-mock">
            <thead><tr><th>业务含义</th><th>我司库列</th><th>客户库列</th><th>等级</th><th>提示</th></tr></thead>
            <tbody>
              <tr><td>商品编码</td><td>SPUID</td><td>编号</td><td><span class="tag green">必需</span></td><td>用于回写和追溯</td></tr>
              <tr><td>商品名称</td><td>SPU名称</td><td>商品名称</td><td><span class="tag green">必需</span></td><td>主判断入口</td></tr>
              <tr><td>规格</td><td>SPU描述</td><td>规格</td><td><span class="tag blue">强建议</span></td><td>缺失会影响自动落码</td></tr>
              <tr><td>备注</td><td>描述</td><td>空白列</td><td><span class="tag">可选</span></td><td>发现空白列，默认不参与</td></tr>
            </tbody>
          </table>
        </div>
        <div class="panel tight"><p class="eyebrow">继续条件</p><span class="tag green">必需字段已确认</span><span class="tag red">强建议字段有风险</span></div>
      </div>
    `,
  },
  {
    id: "match",
    flow: "B. 日常商品编码对照",
    title: "候选生成和证据对齐",
    nav: "候选解释",
    goals: ["生成我司候选", "解释候选来源", "把证据对齐说成人话"],
    risks: ["候选层不能最终拍板", "候选为空要说明原因", "必须暴露冲突和没对上的信息"],
    outputs: ["候选列表", "证据对齐摘要", "五档状态草稿"],
    render: () => `
      <div class="review-layout">
        <div class="panel">
          <p class="eyebrow">客户原始记录</p>
          <h3>海天金标生抽</h3>
          <p class="muted">规格：500ml　单位：瓶　类别：调味品</p>
          <div class="textarea-mock">系统理解：海天是品牌，金标更像系列或等级标识，生抽是核心品名，500ml 和瓶是强约束。</div>
        </div>
        <div class="panel">
          <div class="panel-title"><div><p class="eyebrow">Candidates</p><h3>候选和证据</h3></div><span class="tag blue">建议落码待确认</span></div>
          <div class="candidate-list">
            <div class="candidate selected"><h4>海天金标生抽500ml</h4><p><span class="tag green">品牌对上</span><span class="tag green">品名对上</span><span class="tag green">规格对上</span><br>推荐理由：候选完整覆盖客户记录关键语义。</p></div>
            <div class="candidate"><h4>海天生抽 1*12*500ml</h4><p><span class="tag green">品牌对上</span><span class="tag red">包装层级不同</span><br>风险：可能是整箱，不应自动落码。</p></div>
            <div class="candidate"><h4>海天老抽500ml</h4><p><span class="tag red">核心品名冲突</span><br>风险：生抽不能翻成老抽。</p></div>
          </div>
        </div>
      </div>
    `,
  },
  {
    id: "review",
    flow: "B. 日常商品编码对照",
    title: "人工审核",
    nav: "人工审核",
    goals: ["让人工从找答案变成确认证据", "支持确认、改选、无匹配", "记录审核备注和错误类型"],
    risks: ["建议落码不能伪装成已确认", "人工改选要留痕", "记忆第一版只记录不控制自动落码"],
    outputs: ["人工确认结果", "审核备注", "记忆记录草稿"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title"><div><p class="eyebrow">Review Queue</p><h3>待确认 42 条</h3></div><span class="tag red">8 条必须人工审核</span></div>
          <table class="table-mock">
            <thead><tr><th>客户商品</th><th>推荐我司商品</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr><td>海天金标生抽 500ml</td><td>海天金标生抽500ml</td><td><span class="tag blue">建议落码待确认</span></td><td><button class="mini-button" type="button">确认</button> <button class="mini-button" type="button">改选</button></td></tr>
              <tr><td>可口可乐 1*24*330ml 件</td><td>可口可乐330ml</td><td><span class="tag red">必须人工审核</span></td><td><button class="mini-button" type="button">查看风险</button></td></tr>
              <tr><td>瘦肉 备注：切丝</td><td>瘦肉片</td><td><span class="tag red">必须人工审核</span></td><td><button class="mini-button" type="button">标记理解错误</button></td></tr>
            </tbody>
          </table>
        </div>
        <div class="panel tight">
          <p class="eyebrow">审核动作</p>
          <span class="tag green">确认推荐</span>
          <span class="tag">改选候选</span>
          <span class="tag">标记无匹配</span>
          <span class="tag red">标记遗漏</span>
        </div>
      </div>
    `,
  },
  {
    id: "export",
    flow: "B. 日常商品编码对照",
    title: "导出编码对照表",
    nav: "导出",
    goals: ["基于客户原始 Excel 追加结果列", "不覆盖原文件", "导出业务人员能看懂的中文表"],
    risks: ["必须人工审核不能伪造编码", "导出目录不可写要提示", "文件被占用要可恢复"],
    outputs: ["编码对照结果 Excel", "导出记录", "操作日志"],
    render: () => `
      <div class="wireframe">
        <div class="panel">
          <div class="panel-title"><div><p class="eyebrow">Export</p><h3>导出前确认</h3></div><button class="primary-button" type="button">导出 Excel</button></div>
          <table class="table-mock">
            <thead><tr><th>客户商品</th><th>对照状态</th><th>我司编码</th><th>推荐理由</th><th>人工备注</th></tr></thead>
            <tbody>
              <tr><td>海天金标生抽</td><td><span class="tag green">自动落码</span></td><td>SPU100294</td><td>品牌、品名、规格、单位均覆盖</td><td></td></tr>
              <tr><td>可口可乐 1*24*330ml</td><td><span class="tag red">必须人工审核</span></td><td>不回填</td><td>包装层级可能影响结算</td><td>待采购确认</td></tr>
              <tr><td>未知商品 A</td><td><span class="tag">未找到可靠匹配</span></td><td>不回填</td><td>候选均存在核心冲突</td><td></td></tr>
            </tbody>
          </table>
        </div>
        <div class="split-2">
          <div class="panel tight"><p class="eyebrow">导出文件</p><h3>客户商品库_编码对照结果.xlsx</h3><p class="muted">不会覆盖原始文件</p></div>
          <div class="panel tight"><p class="eyebrow">结果统计</p><span class="tag green">自动 128</span><span class="tag blue">待确认 42</span><span class="tag red">人工 8</span><span class="tag">未匹配 3</span></div>
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
