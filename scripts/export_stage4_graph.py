from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.stage4.orchestrator import STAGE4_GRAPH


def main() -> None:
    graph = STAGE4_GRAPH.get_graph()
    out_dir = Path("stage_4")
    out_dir.mkdir(parents=True, exist_ok=True)

    mermaid = graph.draw_mermaid()
    ascii_graph = graph.draw_ascii()

    (out_dir / "graph_stage4.mmd").write_text(mermaid, encoding="utf-8")
    (out_dir / "graph_stage4.txt").write_text(ascii_graph, encoding="utf-8")

    print("Generated:")
    print(out_dir / "graph_stage4.mmd")
    print(out_dir / "graph_stage4.txt")


if __name__ == "__main__":
    main()
