# Jeju-AgenticX

**제주에서 창업을 준비하는 도민과 그 곁의 상담사를 위한 상권 체력 분석 AI Agent**
[데이콘] 제주 AI·빅데이터 활용 AI Agent 개발 챌린지 출품작 · 팀 에이전틱스

> 평소의 언어로 질문하면, Agent 가 제주의 공공데이터를 스스로 찾아 분석하고 검증한 뒤
> 후보지별 **상권 체력**(시즌 안정성 · 관광 의존도 · 평일 안정성 · 날씨 민감도)을
> 근거와 한계가 분명한 리포트로 전달합니다.
> **AI 는 숫자를 만들어내지 않고, 코드가 계산한 숫자만을 전달합니다.**

---

## 1. 빠른 시작

### 센터 PC (Windows)
1. `install.bat` 더블클릭 — 가상환경 생성 → 라이브러리 설치 → 분석 DB 준비 → 바탕화면 바로가기 생성
2. 바탕화면의 **`Jeju-AgenticX 실행`** 더블클릭 → 브라우저에서 `http://localhost:8501` 이 열립니다.

### Linux / macOS
```bash
./run.sh
```

### 수동 설치
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # 필요 시 LLM_API_KEY 입력
python scripts/build_sample_data.py                  # data/jeju.duckdb 생성 (약 5초)
streamlit run app.py
```

요구 사항: Python 3.11 이상, RAM 8GB 이상 권장(센터 PC 최소 사양 i7-8700 / RAM 32GB 에서 여유 있게 동작).

## 2. 환경 변수 (`.env`)

| 변수 | 설명 | 기본값 |
|---|---|---|
| `LLM_MODE` | `auto`(Key 있으면 외부 LLM → Ollama → 규칙 기반) · `anthropic` · `ollama` · `rules` | `auto` |
| `LLM_API_KEY` | 외부 LLM(Claude) API Key. 평가용 Key 는 사용 한도를 설정해 제공 | (없음) |
| `LLM_MODEL` | 외부 LLM 모델 ID | `claude-sonnet-5-5` |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | 오프라인 모드 로컬 모델 | `http://localhost:11434` / `qwen2.5:3b-instruct-q4_K_M` |
| `JEJU_DB_PATH` | 분석 DuckDB 경로. 센터 실데이터 DB 로 바꾸면 그대로 실데이터 분석 | `data/jeju.duckdb` |
| `JEJU_DATAHUB_KEY` | 제주데이터허브 API Key (데이터 최신화용, 선택) | (없음) |

Key 는 `.env` 에만 두며 저장소·제출물에 포함하지 않습니다. **Key 가 없어도 규칙 기반 모드로 전체 기능이 동작합니다.**

오프라인 모드(반출 제한 데이터를 외부로 전혀 보내지 않아야 할 때):
```bash
ollama pull qwen2.5:3b-instruct-q4_K_M     # VRAM 3GB 이내
# .env → LLM_MODE=ollama
```

## 3. 사용자 매뉴얼

| 화면 | 하는 일 |
|---|---|
| ① 시작 | 질문 입력(또는 예시 버튼) · 후보지 지정(지도 클릭 또는 법정동·정류소 목록, 최대 3곳) · 업종 선택 |
| (함께 묻기) | 업종·조건이 정해지지 않았으면 Agent 가 선택지를 보여 줍니다. 예) “비수기, 평일, 비 오는 날 중에서 고르시거나, 모두 비교해 드릴 수도 있습니다.” |
| ② 위치 확인 | 지도에 후보지 · 분석 격자(굵은 선) · 주변 3×3 격자(점선) · 반경 500m 정류소 표시. 맞으면 “위치가 맞습니다” |
| ③ 진행 | “데이터를 찾고 있습니다 → 분석하고 있습니다 → 결과를 검증하고 있습니다” 단계와 활용 데이터 목록 |
| ④ 리포트 | 핵심 요약 → 상담 시 함께 살펴볼 내용 → 후보지 비교표 → 조건별 변화 폭 차트 → 근거 → 한계. **HTML 저장 · PDF로 저장/인쇄** |
| ⑤ 상세 보기 | Agent 가 생성·실행한 분석 코드, 실행 기록, 분석 계획·위치 연결, 검증 기록 (상담사·센터 담당자 검토용) |

