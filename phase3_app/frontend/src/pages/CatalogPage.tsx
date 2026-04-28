import { useEffect, useState } from "react";
import { getCurrentCatalog, importCompanyCatalog, errorMessage } from "../api/client";

type Sample = { code: string; name: string; brand: string; spec: string; unit: string };

export function CatalogPage() {
  const [catalog, setCatalog] = useState<{ product_count: number; sample_products: Sample[] } | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<{ tone: string; message: string }>({ tone: "neutral", message: "我司商品库是系统基础资料。" });
  const [busy, setBusy] = useState(false);

  useEffect(() => { loadCatalog(); }, []);

  async function loadCatalog() {
    try { setCatalog(await getCurrentCatalog()); } catch { /* ignore */ }
  }

  async function handleImport() {
    if (!file) { setNotice({ tone: "warn", message: "请先选择 Excel 文件。" }); return; }
    setBusy(true);
    try {
      const r = await importCompanyCatalog(file);
      setNotice({ tone: "good", message: `导入成功：${r.imported_count} 条商品。` });
      await loadCatalog();
    } catch (e) {
      setNotice({ tone: "warn", message: errorMessage(e) });
    } finally { setBusy(false); }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Company Catalog</p>
          <h1>我司商品库</h1>
        </div>
        <span className={`notice ${notice.tone}`}>{notice.message}</span>
      </header>

      <section className="grid">
        <article className="panel">
          <div className="panel-heading"><span>01</span><div><h2>更新商品库</h2><p>选择我司商品库 Excel 并导入</p></div></div>
          <FilePicker label="选择我司 Excel" onChange={setFile} />
          <div className="actions">
            <button onClick={handleImport} disabled={busy || !file}>上传并更新</button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading"><span>02</span><div><h2>当前商品库</h2><p>已导入 {catalog?.product_count ?? 0} 条商品</p></div></div>
          {catalog && catalog.sample_products.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--line)" }}>
                    <th style={{ textAlign: "left", padding: "0.5rem" }}>编码</th>
                    <th style={{ textAlign: "left", padding: "0.5rem" }}>名称</th>
                    <th style={{ textAlign: "left", padding: "0.5rem" }}>品牌</th>
                    <th style={{ textAlign: "left", padding: "0.5rem" }}>规格</th>
                    <th style={{ textAlign: "left", padding: "0.5rem" }}>单位</th>
                  </tr>
                </thead>
                <tbody>
                  {catalog.sample_products.map((p) => (
                    <tr key={p.code} style={{ borderBottom: "1px solid var(--line)" }}>
                      <td style={{ padding: "0.5rem" }}>{p.code}</td>
                      <td style={{ padding: "0.5rem" }}>{p.name}</td>
                      <td style={{ padding: "0.5rem" }}>{p.brand}</td>
                      <td style={{ padding: "0.5rem" }}>{p.spec}</td>
                      <td style={{ padding: "0.5rem" }}>{p.unit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
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
