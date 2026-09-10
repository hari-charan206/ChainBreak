import { AlertTriangle } from "lucide-react";
import type { ValidationMetrics as ValidationPayload } from "../../lib/api";

interface Props {
  validation: ValidationPayload | null;
}

// Scope label MUST be shown with the number (v3 Section 12 standard carried
// to v4). During model warm-up the backend sends no numbers at all — the
// disclosure renders instead of a fake metric.
export function ValidationMetrics({ validation }: Props) {
  if (!validation) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
        <AlertTriangle size={20} className="text-[#232B3D]" />
        <div className="text-xs text-[#5A6472]">
          Bind a sensor and let live data arrive — validation appears once
          readings exist
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[#232B3D] bg-[#161B27] p-3.5">
      <div className="mb-2.5 text-[11px] font-bold tracking-wider text-[#8A94A8]">
        MODEL VALIDATION
      </div>

      {/* scope label always travels with the number */}
      <div className="mb-3 rounded-md border border-[#FFB800]/30 bg-[#FFB800]/5 px-3 py-2 text-[10px] leading-snug text-[#FFB800]">
        {validation.scope_label}
      </div>

      {validation.warm_up || validation.precision === null ? (
        <div className="text-[10px] leading-snug text-[#5A6472]">
          {validation.bindings_tracked} sensor binding
          {validation.bindings_tracked === 1 ? "" : "s"} tracked · no metrics
          shown during warm-up — numbers appear only after the Isolation
          Forest calibrates on live data.
        </div>
      ) : (
        <>
          <div className="mb-3 grid grid-cols-2 gap-3">
            <div>
              <div className="text-2xl font-extrabold text-[#00E5FF]">
                {(validation.precision * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-[#8A94A8]">precision</div>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-[#00E5FF]">
                {validation.recall === null ? "--" : `${(validation.recall * 100).toFixed(1)}%`}
              </div>
              <div className="text-[10px] text-[#8A94A8]">recall</div>
            </div>
          </div>
          {validation.method && (
            <div className="text-[10px] leading-snug text-[#5A6472]">
              Method: {validation.method}
            </div>
          )}
        </>
      )}
    </div>
  );
}
