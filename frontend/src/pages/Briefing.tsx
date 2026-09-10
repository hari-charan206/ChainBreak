import { Link } from "react-router-dom";
import { Activity } from "lucide-react";
import "lenis/dist/lenis.css";
import { useLenisScroll } from "../hooks/useLenisScroll";
import { Hero } from "../components/Briefing/Hero";
import { ProblemSection } from "../components/Briefing/ProblemSection";
import { HowItWorksScrollLinked } from "../components/Briefing/HowItWorksScrollLinked";
import { AILayerCards } from "../components/Briefing/AILayerCards";
import { CTASection } from "../components/Briefing/CTASection";

// Briefing / landing page (build prompt Section 3) — public, scroll-driven,
// visually separate from the operational dashboard. Lenis is initialized
// here at the page root ONLY (Section 3.4): no other route uses smooth
// scroll, and the dashboard scrolls natively.
export default function Briefing() {
  useLenisScroll();

  return (
    <div className="min-h-screen bg-[#0B0E14] text-[#E8ECF4]">
      <nav className="fixed inset-x-0 top-0 z-40 flex items-center justify-between px-6 py-4 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-[#00E5FF]" />
          <span className="text-sm font-bold tracking-wide">ChainBreak</span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <a href="#how" className="text-[#8A94A8] transition hover:text-[#E8ECF4]">
            How it works
          </a>
          <Link
            to="/login"
            className="rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/10 px-3.5 py-1.5 font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/20"
          >
            Sign in
          </Link>
        </div>
      </nav>

      <Hero />
      <ProblemSection />
      <HowItWorksScrollLinked />
      <AILayerCards />
      <CTASection />

      <footer className="border-t border-[#232B3D] px-6 py-8 text-center text-[10px] leading-relaxed text-[#5A6472]">
        ChainBreak v4 · local-only demo build · anomaly detection is a trained
        Isolation Forest with a disclosed live warm-up; propagation is a
        probabilistic model (not trained); intervention ranking is a heuristic
        with locked weights — never presented as "learned".
      </footer>
    </div>
  );
}
