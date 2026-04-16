import { useState, useEffect } from "react";

const FRAMES = [
  {
    label: "Parsing problem...",
    art: [
      "    ┌───────────────────────────────────────┐",
      "    │                                       │",
      "    │   min   cᵀx                           │",
      "    │   s.t.  Ax  ≤  b                      │",
      "    │         x   ≥  0                      │",
      "    │                                       │",
      "    └───────────────────────────────────────┘",
      "",
      "    ▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░  20%",
    ],
  },
  {
    label: "Building constraint matrix...",
    art: [
      "    ⎡  3   1   0   2  |  12 ⎤",
      "    ⎢  0   2   1   0  |   8 ⎥",
      "    ⎢  1   0   4   1  |  15 ⎥",
      "    ⎢  2   3   0   5  |  10 ⎥",
      "    ⎣  0   1   2   3  |   6 ⎦",
      "",
      "    rank = 4   |   n_vars = 4   |   m_cons = 5",
      "",
      "    ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░  40%",
    ],
  },
  {
    label: "Solving LP relaxation...",
    art: [
      "    ∇f(x)  =  [  0.24,   0.00,  -1.31,   0.77 ]",
      "    α      =    0.4700",
      "    Δ      =    0.0314",
      "",
      "    dual vars:  λ  =  [ 1.20,  0.00,  0.85,  0.32 ]",
      "    slacks:     s  =  [ 0.00,  2.14,  0.00,  4.60 ]",
      "",
      "    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  60%",
    ],
  },
  {
    label: "Branch & Bound...",
    art: [
      "              z*  =  42.300",
      "             /              \\",
      "       z = 38.710        z = 41.050",
      "       x₁  ≤  2          x₁  ≥  3",
      "      /       \\               |",
      "  z=36.201  z=37.800      pruned ✗",
      "    ✓ best",
      "",
      "    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░  70%",
    ],
  },
  {
    label: "Converging...",
    art: [
      "    iter    obj value     gap       time",
      "    ────   ──────────   ──────    ──────",
      "       1    42.300       8.2%      0.1s",
      "       5    38.710       3.1%      0.4s",
      "      12    36.450       1.2%      0.9s",
      "      21    36.205       0.1%      1.4s  ←",
      "",
      "    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░  90%",
    ],
  },
  {
    label: "Optimal solution found!",
    art: [
      "    ╔═══════════════════════════════════╗",
      "    ║                                   ║",
      "    ║   x₁  =   2.000   ←  optimal     ║",
      "    ║   x₂  =   4.500   ←  optimal     ║",
      "    ║   x₃  =   0.000   ←  at bound    ║",
      "    ║   x₄  =   1.200   ←  optimal     ║",
      "    ║                                   ║",
      "    ║   obj  =  36.200   ✓              ║",
      "    ╚═══════════════════════════════════╝",
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
    <div className="mb-12 flex flex-col items-center justify-center py-8">
      <p className="mb-6 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
        {SPINNERS[spinnerIdx]}&nbsp;&nbsp;{frame.label}
      </p>
      <pre className="font-mono text-sm leading-relaxed text-primary select-none">
        {frame.art.join("\n")}
      </pre>
    </div>
  );
}
