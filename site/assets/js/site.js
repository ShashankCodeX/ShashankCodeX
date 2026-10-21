document.documentElement.classList.add("js-ready");

const themeButton = document.querySelector("#theme-toggle");
themeButton?.addEventListener("click", () => {
  const useLight = document.documentElement.dataset.theme !== "light";
  document.documentElement.dataset.theme = useLight ? "light" : "dark";
  themeButton.setAttribute("aria-pressed", String(useLight));
  themeButton.setAttribute("aria-label", `Switch to ${useLight ? "dark" : "light"} theme`);
});

const menuButton = document.querySelector("#menu-toggle");
const siteNav = document.querySelector("#site-nav");

function closeMenu() {
  menuButton?.setAttribute("aria-expanded", "false");
  menuButton?.setAttribute("aria-label", "Open navigation");
  siteNav?.classList.remove("is-open");
}

menuButton?.addEventListener("click", () => {
  const isOpen = menuButton.getAttribute("aria-expanded") !== "true";
  menuButton.setAttribute("aria-expanded", String(isOpen));
  menuButton.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
  siteNav?.classList.toggle("is-open", isOpen);
});

siteNav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
});

const progress = document.querySelector("#reading-progress");
let progressFrame = 0;

function updateProgress() {
  if (!progress) return;
  cancelAnimationFrame(progressFrame);
  progressFrame = requestAnimationFrame(() => {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const percentage = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
    progress.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
  });
}

window.addEventListener("scroll", updateProgress, { passive: true });
window.addEventListener("resize", updateProgress);
updateProgress();

const revealItems = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries, currentObserver) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      currentObserver.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -35px 0px" });
  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

const year = document.querySelector("#current-year");
if (year) year.textContent = String(new Date().getFullYear());