질문 예시: “애월 해안도로와 한림 협재 쪽 중에서, 카페를 하기에 비수기에 덜 흔들리는 곳은 어디일까요?”,
“함덕이랑 월정리 카페, 겨울 평일에도 손님이 있을까요?”, “서귀포 올레시장 근처 분식집은 몇 시에 손님이 많을까요?”

### 명령줄(CLI)
```bash
python -m agent.graph "후보지 비교하기" --place aewol --place hyeopjae --industry cafe --conditions all
python -m tools.replay runs/sample          # 저장된 코드로 결과 재현 → "재현 일치"
```
장소 id·업종 key 는 `data/places.yaml` 참고.

## 4. Agent 구성

```
사용자 질문 ─▶ ① Planner ─▶ ② Navigator ─▶ ③ Analyst ─▶ ④ Critic ─(통과)─▶ ⑤ Reporter
               (ask_user)                     ▲             │
                                              └─ 재분석 요청 ─┘ (최대 2회)
```
LangGraph 상태 그래프(`agent/graph.py`)로 실행되며, LangGraph 가 없으면 같은 순서의 순차 실행기로 자동 대체됩니다.

| Agent | 파일 | 역할 | Tool |
|---|---|---|---|
| ① Planner | `agent/planner.py` | 질문 → JSON 분석 계획(후보지·업종·기간·조건·지표), 불분명하면 선택지 제시, 범위 밖 요청 표시 | `ask_user` |
| ② Navigator | `agent/navigator.py` | 좌표 → 500m 격자·법정동·행정동·반경 내 정류소·최근접 관측소 연결, 카탈로그에서 데이터셋 선택, 스키마·기간 확인 | `point_to_grid` `point_to_bjd` `nearby_stops` `nearest_station` `catalog_search` `schema_peek` |
| ③ Analyst | `agent/analyst.py` | 분석 코드 생성 → 샌드박스 실행 → 오류 시 자가 수정(최대 3회). 표준 지표는 검증된 템플릿, 자유 질문은 LLM 코드 생성 | `run_python` `duckdb_query` `make_chart` |
| ④ Critic | `agent/critic.py` | 표본 수·결측·연도 효과·격자 경계·집계 단위 점검 → 통과/재분석/불가 판정, 한계 문구 | `check_sample_size` `check_missing` `check_period_bias` |
| ⑤ Reporter | `agent/reporter.py` | 비교·크기·조건을 담은 결정적 요약 문장, (LLM 연결 시) 문장 다듬기 + **수치 대조**, HTML/PDF 리포트 | `render_report` `export_pdf` `verify_numbers` |

### 신뢰를 위한 장치
- **수치 대조**: 리포트의 모든 수치를 코드 산출값과 대조합니다. LLM 이 다듬은 문장에 대조되지 않는 수치나 단정적 추천 표현이 있으면 그 문장을 버리고 코드 값으로 만든 문장을 씁니다. 결정적 문장에서도 대조가 실패하면 리포트 생성을 중단합니다.
- **연도 효과 재분석**: 연도별 성수기 규모가 10% 이상 다르면 Critic 이 “같은 시즌연도(여름과 그 직후 겨울)” 비교로 재분석을 요청합니다. (예시 데이터의 월정리·함덕에서 실제로 발생)
- **최소 집계 기준**: 이용 건수 5건 미만 셀, 외식업 표본 점포 3곳 미만은 리포트에 노출하지 않습니다.
- **원본 데이터 비전송**: 외부 LLM 에는 질문·컬럼 구조·집계 결과만 전달합니다(`schema_peek` 는 외부 모드에서 샘플 행을 넣지 않음).
- **샌드박스**(`tools/sandbox.py`): 별도 프로세스, 허용 라이브러리만 import, 파일 쓰기·네트워크·`eval/exec`·dunder 접근 차단, DuckDB 읽기 전용 + 외부 파일 접근 차단, 60초 제한.
- **재현성**: 실행마다 `runs/날짜_질문ID/` 에 요청·계획·위치 연결·생성 코드·결과·검증·리포트·실행 기록·데이터 버전(DB 해시)·LLM 호출 기록(프롬프트 전문 포함)을 저장. `python -m tools.replay` 로 재실행해 결과 일치를 확인합니다. LLM 호출은 temperature 0.

