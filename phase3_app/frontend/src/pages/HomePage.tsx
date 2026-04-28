import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getConfigStatus } from "../api/client";

export function HomePage() {
  const [config, setConfig] = useState<{ model_configured: boolean; model_name: string; has_company_catalog: boolean; company_product_count: number } | null>(null);

  useEffect(() => {
    getConfigStatus().then(setConfig).catch(() => {});
  }, []);

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Phase 3.1 Workspace</p>
          <h1>商品编码对照系统</h1>
        </div>
        <span className={`notice ${config?.model_configured ? "good" : "warn"}`}>
          {config
            ? config.model_configured
              ? "配置正常，可以开始商品对照"
              : "模型未配置，请先完成初始化配置"
            : "正在检查系统状态..."}
        </span>
      </header>

      <section className="grid">
        <article className="panel">
          <div className="panel-heading">
            <span>01</span>
            <div>
              <h2>初始化配置</h2>
              <p>配置模型服务、API Key 和基础参数</p>
            </div>
          </div>
          <div className="metrics">
            <div className="metric">
              <span>模型状态</span>
              <strong>{config?.model_configured ? "已配置" : "未配置"}</strong>
            </div>
            <div className="metric">
              <span>当前模型</span>
              <strong>{config?.model_name ?? "未知"}</strong>
            </div>
          </div>
          <div className="actions">
            <Link to="/settings" className="button-link">进入配置</Link>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <span>02</span>
            <div>
              <h2>我司商品库</h2>
              <p>管理和更新我司基础商品资料</p>
            </div>
          </div>
          <div className="metrics">
            <div className="metric">
              <span>已导入商品数</span>
              <strong>{config?.company_product_count ?? 0} 条</strong>
            </div>
          </div>
          <div className="actions">
            <Link to="/catalog" className="button-link">管理商品库</Link>
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <span>03</span>
            <div>
              <h2>新建对照任务</h2>
              <p>上传客户商品库，确认字段，开始对照</p>
            </div>
          </div>
          <div className="actions">
            <Link to="/tasks/new" className="button-link">新建任务</Link>
          </div>
        </article>
      </section>
    </>
  );
}
