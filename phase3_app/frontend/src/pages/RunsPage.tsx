import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getConfigStatus } from "../api/client";

export function RunsPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    getConfigStatus()
      .then((c) => setTasks(c.tasks || []))
      .catch(() => {});
  }, []);

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>运行看板</h1>
          <p style={{ color: "var(--muted)", marginTop: 4 }}>查看和管理对照任务</p>
        </div>
      </div>
      <div className="grid">
        {tasks.map((t: any) => (
          <div className="panel" key={t.task_id}>
            <div className="panel-heading">
              <span>{t.task_id?.slice(0, 8)}</span>
            </div>
            <h2>{t.customer_count || 0} 条客户商品</h2>
            <p>状态: {t.task_status || "—"}</p>
            <div className="actions">
              <button onClick={() => navigate(`/runs/${t.task_id}`)}>查看</button>
            </div>
          </div>
        ))}
        {tasks.length === 0 && (
          <div className="panel">
            <h2>暂无任务</h2>
            <p>新建对照任务后，运行看板会出现在这里</p>
            <div className="actions">
              <button onClick={() => navigate("/tasks/new")}>新建任务</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
