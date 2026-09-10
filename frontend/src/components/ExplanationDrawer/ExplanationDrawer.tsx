import { X } from "lucide-react";
import type { ExplanationPayload, RankedIntervention } from "../../lib/api";

// Renders the backend explanation verbatim — no client-side math
// (CONTRACT.md Section 13).

interface Props {
  open: boolean;
  explanation: ExplanationPayload | null;
  ranking: RankedIntervention[];
  onApply: (nodeId: string) => void;
  onClose: () => void;
  busy: boolean;
}

export function ExplanationDrawer({ open, explanation, ranking, onApply,
                                    onClose, busy }: Props) {
  if (!open) return null;

  const maxContribution = explanation
    ? Math.max(...explanation.factors.map((f) => f.contribution), 0.01)
    : 1;

  return (
    <div
      className="absolute inset-y-0 right-0 z-30 w-[380px] overflow-y-auto border-l border-[#232B3D] bg-[#11151F] p-5 shadow-2xl"
      style={{ transition: "transform 300ms ease" }}
    >
      <div className="mb-3 flex items-start justify-between">
        <div>
          <div className="text-sm font-bold text-[#E8ECF4]">
            {explanation?.display_name ?? "Node"}
          </div>
          <div className="text-[11px] text-[#8A94A8]">{explanation?.role}</div>
        </div>
        <button onClick={onClose} className="text-[#8A94A8] hover:text-[#E8ECF4]">
          <X size={16} />
        </button>
      </div>

      {explanation?.label && (
        <div className="mb-3 rounded-md border border-[#FFD700]/50 bg-[#FFD700]/10 px-3 py-2 text-xs font-bold text-[#FFD700]">
          ★ {explanation.label}
        </div>
      )}

      <div className="mb-4 rounded-md border border-[#232B3D] bg-[#161B27] p-3">
        <div className="mb-2 text-[11px] font-semibold text-[#8A94A8]">
          Heuristic score breakdown (locked v1 weights)
        </div>
        {explanation?.factors.map((f) => (
          <div key={f.factor} className="mb-2">
            <div className="flex justify-between text-[11px]">
              <span className="text-[#E8ECF4]">{f.label}</span>
              <span className="text-[#8A94A8]">
                {f.value.toFixed(2)} × {f.weight.toFixed(2)} = {f.contribution.toFixed(3)}
              </span>
            </div>
            <div className="mt-1 h-1.5 w-full rounded bg-[#232B3D]">
              <div
                className="h-1.5 rounded bg-[#00E5FF]"
                style={{ width: `${(f.contribution / maxContribution) * 100}%` }}
              />
            </div>
          </div>
        ))}
        <div className="mt-2 border-t border-[#232B3D] pt-2 text-xs font-bold text-[#00E5FF]">
          Total score: {explanation?.score.toFixed(3) ?? "--"}
        </div>
      </div>

      <div className="mb-4 rounded-md border border-[#232B3D] bg-[#161B27] p-3 text-[11px] leading-relaxed text-[#E8ECF4]">
        {explanation?.summary}
      </div>

      {ranking.length > 1 && (
        <div className="mb-4 rounded-md border border-[#232B3D] bg-[#161B27] p-3">
          <div className="mb-2 text-[11px] font-semibold text-[#8A94A8]">
            All ranked interventions
          </div>
          {ranking.map((r) => (
            <div key={r.node_id} className="flex justify-between py-1 text-[11px]">
              <span className="text-[#E8ECF4]">
                #{r.rank} {r.node_id} {r.label ? "★" : ""}
              </span>
              <span className="font-semibold text-[#00E5FF]">{r.score.toFixed(3)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mb-4 rounded-md border border-[#FFB800]/30 bg-[#FFB800]/5 p-3">
        <div className="mb-1 text-[10px] font-bold text-[#FFB800]">AI honesty labels</div>
        {explanation?.honesty_labels.map((l, i) => (
          <div key={i} className="text-[10px] leading-snug text-[#8A94A8]">• {l}</div>
        ))}
      </div>

      <button
        onClick={() => explanation && onApply(explanation.node_id)}
        disabled={busy}
        className="w-full rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/15 px-4 py-2.5 text-sm font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25 disabled:opacity-50"
      >
        Apply intervention here
      </button>
    </div>
  );
}
