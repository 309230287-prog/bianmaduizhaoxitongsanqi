import { Link, useLocation, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "首页" },
  { to: "/settings", label: "初始化配置" },
  { to: "/catalog", label: "我司商品库" },
  { to: "/tasks/new", label: "新建对照任务" },
  { to: "/runs", label: "运行看板" },
  { to: "/export", label: "导出结果" },
];

export function Layout() {
  const location = useLocation();

  return (
    <main className="workspace">
      <aside className="rail" aria-label="三期流程">
        <div className="brand-mark">三期</div>
        <nav>
          {NAV_ITEMS.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                style={active ? { color: "var(--text)", fontWeight: 700 } : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <section className="surface">
        <Outlet />
      </section>
    </main>
  );
}
