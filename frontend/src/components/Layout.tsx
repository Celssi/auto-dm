import { Link, Outlet, useLocation } from "react-router-dom";

export default function Layout() {
  const loc = useLocation();
  const links = [
    { to: "/", label: "Home" },
    { to: "/characters", label: "Characters" },
    { to: "/campaigns", label: "Campaigns" },
    { to: "/adventures", label: "Adventures" },
    { to: "/play", label: "Play" },
    { to: "/settings", label: "Settings" },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="border-b border-border bg-panel/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
          <Link to="/" className="font-bold text-accent">
            Auto-DM
          </Link>
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={`text-sm ${loc.pathname.startsWith(l.to) && l.to !== "/" ? "text-accent" : loc.pathname === l.to ? "text-accent" : "text-muted hover:text-white"}`}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </nav>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
