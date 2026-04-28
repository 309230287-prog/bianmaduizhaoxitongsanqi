import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  confirmFields,
  errorMessage,
  getFieldSuggestions,
  type FieldMapping,
  type FieldSuggestions,
} from "../api/client";

export function FieldConfirmPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const nav = useNavigate();
  const [suggestions, setSuggestions] = useState<FieldSuggestions | null>(null);
  const [notice, setNotice] = useState<{ tone: string; message: string }>({
    tone: "neutral",
    message: "系统已根据列名做初步识别，请确认后再开始对照。",
  });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!taskId) return;
    getFieldSuggestions(taskId)
      .then(setSuggestions)
      .catch((e) => setNotice({ tone: "warn", message: errorMessage(e) }));
  }, [taskId]);

  async function handleConfirm() {
    if (!taskId || !suggestions) return;
    setBusy(true);
    try {
      const response = await confirmFields(taskId, suggestions.customer_mappings, suggestions.company_mappings);
      if (!response.confirmed) {
        setNotice({ tone: "warn", message: `还有必需字段未确认：${response.missing_required.join("、")}` });
        return;
      }
      setNotice({ tone: "good", message: "字段确认完成，正在进入运行看板。" });
      nav(`/runs/${taskId}`);
    } catch (e) {
      setNotice({ tone: "warn", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Field Confirmation</p>
          <h1>字段含义确认</h1>
        </div>
        <span className={`notice ${notice.tone}`}>{notice.message}</span>
      </header>

      <section className="grid">
        <MappingPanel title="客户商品库字段" mappings={suggestions?.customer_mappings ?? []} />
        <MappingPanel title="我司商品库字段" mappings={suggestions?.company_mappings ?? []} />
        <article className="panel">
          <div className="panel-heading">
            <span>继续</span>
            <div>
              <h2>确认后开始第一轮</h2>
              <p>字段确认完成后，系统才允许进入运行看板。</p>
            </div>
          </div>
          {suggestions?.missing_required.length ? (
            <div className="metrics">
              {suggestions.missing_required.map((item) => (
                <div className="metric" key={item}>
                  <span>缺少必需字段</span>
                  <strong style={{ color: "var(--warn)" }}>{item}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">必需字段已识别。当前 3.1 版本先使用系统建议映射，后续版本再开放逐列手工改映射。</p>
          )}
          <div className="actions">
            <button className="secondary" onClick={() => nav("/tasks/new")}>返回任务</button>
            <button onClick={handleConfirm} disabled={busy || !suggestions || suggestions.missing_required.length > 0}>
              确认字段并进入运行看板
            </button>
          </div>
        </article>
      </section>
    </>
  );
}

function MappingPanel({ title, mappings }: { title: string; mappings: FieldMapping[] }) {
  return (
    <article className="panel">
      <div className="panel-heading">
        <span>字段</span>
        <div>
          <h2>{title}</h2>
          <p>把 Excel 列名翻译成系统业务含义</p>
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--line)" }}>
              <th style={cellStyle}>Excel 列名</th>
              <th style={cellStyle}>系统理解</th>
              <th style={cellStyle}>等级</th>
            </tr>
          </thead>
          <tbody>
            {mappings.map((mapping) => (
              <tr key={`${mapping.column_index}-${mapping.column_name}`} style={{ borderBottom: "1px solid var(--line)" }}>
                <td style={cellStyle}>{mapping.column_name}</td>
                <td style={cellStyle}>{mapping.business_field}</td>
                <td style={cellStyle}>{importanceLabel(mapping.importance_level)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

const cellStyle = { textAlign: "left" as const, padding: "0.55rem" };

function importanceLabel(value: string) {
  if (value === "required") return "必需";
  if (value === "suggested") return "建议";
  if (value === "ignored") return "不参与";
  return "可选";
}
