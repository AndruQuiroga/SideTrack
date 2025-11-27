"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";

const links = [
  { href: "/", label: "Overview" },
  { href: "/club", label: "Club Archive" },
  { href: "/discover", label: "Discover" },
  { href: "/u/dreski", label: "My Taste" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-sidetrack-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 lg:px-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 via-fuchsia-500 to-emerald-400 text-xs font-semibold shadow-soft">
            ST
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold tracking-wide text-slate-50">
              Sidetrack
            </span>
            <span className="text-xs text-slate-400">
              Club · Archive · Taste
            </span>
          </div>
        </Link>

        <nav className="hidden gap-1 rounded-full bg-sidetrack-soft/70 p-1 text-xs font-medium text-slate-300 shadow-soft md:flex">
          {links.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  "relative rounded-full px-3 py-1.5 transition-colors",
                  active
                    ? "bg-slate-100 text-sidetrack-bg"
                    : "hover:bg-slate-700/80 hover:text-slate-50"
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
