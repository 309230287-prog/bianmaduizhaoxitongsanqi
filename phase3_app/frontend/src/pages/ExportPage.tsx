import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getConfigStatus, exportTaskUrl } from "../api/client";

export function ExportPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [notice, setNotice] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    getConfigStatus()
      .then((c) => setTasks((c.tasks || []).filter((t: any) => t.can_export)))
      .catch(() => {});
  }, []);

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>导出结果</h1>
          <p style={{ color: "var(--muted)", marginTop: 4 }}>下载已完成任务的对照结果 Excel</p>
        </div>
      </div>
      {notice && <p className={`notice ${notice.includes("成功") ? "good" : "warn"}`} style={{ marginBottom: 12 }}>{notice}</p>}
      <div className="grid">
        {tasks.map((t: any) => (
          <div className="panel" key={t.task_id}>
            <div className="panel-heading">
              <span>{t.task_id?.slice(0, 8)}</span>
              <span style={{ color: "var(--good)" }}>可导出</span>
            </div>
            <h2>{t.customer_count || 0} 条客户商品</h2>
            <p>状态: {t.task_status || "—"}</p>
            <div className="actions">
              <a
                className="button-link"
                href={exportTaskUrl(t.task_id)}
                target="_blank"
                rel="noreferrer"
                onClick={() => setNotice("导出已开始")}
              >
                下载 Excel
              </a>
              <button className="secondary" onClick={() => navigate(`/runs/${t.task_id}`)}>查看详情</button>
            </div>
          </div>
        ))}
        {tasks.length === 0 && (
          <div className="panel">
            <h2>暂无已完成任务</h2>
            <p>任务运行完成后，可在此导出结果</p>
          </div>
        )}
      </div>
    </div>
  );
}
