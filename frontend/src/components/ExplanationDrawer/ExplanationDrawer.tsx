import { X } from "lucide-react";
import type {
  Intervention,
  RankedIntervention,
  StateNode,
} from "../../lib/api";

// Renders the backend explanation verbatim — no client-side math
// (v3 Section 13 standard carried to v4). The four locked factors and
// weights must match the backend payload exactly.

const FACTOR_LABELS: Record<string, string> = {
  downstream_count_norm: "Downstream node count",
  propagation_prob: "Propagation probability",
  time_to_impact_inv_norm: "Time-to-impact (sooner scores higher)",
  criticality: "Dependency criticality",
};

interface Props {
  open: boolean;
  node: StateNode | null;
  intervention: Intervention | null;
  ranking: RankedIntervention[];
  onClose: () => void;
}

export function ExplanationDrawer({ open, node, intervention, ranking, onClose }: Props) {
  if (!open || !node) return null;

  const isFocus = intervention?.recommended_node_id === node.id;
  const entry = ranking.find((r) => r.node_id === node.id) ?? null;

  const factors = entry
    ? Object.entries(entry.breakdown).map(([factor, value]) => {
        const weight = entry.weights[
          factor === "downstream_count_norm" ? "downstream_count"
          : factor === "time_to_impact_inv_norm" ? "time_to_impact_inv"
          : factor
        ] ?? 0;
        return { factor, label: FACTOR_LABELS[factor] ?? factor, weight, value,
                 contribution: weight * value };
      })
    : [];
  const maxContribution = Math.max(...factors.map((f) => f.contribution), 0.01);

  return (
    <div
      className="absolute inset-y-0 right-0 z-30 w-[380px] overflow-y-auto border-l border-[#232B3D] bg-[#11151F] p-5 shadow-2xl"
      style={{ transition: "transform 300ms ease" }}
    >
      <div className="mb-3 flex items-start justify-between">
        <div>
          <div className="text-sm font-bold text-[#E8ECF4]">{node.display_name}</div>
          <div className="text-[11px] text-[#8A94A8]">type: {node.node_type} · id {node.id}</div>
        </div>
        <button onClick={onClose} className="text-[#8A94A8] hover:text-[#E8ECF4]">
          <X size={16} />
        </button>
      </div>

      {isFocus && (
        <div className="mb-3 rounded-md border border-[#FFD700]/50 bg-[#FFD700]/10 px-3 py-2 text-xs font-bold text-[#FFD700]">
          ★ FOCUS HERE FIRST
        </div>
      )}

      {node.status === "offline" && (
        <div className="mb-3 rounded-md border border-[#5A6472]/50 bg-[#5A6472]/10 px-3 py-2 text-[11px] text-[#8A94A8]">
          This node has no live data yet. Status turns healthy once its bound
          MQTT topic receives values.
        </div>
      )}
      {node.warm_up && node.status !== "offline" && (
        <div className="mb-3 rounded-md border border-[#FFB800]/30 bg-[#FFB800]/5 px-3 py-2 text-[10px] leading-snug text-[#FFB800]">
          Warm-up: the anomaly model needs a short period of live readings on
          this node before its flags are fully calibrated — threshold
          detection only until then (disclosed per contract).
        </div>
      )}

      {/* bound sensors + thresholds, straight from the payload */}
      {node.bindings.length > 0 && (
        <div className="mb-4 rounded-md border border-[#232B3D] bg-[#161B27] p-3">
          <div className="mb-2 text-[11px] font-semibold text-[#8A94A8]">Bound sensors</div>
          {node.bindings.map((b) => (
            <div key={b.topic} className="mb-1 text-[10px] text-[#E8ECF4]">
              <code className="text-[#00E5FF]/80">{b.topic}</code>
              {" "}· warn {b.warning_threshold ?? "--"} / fail {b.failure_threshold ?? "--"}
              {b.unit ? ` ${b.unit}` : ""}
            </div>
          ))}
        </div>
      )}

      {/* locked-weight score breakdown — verbatim from the backend */}
      {entry ? (
        <div className="mb-4 rounded-md border border-[#232B3D] bg-[#161B27] p-3">
          <div className="mb-2 text-[11px] font-semibold text-[#8A94A8]">
            Heuristic score breakdown (locked v1 weights)
          </div>
          {factors.map((f) => (
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
            Total score: {entry.score.toFixed(3)}
          </div>
        </div>
      ) : (
        <div className="mb-4 rounded-md border border-[#232B3D] bg-[#161B27] p-3 text-[11px] text-[#5A6472]">
          No active anomaly or propagation prediction for this node — it only
          appears in the ranking when it (or something upstream of it) is
          warning or failed.
        </div>
      )}

      {isFocus && intervention && (
        <div className="mb-4 rounded-md border border-[#00E5FF]/30 bg-[#00E5FF]/5 p-3 text-[11px] leading-relaxed text-[#E8ECF4]">
          {intervention.explanation}
        </div>
      )}

      {ranking.length > 1 && (
        <div className="mb-4 rounded-md border border-[#232B3D] bg-[#161B27] p-3">
          <div className="mb-2 text-[11px] font-semibold text-[#8A94A8]">
            All ranked interventions
          </div>
          {ranking.map((r) => (
            <div key={r.node_id} className="flex justify-between py-1 text-[11px]">
              <span className="text-[#E8ECF4]">
                #{r.rank} {r.node_name} {r.label ? "★" : ""}
              </span>
              <span className="font-semibold text-[#00E5FF]">{r.score.toFixed(3)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mb-4 rounded-md border border-[#FFB800]/30 bg-[#FFB800]/5 p-3">
        <div className="mb-1 text-[10px] font-bold text-[#FFB800]">AI honesty labels</div>
        <div className="text-[10px] leading-snug text-[#8A94A8]">
          • Anomaly detection: trained Isolation Forest (scikit-learn), trained
          live per sensor after a disclosed warm-up; user-set thresholds until then
        </div>
        <div className="text-[10px] leading-snug text-[#8A94A8]">
          • Propagation: probabilistic model over anomaly score × edge
          criticality (not trained); assumed 300s per hop, disclosed
        </div>
        <div className="text-[10px] leading-snug text-[#8A94A8]">
          • Intervention ranking: heuristic scoring model with locked v1
          weights 0.35/0.30/0.20/0.15 (not trained/learned)
        </div>
      </div>

      {node.predicted_path && (
        <div className="rounded-md border border-[#FFB800]/30 bg-[#FFB800]/5 p-3 text-[10px] leading-snug text-[#FFB800]">
          Predicted propagation path: {node.predicted_path.join(" → ")}
          {node.eta_seconds !== null && <> · ETA ~{Math.round(node.eta_seconds / 60)}m of process time</>}
        </div>
      )}
    </div>
  );
}
