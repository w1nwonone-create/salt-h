"""샌드박스 하위 프로세스 진입점 (tools/sandbox.py 가 호출). 직접 실행하지 않습니다."""
import json
import socket
import sys
import traceback


def _blocked(*_a, **_k):
    raise PermissionError("네트워크 접근이 차단된 실행 환경입니다.")


def main() -> None:
    req = json.loads(sys.stdin.read())
    socket.socket.connect = _blocked  # type: ignore[assignment]
    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.getaddrinfo = _blocked  # type: ignore[assignment]

    import duckdb
    import numpy as np  # noqa: F401  (분석 코드에서 자주 사용)
    import pandas as pd  # noqa: F401

    con = duckdb.connect(req["db"], read_only=True, config={"enable_external_access": False})
    env = {"__name__": "__analysis__", "con": con, "PARAMS": req["params"], "RESULT": None}
    try:
        exec(compile(req["code"], "<analysis>", "exec"), env)  # noqa: S102 — 정적 검사를 통과한 코드
        result = env.get("RESULT")
        if not isinstance(result, dict):
            raise TypeError("분석 코드는 RESULT 에 dict 를 남겨야 합니다.")
        msg = {"ok": True, "result": result}
        body = json.dumps(msg, ensure_ascii=False, default=_default)
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc(limit=4)
        body = json.dumps({"ok": False, "error": tb[-3000:]}, ensure_ascii=False)
    finally:
        con.close()
    sys.stdout.write("<<<RESULT>>>" + body)


def _default(o):
    try:
        import numpy as np

        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if o != o else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except Exception:  # noqa: BLE001
        pass
    return str(o)


if __name__ == "__main__":
    main()
