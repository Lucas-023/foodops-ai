"""Run the benchmark against the agent (Phase 4).

Usage:
    python -m eval.run_eval
"""

import json
import time
from pathlib import Path

from app.agent.graph import run_agent
from app.db.session import SessionLocal
from eval.metrics import answer_contains, tool_selection_accuracy

DATASET = Path(__file__).parent / "dataset.jsonl"


def load_dataset(path: Path = DATASET) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    results = []
    with SessionLocal() as session:
        for case in load_dataset():
            t0 = time.perf_counter()
            response = run_agent(session, case["question"])
            latency = time.perf_counter() - t0
            called = [c.tool for c in response.tool_calls]
            results.append(
                {
                    "id": case["id"],
                    "tool_accuracy": tool_selection_accuracy(case["expected_tools"], called),
                    "answer_contains": answer_contains(response.answer, case.get("expected_answer_contains", [])),
                    "latency_s": round(latency, 3),
                }
            )

    n = len(results)
    print(json.dumps(results, indent=2))
    print(f"tool_accuracy={sum(r['tool_accuracy'] for r in results) / n:.2%}")


if __name__ == "__main__":
    main()
