import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  startTask, pauseTask, resumeTask, stopTask, getTask,
  exportTaskUrl, startNextRound, previewNextRound,
  errorMessage, type TaskStatus,
} from "../api/client";

export function RunBoardPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const nav = useNavigate();
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [notice, setNotice] = useState<{ tone: string; message: string }>({ tone: "neutral", message: "" });
  const [busy, setBusy] = useState(false);
  const [reviewFile, setReviewFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ valid: boolean; errors: string[]; warnings: string[]; confirmed_count: number; no_match_count: number } | null>(null);

  useEffect(() => {
    if (!taskId) return;
    // Start the task automatically when entering the page
    if (!status) {
      startTask(taskId).then(setStatus).catch((e) => setNotice({ tone: "warn", message: errorMessage(e) }));
    }
    const interval = setInterval(async () => {
      try { setStatus(await getTask(taskId)); } catch { /* ignore */ }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  async function handlePause() {
    if (!taskId) return;
    setBusy(true);
    try { setStatus(await pauseTask(taskId)); } catch (e) { setNotice({ tone: "warn", message: errorMessage(e) }); }
    finally { setBusy(false); }
  }

  async function handleResume() {
    if (!taskId) return;
    setBusy(true);
    try { setStatus(await resumeTask(taskId)); } catch (e) { setNotice({ tone: "warn", message: errorMessage(e) }); }
    finally { setBusy(false); }
  }

  async function handleStop() {
    if (!taskId) return;
    setBusy(true);
    try { setStatus(await stopTask(taskId)); } catch (e) { setNotice({ tone: "warn", message: errorMessage(e) }); }
    finally { setBusy(false); }
  }

  async function handlePreviewNextRound() {
    if (!taskId || !reviewFile) { setNotice({ tone: "warn", message: "请先选择人工加工后的 Excel。" }); return; }
    setBusy(true);
    try {
      const r = await previewNextRound(taskId, reviewFile);
      setPreview(r);
      if (r.valid) {
        setNotice({ tone: "good", message: `预览通过：${r.confirmed_count} 条已确认，${r.no_match_count} 条无匹配。` });
      } else {
        setNotice({ tone: "warn", message: `校验发现问题：${r.errors.join("; ")}` });
      }
    } catch (e) {
      setNotice({ tone: "warn", message: errorMessage(e) });
    } finally { setBusy(false); }
  }

  async function handleStartNextRound() {
    if (!taskId) return;
    setBusy(true);
    try {
      setStatus(await startNextRound(taskId));
      setNotice({ tone: "good", message: "第二轮对照已完成。" });
    } catch (e) { setNotice({ tone: "warn", message: errorMessage(e) }); }
    finally { setBusy(false); }
  }

  const m = status?.metrics;
  const isRunning = status?.run_status === "running";
  const isPaused = status?.run_status === "paused";
  const isCompleted = status?.run_status === "completed";
  const canExport = status?.can_export ?? false;
  const progress = m ? Math.round((m.auto_code_count + m.manual_review_count + m.no_reliable_match_count + m.suggested_review_count) / Math.max(m.total_count, 1) * 100) : 0;

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Run Board</p>
          <h1>对照进度看板</h1>
        </div>
        <span className={`notice ${notice.tone || "neutral"}`}>
          {notice.message || (isRunning ? "正在运行..." : isPaused ? "已暂停" : isCompleted ? "本轮已完成" : "准备中")}
        </span>
      </header>

      <section className="grid">
        <article className="panel">
          <div className="panel-heading"><span>运行</span><div><h2>任务状态</h2><p>任务 {taskId?.slice(0, 8)}</p></div></div>
          <div className="metrics">
            <div className="metric"><span>运行状态</span><strong>{status?.run_status ?? "..."}</strong></div>
            <div className="metric"><span>客户库</span><strong>{status?.customer_count ?? 0} 条</strong></div>
            <div className="metric"><span>自动落码</span><strong>{m?.auto_code_count ?? "-"} 条</strong></div>
            <div className="metric"><span>建议复核</span><strong>{m?.suggested_review_count ?? "-"} 条</strong></div>
            <div className="metric"><span>必须人工</span><strong>{m?.manual_review_count ?? "-"} 条</strong></div>
            <div className="metric"><span>未匹配</span><strong>{m?.no_reliable_match_count ?? "-"} 条</strong></div>
            <div className="metric"><span>回大自然池</span><strong>{m?.returned_to_nature_count ?? "-"} 条</strong></div>
            <div className="metric"><span>总轮次</span><strong>{m?.total_rounds ?? "-"}</strong></div>
          </div>
          <div className="progress"><span style={{ width: `${Math.min(progress, 100)}%` }} /></div>
          <div className="actions">
            {isRunning && <button className="secondary" onClick={handlePause} disabled={busy}>暂停</button>}
            {isPaused && <button onClick={handleResume} disabled={busy}>继续</button>}
            {(isRunning || isPaused) && <button className="secondary" onClick={handleStop} disabled={busy}>停止</button>}
            <a className={`button-link ${canExport ? "" : "disabled"}`} href={canExport ? exportTaskUrl(taskId!) : undefined}>
              导出 Excel
            </a>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading"><span>第二轮</span><div><h2>下一轮对照</h2><p>上传人工加工后的 Excel 继续</p></div></div>
          <div className="dropzone" onClick={() => document.getElementById("review-file")?.click()}>
            <span>选择人工加工后的 Excel</span>
            <strong>支持 .xlsx 文件</strong>
            <input id="review-file" accept=".xlsx" onChange={(e) => setReviewFile(e.target.files?.[0] ?? null)} type="file" hidden />
          </div>
          {preview && (
            <div className="metrics">
              <div className="metric"><span>校验结果</span><strong>{preview.valid ? "通过" : "失败"}</strong></div>
              <div className="metric"><span>已确认</span><strong>{preview.confirmed_count} 条</strong></div>
              <div className="metric"><span>无匹配</span><strong>{preview.no_match_count} 条</strong></div>
              {preview.errors.map((e, i) => <div key={i} className="metric"><span>错误</span><strong style={{ color: "var(--warn)" }}>{e}</strong></div>)}
            </div>
          )}
          <div className="actions">
            <button className="secondary" onClick={handlePreviewNextRound} disabled={busy || !reviewFile || !canExport}>预览校验</button>
            <button onClick={handleStartNextRound} disabled={busy || !preview?.valid}>开始第二轮</button>
          </div>
        </article>
      </section>
    </>
  );
}
