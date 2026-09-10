import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

// Hero (Section 3.3 item 1): core promise headline, Framer Motion fade-up
// on PAGE LOAD (not scroll-triggered), per spec.

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 26 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const } },
};

export function Hero() {
  return (
    <header className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center">
      {/* expressive marketing background — same base palette, more drama */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(60% 45% at 50% 30%, rgba(0,229,255,0.10) 0%, rgba(0,229,255,0.0) 60%), radial-gradient(40% 35% at 75% 70%, rgba(255,59,59,0.07) 0%, rgba(255,59,59,0.0) 70%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.14]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,229,255,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.35) 1px, transparent 1px)",
          backgroundSize: "56px 56px",
          maskImage: "radial-gradient(70% 55% at 50% 40%, black 0%, transparent 75%)",
          WebkitMaskImage: "radial-gradient(70% 55% at 50% 40%, black 0%, transparent 75%)",
        }}
      />

      <motion.div variants={container} initial="hidden" animate="show" className="relative z-10 max-w-3xl">
        <motion.div
          variants={item}
          className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#00E5FF]/30 bg-[#00E5FF]/5 px-3.5 py-1.5 text-[11px] font-semibold text-[#00E5FF]"
        >
          live industrial telemetry · AI failure-chain analysis
        </motion.div>

        <motion.h1
          variants={item}
          className="text-balance text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl"
        >
          We tell you{" "}
          <span className="bg-gradient-to-r from-[#00E5FF] to-[#7FE9FF] bg-clip-text text-transparent">
            where to act first
          </span>{" "}
          to stop the chain
        </motion.h1>

        <motion.p variants={item} className="mx-auto mt-6 max-w-xl text-pretty text-sm leading-relaxed text-[#8A94A8] sm:text-base">
          One drifting sensor becomes a failed pump, a dead line, a halted
          process. ChainBreak watches your live dependency graph, predicts how
          a failure will spread, and ranks the single best place to intervene —
          before the cascade runs.
        </motion.p>

        <motion.div variants={item} className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/login"
            className="group flex items-center gap-2 rounded-lg border border-[#00E5FF]/60 bg-[#00E5FF]/15 px-6 py-3 text-sm font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25"
          >
            Launch ChainBreak
            <ArrowRight size={15} className="transition group-hover:translate-x-0.5" />
          </Link>
          <a
            href="#how"
            className="rounded-lg border border-[#232B3D] bg-[#161B27]/80 px-6 py-3 text-sm font-semibold text-[#8A94A8] transition hover:text-[#E8ECF4]"
          >
            See how it works
          </a>
        </motion.div>
      </motion.div>
    </header>
  );
}
