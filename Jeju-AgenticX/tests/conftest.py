import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def sample_db():
    if not config.DB_PATH.exists():
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_sample_data.py")], check=True)
    return config.DB_PATH


class FakeLLM:
    """테스트용 LLM — 목적(purpose)별로 정해진 응답을 돌려줍니다."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls = []
        self.mode = "anthropic"

    available = True
    external = True
    label = "테스트 LLM"

    def chat(self, system, user, purpose="", max_tokens=2000):
        self.calls.append(purpose)
        r = self.responses.get(purpose)
        if callable(r):
            r = r(user)
        if r is None:
            raise RuntimeError("no response")
        return r

    def json(self, system, user, purpose="", max_tokens=2000):
        from agent.llm import extract_json

        return extract_json(self.chat(system, user, purpose, max_tokens))
