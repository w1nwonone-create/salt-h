export const Footer = () => {
  return (
    <footer className="border-t border-[#f1dec8] bg-[#f5e4d3]">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-6 text-[11px] text-[#7b6550] sm:flex-row sm:items-center sm:justify-between">
        <p>
          © 2025–{new Date().getFullYear()} Salt H. All rights reserved. Founded
          in 2025.
        </p>
        <div className="flex flex-wrap gap-3">
          <span>winthefirst@salt-h.com</span>
          <span className="text-[#b0967d]">|</span>
          <span>서울, Remote-friendly</span>
        </div>
      </div>
    </footer>
  );
};

