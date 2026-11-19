"""실행 컨텍스트 — 실행 폴더(runs/날짜_질문ID/), 진행 이벤트, 기록."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import config
from agent.llm import LLM

STAGES = {
    "planner": "질문을 이해하고 있습니다",
    "navigator": "데이터를 찾고 있습니다",
    "analyst": "분석하고 있습니다",
    "critic": "결과를 검증하고 있습니다",
    "reporter": "리포트를 만들고 있습니다",
}


@dataclass
class RunContext:
    run_dir: Path
    llm: LLM
    db_path: Path = field(default_factory=lambda: config.DB_PATH)
    on_event: Callable[[dict], None] | None = None
    events: list = field(default_factory=list)

    @classmethod
    def create(cls, question: str, llm_mode: str | None = None, on_event=None, db_path=None,
               runs_dir: Path | None = None, run_name: str | None = None) -> "RunContext":
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        qid = hashlib.sha1(question.encode("utf-8")).hexdigest()[:6]
        run_dir = Path(runs_dir or config.RUNS_DIR) / (run_name or f"{stamp}_{qid}")
        if run_name and run_dir.exists():  # 같은 이름으로 다시 실행하면 이전 기록을 지웁니다
            shutil.rmtree(run_dir)
        (run_dir / "code").mkdir(parents=True, exist_ok=True)
        llm = LLM(llm_mode, log_path=run_dir / "llm_calls.jsonl")
        return cls(run_dir=run_dir, llm=llm, db_path=Path(db_path or config.DB_PATH), on_event=on_event)

    def emit(self, stage: str, message: str, **detail) -> None:
        ev = {"time": dt.datetime.now().isoformat(timespec="seconds"), "stage": stage, "message": message, **detail}
        self.events.append(ev)
        with open(self.run_dir / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
        if self.on_event:
            try:
                self.on_event(ev)
            except Exception:  # noqa: BLE001 — UI 콜백 오류가 분석을 멈추지 않도록
                pass

    def save_json(self, name: str, obj) -> Path:
        p = self.run_dir / name
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return p
