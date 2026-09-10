import { useState } from "react";
import { ExternalLink } from "lucide-react";
import type { ValidationPayload } from "../../lib/api";

interface Props {
  validation: ValidationPayload | null;
  fullMetrics: Record<string, unknown> | null;
}

export function ValidationMetrics({ validation, fullMetrics }: Props) {
  const [showFull, setShowFull] = useState(false);

  if (!validation) return null;

  return (
    <div className="rounded-lg border border-[#232B3D] bg-[#161B27] p-3.5">
      <div className="mb-2.5 text-[11px] font-bold tracking-wider text-[#8A94A8]">
        MODEL VALIDATION
      </div>

      {/* scope label MUST be shown with the number (CONTRACT.md Section 12) */}
      <div className="mb-3 rounded-md border border-[#FFB800]/30 bg-[#FFB800]/5 px-3 py-2 text-[10px] leading-snug text-[#FFB800]">
        {validation.scope}
      </div>

      <div className="mb-3 grid grid-cols-2 gap-3">
        <div>
          <div className="text-2xl font-extrabold text-[#00E5FF]">
            {(validation.precision * 100).toFixed(1)}%
          </div>
          <div className="text-[10px] text-[#8A94A8]">precision</div>
        </div>
        <div>
          <div className="text-2xl font-extrabold text-[#00E5FF]">
            {(validation.recall * 100).toFixed(1)}%
          </div>
          <div className="text-[10px] text-[#8A94A8]">recall</div>
        </div>
      </div>

      <div className="space-y-1 text-[10px] leading-snug text-[#5A6472]">
        <div>Detector: {validation.method}</div>
        {validation.truth_basis && <div>Ground truth: {validation.truth_basis}</div>}
      </div>

      {validation.full_dataset_available && (
        <button
          onClick={() => setShowFull(!showFull)}
          className="mt-2.5 flex items-center gap-1 text-[10px] text-[#00E5FF]/70 hover:text-[#00E5FF]"
        >
          <ExternalLink size={10} />
          {showFull ? "Hide" : "Show"} full-dataset fact (on judge request)
        </button>
      )}
      {showFull && fullMetrics && (
        <div className="mt-2 space-y-1 rounded-md border border-[#232B3D] bg-[#11151F] p-2.5 text-[10px] leading-snug text-[#8A94A8]">
          {Object.entries(fullMetrics).map(([k, v]) => (
            <div key={k}>
              <span className="text-[#5A6472]">{k}: </span>
              {typeof v === "object" ? JSON.stringify(v) : String(v)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
