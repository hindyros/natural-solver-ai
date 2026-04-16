import { useState, useEffect } from "react";

const FRAMES = [
  {
    label: "Parsing problem...",
    art: [
      "  ┌─────────────────────────────┐",
      "  │   min   cᵀx                 │",
      "  │   s.t.  Ax  ≤  b            │",
      "  │         x   ≥  0            │",
      "  └─────────────────────────────┘",
      "  ▓▓▓▓░░░░░░░░░░░░░░  20%",
    ],
  },
  {
    label: "Building constraint matrix...",
    art: [
      "  ⎡  3   1   0  |  12 ⎤",
      "  ⎢  0   2   1  |   8 ⎥",
      "  ⎢  1   0   4  |  15 ⎥",
      "  ⎣  2   3   0  |  10 ⎦",
      "",
      "  ▓▓▓▓▓▓▓▓░░░░░░░░░░  40%",
    ],
  },
  {
    label: "Solving LP relaxation...",
    art: [
      "  ∇f(x) = [ 0.24,  0.00, -1.31 ]",
      "  α      =   0.4700",
      "  Δ      =   0.0314",
      "",
      "  dual vars: λ = [ 1.2, 0.0, 0.8 ]",
      "  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░  60%",
    ],
  },
  {
    label: "Branch & Bound...",
    art: [
      "         z* = 42.3",
      "        /          \\",
      "   z = 38.7      z = 41.0",
      "   x₁ ≤ 2        x₁ ≥ 3",
      "     ✓ prune →  exploring",
      "  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  70%",
    ],
  },
  {
    label: "Converging...",
    art: [
      "  iter   obj       gap",
      "  ────  ───────   ──────",
      "    1   42.300    8.2%",
      "    5   38.710    3.1%",
      "   12   36.201    0.4%  ←",
      "  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░  90%",
    ],
  },
  {
    label: "Optimal solution found!",
    art: [
      "  ╔═══════════════════════════╗",
      "  ║  x₁  =   2.000    ←      ║",
      "  ║  x₂  =   4.500    ←      ║",
      "  ║  x₃  =   0.000    ←      ║",
      "  ║  obj =  36.200   ✓       ║",
      "  ╚═══════════════════════════╝",
    ],
  },
];

const SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export default function MathAnimation() {
  const [frameIdx, setFrameIdx] = useState(0);
  const [spinnerIdx, setSpinnerIdx] = useState(0);

  useEffect(() => {
    const frameTimer = setInterval(() => {
      setFrameIdx((i) => (i + 1) % FRAMES.length);
    }, 1800);
    const spinnerTimer = setInterval(() => {
      setSpinnerIdx((i) => (i + 1) % SPINNERS.length);
    }, 100);
    return () => {
      clearInterval(frameTimer);
      clearInterval(spinnerTimer);
    };
  }, []);

  const frame = FRAMES[frameIdx];

  return (
    <div className="mb-12 rounded border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
          Solver
        </span>
        <span className="text-[10px] font-mono text-primary">
          {SPINNERS[spinnerIdx]} {frame.label}
        </span>
      </div>
      <div className="p-4">
        <pre className="font-mono text-xs leading-relaxed text-primary/80 select-none">
          {frame.art.join("\n")}
        </pre>
      </div>
    </div>
  );
}
