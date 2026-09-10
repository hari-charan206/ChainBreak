import { motion } from "framer-motion";
import { TrendingDown, Unplug, Waves } from "lucide-react";

// Problem section (Section 3.3 item 2): short scroll-reveal on cascading
// failures being hard to see coming. Framer Motion whileInView — one-shot
// enter, no scrubbing (rule of thumb, Section 3.2).

const cards = [
  {
    icon: Waves,
    color: "#FF3B3B",
    title: "Failures travel",
    body: "A single out-of-range reading rarely stays single. It flows downstream through pumps, valves, and controllers — each hop a little later, a little worse.",
  },
  {
    icon: Unplug,
    color: "#FFB800",
    title: "Alarms come too late",
    body: "Traditional monitoring raises the alarm per-sensor, per-threshold. By the time the third system is complaining, the chain has already formed.",
  },
  {
    icon: TrendingDown,
    color: "#00E5FF",
    title: "Nobody sees the graph",
    body: "The dependency map lives in operators' heads and stale diagrams. Under pressure, the question isn't what's broken — it's where to act first.",
  },
];

export function ProblemSection() {
  return (
    <section className="relative px-6 py-28">
      <div className="mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.6 }}
        >
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#00E5FF]">
            The problem
          </div>
          <h2 className="mt-3 text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">
            Cascading failures are invisible until they've already won
          </h2>
        </motion.div>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {cards.map((c, i) => (
            <motion.div
              key={c.title}
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.55, delay: i * 0.12 }}
              className="rounded-xl border border-[#232B3D] bg-[#11151F] p-5"
            >
              <c.icon size={20} style={{ color: c.color }} />
              <div className="mt-3 text-sm font-bold text-[#E8ECF4]">{c.title}</div>
              <p className="mt-2 text-[12px] leading-relaxed text-[#8A94A8]">{c.body}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
