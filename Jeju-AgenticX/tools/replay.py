"""저장된 실행을 재현합니다 — runs/<실행>/code/ 의 코드를 다시 실행해 results.json 과 대조.

    python -m tools.replay runs/sample
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import config
from tools.sandbox import run_python


def _close(a, b, tol=1e-9) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a is b
        return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    return a == b


def replay(run_dir: Path, db_path: Path | None = None) -> dict:
    saved = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    report = {}
    for name, run in saved["runs"].items():
        if not run.get("ok"):
            continue
        code = (run_dir / run["code_file"]).read_text(encoding="utf-8")
        rr = run_python(code, {}, db_path=db_path or config.DB_PATH)
        same = rr.ok and _close(json.loads(json.dumps(rr.result, default=str)), saved["results"].get(name))
        report[name] = {"file": run["code_file"], "ok": rr.ok, "identical": bool(same), "error": rr.error[-300:]}
    return report


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("사용법: python -m tools.replay runs/<실행 폴더>")
    run_dir = Path(sys.argv[1])
    dv = json.loads((run_dir / "data_version.json").read_text(encoding="utf-8"))
    from tools.db import data_version

    now = data_version()
    print(f"데이터 버전: 저장 {dv['sha256'][:12]} / 현재 {now['sha256'][:12]} "
          f"→ {'동일' if dv['sha256'] == now['sha256'] else '다름(테이블 행 수 비교: ' + str(dv['tables'] == now['tables']) + ')'}")
    rep = replay(run_dir)
    for k, v in rep.items():
        print(f"  {k:<22} {'재현 일치' if v['identical'] else '불일치'}  ({v['file']}) {v['error']}")
    if not all(v["identical"] for v in rep.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
