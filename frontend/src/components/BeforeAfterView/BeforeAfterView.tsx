import { ArrowRight, CheckCircle2 } from "lucide-react";
import type { BeforeAfterProjection } from "../../lib/api";

interface Props {
  projection: BeforeAfterProjection | null;
}

// Renders the backend-computed projected impact (headline number travels
// with the payload; the frontend does no math of its own, Section 13).
export function BeforeAfterView({ projection }: Props) {
  if (!projection) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
        <CheckCircle2 size={22} className="text-[#232B3D]" />
        <div className="text-xs text-[#5A6472]">
          When a cascade is live, the projected before/after impact of acting
          on the recommended node appears here
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col justify-center gap-4 p-5">
      <div className="text-xs font-bold tracking-wider text-[#00E5FF]">
        PROJECTED IMPACT — BEFORE / AFTER
      </div>

      <div className="flex items-center justify-center gap-4">
        <div className="text-center">
          <div className="text-5xl font-extrabold text-[#FF3B3B]">
            {projection.before.downstream_systems_affected}
          </div>
          <div className="mt-1 text-[11px] text-[#8A94A8]">without intervention</div>
        </div>
        <ArrowRight size={26} className="text-[#8A94A8]" />
        <div className="text-center">
          <div className="text-5xl font-extrabold text-[#00E5FF]">
            {projection.after.downstream_systems_affected}
          </div>
          <div className="mt-1 text-[11px] text-[#8A94A8]">
            acting at the recommended node
          </div>
        </div>
      </div>

      <div className="rounded-md border border-[#00E5FF]/30 bg-[#00E5FF]/5 px-4 py-2.5 text-center text-sm font-bold text-[#00E5FF]">
        {projection.headline}
      </div>

      <div className="text-center text-[10px] leading-snug text-[#5A6472]">
        {projection.method}
      </div>
    </div>
  );
}
