import { useEffect, type RefObject } from "react";
import { createLenis, syncLenisWithGsap } from "../lib/gsapScrollTrigger";
import type Lenis from "lenis";

// Briefing-page-only smooth scroll (Section 3.2/3.4). Mounts Lenis once at
// the page root, wires it into GSAP's ticker, and fully tears down on
// unmount so no other route ever inherits smooth-scroll behavior.

export function useLenisScroll(_container?: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const lenis = createLenis();
    const cleanup = syncLenisWithGsap(lenis);
    return () => {
      cleanup();
      lenis.destroy();
    };
  }, []);
}
