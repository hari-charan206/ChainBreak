import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

// Lenis + ScrollTrigger integration (build prompt Section 3.2).
// Lenis must be initialized once at the Briefing page root and wired to
// GSAP's ticker so smooth scroll and ScrollTrigger's position tracking
// stay in sync — the most common integration bug, called out explicitly
// in the spec. Used ONLY on the Briefing route; the dashboard scrolls
// natively (Section 3.4).

gsap.registerPlugin(ScrollTrigger);

export { gsap, ScrollTrigger };

export function createLenis(): Lenis {
  return new Lenis({
    lerp: 0.09,          // buttery inertia feel
    smoothWheel: true,
  });
}

/**
 * Wire a Lenis instance into GSAP's ticker + ScrollTrigger.
 * Returns a cleanup that removes the ticker callback.
 */
export function syncLenisWithGsap(lenis: Lenis): () => void {
  const update = (time: number) => {
    lenis.raf(time * 1000);
  };
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add(update);
  gsap.ticker.lagSmoothing(0);
  return () => {
    gsap.ticker.remove(update);
    lenis.off?.("scroll", ScrollTrigger.update);
  };
}
