import { CategorySections } from "../sections/CategorySections";
import { ThreeHInfographic } from "../sections/ThreeHInfographic";
import { Header } from "../shared/Header";
import { Footer } from "../shared/Footer";
import type { Language } from "../App";

type MainPageProps = {
  lang: Language;
  onToggleLang: () => void;
  onGoContact: () => void;
  onLogoClick: () => void;
};

export const MainPage = ({
  lang,
  onToggleLang,
  onGoContact,
  onLogoClick
}: MainPageProps) => {
  return (
    <div className="min-h-screen flex flex-col bg-[#fff7ed] text-[#2b2118]">
      <Header
        lang={lang}
        onToggleLang={onToggleLang}
        onLogoClick={onLogoClick}
        showContactButton
        onContactClick={onGoContact}
      />

      <main className="flex-1">
        {/* Hero 영역 */}
        <section className="relative overflow-hidden border-b border-[#f1dec8]">
          <div className="absolute inset-0 bg-gradient-to-br from-[#ffe8cc] via-[#fff7ed] to-[#fdf2e9]" />
          <div className="absolute -top-32 -right-24 w-72 h-72 bg-salt-primary/20 blur-3xl rounded-full" />
          <div className="relative mx-auto max-w-6xl px-6 py-16 lg:py-24 lg:grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:items-center lg:gap-10">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-white/0 bg-white/80 px-3 py-1 text-xs font-medium text-[#7c5c3a] shadow-sm">
                {lang === "ko"
                  ? "공감 기반 인사이트 스튜디오"
                  : "Empathy-driven insight studio"}
              </p>
              <h1 className="mt-6 text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight">
                {lang === "ko" ? (
                  <>
                    데이터 위에 쌓는
                    <span className="block text-salt-secondary mt-1">
                      사람 중심 인사이트.
                    </span>
                    <span className="mt-2 block text-base sm:text-lg font-normal text-[#6b5740]">
                      일과 삶에 오래 남는 따뜻한 문장들을 만듭니다.
                    </span>
                  </>
                ) : (
                  <>
                    Layering human stories
                    <span className="block text-salt-secondary mt-1">
                      on top of data.
                    </span>
                    <span className="mt-2 block text-base sm:text-lg font-normal text-[#6b5740]">
                      Warm, everyday insights you can actually use.
                    </span>
                  </>
                )}
              </h1>
              <p className="mt-4 max-w-xl text-sm sm:text-base text-[#5b4630]">
                {lang === "ko"
                  ? "숫자와 이야기 사이에서 길을 잃지 않도록, Salt H는 삶에 바로 닿는 한 줌의 인사이트만을 남깁니다."
                  : "Between numbers and narratives, Salt H curates just a handful of insights that speak directly to your life and work."}
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={onGoContact}
                  className="rounded-full bg-salt-secondary px-5 py-2.5 text-sm font-semibold text-[#3b2714] shadow-md shadow-salt-secondary/40 hover:shadow-lg hover:-translate-y-0.5 transition"
                >
                  {lang === "ko" ? "프로젝트 상담 요청" : "Project inquiry"}
                </button>
              </div>
              <div className="mt-10 grid gap-4 sm:grid-cols-3 text-xs text-[#6b5740]">
              <div className="rounded-2xl border border-[#f1dec8] bg-white p-4 shadow-sm">
                <p className="font-semibold text-[#3b2714]">Human Insight</p>
                <p className="mt-1">
                  {lang === "ko"
                    ? "인터뷰, FGI, 리서치 메모에서 숨은 의미를 포착합니다."
                    : "We capture nuance in interviews, focus groups, and research notes."}
                </p>
              </div>
              <div className="rounded-2xl border border-[#f1dec8] bg-white p-4 shadow-sm">
                <p className="font-semibold text-[#3b2714]">Holistic View</p>
                <p className="mt-1">
                  {lang === "ko"
                    ? "데이터・조직・시장 맥락을 한 장의 지도처럼 연결합니다."
                    : "We connect data, organization, and market context into one clear map."}
                </p>
              </div>
              <div className="rounded-2xl border border-[#f1dec8] bg-white p-4 shadow-sm">
                <p className="font-semibold text-[#3b2714]">Honest Story</p>
                <p className="mt-1">
                  {lang === "ko"
                    ? "포장보다 진정성 있는 스토리로 설득력을 만듭니다."
                    : "We tell honest stories that persuade without over-polishing."}
                </p>
              </div>
              </div>
            </div>

            <div className="mt-12 lg:mt-0">
              <div className="relative mx-auto max-w-md overflow-hidden rounded-3xl border border-[#f1dec8] bg-gradient-to-b from-[#302013] via-[#1f150d] to-[#120b06] shadow-[0_18px_45px_rgba(87,63,37,0.45)]">
                {/* 책상 면 */}
                <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-gradient-to-t from-[#3b2412] via-[#2b1a0e] to-transparent" />
                {/* 스탠드 조명 */}
                <div className="absolute -top-10 left-1/2 h-40 w-40 -translate-x-1/2 rounded-full bg-[#f6e0b5] blur-3xl opacity-70" />
                <div className="absolute left-[18%] top-[32%] h-16 w-16 rounded-t-2xl bg-[#fbe2aa]" />
                <div className="absolute left-[28%] top-[48%] h-20 w-2 rounded-full bg-[#e2c38b]" />
                {/* 노트 & 펜 */}
                <div className="absolute bottom-[16%] left-[18%] h-10 w-36 rounded-xl bg-[#f4e0c1]" />
                <div className="absolute bottom-[14%] left-[26%] h-1 w-24 rounded-full bg-[#c79a60]" />
                {/* 사람 실루엣 */}
                <div className="absolute right-[14%] bottom-[10%] h-32 w-24 rounded-[999px] bg-gradient-to-t from-black via-[#120d09] to-[#20160e]" />
                <div className="absolute right-[8%] bottom-[30%] h-10 w-10 rounded-full bg-gradient-to-br from-black via-[#1a120c] to-[#3b2717]" />
              </div>
            </div>
          </div>
        </section>

        {/* 카테고리 섹션 */}
        <CategorySections lang={lang} />

        {/* 3H 인포그래픽 */}
        <ThreeHInfographic lang={lang} />
      </main>

      <Footer />
    </div>
  );
};

