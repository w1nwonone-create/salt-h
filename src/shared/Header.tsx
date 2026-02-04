import type { Language } from "../App";

type HeaderProps = {
  lang: Language;
  onToggleLang: () => void;
  onLogoClick?: () => void;
  showContactButton?: boolean;
  onContactClick?: () => void;
};

export const Header = ({
  lang,
  onToggleLang,
  onLogoClick,
  showContactButton = true,
  onContactClick
}: HeaderProps) => {
  return (
    <header className="sticky top-0 z-20 border-b border-[#f1dec8] bg-[#fff7edcc] backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <button
          type="button"
          onClick={onLogoClick}
          className="flex items-center gap-2 group"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-gradient-to-br from-salt-primary to-salt-secondary text-[13px] font-semibold text-[#3b2714] shadow-md shadow-salt-primary/40 group-hover:shadow-lg transition">
            H
          </div>
          <div className="leading-tight text-left">
            <p className="text-sm font-semibold text-[#2b2118]">Salt H</p>
            <p className="text-[10px] text-[#7b6550]">
              {lang === "ko"
                ? "공감 기반 인사이트 스튜디오"
                : "Empathy-driven insight studio"}
            </p>
          </div>
        </button>
        <div className="flex items-center gap-3">
          <div className="flex items-center rounded-full border border-[#e5d2c0] bg-white/70 px-1.5 py-0.5 text-[10px] text-[#7b6550] shadow-sm">
            <button
              type="button"
              onClick={lang === "ko" ? undefined : onToggleLang}
              aria-label="Switch to Korean"
              className={`px-1.5 py-0.5 rounded-full transition ${
                lang === "ko"
                  ? "bg-[#3b2714] text-[#fff7ed]"
                  : "hover:text-[#3b2714]"
              }`}
            >
              <span className="text-base leading-none">🇰🇷</span>
            </button>
            <span className="px-1 text-[#c4ac93]">/</span>
            <button
              type="button"
              onClick={lang === "en" ? undefined : onToggleLang}
              aria-label="Switch to English"
              className={`px-1.5 py-0.5 rounded-full transition ${
                lang === "en"
                  ? "bg-[#3b2714] text-[#fff7ed]"
                  : "hover:text-[#3b2714]"
              }`}
            >
              <span className="text-base leading-none">🇺🇸</span>
            </button>
          </div>
          {showContactButton && (
            <button
              type="button"
              onClick={onContactClick}
              className="rounded-full border border-salt-secondary/60 bg-salt-secondary/10 px-3 py-1.5 text-[11px] font-medium text-salt-secondary hover:bg-salt-secondary/20 transition"
            >
              {lang === "ko" ? "프로젝트 문의" : "Contact"}
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

