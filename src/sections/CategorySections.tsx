import type { Language } from "../App";

type Category = {
  id: string;
  label: {
    ko: string;
    en: string;
  };
  title: {
    ko: string;
    en: string;
  };
  description: {
    ko: string;
    en: string;
  };
  tags: string[];
};

const CATEGORIES: Category[] = [
  {
    id: "brand",
    label: {
      ko: "브랜드 인사이트",
      en: "Brand Insight"
    },
    title: {
      ko: "브랜드가 스스로를 이해하도록",
      en: "Helping brands understand themselves"
    },
    description: {
      ko: "브랜드의 말과 행동이 한 방향을 바라보도록 맥락을 정리합니다.",
      en: "We align what your brand says and does into one clear narrative."
    },
    tags: ["#BrandStory", "#Voice&Tone", "#Identity"]
  },
  {
    id: "org",
    label: {
      ko: "조직 인사이트",
      en: "Organization Insight"
    },
    title: {
      ko: "사람들이 일하는 방식을 비춥니다",
      en: "Illuminating how people really work together"
    },
    description: {
      ko: "인터뷰와 설문을 통해 조직 안에서 오가는 진짜 이야기를 기록합니다.",
      en: "We listen to everyday stories inside the company through interviews and surveys."
    },
    tags: ["#Culture", "#Onboarding", "#Collaboration"]
  },
  {
    id: "product",
    label: {
      ko: "제품 인사이트",
      en: "Product Insight"
    },
    title: {
      ko: "데이터 뒤에 숨은 맥락까지",
      en: "Reading the context behind product data"
    },
    description: {
      ko: "숫자와 사용자의 하루를 함께 바라보며 제품의 다음 한 걸음을 제안합니다.",
      en: "We look at numbers and the user's day together to suggest your product's next step."
    },
    tags: ["#UXResearch", "#Journey", "#NextFeature"]
  }
];

type CategorySectionsProps = {
  lang: Language;
};

export const CategorySections = ({ lang }: CategorySectionsProps) => {
  return (
    <section className="border-b border-[#f1dec8] bg-gradient-to-b from-[#fff7ed] via-[#fff7ed] to-[#fef3e7]">
      <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-salt-secondary">
              {lang === "ko" ? "WHAT WE DO" : "WHAT WE DO"}
            </p>
            <h2 className="mt-2 text-2xl lg:text-3xl font-semibold text-[#2b2118]">
              {lang === "ko" ? (
                <>
                  Salt H가 함께하는
                  <span className="block text-salt-secondary">
                    세 가지 인사이트 영역
                  </span>
                </>
              ) : (
                <>
                  Three lenses of insight
                  <span className="block text-salt-secondary">
                    we bring to every project
                  </span>
                </>
              )}
            </h2>
          </div>
          <p className="max-w-md text-xs sm:text-sm text-[#6b5740]">
            {lang === "ko" ? (
              <>
                하나의 프로젝트 안에서도 우리는{" "}
                <span className="font-semibold text-[#3b2714]">
                  브랜드・조직・제품
                </span>
                을 유기적으로 바라봅니다. 각 카테고리는 독립적인 동시에 서로를
                보완하는 렌즈입니다.
              </>
            ) : (
              <>
                Even in a single project, we look at{" "}
                <span className="font-semibold text-[#3b2714]">
                  brand, organization, and product
                </span>{" "}
                together. Each lens stands alone, yet completes the others.
              </>
            )}
          </p>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {CATEGORIES.map((category) => (
            <article
              key={category.id}
              className="group flex flex-col rounded-2xl border border-[#f1dec8] bg-white p-5 shadow-sm shadow-[#f1dec8]/70 ring-1 ring-transparent transition hover:-translate-y-1 hover:border-salt-secondary/70 hover:ring-salt-secondary/40"
            >
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-[11px] font-medium text-salt-secondary">
                  {category.label[lang]}
                </p>
              </div>
              <h3 className="mt-2 text-base font-semibold text-[#2b2118]">
                {category.title[lang]}
              </h3>
              <p className="mt-2 text-xs text-[#6b5740]">
                {category.description[lang]}
              </p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {category.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-[#fff7ed] px-2 py-1 text-[11px] text-[#6b5740] border border-[#f1dec8]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

