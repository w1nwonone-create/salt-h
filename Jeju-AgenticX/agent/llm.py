"""LLM 연결 계층 — 외부 LLM(기본) · 로컬 모델(오프라인) · 규칙 기반(LLM 없음).

원칙: LLM 은 계획 수립·코드 작성·설명만 담당하며, 수치는 만들지 않습니다.
외부 LLM 에는 원본 데이터를 보내지 않습니다(컬럼 구조와 집계 결과만).
모든 호출은 temperature 0, 호출 기록은 실행 폴더의 llm_calls.jsonl 에 남습니다.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import config


def load_prompt(name: str) -> str:
    return (config.PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


class LLM:
    def __init__(self, mode: str | None = None, log_path: Path | None = None):
        self.requested = (mode or config.LLM_MODE).lower()
        self.log_path = log_path
        self.mode = self._resolve()
        self._client = None

    # ------------------------------------------------------------------
    def _resolve(self) -> str:
        want = self.requested
        if want in ("anthropic", "auto") and config.LLM_API_KEY:
            try:
                import anthropic  # noqa: F401

                return "anthropic"
            except ImportError:
                if want == "anthropic":
                    return "rules"
        if want in ("ollama", "auto") and self._ollama_alive():
            return "ollama"
        return "rules"

    @staticmethod
    def _ollama_alive() -> bool:
        try:
            with urllib.request.urlopen(f"{config.OLLAMA_HOST}/api/tags", timeout=1.0) as r:
                return r.status == 200
        except Exception:  # noqa: BLE001
            return False

    @property
    def available(self) -> bool:
        return self.mode != "rules"

    @property
    def external(self) -> bool:
        """데이터가 센터 밖으로 나가는 모드인가 (외부 API)."""
        return self.mode == "anthropic"

    @property
    def label(self) -> str:
        return {"anthropic": f"외부 LLM ({config.LLM_MODEL})",
                "ollama": f"오프라인 로컬 모델 ({config.OLLAMA_MODEL})",
                "rules": "규칙 기반 (LLM 미사용)"}[self.mode]

    # ------------------------------------------------------------------
    def chat(self, system: str, user: str, purpose: str = "", max_tokens: int = 2000) -> str:
        if not self.available:
            raise RuntimeError("LLM 이 연결되어 있지 않습니다(규칙 기반 모드).")
        t0 = time.time()
        err = None
        text = ""
        try:
            text = self._anthropic(system, user, max_tokens) if self.mode == "anthropic" else self._ollama(system, user)
            return text
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            raise
        finally:
            self._log({"purpose": purpose, "mode": self.mode, "seconds": round(time.time() - t0, 2),
                       "system": system, "user": user, "response": text, "error": err})

    def json(self, system: str, user: str, purpose: str = "", max_tokens: int = 2000) -> dict:
        text = self.chat(system, user, purpose, max_tokens)
        return extract_json(text)

    def _anthropic(self, system: str, user: str, max_tokens: int) -> str:
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=config.LLM_API_KEY, timeout=config.LLM_TIMEOUT)
        kwargs = dict(model=config.LLM_MODEL, max_tokens=max_tokens, system=system,
                      messages=[{"role": "user", "content": user}])
        try:
            msg = self._client.messages.create(temperature=0, **kwargs)
        except anthropic.BadRequestError as e:
            if "temperature" not in str(e):
                raise
            msg = self._client.messages.create(**kwargs)  # temperature 를 받지 않는 모델 대비
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

    def _ollama(self, system: str, user: str) -> str:
        body = json.dumps({
            "model": config.OLLAMA_MODEL, "stream": False, "options": {"temperature": 0},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode()
        req = urllib.request.Request(f"{config.OLLAMA_HOST}/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT * 3) as r:
            return json.loads(r.read())["message"]["content"]

    def _log(self, rec: dict) -> None:
        if not self.log_path:
            return
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()
