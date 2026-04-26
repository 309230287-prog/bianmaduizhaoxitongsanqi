import { ChangeEvent, useState } from "react";

import {
  createTask,
  exportTaskUrl,
  importCompanyCatalog,
  saveModelSettings,
  startTask,
  testModelSettings,
  TaskStatus,
} from "../api/client";

type Notice = {
  tone: "good" | "warn" | "neutral";
  message: string;
};

export function WorkspacePage() {
  const [apiKey, setApiKey] = useState("");
  const [companyFile, setCompanyFile] = useState<File | null>(null);
  const [customerFile, setCustomerFile] = useState<File | null>(null);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [notice, setNotice] = useState<Notice>({
    tone: "neutral",
    message: "先完成模型配置，再更新我司库，然后上传客户库开始第一轮对照。",
  });
  const [busy, setBusy] = useState(false);

  async function handleSaveModel() {
    await runAction("模型配置已保存，API Key 不会回显。", async () => {
      await saveModelSettings({
        provider: "DeepSeek",
        model_name: "deepseek-chat",
        base_url: "https://api.deepseek.com",
        api_key: apiKey,
      });
    });
  }

  async function handleTestModel() {
    setBusy(true);
    try {
      const result = await testModelSettings();
      setNotice({ tone: result.ok ? "good" : "warn", message: String(result.message) });
    } catch (error) {
      setNotice({ tone: "warn", message: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function handleImportCompany() {
    if (!companyFile) {
      setNotice({ tone: "warn", message: "请先选择我司商品库 Excel。" });
      return;
    }
    await runAction("我司商品库已更新。", async () => {
      const result = await importCompanyCatalog(companyFile);
      setNotice({ tone: "good", message: `我司商品库已更新：${result.imported_count} 条。` });
    });
  }

  async function handleCreateTask() {
    if (!customerFile) {
      setNotice({ tone: "warn", message: "请先选择客户商品库 Excel。" });
      return;
    }
    await runAction("客户任务已创建。", async () => {
      const result = await createTask(customerFile);
      setTask(result);
      setNotice({ tone: "good", message: `客户任务已创建：${result.customer_count} 条。` });
    });
  }

  async function handleStartTask() {
    if (!task) {
      setNotice({ tone: "warn", message: "请先创建客户任务。" });
      return;
    }
    await runAction("第一轮对照已完成。", async () => {
      const result = await startTask(task.task_id);
      setTask(result);
    });
  }

  async function runAction(successMessage: string, action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
      setNotice((current) =>
        current.tone === "good" ? current : { tone: "good", message: successMessage },
      );
    } catch (error) {
      setNotice({ tone: "warn", message: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  const canExport = task?.status === "completed";

  return (
    <main className="workspace">
      <aside className="rail" aria-label="三期流程">
        <div className="brand-mark">三期</div>
        <nav>
          <a href="#settings">初始化配置</a>
          <a href="#company">我司库</a>
          <a href="#customer">客户任务</a>
          <a href="#run">运行看板</a>
        </nav>
      </aside>

      <section className="surface">
        <header className="topbar">
          <div>
            <p className="eyebrow">Phase 3.1 Workspace</p>
            <h1>商品编码对照系统</h1>
          </div>
          <span className={`notice ${notice.tone}`}>{notice.message}</span>
        </header>

        <section className="grid">
          <Panel id="settings" step="01" title="模型配置" description="第一版使用 DeepSeek 配置，真实调用会在下一步接入。">
            <div className="form-grid">
              <ReadOnlyField label="提供方" value="DeepSeek" />
              <ReadOnlyField label="模型" value="deepseek-chat" />
              <ReadOnlyField label="Base URL" value="https://api.deepseek.com" />
              <label className="field">
                <span>API Key</span>
                <input
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="输入后只保存在本地服务内存"
                  type="password"
                />
              </label>
            </div>
            <div className="actions">
              <button onClick={handleSaveModel} disabled={busy}>保存配置</button>
              <button className="secondary" onClick={handleTestModel} disabled={busy}>测试配置</button>
            </div>
          </Panel>

          <Panel id="company" step="02" title="更新我司商品库" description="这是基础资料，不需要每次任务都更新。">
            <FilePicker label="选择我司 Excel" onChange={setCompanyFile} />
            <div className="actions">
              <button onClick={handleImportCompany} disabled={busy || !companyFile}>上传并更新</button>
            </div>
          </Panel>

          <Panel id="customer" step="03" title="新建客户对照任务" description="上传客户库，或者先记录单条手工输入。">
            <FilePicker label="选择客户 Excel" onChange={setCustomerFile} />
            <div className="manual-row">
              <input placeholder="手工输入商品名称，例如：海天金标生抽" />
              <input placeholder="规格，例如：500ml" />
              <input placeholder="单位，例如：瓶" />
            </div>
            <div className="actions">
              <button onClick={handleCreateTask} disabled={busy || !customerFile}>创建任务</button>
            </div>
          </Panel>

          <Panel id="run" step="04" title="运行看板" description="第一轮完成后才能导出 Excel。暂停/继续会在后台任务化后接入。">
            <div className="metrics">
              <Metric label="任务状态" value={task?.status ?? "未创建"} />
              <Metric label="客户库" value={task ? `${task.customer_count} 条` : "-"} />
              <Metric label="自动落码" value={task?.metrics ? `${task.metrics.auto_code_count} 条` : "-"} />
              <Metric label="回大自然池" value={task?.metrics ? `${task.metrics.returned_to_nature_count} 条` : "-"} />
            </div>
            <div className="progress">
              <span style={{ width: canExport ? "100%" : task ? "45%" : "8%" }} />
            </div>
            <div className="actions">
              <button onClick={handleStartTask} disabled={busy || !task || task.status === "completed"}>
                开始第一轮对照
              </button>
              <button className="secondary" disabled>暂停</button>
              <button className="secondary" disabled>停止</button>
              <a
                className={`button-link ${canExport ? "" : "disabled"}`}
                href={canExport ? exportTaskUrl(task.task_id) : undefined}
              >
                导出 Excel
              </a>
            </div>
          </Panel>
        </section>
      </section>
    </main>
  );
}

function Panel(props: {
  id: string;
  step: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <article className="panel" id={props.id}>
      <div className="panel-heading">
        <span>{props.step}</span>
        <div>
          <h2>{props.title}</h2>
          <p>{props.description}</p>
        </div>
      </div>
      {props.children}
    </article>
  );
}

function ReadOnlyField(props: { label: string; value: string }) {
  return (
    <label className="field">
      <span>{props.label}</span>
      <input value={props.value} readOnly />
    </label>
  );
}

function FilePicker(props: { label: string; onChange: (file: File | null) => void }) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    props.onChange(event.target.files?.[0] ?? null);
  }

  return (
    <label className="dropzone">
      <span>{props.label}</span>
      <strong>支持 .xlsx 文件</strong>
      <input accept=".xlsx" onChange={handleChange} type="file" />
    </label>
  );
}

function Metric(props: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "操作失败，请检查本地服务。";
}

