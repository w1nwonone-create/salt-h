import { type ReactNode, useEffect, useRef, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Header } from "../shared/Header";
import { Footer } from "../shared/Footer";
import { About } from "../components/About";
import type { Language } from "../App";

type MainPageProps = {
  lang: Language;
  onToggleLang: () => void;
  onGoContact: () => void;
  onLogoClick: () => void;
};

// ─── FadeIn ───────────────────────────────────────────────────────────────────

function FadeIn({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.12 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`${visible ? "animate-fadeInUp" : "opacity-0"} ${className}`}
      style={delay ? { animationDelay: `${delay}s` } : undefined}
    >
      {children}
    </div>
  );
}

// ─── Section transitions ──────────────────────────────────────────────────────

const DarkToCream = () => (
  <div style={{ height: "120px", background: "linear-gradient(to bottom, #0f0a07, #f7f2ea)" }} />
);
const CreamToDarkBg = () => (
  <div style={{ height: "120px", background: "linear-gradient(to bottom, #f7f2ea, #0f0a07)" }} />
);

// ─── Static Data ──────────────────────────────────────────────────────────────

type WorkItem = {
  category: string;
  title: { ko: string; en: string };
  desc: { ko: string; en: string };
  stat?: { ko: string; en: string };
  statLabel?: { ko: string; en: string };
  outcome?: { ko: string; en: string };
};

const WORK_ITEMS: WorkItem[] = [
  {
    category: "CHATBOT SCENARIO",
    title: { ko: "챗봇 시나리오 기획·제작", en: "Chatbot Scenario Planning & Production" },
    desc: { ko: "대화 설계", en: "Conversation Design" },
    stat: { ko: "45억+", en: "₩4.5B+" },
    statLabel: { ko: "1년 누적 챗봇 기여 매출", en: "Revenue contributed via chatbot scenario (1yr)" },
  },
  {
    category: "SOCIAL MEDIA",
    title: { ko: "SNS 콘텐츠 제작·운영", en: "Social Content Creation & Management" },
    desc: { ko: "소셜 미디어 / 브랜드 콘텐츠", en: "Social Media / Brand Content" },
    stat: { ko: "10만", en: "100K" },
    statLabel: { ko: "최대 팔로워 계정 운영", en: "Peak followers on managed account" },
  },
  {
    category: "BRAND LANGUAGE",
    title: { ko: "CRM 카피라이팅", en: "CRM Copywriting" },
    desc: { ko: "마케팅 전략 / 브랜드 언어", en: "Marketing Strategy / Brand Language" },
    stat: { ko: "+30%", en: "+30%" },
    statLabel: { ko: "CTR 증가", en: "CTR lift after CRM copy overhaul" },
  },
  {
    category: "CONTENT SYSTEM",
    title: { ko: "콘텐츠 제작팀을 위한 이미지 에셋 제작", en: "Image Asset Production for Content Teams" },
    desc: { ko: "프롬프트 시스템 및 아카이브 공유 기반", en: "Prompt System & Shared Archive" },
    stat: { ko: "90%", en: "90%" },
    statLabel: { ko: "이미지 제작 리드타임 단축 (30일→3일)", en: "Image production lead time cut (30d → 3d)" },
  },
  {
    category: "PERSONAL BRANDING",
    title: { ko: "1인 브랜드 세계관 설계", en: "Solo Brand Universe Design" },
    desc: { ko: "퍼스널 브랜딩", en: "Personal Branding" },
    outcome: {
      ko: "브랜드의 목소리를 처음으로 갖게 된 창업자들",
      en: "Founders who found their brand voice for the first time.",
    },
  },
];

