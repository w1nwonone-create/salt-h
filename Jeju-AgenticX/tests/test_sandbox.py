from tools.sandbox import run_python


def test_runs_and_returns_result():
    r = run_python("import pandas as pd\nRESULT = {'n': int(con.execute('SELECT COUNT(*) FROM weather_station').fetchone()[0])}", {})
    assert r.ok and r.result == {"n": 4}


def test_blocks_imports_files_dunder_and_sql_copy():
    assert "import" in run_python("import os\nRESULT={}", {}).error
    assert "open" in run_python("open('x','w')\nRESULT={}", {}).error
    assert "__class__" in run_python("x=(1).__class__\nRESULT={}", {}).error
    assert "COPY" in run_python("con.execute(\"COPY weather_station TO 'a.csv'\")\nRESULT={}", {}).error
    r = run_python("RESULT={'x': con.execute(\"SELECT * FROM read_csv('/etc/hostname')\").fetchall()}", {})
    assert not r.ok


def test_timeout():
    r = run_python("while True:\n    pass\nRESULT={}", {}, timeout=2)
    assert not r.ok and "Timeout" in r.error


def test_requires_result_dict():
    assert not run_python("x = 1", {}).ok