## 5. 지표 정의

| 지표 | 정의 | 데이터 (단위) |
|---|---|---|
| 소비 규모 | 후보지 격자 업종 카드 이용 금액의 최근 12개월 월평균 (+ 주변 3×3 격자) | 카드 이용 현황(500m격자) · 월 |
| 시즌 안정성 | 비수기(11~2월) 월평균 ÷ 성수기(7~8월) 월평균. 연도 효과가 있으면 같은 시즌연도끼리 비교. 외식업 포스 매출 기준 값도 병기 | 카드(500m격자), 외식업 포스(500m격자) · 월 |
| 관광 의존도 | (개별+단체관광객) 이용 금액 ÷ 전체, 비수기 값 병기 | 카드(요일별)_v02 · 법정동·월 |
| 평일 안정성 | 평일 하루 평균 ÷ 주말·공휴일 하루 평균 (월별 요일 합계 ÷ 해당 요일 일수). “비수기 평일 하루 ÷ 성수기 주말 하루” 병기 | 카드(요일별)_v02 · 법정동·월 |
| 날씨 민감도 | 같은 달·같은 요일유형(평일/주말·공휴일) 안에서 우천일(일강수량 1mm 이상) 평균 ÷ 비우천일 평균 − 1, 우천일 수로 가중평균. 방문인구(행정동)와 인근 정류소 버스 이용 두 지표 | 내국인 유동인구(읍면동)_v02, 버스 정류소별 이용 현황 × 일일 날씨 정보 · 일 |
| 시간대 패턴 | 시간대(오전·점심·오후·저녁·밤)별 이용 금액 비중과 최대 시간대 | 카드(시간대)_v02 · 법정동·월 |

카드·외식업 매출은 월 단위라 특정 날짜의 날씨와 직접 연결하지 않습니다. 서로 다른 시간 단위의 데이터는 억지로 결합하지 않고 지표별로 알맞은 단위에서 분석합니다.

## 6. 검증 결과

```bash
python -m pytest -q tests          # 단위·통합 테스트 17건
python eval/build_reference.py     # 기준 질문 20개의 정답을 Agent 와 독립된 pandas 코드로 계산
python eval/run_eval.py            # Agent 실행 → 계획·데이터 선택·수치 정확도 측정 → eval/results.md
```

| 항목 (규칙 기반 모드, 예시 데이터) | 결과 |
|---|---|
| 계획 정확도 (후보지·업종·지표) | 20/20 |
| 데이터 선택 정확도 | 20/20 |
| 수치 정확도 (독립 구현 대비 ±0.001) | 43/43 |

해석 시 유의: 기준 질문은 개발팀이 작성했고 “정답”은 사람이 손으로 계산한 값이 아니라 **Agent 와 별도로 작성한 독립 구현**의 값입니다. 따라서 이 결과는 “지표 정의대로 정확히 계산·선택하는가”를 보여 주며, 처음 보는 표현의 질문에 대한 이해력은 센터 시범 운영에서 실제 질문으로 추가 측정해야 합니다.

## 7. 데이터

자세한 내용은 [`data/README_data.md`](data/README_data.md).

- **반출 제한 데이터**(카드·외식업 포스·유동인구)는 센터 밖에서 원본을 확보할 수 없어, 「데이터 명세서」와 **같은 컬럼 구조의 예시 데이터**로 전체 흐름을 검증합니다. 예시 데이터의 수치는 실제 상권 실적이 아닙니다.
- **반출 가능 데이터**(버스·날씨·정류소·관측소)는 `data/raw/<테이블명>.csv` 로 넣고 `python scripts/build_sample_data.py` 를 실행하면 실데이터가 우선 적재됩니다.
- 센터 PC 에서는 실데이터로 만든 DuckDB 경로를 `JEJU_DB_PATH` 에 지정하면 코드 수정 없이 동작합니다.

## 8. 오류·제약 사항

