import { motion } from "framer-motion";
import { BrainCircuit, GitFork, ListOrdered } from "lucide-react";

// AI layer explainer (Section 3.3 item 4): three cards, Framer Motion
// whileInView, staggered. Honesty labels mirror the dashboard's (the same
// standard: state plainly what's trained vs. heuristic).

const CARDS = [
  {
    icon: BrainCircuit,
    color: "#00E5FF",
    badge: "trained · live warm-up",
    title: "Anomaly detection",
    body: "An Isolation Forest trains on each sensor's live values after a short, disclosed warm-up. Your own warning/failure thresholds guard the node from the very first reading.",
  },
  {
    icon: GitFork,
    color: "#FFB800",
    badge: "probabilistic · not trained",
    title: "Propagation prediction",
    body: "When a node degrades, the model multiplies anomaly strength by each edge's criticality to forecast which systems are next — and how soon.",
  },
  {
    icon: ListOrdered,
    color: "#FFD700",
    badge: "heuristic · locked weights",
    title: "Intervention ranking",
    body: "Four locked factors — downstream reach, propagation probability, time-to-impact, criticality — score every candidate and crown the FOCUS HERE FIRST node.",
  },
];

export function AILayerCards() {
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
            The AI layer
          </div>
          <h2 className="mt-3 text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">
            Three models, one answer: act here first
          </h2>
          <p className="mt-3 max-w-xl text-xs leading-relaxed text-[#5A6472]">
            Each component is labeled exactly as it is — trained, probabilistic,
            or heuristic. No pretending.
          </p>
        </motion.div>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {CARDS.map((c, i) => (
            <motion.div
              key={c.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.55, delay: i * 0.14 }}
              className="rounded-xl border border-[#232B3D] bg-[#11151F] p-5"
            >
              <div className="flex items-start justify-between">
                <c.icon size={20} style={{ color: c.color }} />
                <span
                  className="rounded-full border px-2 py-0.5 text-[9px] font-bold tracking-wide"
                  style={{ borderColor: `${c.color}55`, color: c.color }}
                >
                  {c.badge}
                </span>
              </div>
              <div className="mt-3 text-sm font-bold text-[#E8ECF4]">{c.title}</div>
              <p className="mt-2 text-[12px] leading-relaxed text-[#8A94A8]">{c.body}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
