import type { Language } from "../App";

const PILL_CLASS =
  "inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-medium";

type ThreeHInfographicProps = {
  lang: Language;
};

export const ThreeHInfographic = ({ lang }: ThreeHInfographicProps) => {
  return (
    <section className="border-b border-[#f1dec8] bg-[#fff7ed]">
      <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-md">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-salt-secondary">
              {lang === "ko" ? "OUR 3H FRAME" : "OUR 3H FRAME"}
            </p>
            <h2 className="mt-2 text-2xl lg:text-3xl font-semibold text-[#2b2118]">
              {lang === "ko" ? (
                <>
                  Salt H의
                  <span className="block text-salt-secondary">
                    3H 콘텐츠 철학
                  </span>
                </>
              ) : (
                <>
                  Salt H&apos;s
                  <span className="block text-salt-secondary">
                    3H content philosophy
                  </span>
                </>
              )}
            </h2>
            <p className="mt-3 text-xs sm:text-sm text-[#6b5740]">
              {lang === "ko"
                ? "Heritage, Habitat, Heal. 세 가지 H는 Salt-H가 콘텐츠를 만들 때 끝까지 놓지 않는 기준입니다. 사용자의 일상과 비즈니스가 조금 더 따뜻해지도록 삶의 본질을 천천히 비춰 봅니다."
                : "Heritage, Habitat, Heal. These three Hs are the questions we keep asking as we create content, so everyday life and business can feel a little warmer and more grounded."}
            </p>
          </div>

          {/* Infographic 카드 */}
          <div className="grid w-full max-w-xl gap-3 text-xs text-[#6b5740]">
            {/* Heritage */}
            <div className="relative overflow-hidden rounded-2xl border border-[#e4d0ff] bg-gradient-to-br from-[#f4ebff] via-white to-[#fff7ed] p-4 shadow-md shadow-[#e4d0ff]/60">
              <div className="absolute -right-10 -top-10 h-24 w-24 rounded-full bg-salt-primary/20 blur-3xl" />
              <div className="relative flex items-start justify-between gap-4">
                <div>
                  <span className={PILL_CLASS}>
                    <span className="h-1.5 w-1.5 rounded-full bg-salt-primary" />
                    Heritage
                  </span>
                  <h3 className="mt-2 text-sm font-semibold text-[#2b2118]">
                    {lang === "ko"
                      ? "변치 않는 깊이를 가진 이야기"
                      : "Stories with depth that stay"}
                  </h3>
                  <p className="mt-1 text-[11px] text-[#6b5740]">
                    {lang === "ko"
                      ? "금방 잊히는 정보보다 오래 남는 서사를 중요하게 생각합니다. 인문적 가치와 철학을 담아, 시간이 지나도 다시 펼쳐볼 수 있는 콘텐츠 자산을 쌓습니다."
                      : "We value narratives that outlast trends. By grounding content in humanistic values and clear philosophy, it becomes an asset you can return to over time."}
                  </p>
                </div>
                <p className="text-[24px] font-semibold text-[#b8a4ff]">H</p>
              </div>
            </div>

            {/* Habitat */}
            <div className="relative overflow-hidden rounded-2xl border border-[#fbd4a4] bg-gradient-to-br from-[#fff4e0] via-white to-[#fff7ed] p-4 shadow-md shadow-[#f6ad55]/40">
              <div className="absolute -left-6 -bottom-10 h-24 w-24 rounded-full bg-salt-secondary/25 blur-3xl" />
              <div className="relative flex items-start justify-between gap-4">
                <div>
                  <span className={PILL_CLASS}>
                    <span className="h-1.5 w-1.5 rounded-full bg-salt-secondary" />
                    Habitat
                  </span>
                  <h3 className="mt-2 text-sm font-semibold text-[#2b2118]">
                    {lang === "ko"
                      ? "사용자의 하루 속으로 스며드는 솔루션"
                      : "Solutions that live in the user’s everyday habitat"}
                  </h3>
                  <p className="mt-1 text-[11px] text-[#6b5740]">
                    {lang === "ko"
                      ? "Tech, F&B, 일과 삶이 만나 있는 공간까지, 사용자가 실제로 머무는 '서식지'에 닿는 콘텐츠를 만듭니다. 읽고 끝나는 것이 아니라, 생활 속에서 자연스럽게 쓰이도록 설계합니다."
                      : "From digital tools to food and daily routines, we design content that reaches the places people actually live and work in, so it becomes something they naturally use, not just read once."}
                  </p>
                </div>
                <p className="text-[24px] font-semibold text-[#f6b772]">H</p>
              </div>
            </div>

            {/* Heal */}
            <div className="relative overflow-hidden rounded-2xl border border-[#e4cfd0] bg-gradient-to-br from-[#ffeef0] via-white to-[#fff7ed] p-4 shadow-md shadow-[#f3c4ca]/50">
              <div className="absolute right-0 top-0 h-20 w-20 bg-gradient-to-br from-[#fbd4a4] to-[#e4c7ff] opacity-70 blur-3xl" />
              <div className="relative flex items-start justify-between gap-4">
                <div>
                  <span className={PILL_CLASS}>
                    <span className="h-1.5 w-1.5 rounded-full bg-[#c37b85]" />
                    Heal
                  </span>
                  <h3 className="mt-2 text-sm font-semibold text-[#2b2118]">
                    {lang === "ko"
                      ? "막막함을 덜어내는 비즈니스적 치유"
                      : "Business healing that eases the overwhelm"}
                  </h3>
                  <p className="mt-1 text-[11px] text-[#6b5740]">
                    {lang === "ko"
                      ? "1인 창업가와 작은 팀이 겪는 정보 비대칭과 시행착오를 줄이는 것이 목표입니다. 위로만이 아닌, 바로 적용할 수 있는 가이드로 다시 시작할 수 있는 용기를 함께 건넵니다."
                      : "We aim to reduce information gaps and trial-and-error for solo founders and small teams. Beyond comfort, we provide practical guidance that makes it easier to start again."}
                  </p>
                </div>
                <p className="text-[24px] font-semibold text-[#e9a4b0]">H</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