- **지도 타일**은 인터넷(OpenStreetMap)이 필요합니다. 오프라인이면 지도 대신 “법정동·정류소에서 고르기” 목록을 사용하세요.
- **PDF**: 리포트의 “PDF로 저장 / 인쇄” 버튼(브라우저 인쇄 → PDF로 저장)을 기본으로 사용합니다. Python Playwright 가 설치된 PC 에서는 “PDF 만들기” 버튼으로 바로 생성됩니다.
- **법정동 연결**은 기준 장소(15곳) 중심점과의 거리로 근사합니다. 기준 장소에서 3km 이상 떨어진 지점은 경고를 표시합니다. 실데이터 환경에서는 법정동 경계(SHP) 공간조인으로 교체할 수 있습니다(`tools/geo.py: point_to_bjd`).
- **격자 ID**는 UTM-K(EPSG:5179) 좌표를 500m 로 절사한 `G500_{X}_{Y}` 형식입니다. 센터 데이터의 격자 ID 체계가 다르면 `tools/geo.py: grid_id()` 한 곳만 맞추면 됩니다.
- **기상 관측소**는 종관기상관측(ASOS) 4곳(제주·고산·성산·서귀포)입니다. 후보지에서 10km 이상 떨어지면 Critic 이 “국지적인 비는 다를 수 있다”는 한계를 표시합니다. AWS 지점을 `weather_station` 에 추가하면 자동으로 가장 가까운 지점을 씁니다.
- **외부 LLM·로컬 모델 경로**는 테스트에서 가짜 LLM 으로 검증했습니다(계획 환각 무시, 수치 불일치 문장 폐기, 코드 자가 수정). 실제 API·Ollama 응답 품질은 Key·모델을 연결한 환경에서 확인이 필요합니다.
- 샌드박스는 Agent 가 생성한 코드의 실수·오작동을 막기 위한 장치이며, 악의적 공격자를 상정한 보안 경계는 아닙니다.

## 9. 폴더 구성

```
Jeju-AgenticX/
├─ README.md · requirements.txt · .env.example · install.bat · run.bat · run.sh
├─ app.py                      # Streamlit UI
├─ config.py                   # 경로·임계값
├─ agent/                      # planner · navigator · analyst · critic · reporter · graph · llm · context
├─ tools/                      # geo · catalog · sandbox · db · checks · charts · report · replay
├─ analysis_templates/         # 검증된 분석 코드 템플릿 (지표별)
├─ prompts/                    # 각 Agent 프롬프트 전문
├─ templates/report.html.j2    # 리포트 템플릿
├─ data/
│  ├─ data_catalog.yaml        # 데이터셋·항목 명세 및 지표 매핑
│  ├─ places.yaml              # 기준 장소·관측소·업종 매핑
│  └─ README_data.md           # 출처·이용 조건·전처리 흐름 (원본 데이터 미포함)
├─ scripts/build_sample_data.py
├─ eval/                       # golden_questions.json · build_reference.py · run_eval.py · results.md
├─ tests/
├─ runs/sample/                # 실행 결과 예시 (리포트 HTML/PDF · 생성 코드 · 실행 기록)
└─ docs/결과설명자료.pdf
```

## 10. AI 활용 내역 · 오픈소스

- **서비스 내 AI**: 외부 LLM API(Anthropic Claude, 기본 `claude-sonnet-5-5`) — 질문 해석 보조, 자유 질문 분석 코드 작성·수정, 요약 문장 다듬기. 오프라인 모드 Qwen2.5-3B-Instruct(Q4, Ollama). 수치 계산에는 LLM 을 쓰지 않습니다(pandas/DuckDB).
- **개발 과정**: Claude Code(AI 코딩 도구)를 코드 작성 보조에 활용했습니다.
- **외부 API**: Anthropic API(선택), 제주데이터허브 API(선택), OpenStreetMap 타일(지도 표시).

| 라이브러리 | 라이선스 |
|---|---|
| pandas, numpy, Jinja2, python-dotenv | BSD-3-Clause |
| duckdb, PyYAML, langgraph, anthropic, folium, streamlit-folium | MIT |
| streamlit | Apache-2.0 |
| Qwen2.5-3B-Instruct | Qwen Research License (모델 카드 확인 필요) |

데이터 출처: 제주데이터허브(jejudatahub.net) · 제주빅데이터센터 · 기상청. 이용약관과 반출 정책을 준수하며, 리포트 하단에 출처를 자동 표기합니다.
