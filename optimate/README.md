# OptiMATE v1-light

An autonomous Operations Research consulting pipeline. Give it a plain-English business problem and raw data — it profiles the data, detects the optimization opportunity, formulates the math, writes and runs solver code, debugs it if it fails, and delivers a polished Markdown report. No human in the loop.

---

## Agentic System

```mermaid
flowchart TD
    IN([Input: problem.txt + data.csv]) --> BA
    IN --> DP

    subgraph L1[Layer 1 - Understand]
        BA[BusinessAnalyst\nExtracts ProblemBrief\nlight model]
        DP[DataProfiler\nPandas stats + column interpretation\nlight model]
    end

    BA --> AS
    BA --> IS
    BA --> SS
    DP --> AS
    DP --> IS
    DP --> SS

    subgraph L2[Layer 2 - Detect in parallel]
        AS[AssignmentScout\nworker / vehicle / task matching]
        IS[InventoryScout\nEOQ / lot sizing / replenishment]
        SS[SchedulingScout\njob-shop / shift / deadline]
    end

    AS -->|confidence scored proposal| OR
    IS -->|confidence scored proposal| OR
    SS -->|confidence scored proposal| OR

    subgraph L3[Layer 3 - Rank]
        OR[OpportunityRanker\nPicks best opportunity\nlight model]
    end

    OR --> FM

    subgraph L4[Layer 4 - Build and Solve]
        FM[Formulator\nvariables + objective + constraints\nheavy model]
        FM --> MD[Modeler\ngenerates solver code\nPuLP or OR-Tools\nlight model]
        MD --> EX[Executor\nruns code in sandbox\ndebug loop x3]
    end

    EX --> RW

    subgraph L5[Layer 5 - Report]
        RW[ReportWriter\nconsultant-grade Markdown report\nheavy model]
    end

    RW --> OUT([Output: report.md + solution.json])

    style L1 fill:#f0e6ff,stroke:#9b59b6
    style L2 fill:#dbeafe,stroke:#2563eb
    style L3 fill:#fef9c3,stroke:#d97706
    style L4 fill:#dcfce7,stroke:#16a34a
    style L5 fill:#ffe4e6,stroke:#e11d48
```

### Models used

| Layer | Agent(s) | Model tier | OpenAI default |
|-------|----------|-----------|----------------|
| Understand | BusinessAnalyst, DataProfiler | Light | `gpt-4o-mini` |
| Detect | AssignmentScout, InventoryScout, SchedulingScout | Light | `gpt-4o-mini` |
| Rank | OpportunityRanker | Light | `gpt-4o-mini` |
| Build | Formulator | **Heavy** | `gpt-4o` |
| Build | Modeler | Light | `gpt-4o-mini` |
| Report | ReportWriter | **Heavy** | `gpt-4o` |

Solvers: **PuLP/CBC** (assignment, inventory) · **OR-Tools CP-SAT** (scheduling)

---

## Setup

```bash
cd OptiMATE-v1-light
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Add your OpenAI key to `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

---

## How to Run

### Run the full pipeline

```bash
python cli.py run \
  --input examples/sample_problem.txt \
  --data examples/sample_data.csv \
  --provider openai
```

With multiple data files:

```bash
python cli.py run \
  --input problem.txt \
  --data file1.csv \
  --data file2.csv \
  --provider openai
```

With a custom run ID:

```bash
python cli.py run \
  --input problem.txt \
  --data data.csv \
  --run-id my_run_001 \
  --provider openai
```

Output lands in `artifacts/{run_id}/`:
- `report.md` — consultant Markdown report
- `solution_output.json` — objective value, decision variables
- `generated_code.py` — solver code that was executed

### Check run status

```bash
python cli.py status <run_id>
```

### Run tests

```bash
pytest tests/
```

---

## Project Structure

```
OptiMATE-v1-light/
├── cli.py                        Entry point
├── .env                          API keys (gitignored)
├── examples/
│   ├── sample_problem.txt        Example logistics problem
│   └── sample_data.csv           8 drivers × 12 routes cost matrix
├── optimatecore/
│   ├── orchestrator.py           Pipeline runner
│   ├── base_agent.py             Shared LLM call + retry logic
│   ├── llm_client.py             Anthropic / OpenAI / Groq adapters
│   ├── artifact_store.py         Atomic file store per run
│   ├── sandbox.py                Resource-limited subprocess
│   ├── agents/                   All agents (see diagram above)
│   │   └── scouts/               Parallel opportunity detectors
│   ├── schemas/                  Pydantic contracts between agents
│   └── solvers/                  PuLP + OR-Tools templates
└── artifacts/                    Runtime output (gitignored)
```