const CATEGORIES = [
  {
    tag: "BRAND INSIGHT",
    title: { ko: "브랜드가 스스로를 이해하게 합니다", en: "We help brands understand themselves." },
    desc: {
      ko: "브랜드의 말과 행동이 한 방향을 바라보도록 맥락을 정리합니다.",
      en: "We align what your brand says and does into one clear narrative.",
    },
  },
  {
    tag: "ORGANIZATION INSIGHT",
    title: { ko: "사람들이 일하는 방식을 비춥니다", en: "We illuminate how people really work." },
    desc: {
      ko: "인터뷰와 설문을 통해 조직 안에서 오가는 진짜 이야기를 기록합니다.",
      en: "We listen to everyday stories inside the company through interviews and surveys.",
    },
  },
  {
    tag: "PRODUCT INSIGHT",
    title: { ko: "데이터 뒤의 맥락까지 읽어냅니다", en: "We read the context behind the data." },
    desc: {
      ko: "숫자와 사용자의 하루를 함께 바라보며 제품의 다음 한 걸음을 제안합니다.",
      en: "We look at numbers and the user's day together to suggest your product's next step.",
    },
  },
] as const;

const PROCESS_STEPS = [
  { num: "01", name: "INTAKE",      desc: { ko: "프로젝트 맥락, 목표, 제약을 듣고 기록합니다",       en: "We listen and document project context, goals, and constraints." } },
  { num: "02", name: "RESEARCH",    desc: { ko: "인터뷰, 데이터, 시장 맥락을 교차 분석합니다",       en: "Interviews, data, and market context are cross-analyzed." } },
  { num: "03", name: "STORY BIBLE", desc: { ko: "브랜드 세계관의 헌법을 씁니다",                    en: "We write the constitution of your brand universe." } },
  { num: "04", name: "CHARACTER",   desc: { ko: "브랜드 페르소나와 타겟 캐릭터를 설계합니다",       en: "Brand persona and target characters are designed." } },
  { num: "05", name: "VISUALS",     desc: { ko: "세계관에 맞는 비주얼 방향을 제안합니다 (optional)", en: "A visual direction aligned with the world is proposed (optional)." } },
  { num: "06", name: "DELIVERY",    desc: { ko: "납품 문서 + 사용 가이드 + 확장 방향을 전달합니다", en: "Deliverables include documents, usage guides, and expansion directions." } },
] as const;

// ─── Component ────────────────────────────────────────────────────────────────

