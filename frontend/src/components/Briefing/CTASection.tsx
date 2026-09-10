import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

// CTA section (Section 3.3 item 5): "Launch ChainBreak" -> /login.

export function CTASection() {
  return (
    <section className="relative overflow-hidden px-6 py-32 text-center">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(45% 60% at 50% 50%, rgba(0,229,255,0.10) 0%, rgba(0,229,255,0.0) 65%)",
        }}
      />
      <motion.div
        initial={{ opacity: 0, y: 26 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.5 }}
        transition={{ duration: 0.65 }}
        className="relative z-10"
      >
        <h2 className="mx-auto max-w-2xl text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">
          Stop watching alarms. Start stopping chains.
        </h2>
        <p className="mx-auto mt-4 max-w-md text-sm text-[#8A94A8]">
          Build an environment, bind a sensor, and watch the AI layer respond
          to live data in under two seconds.
        </p>
        <Link
          to="/login"
          className="group mt-9 inline-flex items-center gap-2 rounded-lg border border-[#00E5FF]/60 bg-[#00E5FF]/15 px-8 py-3.5 text-sm font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25"
        >
          Launch ChainBreak
          <ArrowRight size={15} className="transition group-hover:translate-x-0.5" />
        </Link>
      </motion.div>
    </section>
  );
}
