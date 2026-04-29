import { useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import { MainPage } from "./pages/MainPage";
import { ContactPage } from "./pages/ContactPage";

export type Language = "ko" | "en";

function App() {
  const [language, setLanguage] = useState<Language>("ko");
  const navigate = useNavigate();

  const toggleLanguage = () => {
    setLanguage((prev) => (prev === "ko" ? "en" : "ko"));
  };

  return (
    <Routes>
      <Route
        path="/"
        element={
          <MainPage
            lang={language}
            onToggleLang={toggleLanguage}
            onGoContact={() => navigate("/contact")}
            onLogoClick={() => navigate("/")}
          />
        }
      />
      <Route
        path="/contact"
        element={
          <ContactPage
            lang={language}
            onToggleLang={toggleLanguage}
            onGoHome={() => navigate("/")}
          />
        }
      />
    </Routes>
  );
}

export default App;