export const MainPage = ({
  lang,
  onToggleLang,
  onGoContact,
  onLogoClick,
}: MainPageProps) => {
  const [hoveredWork, setHoveredWork] = useState<number | null>(null);
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);

  const TITLE = "Salt H — Brand Language Studio";
  const DESC = "브랜드가 말하고자 하는 것과 실제로 말하고 있는 것 사이의 거리를 좁힙니다. Salt H는 브랜드 언어를 설계합니다.";

  return (
    <div className="flex min-h-screen flex-col" style={{ backgroundColor: "#0f0a07" }}>

      <Helmet>
        <title>{TITLE}</title>
        <meta name="description" content={DESC} />
        <link rel="canonical" href="https://salt-h.com/" />
        <meta property="og:title" content={TITLE} />
        <meta property="og:description" content={DESC} />
        <meta property="og:url" content="https://salt-h.com/" />
        <meta property="og:type" content="website" />
        <meta property="og:image" content="https://salt-h.com/og-image.png" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={TITLE} />
        <meta name="twitter:description" content={DESC} />
      </Helmet>

      {/* Cinematic grain */}
      <div
        aria-hidden
        style={{ position: "fixed", inset: 0, zIndex: 9999, pointerEvents: "none", opacity: 0.025 }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
          <filter id="page-grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.68" numOctaves="3" stitchTiles="stitch" />
          </filter>
          <rect width="100%" height="100%" filter="url(#page-grain)" />
        </svg>
      </div>

      <Header
        lang={lang}
        onToggleLang={onToggleLang}
        onLogoClick={onLogoClick}
        showContactButton
        onContactClick={onGoContact}
      />

      <main className="flex-1">

        {/* ── HERO ──────────────────────────────────────────────────────────── */}
        <section id="hero" className="relative min-h-screen" style={{ backgroundColor: "#0f0a07" }}>

          {/* Silk drift background */}
          <div
            aria-hidden
            style={{
              position: "absolute",
              inset: "-5% -10%",
              backgroundImage: "url('/hero-bg.webp')",
              backgroundSize: "cover",
              backgroundPosition: "center",
              animation: "silkDrift 20s ease-in-out infinite alternate",
              willChange: "transform",
            }}
          />

          {/* Depth overlay */}
          <div
            aria-hidden
            style={{
              position: "absolute",
              inset: 0,
              background:
                "linear-gradient(to bottom, rgba(10,8,6,0.78) 0%, rgba(10,8,6,0.55) 45%, rgba(10,8,6,0.82) 100%)",
            }}
          />

          {/* Content */}
          <div
            className="relative mx-auto flex min-h-screen max-w-[1280px] flex-col justify-center px-6 pb-32 pt-36"
            style={{ zIndex: 10 }}
          >
            {/* Eyebrow */}
            <div className="flex items-center gap-5" style={{ marginBottom: "40px" }}>
              <div
                style={{
                  width: "36px",
                  height: "1px",
                  backgroundColor: "rgba(212,139,95,0.5)",
                  flexShrink: 0,
                }}
              />
              <p
                className="font-sans"
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.28em",
                  color: "rgba(212,139,95,0.68)",
                  textTransform: "uppercase",
                }}
              >
                BRAND LANGUAGE STUDIO
              </p>
            </div>

            {/* Headline — Fraunces */}
            <h1
              className="font-display"
              style={{
                fontSize: "clamp(60px, 9.5vw, 152px)",
                lineHeight: 0.88,
                color: "#f7f2ea",
                letterSpacing: "-0.025em",
                maxWidth: "860px",
              }}
            >
              {["WE FIND", "THE STORY", "YOUR BRAND", "IS ALREADY", "TELLING."].map((line, i) => (
                <span
                  key={line}
                  className="hero-line-blur block"
                  style={{ animationDelay: `${i * 150}ms` }}
                >
                  {line}
                </span>
              ))}
            </h1>

            {/* Subheadline */}
            <p
              className="hero-line-blur font-sans"
              style={{
                marginTop: "48px",
                fontSize: "17px",
                lineHeight: 1.72,
                color: "rgba(247,242,234,0.4)",
                maxWidth: "400px",
                animationDelay: "820ms",
              }}
            >
              {lang === "ko"
                ? "브랜드가 이미 말하고 있는 이야기를, 언어로 완성합니다."
                : "We find the language your brand hasn't named yet."}
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-4" style={{ marginTop: "56px" }}>
              <button
                type="button"
                onClick={onGoContact}
                className="font-sans"
                style={{
                  background: "#f7f2ea",
                  color: "#0f0a07",
                  padding: "14px 32px",
                  fontSize: "11px",
                  fontWeight: 600,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  borderRadius: "2px",
                  border: "1px solid #f7f2ea",
                  cursor: "pointer",
                  transition: "background 0.22s, color 0.22s",
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.background = "transparent";
                  el.style.color = "#f7f2ea";
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.background = "#f7f2ea";
                  el.style.color = "#0f0a07";
                }}
              >
                {lang === "ko" ? "프로젝트 상담 요청" : "Start a Project"}
              </button>

              <a
                href="#work"
                className="font-sans"
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "rgba(247,242,234,0.55)",
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "transparent",
                  border: "1px solid rgba(247,242,234,0.22)",
                  borderRadius: "2px",
                  padding: "14px 32px",
                  transition: "color 0.22s, border-color 0.22s",
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLAnchorElement;
                  el.style.color = "#f7f2ea";
                  el.style.borderColor = "rgba(247,242,234,0.55)";
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLAnchorElement;
                  el.style.color = "rgba(247,242,234,0.55)";
                  el.style.borderColor = "rgba(247,242,234,0.22)";
                }}
              >
                {lang === "ko" ? "작업 보기" : "View Work"}
                <span style={{ fontSize: "13px" }}>→</span>
              </a>
            </div>
          </div>

          {/* Scroll indicator */}
          <div
            className="absolute bottom-10 left-6 flex flex-col items-center gap-3"
            style={{ zIndex: 10 }}
          >
            <p
              className="font-sans"
              style={{
                fontSize: "8px",
                letterSpacing: "0.35em",
                color: "rgba(247,242,234,0.2)",
                textTransform: "uppercase",
                writingMode: "vertical-lr",
                transform: "rotate(180deg)",
                marginBottom: "8px",
              }}
            >
              SCROLL
            </p>
            <div
              style={{
                width: "1px",
                height: "64px",
                backgroundColor: "rgba(247,242,234,0.08)",
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "45%",
                  background: "rgba(212,139,95,0.65)",
                  animation: "scrollLine 2.2s cubic-bezier(0.4,0,0.2,1) infinite",
                }}
              />
            </div>
          </div>

          {/* Location tag */}
          <div
            className="absolute bottom-10 right-6 hidden lg:flex items-center gap-3"
            style={{ zIndex: 10 }}
          >
            <div
              style={{ width: "20px", height: "1px", backgroundColor: "rgba(247,242,234,0.12)" }}
            />
            <span
              className="font-sans"
              style={{
                fontSize: "9px",
                letterSpacing: "0.25em",
                color: "rgba(247,242,234,0.18)",
                textTransform: "uppercase",
              }}
            >
              SEOUL, KR
            </span>
          </div>
        </section>

        <DarkToCream />

        {/* ── WHAT WE DO ────────────────────────────────────────────────────── */}
        <section className="py-24" style={{ backgroundColor: "#f7f2ea" }}>
          <div className="mx-auto max-w-[1280px] px-6">
            <FadeIn>
              <p
                className="font-sans"
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.25em",
                  color: "#d48b5f",
                  textTransform: "uppercase",
                }}
              >
                WHAT WE DO
              </p>
              <h2
                className="font-display"
                style={{
                  fontSize: "clamp(40px,6vw,80px)",
                  color: "#1a120c",
                  marginTop: "16px",
                  lineHeight: 0.92,
                  letterSpacing: "-0.02em",
                }}
              >
                THREE LENSES,
                <br />
                ONE INSIGHT.
              </h2>
            </FadeIn>

            <div style={{ marginTop: "72px" }}>
              {CATEGORIES.map((cat, i) => (
                <FadeIn key={cat.tag} delay={i * 0.12}>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "140px 1fr",
                      gap: "40px",
                      alignItems: "center",
                      minHeight: "120px",
                      paddingTop: "32px",
                      paddingBottom: "32px",
                      borderBottom:
                        i < CATEGORIES.length - 1
                          ? "1px solid rgba(211,183,155,0.28)"
                          : "none",
                    }}
                  >
                    {/* Dominant outline number */}
                    <span
                      className="font-display select-none"
                      style={{
                        fontSize: "clamp(100px,12vw,120px)",
                        lineHeight: 0.88,
                        color: "transparent",
                        WebkitTextStroke: "1.5px #b56a3e",
                        fontWeight: 700,
                        letterSpacing: "-0.03em",
                        marginTop: "-20px",
                        display: "block",
                      }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>

                    {/* Content */}
                    <div>
                      <p
                        className="font-sans"
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          letterSpacing: "0.2em",
                          color: "#7a4820",
                          textTransform: "uppercase",
                        }}
                      >
                        {cat.tag}
                      </p>
                      <h3
                        className="font-sans"
                        style={{
                          fontSize: "clamp(20px,2.2vw,26px)",
                          fontWeight: 600,
                          color: "#1a120c",
                          marginTop: "10px",
                          lineHeight: 1.28,
                          letterSpacing: "-0.01em",
                        }}
                      >
                        {cat.title[lang]}
                      </h3>
                      <p
                        className="font-sans"
                        style={{
                          fontSize: "15px",
                          color: "rgba(26,18,12,0.56)",
                          marginTop: "10px",
                          lineHeight: 1.78,
                          maxWidth: "540px",
                        }}
                      >
                        {cat.desc[lang]}
                      </p>
                    </div>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        <CreamToDarkBg />

        {/* ── SELECTED WORK ─────────────────────────────────────────────────── */}
        <section id="work" className="py-32 relative">
          <div
            aria-hidden
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: "url('/hero-bg.webp')",
              backgroundSize: "cover",
              backgroundPosition: "center",
              zIndex: 0,
            }}
          />
          <div
            aria-hidden
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: "rgba(12,9,6,0.88)",
              zIndex: 1,
            }}
          />
          <div className="relative mx-auto max-w-[1280px] px-6" style={{ zIndex: 2 }}>
            <FadeIn>
              <p
                className="font-sans"
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.25em",
                  color: "#d48b5f",
                  textTransform: "uppercase",
                }}
              >
                SELECTED WORK
              </p>
              <div className="flex flex-wrap items-end justify-between gap-4">
                <h2
                  className="font-display"
                  style={{
                    fontSize: "clamp(36px,5vw,64px)",
                    color: "#f7f2ea",
                    marginTop: "16px",
                    lineHeight: 0.93,
                    letterSpacing: "-0.02em",
                  }}
                >
                  OUR WORK.
                </h2>
                <p
                  className="font-sans"
                  style={{
                    fontSize: "11px",
                    color: "rgba(247,242,234,0.24)",
                    letterSpacing: "0.04em",
                    lineHeight: 1.6,
                    maxWidth: "260px",
                    paddingBottom: "4px",
                  }}
                >
                  {lang === "ko"
                    ? "모든 클라이언트는 비밀유지 조항에 따라 익명으로 표기됩니다."
                    : "All clients listed anonymously by request."}
                </p>
              </div>
            </FadeIn>

            {/* 2×2 grid — first 4 cards */}
            <div className="mt-14 grid gap-4 sm:grid-cols-2">
              {WORK_ITEMS.slice(0, 4).map((item, i) => (
                <FadeIn key={item.category} delay={i * 0.07} className="h-full">
                  <article
                    className="rounded-2xl flex flex-col h-full"
                    style={{
                      backgroundColor: hoveredWork === i ? "#2f2018" : "#241812",
                      padding: "2rem",
                      border: "1px solid rgba(255,255,255,0.06)",
                      transition: "transform 0.5s cubic-bezier(0.16,1,0.3,1), background-color 0.6s ease, border-color 0.3s ease",
                      transform: hoveredWork === i ? "translateY(-4px)" : "translateY(0)",
                      borderColor: hoveredWork === i ? "rgba(212,139,95,0.22)" : "rgba(255,255,255,0.06)",
                      cursor: "default",
                    }}
                    onMouseEnter={() => setHoveredWork(i)}
                    onMouseLeave={() => setHoveredWork(null)}
                  >
                    <p className="font-sans" style={{ fontSize: "10px", letterSpacing: "0.16em", color: "#d48b5f", textTransform: "uppercase" }}>
                      {item.category}
                    </p>
                    <h3 className="font-sans" style={{ fontSize: "16px", fontWeight: 600, color: "#f7f2ea", marginTop: "14px", lineHeight: 1.42, letterSpacing: "-0.01em" }}>
                      {item.title[lang]}
                    </h3>
                    <p className="font-sans" style={{ fontSize: "12px", color: "rgba(247,242,234,0.33)", marginTop: "6px", lineHeight: 1.55 }}>
                      {item.desc[lang]}
                    </p>
                    {item.stat && (
                      <div style={{ marginTop: "auto", paddingTop: "24px", borderTop: "1px solid rgba(247,242,234,0.07)" }}>
                        <span className="font-sans" style={{ fontSize: "clamp(26px,3vw,34px)", fontWeight: 700, color: "#d48b5f", lineHeight: 1, letterSpacing: "-0.02em", display: "block" }}>
                          {item.stat[lang]}
                        </span>
                        <p className="font-sans" style={{ fontSize: "11px", fontWeight: 400, color: "rgba(247,242,234,0.28)", marginTop: "7px", lineHeight: 1.5 }}>
                          {item.statLabel?.[lang]}
                        </p>
                      </div>
                    )}
                  </article>
                </FadeIn>
              ))}
            </div>

            {/* Wide card — Personal Branding */}
            {(() => {
              const item = WORK_ITEMS[4];
              const idx = 4;
              return (
                <FadeIn key={item.category} delay={0.28}>
                  <article
                    className="rounded-2xl mt-4"
                    style={{
                      backgroundColor: hoveredWork === idx ? "#2f2018" : "#241812",
                      border: "1px solid rgba(255,255,255,0.06)",
                      transition: "transform 0.5s cubic-bezier(0.16,1,0.3,1), background-color 0.6s ease, border-color 0.3s ease",
                      transform: hoveredWork === idx ? "translateY(-4px)" : "translateY(0)",
                      borderColor: hoveredWork === idx ? "rgba(212,139,95,0.22)" : "rgba(255,255,255,0.06)",
                      cursor: "default",
                      display: "grid",
                      gridTemplateColumns: "1fr 1px 1fr",
                      gap: "0",
                    }}
                    onMouseEnter={() => setHoveredWork(idx)}
                    onMouseLeave={() => setHoveredWork(null)}
                  >
                    {/* Left: category + title + desc */}
                    <div style={{ padding: "2rem" }}>
                      <p className="font-sans" style={{ fontSize: "10px", letterSpacing: "0.16em", color: "#d48b5f", textTransform: "uppercase" }}>
                        {item.category}
                      </p>
                      <h3 className="font-sans" style={{ fontSize: "16px", fontWeight: 600, color: "#f7f2ea", marginTop: "14px", lineHeight: 1.42, letterSpacing: "-0.01em" }}>
                        {item.title[lang]}
                      </h3>
                      <p className="font-sans" style={{ fontSize: "12px", color: "rgba(247,242,234,0.33)", marginTop: "6px", lineHeight: 1.55 }}>
                        {item.desc[lang]}
                      </p>
                    </div>

                    {/* Divider */}
                    <div style={{ backgroundColor: "rgba(247,242,234,0.07)", alignSelf: "stretch" }} />

                    {/* Right: outcome statement */}
                    <div style={{ padding: "2rem", display: "flex", alignItems: "center" }}>
                      <p
                        className="font-sans"
                        style={{
                          fontSize: "clamp(15px,1.8vw,20px)",
                          fontWeight: 400,
                          color: "rgba(247,242,234,0.62)",
                          lineHeight: 1.7,
                          letterSpacing: "-0.005em",
                        }}
                      >
                        {item.outcome?.[lang]}
                      </p>
                    </div>
                  </article>
                </FadeIn>
              );
            })()}
          </div>
        </section>

        <DarkToCream />

        {/* ── PROCESS ───────────────────────────────────────────────────────── */}
        <section id="process" className="py-32" style={{ backgroundColor: "#f7f2ea" }}>
          <div className="mx-auto max-w-[1280px] px-6">
            <FadeIn>
              <p
                className="font-sans"
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.25em",
                  color: "#d48b5f",
                  textTransform: "uppercase",
                }}
              >
                HOW WE WORK
              </p>
              <h2
                className="font-display"
                style={{
                  fontSize: "clamp(40px,6vw,80px)",
                  color: "#1a120c",
                  marginTop: "16px",
                  lineHeight: 0.92,
                  letterSpacing: "-0.02em",
                }}
              >
                THE
                <br />
                PROCESS.
              </h2>
            </FadeIn>

            <div style={{ marginTop: "72px" }}>
              {PROCESS_STEPS.map(({ num, name, desc }, i, arr) => (
                <FadeIn key={num} delay={i * 0.05}>
                  <div>
                    <div
                      className="grid items-start py-8 transition-all duration-300"
                      style={{
                        gridTemplateColumns: "190px 1fr",
                        gap: "24px",
                        backgroundColor:
                          hoveredStep === num
                            ? "rgba(212,139,95,0.04)"
                            : "transparent",
                        borderLeft:
                          hoveredStep === num
                            ? "2px solid #d48b5f"
                            : "2px solid transparent",
                        paddingLeft:
                          hoveredStep === num ? "12px" : "0",
                        cursor: "default",
                      }}
                      onMouseEnter={() => setHoveredStep(num)}
                      onMouseLeave={() => setHoveredStep(null)}
                    >
                      <span
                        className="font-display select-none"
                        style={{
                          fontSize: "clamp(120px,14vw,160px)",
                          lineHeight: 0.82,
                          color: "transparent",
                          WebkitTextStroke:
                            hoveredStep === num
                              ? "1.5px #d48b5f"
                              : "1.5px rgba(212,139,95,0.16)",
                          transition: "all 0.3s ease",
                          letterSpacing: "-0.03em",
                        }}
                      >
                        {num}
                      </span>
                      <div style={{ paddingTop: "14px" }}>
                        <p
                          className="font-sans"
                          style={{
                            fontSize: "12px",
                            letterSpacing: "0.1em",
                            color: "#d48b5f",
                            fontWeight: 600,
                          }}
                        >
                          {name}
                        </p>
                        <p
                          className="font-sans"
                          style={{
                            fontSize: "16px",
                            color: "rgba(26,18,12,0.56)",
                            marginTop: "8px",
                            lineHeight: 1.72,
                          }}
                        >
                          {desc[lang]}
                        </p>
                      </div>
                    </div>
                    {i < arr.length - 1 && (
                      <div
                        style={{
                          height: "1px",
                          background: "rgba(211,183,155,0.22)",
                        }}
                      />
                    )}
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        <CreamToDarkBg />

        {/* ── ABOUT ─────────────────────────────────────────────────────────── */}
        <About lang={lang} />

        {/* ── CONTACT CTA ───────────────────────────────────────────────────── */}
        <section
          id="contact"
          className="py-32 text-center relative"
          style={{ borderTop: "1px solid rgba(247,242,234,0.05)" }}
        >
          <div
            aria-hidden
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: "url('/hero-bg.webp')",
              backgroundSize: "cover",
              backgroundPosition: "center",
              zIndex: 0,
            }}
          />
          <div
            aria-hidden
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: "rgba(12,8,5,0.93)",
              zIndex: 1,
            }}
          />
          <div
            className="relative mx-auto max-w-[1280px] px-6"
            style={{ zIndex: 2 }}
          >
            <FadeIn>
              <p
                className="font-sans"
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.25em",
                  color: "rgba(212,139,95,0.6)",
                  textTransform: "uppercase",
                }}
              >
                READY TO START?
              </p>
              <h2
                className="font-display"
                style={{
                  fontSize: "clamp(48px,7vw,96px)",
                  color: "#f7f2ea",
                  marginTop: "18px",
                  lineHeight: 0.9,
                  letterSpacing: "-0.025em",
                }}
              >
                LET'S BUILD
                <br />
                YOUR WORLD.
              </h2>
              <p
                className="font-sans"
                style={{
                  fontSize: "16px",
                  color: "rgba(247,242,234,0.42)",
                  marginTop: "24px",
                  lineHeight: 1.72,
                }}
              >
                {lang === "ko"
                  ? "지금 바로 이야기를 시작해보세요."
                  : "Let's start the conversation."}
              </p>

              <div
                style={{
                  marginTop: "52px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "18px",
                }}
              >
                <a
                  href="mailto:winthefirst@salt-h.com"
                  className="font-sans"
                  style={{
                    display: "inline-block",
                    background: "#d48b5f",
                    color: "#0f0a07",
                    padding: "16px 44px",
                    borderRadius: "3px",
                    fontSize: "12px",
                    fontWeight: 600,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    textDecoration: "none",
                    transition: "background 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLAnchorElement).style.background =
                      "#b56a3e";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLAnchorElement).style.background =
                      "#d48b5f";
                  }}
                >
                  {lang === "ko" ? "프로젝트 상담 요청" : "Start a Project"}
                </a>
                <p
                  className="font-sans"
                  style={{
                    fontSize: "13px",
                    color: "rgba(247,242,234,0.32)",
                    lineHeight: 1.6,
                  }}
                >
                  {lang === "ko"
                    ? "영업일 기준 48시간 내 이메일로 회신드립니다"
                    : "We respond within 48 business hours by email."}
                </p>
                <p
                  className="font-sans"
                  style={{ fontSize: "12px", color: "rgba(247,242,234,0.22)" }}
                >
                  winthefirst@salt-h.com
                </p>
              </div>
            </FadeIn>
          </div>
        </section>

      </main>

      <Footer />
    </div>
  );
};
