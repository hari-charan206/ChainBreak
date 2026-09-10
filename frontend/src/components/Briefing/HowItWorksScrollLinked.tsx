import { useLayoutEffect, useRef } from "react";
import { gsap, ScrollTrigger } from "../../lib/gsapScrollTrigger";

// How-it-works centerpiece (Section 3.3 item 3): a failure propagating
// node->node, DRAWN BY SCROLL POSITION — GSAP ScrollTrigger with scrub:true
// so progress tracks scroll offset directly (forward AND backward). Per the
// spec's rule of thumb this is the one section using GSAP; the reveal
// sections use Framer Motion, never both on the same element (Section 3.2).
// A container-pinned timeline works with Lenis without scrollerProxy since
// Lenis drives native scroll here.

const NODES = [
  { label: "Sensor drift", sub: "value leaves its band", color: "#FFB800" },
  { label: "Pump strains", sub: "downstream demand rises", color: "#FFB800" },
  { label: "Valve sticks", sub: "flow destabilizes", color: "#FF3B3B" },
  { label: "Line stops", sub: "cascade complete", color: "#FF3B3B" },
];

export function HowItWorksScrollLinked() {
  const sectionRef = useRef<HTMLElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const section = sectionRef.current;
    const track = trackRef.current;
    if (!section || !track) return;      const ctx = gsap.context(() => {
      const cards = gsap.utils.toArray<HTMLElement>(".hiw-node");
      const wires = gsap.utils.toArray<SVGPathElement>(".hiw-wire");
      // dot travels node centers: 4 cards -> 4 x-positions on the viewBox
      const xs = [100, 366, 633, 900];

      // one scrubbed timeline: play head == scroll position
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: section,
          start: "top top",
          end: "+=1800", // ~3 viewport heights of scroll distance
          scrub: true,
          pin: true,
          anticipatePin: 1,
          invalidateOnRefresh: true,
        },
      });

      // hide everything until its moment in the scroll
      gsap.set(cards, { opacity: 0.16, y: 14, scale: 0.96 });
      gsap.set(wires, { strokeDasharray: 240, strokeDashoffset: 240 });
      gsap.set(".hiw-dot", { scale: 0, opacity: 0 });
      gsap.set(".hiw-headline", { opacity: 0, y: 18 });

      // stage 0: headline
      tl.to(".hiw-headline", { opacity: 1, y: 0, duration: 0.4 });

      // each stage: light the node, draw its outgoing wire, move the dot
      cards.forEach((card, i) => {
        const label = `stage${i}`;
        tl.to(card, { opacity: 1, y: 0, scale: 1, duration: 0.45 }, label);
        if (i < wires.length) {
          tl.to(wires[i], { strokeDashoffset: 0, duration: 0.5 }, `${label}+=0.15`);
          tl.to(".hiw-dot", {
            attr: { cx: xs[i + 1], cy: 60 },
            scale: 1, opacity: 1,
            duration: 0.5,
          }, `${label}+=0.15`);
        }
      });

      // closing note
      tl.fromTo(
        ".hiw-note",
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.5 },
        ">0.2",
      );
    }, section);

    ScrollTrigger.refresh();
    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} id="how" className="relative overflow-hidden px-6">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center py-20">
        <h2 className="hiw-headline mx-auto max-w-2xl text-balance text-center text-3xl font-extrabold tracking-tight sm:text-4xl">
          Watch a failure travel — and know where to cut it
        </h2>

        <div ref={trackRef} className="relative mt-14">
          {/* wiring diagram */}
          <svg
            className="pointer-events-none absolute inset-x-0 top-[54px] mx-auto hidden h-[120px] w-full max-w-4xl md:block"
            viewBox="0 0 1000 120"
            fill="none"
            preserveAspectRatio="none"
          >
            {[100, 366, 633].map((x, i) => (
              <path
                key={x}
                className="hiw-wire"
                d={`M ${x} 60 C ${x + 60} 20, ${x + 155} 20, ${x + 220} 60`}
                stroke={i < 2 ? "#FFB800" : "#FF3B3B"}
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            ))}
            <circle className="hiw-dot" r="7" fill="#FF3B3B" cx="100" cy="60" />
          </svg>

          <div className="grid grid-cols-2 gap-6 md:grid-cols-4 md:gap-8">
            {NODES.map((n, i) => (
              <div key={n.label} className="hiw-node rounded-xl border border-[#232B3D] bg-[#11151F] p-4 text-center">
                <div
                  className="mx-auto flex h-11 w-11 items-center justify-center rounded-full border-2"
                  style={{ borderColor: n.color, color: n.color }}
                >
                  {i + 1}
                </div>
                <div className="mt-3 text-[12.5px] font-bold text-[#E8ECF4]">{n.label}</div>
                <div className="mt-1 text-[10.5px] text-[#8A94A8]">{n.sub}</div>
              </div>
            ))}
          </div>

          <p className="hiw-note mx-auto mt-10 max-w-lg text-center text-[11.5px] leading-relaxed text-[#5A6472]">
            ChainBreak watches every node's live values, models how the failure
            will spread across <em>your</em> dependency graph, and ranks the
            intervention point that stops it soonest.
          </p>
        </div>
      </div>
    </section>
  );
}
