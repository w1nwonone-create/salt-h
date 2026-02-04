import { useState } from "react";
import { MainPage } from "./pages/MainPage";
import { ContactPage } from "./pages/ContactPage";

export type Language = "ko" | "en";
type Page = "home" | "contact";

function App() {
  const [language, setLanguage] = useState<Language>("ko");
  const [page, setPage] = useState<Page>("home");

  const toggleLanguage = () => {
    setLanguage((prev) => (prev === "ko" ? "en" : "ko"));
  };

  const goHome = () => setPage("home");
  const goContact = () => setPage("contact");

  if (page === "contact") {
    return (
      <ContactPage
        lang={language}
        onToggleLang={toggleLanguage}
        onGoHome={goHome}
      />
    );
  }

  return (
    <MainPage
      lang={language}
      onToggleLang={toggleLanguage}
      onGoContact={goContact}
      onLogoClick={goHome}
    />
  );
}

export default App;

