"""run_python — 분석 코드 제한 실행 환경.

제한 사항 (계획서 5.2):
  * 허용 라이브러리만 import (정적 AST 검사)
  * 파일 쓰기·네트워크 차단 (open/eval/exec/__import__/dunder 접근 금지, socket 차단,
    DuckDB 는 read_only + enable_external_access=false 로 COPY/외부 파일 접근 불가)
  * 별도 프로세스, 실행 시간 60초 제한

분석 코드는 전역 ``con``(읽기 전용 DuckDB 연결), ``PARAMS``(dict)를 받아
``RESULT``(JSON 직렬화 가능한 dict)를 남겨야 합니다.

※ 이 샌드박스는 Agent 가 생성한 코드의 실수·오작동을 막기 위한 것으로,
  악의적인 공격자를 상정한 보안 경계는 아닙니다(센터 PC 는 별도 망 정책 적용).
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import config

ALLOWED_IMPORTS = {"pandas", "numpy", "math", "statistics", "datetime", "calendar", "collections",
                   "itertools", "functools", "json", "re", "decimal"}
FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "open", "input", "breakpoint", "globals",
                   "locals", "vars", "memoryview", "exit", "quit", "help", "setattr", "delattr"}
FORBIDDEN_ATTRS = {"connect", "to_csv", "to_excel", "to_parquet", "to_pickle", "to_sql", "to_hdf",
                   "to_feather", "to_stata", "savefig", "write", "write_text", "write_bytes", "unlink",
                   "system", "popen", "remove", "rmdir", "mkdir", "install_extension", "load_extension"}

RUNNER = Path(__file__).with_name("_sandbox_runner.py")


class CodeRejected(Exception):
    pass


def validate(code: str) -> None:
    """정적 검사. 위반 시 CodeRejected."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise CodeRejected(f"문법 오류: {e}") from e
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    raise CodeRejected(f"허용되지 않은 import: {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                raise CodeRejected(f"허용되지 않은 import: {node.module}")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise CodeRejected(f"사용할 수 없는 함수: {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in FORBIDDEN_ATTRS:
                raise CodeRejected(f"사용할 수 없는 속성: .{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            up = node.value.upper()
            for kw in ("COPY ", "ATTACH ", "EXPORT ", "INSTALL ", "LOAD ", "PRAGMA "):
                if kw in up:
                    raise CodeRejected(f"허용되지 않은 SQL 구문: {kw.strip()}")


@dataclass
class RunResult:
    ok: bool
    result: dict | None = None
    stdout: str = ""
    error: str = ""
    seconds: float = 0.0
    meta: dict = field(default_factory=dict)


def run_python(code: str, params: dict, db_path: Path | str | None = None,
               timeout: int | None = None, workdir: Path | None = None) -> RunResult:
    """코드를 별도 프로세스에서 실행하고 RESULT 를 돌려줍니다."""
    try:
        validate(code)
    except CodeRejected as e:
        return RunResult(False, error=f"CodeRejected: {e}")
    payload = json.dumps({"code": code, "params": params, "db": str(db_path or config.DB_PATH)},
                         ensure_ascii=False, default=str)
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-E", str(RUNNER)], input=payload, capture_output=True, text=True,
            encoding="utf-8", timeout=timeout or config.SANDBOX_TIMEOUT_S, cwd=str(workdir or RUNNER.parent),
        )
    except subprocess.TimeoutExpired:
        return RunResult(False, error=f"Timeout: 실행 시간 {timeout or config.SANDBOX_TIMEOUT_S}초 초과",
                         seconds=time.time() - t0)
    secs = time.time() - t0
    out = proc.stdout
    marker = "<<<RESULT>>>"
    if marker in out:
        head, _, body = out.partition(marker)
        try:
            msg = json.loads(body)
        except json.JSONDecodeError as e:
            return RunResult(False, stdout=head, error=f"결과 해석 실패: {e}", seconds=secs)
        if msg.get("ok"):
            return RunResult(True, result=msg["result"], stdout=head, seconds=secs)
        return RunResult(False, stdout=head, error=msg.get("error", "알 수 없는 오류"), seconds=secs)
    return RunResult(False, stdout=out, error=(proc.stderr or "출력 없음")[-3000:], seconds=secs)
