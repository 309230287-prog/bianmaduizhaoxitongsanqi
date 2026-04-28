import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createTask, createManualTask, addManualRow, errorMessage } from "../api/client";

export function NewTaskPage() {
  const nav = useNavigate();
  const [customerFile, setCustomerFile] = useState<File | null>(null);
  const [manualName, setManualName] = useState("");
  const [manualSpec, setManualSpec] = useState("");
  const [manualUnit, setManualUnit] = useState("");
  const [manualBrand, setManualBrand] = useState("");
  const [manualNote, setManualNote] = useState("");
  const [notice, setNotice] = useState<{ tone: string; message: string }>({
    tone: "neutral",
    message: "上传客户商品库或手工输入单品，确认后开始对照。",
  });
  const [busy, setBusy] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);

  async function handleCreateFromFile() {
    if (!customerFile) { setNotice({ tone: "warn", message: "请先选择客户商品库 Excel。" }); return; }
    setBusy(true);
    try {
      const r = await createTask(customerFile);
      setTaskId(r.task_id);
      setNotice({ tone: "good", message: `任务已创建：${r.customer_count} 条。下一步确认字段。` });
      nav(`/tasks/${r.task_id}/fields`);
    } catch (e) {
      setNotice({ tone: "warn", message: errorMessage(e) });
    } finally { setBusy(false); }
  }

  async function handleManualAdd() {
    if (!manualName.trim()) { setNotice({ tone: "warn", message: "商品名称不能为空。" }); return; }
    setBusy(true);
    try {
      // Create task first if needed, or reuse existing
      let tid = taskId;
      if (!tid) {
        const created = await createManualTask({
          "商品名称": manualName,
          "规格": manualSpec,
          "单位": manualUnit,
          "品牌": manualBrand,
          "备注": manualNote,
        });
        setTaskId(created.task_id);
        setNotice({ tone: "good", message: `手工任务已创建：${manualName}。下一步确认字段。` });
        nav(`/tasks/${created.task_id}/fields`);
        return;
      }
      await addManualRow(tid, {
        "商品名称": manualName, "规格": manualSpec, "单位": manualUnit,
        "品牌": manualBrand, "备注": manualNote,
      });
      setNotice({ tone: "good", message: `手工商品已添加：${manualName}` });
      setManualName(""); setManualSpec(""); setManualUnit(""); setManualBrand(""); setManualNote("");
    } catch (e) {
      setNotice({ tone: "warn", message: errorMessage(e) });
    } finally { setBusy(false); }
  }

  function handleStart() {
    if (!taskId) { setNotice({ tone: "warn", message: "请先创建任务。" }); return; }
    nav(`/tasks/${taskId}/fields`);
  }

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">New Task</p>
          <h1>新建对照任务</h1>
        </div>
        <span className={`notice ${notice.tone}`}>{notice.message}</span>
      </header>

      <section className="grid">
        <article className="panel">
          <div className="panel-heading"><span>01</span><div><h2>导入客户数据</h2><p>上传客户商品库 Excel</p></div></div>
          <FilePicker label="选择客户 Excel" onChange={setCustomerFile} />
          <div className="actions">
            <button onClick={handleCreateFromFile} disabled={busy || !customerFile}>创建任务</button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading"><span>02</span><div><h2>手工输入单品</h2><p>补充单条客户商品记录</p></div></div>
          <div className="form-grid">
            <label className="field"><span>商品名称 *</span><input value={manualName} onChange={(e) => setManualName(e.target.value)} placeholder="例如：海天金标生抽" /></label>
            <label className="field"><span>品牌</span><input value={manualBrand} onChange={(e) => setManualBrand(e.target.value)} placeholder="例如：海天" /></label>
            <label className="field"><span>规格</span><input value={manualSpec} onChange={(e) => setManualSpec(e.target.value)} placeholder="例如：500ml" /></label>
            <label className="field"><span>单位</span><input value={manualUnit} onChange={(e) => setManualUnit(e.target.value)} placeholder="例如：瓶" /></label>
            <label className="field"><span>备注</span><input value={manualNote} onChange={(e) => setManualNote(e.target.value)} placeholder="例如：切丝" /></label>
          </div>
          <div className="actions">
            <button className="secondary" onClick={handleManualAdd} disabled={busy}>添加手工商品</button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading"><span>03</span><div><h2>字段确认</h2><p>开始对照前必须确认字段含义</p></div></div>
          <div className="metrics">
            <div className="metric"><span>任务状态</span><strong>{taskId ? "已创建" : "未创建"}</strong></div>
            <div className="metric"><span>任务ID</span><strong>{taskId ? taskId.slice(0, 12) + "..." : "-"}</strong></div>
          </div>
          <div className="actions">
            <button onClick={handleStart} disabled={!taskId}>进入字段确认</button>
          </div>
        </article>
      </section>
    </>
  );
}

function FilePicker({ label, onChange }: { label: string; onChange: (f: File | null) => void }) {
  return (
    <label className="dropzone">
      <span>{label}</span>
      <strong>支持 .xlsx 文件</strong>
      <input accept=".xlsx" onChange={(e) => onChange(e.target.files?.[0] ?? null)} type="file" />
    </label>
  );
}
