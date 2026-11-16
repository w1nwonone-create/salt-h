import { useState } from "react";
import { Helmet } from "react-helmet-async";
import type { Language } from "../App";
import { Header } from "../shared/Header";
import { Footer } from "../shared/Footer";

type ContactPageProps = {
  lang: Language;
  onToggleLang: () => void;
  onGoHome: () => void;
};

export const ContactPage = ({
  lang,
  onToggleLang,
  onGoHome
}: ContactPageProps) => {
  const isKo = lang === "ko";

  const [nameOrg, setNameOrg] = useState("");
  const [email, setEmail] = useState("");
  const [projectType, setProjectType] = useState("");
  const [budget, setBudget] = useState("");
  const [message, setMessage] = useState("");

  const TARGET_EMAIL = "ceo@ai-agentics.kr";

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = (e) => {
    e.preventDefault();

    const subject = isKo
      ? `[Salt H] 프로젝트 문의 - ${nameOrg || "이름 미기재"}`
      : `[Salt H] Project inquiry - ${nameOrg || "No name"}`;

    const bodyLines = [
      isKo ? "새 프로젝트 문의가 접수되었습니다." : "A new project inquiry has been submitted.",
      "",
      `${isKo ? "이름 / 소속" : "Name / Organization"}: ${nameOrg || "-"}`,
      `${isKo ? "이메일" : "Email"}: ${email || "-"}`,
      `${isKo ? "프로젝트 유형" : "Project type"}: ${projectType || "-"}`,
      `${isKo ? "예상 예산 (KRW / USD)" : "Estimated budget (KRW / USD)"}: ${
        budget || "-"
      }`,
      "",
      `${isKo ? "현재 상황과 원하는 변화" : "Current situation & goal"}`,
      message || "-"
    ];

    const mailtoUrl = `mailto:${TARGET_EMAIL}?subject=${encodeURIComponent(
      subject
    )}&body=${encodeURIComponent(bodyLines.join("\n"))}`;

    window.location.href = mailtoUrl;
  };

  const TITLE = "프로젝트 문의 — Salt H";
  const DESC = "브랜드 언어 설계, 세계관 구축, 콘텐츠 전략에 대해 문의하세요. Salt H가 답합니다.";

  return (
    <div className="min-h-screen flex flex-col bg-[#fff7ed] text-[#2b2118]">
      <Helmet>
        <title>{TITLE}</title>
        <meta name="description" content={DESC} />
        <link rel="canonical" href="https://salt-h.com/contact" />
        <meta property="og:title" content={TITLE} />
        <meta property="og:description" content={DESC} />
        <meta property="og:url" content="https://salt-h.com/contact" />
        <meta property="og:type" content="website" />
        <meta property="og:image" content="https://salt-h.com/og-image.png" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={TITLE} />
        <meta name="twitter:description" content={DESC} />
      </Helmet>
      <Header
        lang={lang}
        onToggleLang={onToggleLang}
        onLogoClick={onGoHome}
        showContactButton={false}
      />

      <main className="flex-1">
        <section className="border-b border-[#f1dec8]">
          <div className="mx-auto max-w-4xl px-6 py-16 lg:py-20">
            <div className="max-w-xl">
              <p className="text-xs font-medium text-[#a08b76] uppercase tracking-[0.18em]">
                {isKo ? "PROJECT INQUIRY" : "PROJECT INQUIRY"}
              </p>
              <h1 className="mt-3 text-2xl sm:text-3xl lg:text-4xl font-semibold tracking-tight">
                {isKo ? "지금 고민하고 있는 이야기" : "The story you’re working on"}
              </h1>
              <p className="mt-3 text-sm text-[#6b5740]">
                {isKo
                  ? "아직 정리가 덜 된 생각이어도 괜찮습니다. 편하게 현재 상황과 바라는 방향을 적어 주세요. 2–3 영업일 안에 메일로 답을 드립니다."
                  : "It’s okay if your thoughts aren’t fully formed yet. Share where you are and where you’d like to go. We’ll get back to you within 2–3 business days."}
              </p>
            </div>

            <form
              className="mt-10 grid gap-6 sm:grid-cols-2"
              onSubmit={handleSubmit}
            >
              <div className="sm:col-span-1 flex flex-col gap-1.5 text-sm">
                <label className="text-[#4a3826] font-medium">
                  {isKo ? "이름 / 소속" : "Name / Organization"}
                </label>
                <input
                  value={nameOrg}
                  onChange={(e) => setNameOrg(e.target.value)}
                  className="rounded-xl border border-[#e5d2c0] bg-white px-3 py-2 text-sm text-[#2b2118] outline-none focus:border-salt-secondary focus:ring-2 focus:ring-salt-secondary/30 transition"
                  placeholder={
                    isKo ? "예: 홍길동 / Salt H" : "e.g. Alex Kim / Salt H"
                  }
                />
              </div>

              <div className="sm:col-span-1 flex flex-col gap-1.5 text-sm">
                <label className="text-[#4a3826] font-medium">
                  {isKo ? "이메일" : "Email"}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="rounded-xl border border-[#e5d2c0] bg-white px-3 py-2 text-sm text-[#2b2118] outline-none focus:border-salt-secondary focus:ring-2 focus:ring-salt-secondary/30 transition"
                  placeholder={
                    isKo ? "답변을 받을 메일 주소" : "Email for our reply"
                  }
                />
              </div>

              <div className="sm:col-span-2 flex flex-col gap-1.5 text-sm">
                <label className="text-[#4a3826] font-medium">
                  {isKo ? "프로젝트 유형" : "Project type"}
                </label>
                <input
                  value={projectType}
                  onChange={(e) => setProjectType(e.target.value)}
                  className="rounded-xl border border-[#e5d2c0] bg-white px-3 py-2 text-sm text-[#2b2118] outline-none focus:border-salt-secondary focus:ring-2 focus:ring-salt-secondary/30 transition"
                  placeholder={
                    isKo
                      ? "예: 브랜드 리포트 / 조직 문화 진단 / 콘텐츠 전략 등"
                      : "e.g. brand report / culture diagnosis / content strategy"
                  }
                />
              </div>

              <div className="sm:col-span-2 flex flex-col gap-1.5 text-sm">
                <label className="text-[#4a3826] font-medium">
                  {isKo
                    ? "예상 예산 (선택 · KRW / USD)"
                    : "Estimated budget (optional · KRW / USD)"}
                </label>
                <input
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="rounded-xl border border-[#e5d2c0] bg-white px-3 py-2 text-sm text-[#2b2118] outline-none focus:border-salt-secondary focus:ring-2 focus:ring-salt-secondary/30 transition"
                  placeholder={
                    isKo
                      ? "예: 500만–1,000만 원 또는 $5K–$10K 등 편하게 범위를 적어 주세요"
                      : "e.g. 5,000,000–10,000,000 KRW or $5K–$10K"
                  }
                />
              </div>

              <div className="sm:col-span-2 flex flex-col gap-1.5 text-sm">
                <label className="text-[#4a3826] font-medium">
                  {isKo ? "현재 상황과 원하는 변화" : "Current situation & goal"}
                </label>
                <textarea
                  rows={6}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="rounded-xl border border-[#e5d2c0] bg-white px-3 py-2 text-sm text-[#2b2118] outline-none focus:border-salt-secondary focus:ring-2 focus:ring-salt-secondary/30 transition resize-none"
                  placeholder={
                    isKo
                      ? "지금 어떤 상황인지, Salt H와 함께 어떤 변화를 만들고 싶은지 자유롭게 적어 주세요."
                      : "Share where you are right now and what kind of change you’d like to make with Salt H."
                  }
                />
              </div>

              <div className="sm:col-span-2 flex justify-between items-center gap-4 text-[11px] text-[#8a745e]">
                <p>
                  {isKo
                    ? "예산이 아직 정확하지 않아도 괜찮습니다. 대략적인 범위를 알려주시면 함께 현실적인 스코프를 제안해 드립니다."
                    : "Your budget doesn’t have to be exact. A rough range helps us suggest a realistic scope together."}
                </p>
                <button
                  type="submit"
                  className="rounded-full bg-salt-secondary px-5 py-2 text-xs font-semibold text-[#3b2714] shadow-md shadow-salt-secondary/40 hover:shadow-lg hover:-translate-y-0.5 transition whitespace-nowrap"
                >
                  {isKo ? "문의 보내기" : "Send inquiry"}
                </button>
              </div>
            </form>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

