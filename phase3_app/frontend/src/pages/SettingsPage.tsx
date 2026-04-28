import { useEffect, useState } from "react";
import { getModelSettings, saveModelSettings, testModelSettings, selfCheck, errorMessage } from "../api/client";

export function SettingsPage() {
  const [apiKey, setApiKey] = useState("");
  const [provider, setProvider] = useState("DeepSeek");
  const [modelName, setModelName] = useState("deepseek-chat");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");
  const [dataDir, setDataDir] = useState("D:\\bianmaduizhaoxiangmu\\数据");
  const [exportDir, setExportDir] = useState("D:\\bianmaduizhaoxiangmu\\导出");
  const [notice, setNotice] = useState<{ tone: string; message: string }>({ tone: "neutral", message: "" });
  const [busy, setBusy] = useState(false);
  const [checkResult, setCheckResult] = useState<{ ok: boolean; issues: string[] } | null>(null);

  useEffect(() => {
    getModelSettings().then((s) => {
      setProvider(s.provider || "DeepSeek");
      setModelName(s.model_name || "deepseek-chat");
      setBaseUrl(s.base_url || "https://api.deepseek.com");
      setDataDir(s.data_dir || "D:\\bianmaduizhaoxiangmu\\数据");
      setExportDir(s.export_dir || "D:\\bianmaduizhaoxiangmu\\导出");
    }).catch(() => {});
  }, []);

  async function handleSave() {
    await run(async () => {
      await saveModelSettings({
        provider, model_name: modelName, base_url: baseUrl, api_key: apiKey,
        data_dir: dataDir, export_dir: exportDir,
      } as any);
      setNotice({ tone: "good", message: "模型配置已保存，API Key 不会回显。" });
    });
  }

  async function handleTest() {
    await run(async () => {
      const r = await testModelSettings();
      setNotice({ tone: r.ok ? "good" : "warn", message: r.message });
    });
  }

  async function handleSelfCheck() {
    await run(async () => {
      const r = await selfCheck();
      setCheckResult(r);
      setNotice({ tone: r.ok ? "good" : "warn", message: r.ok ? "自检通过" : `发现 ${r.issues.length} 个问题` });
    });
  }

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    try { await fn(); }
    catch (e) { setNotice({ tone: "warn", message: errorMessage(e) }); }
    finally { setBusy(false); }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>初始化配置</h1>
        </div>
        <span className={`notice ${notice.tone}`}>{notice.message || "配置模型服务和 API Key"}</span>
      </header>

      <section className="grid">
        <article className="panel">
          <div className="panel-heading"><span>01</span><div><h2>模型配置</h2><p>第一版使用 OpenAI 兼容接口</p></div></div>
          <div className="form-grid">
            <ReadOnlyField label="提供方" value={provider} />
            <ReadOnlyField label="模型" value={modelName} />
            <ReadOnlyField label="Base URL" value={baseUrl} />
            <label className="field">
              <span>API Key</span>
              <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="输入后保存在本地数据库" type="password" />
            </label>
            <label className="field">
              <span>默认数据目录</span>
              <input value={dataDir} onChange={(e) => setDataDir(e.target.value)} placeholder="Excel 导入和数据库存储目录" />
            </label>
            <label className="field">
              <span>默认导出目录</span>
              <input value={exportDir} onChange={(e) => setExportDir(e.target.value)} placeholder="对照结果 Excel 导出目录" />
            </label>
          </div>
          <div className="actions">
            <button onClick={handleSave} disabled={busy}>保存配置</button>
            <button className="secondary" onClick={handleTest} disabled={busy}>测试连接</button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading"><span>02</span><div><h2>系统自检</h2><p>检查模型、目录和中文路径</p></div></div>
          {checkResult && (
            <div className="metrics">
              <div className="metric"><span>自检结果</span><strong>{checkResult.ok ? "通过" : "存在问题"}</strong></div>
              {checkResult.issues.map((issue, i) => (
                <div key={i} className="metric"><span>问题 {i + 1}</span><strong>{issue}</strong></div>
              ))}
            </div>
          )}
          <div className="actions">
            <button onClick={handleSelfCheck} disabled={busy}>开始自检</button>
          </div>
        </article>
      </section>
    </>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return <label className="field"><span>{label}</span><input value={value} readOnly /></label>;
}
