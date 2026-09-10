import { ArrowRight, CheckCircle2 } from "lucide-react";
import type { BeforeAfterPayload } from "../../lib/api";

interface Props {
  impact: BeforeAfterPayload | null;
}

export function BeforeAfterView({ impact }: Props) {
  if (!impact || !impact.intervention_applied) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
        <CheckCircle2 size={22} className="text-[#232B3D]" />
        <div className="text-xs text-[#5A6472]">
          Apply an intervention to see the before/after impact comparison
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col justify-center gap-4 p-5">
      <div className="text-xs font-bold tracking-wider text-[#00E5FF]">
        IMPACT — BEFORE / AFTER
      </div>

      <div className="flex items-center justify-center gap-4">
        <div className="text-center">
          <div className="text-5xl font-extrabold text-[#FF3B3B]">
            {impact.before.downstream_systems_affected}
          </div>
          <div className="mt-1 text-[11px] text-[#8A94A8]">without intervention</div>
        </div>
        <ArrowRight size={26} className="text-[#8A94A8]" />
        <div className="text-center">
          <div className="text-5xl font-extrabold text-[#00E5FF]">
            {impact.after.downstream_systems_affected}
          </div>
          <div className="mt-1 text-[11px] text-[#8A94A8]">with intervention at {impact.intervention_applied}</div>
        </div>
      </div>

      <div className="rounded-md border border-[#00E5FF]/30 bg-[#00E5FF]/5 px-4 py-2.5 text-center text-sm font-bold text-[#00E5FF]">
        {impact.headline}
      </div>

      <div className="text-center text-[10px] text-[#5A6472]">{impact.method}</div>
    </div>
  );
}
