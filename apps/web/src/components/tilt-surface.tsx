"use client";

import type { CSSProperties, PointerEvent, ReactNode } from "react";

export function TiltSurface({ children, className = "" }: { children: ReactNode; className?: string }) {
  function onMove(event: PointerEvent<HTMLDivElement>) {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    event.currentTarget.style.setProperty("--rx", `${-y * 7}deg`);
    event.currentTarget.style.setProperty("--ry", `${x * 8}deg`);
    event.currentTarget.style.setProperty("--gx", `${(x + 0.5) * 100}%`);
    event.currentTarget.style.setProperty("--gy", `${(y + 0.5) * 100}%`);
  }
  function reset(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.style.setProperty("--rx", "0deg");
    event.currentTarget.style.setProperty("--ry", "0deg");
  }
  return <div className={`tilt-surface ${className}`} onPointerMove={onMove} onPointerLeave={reset} style={{ "--rx": "0deg", "--ry": "0deg" } as CSSProperties}>{children}</div>;
}
