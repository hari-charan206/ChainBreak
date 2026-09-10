import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type EnvironmentState } from "../lib/api";
import { usePolling } from "../hooks/usePolling";
import { StatusBar } from "../components/StatusBar/StatusBar";
import { DependencyGraph } from "../components/DependencyGraph/DependencyGraph";
import { SensorPanel } from "../components/SensorPanel/SensorPanel";
import { ExplanationDrawer } from "../components/ExplanationDrawer/ExplanationDrawer";
import { BeforeAfterView } from "../components/BeforeAfterView/BeforeAfterView";
import { ValidationMetrics } from "../components/ValidationMetrics/ValidationMetrics";

const POLL_MS = 2000; // contract: ~2s, no faster (Section 13)

// Dashboard (Section 5.5): existing components, now parameterized by
// :environmentId. Live values arrive only via Wokwi -> MQTT -> backend ->
// this 2s poll. There is NO simulate-failure or replay control anywhere —
// by design (Section 6.1).
export default function Dashboard() {
  const { environmentId } = useParams<{ environmentId: string }>();
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showImpact, setShowImpact] = useState(true);
  const [envName, setEnvName] = useState<string | null>(null);

  const state = usePolling<EnvironmentState | null>(
    useCallback(
      () => (environmentId ? api.state(environmentId) : Promise.resolve(null)),
      [environmentId],
    ),
    POLL_MS,
  );

  // environment name for the header (fetched once per env)
  useEffect(() => {
    setEnvName(null);
    if (!environmentId) return;
    let cancelled = false;
    api.environment(environmentId).then((d) => {
      if (!cancelled && d) setEnvName(d.name);
    });
    return () => { cancelled = true; };
  }, [environmentId]);

  // keep a sensible selection when the payload updates
  useEffect(() => {
    if (!state) return;
    if (selectedNode !== null && state.nodes.some((n) => n.id === selectedNode)) return;
    const focus = state.intervention?.recommended_node_id;
    setSelectedNode(focus ?? state.nodes[0]?.id ?? null);
  }, [state, selectedNode]);

  const selected = state?.nodes.find((n) => n.id === selectedNode) ?? null;
  const cascade = state?.active_cascade ?? null;

  // empty / error states
  if (state !== null && state.nodes.length === 0) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-[#0B0E14]">
        <div className="text-sm font-bold text-[#E8ECF4]">
          {envName ?? "This environment"} has no nodes yet
        </div>
        <div className="max-w-sm text-center text-xs text-[#5A6472]">
          Add nodes, connect them, and bind a Wokwi sensor topic in the
          Environment Builder — the dashboard comes alive once MQTT data flows.
        </div>
        <Link
          to="/environments/new"
          className="rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/15 px-4 py-2 text-xs font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25"
        >
          Open Environment Builder
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-[#0B0E14]">
      <StatusBar state={state} environmentName={envName} />

      <div className="flex min-h-0 flex-1">
        {/* left/center graph — native scroll behavior only, no Lenis here */}
        <div className="relative min-w-0 flex-1">
          <DependencyGraph
            state={state}
            focusNode={state?.intervention?.recommended_node_id ?? null}
            selectedNode={selectedNode}
            onSelectNode={(id) => {
              setSelectedNode(id);
              setDrawerOpen(true);
            }}
          />
        </div>

        {/* right panel */}
        <div className="flex w-[340px] shrink-0 flex-col gap-3 overflow-y-auto border-l border-[#232B3D] bg-[#0B0E14] p-3">
          {/* cascade warning banner */}
          {cascade && cascade.affected_nodes.length > 0 && (
            <div className="rounded-md border border-[#FF3B3B]/50 bg-[#FF3B3B]/10 px-3 py-2 text-[11px] font-semibold text-[#FF3B3B]">
              ⚠ Cascade predicted from {cascade.origin_node_name}:{" "}
              {cascade.affected_node_names.join(" → ")}
            </div>
          )}

          {/* disclosure note (Section 13: never swallow honesty fields) */}
          {cascade && (
            <div className="rounded-md border border-[#FFB800]/40 bg-[#FFB800]/5 px-3 py-2 text-[10px] leading-snug text-[#FFB800]">
              Disclosure: {cascade.method}. Propagation beyond the detected
              node is the model's prediction, not observed data.
            </div>
          )}

          {/* live-data hint when nothing is flowing yet */}
          {state && state.nodes.every((n) => n.status === "offline") && (
            <div className="rounded-md border border-[#00E5FF]/30 bg-[#00E5FF]/5 px-3 py-2 text-[11px] text-[#8A94A8]">
              Waiting for live MQTT data on the bound topics. Publish from your
              Wokwi sketch (or the operator fallback script) and nodes will
              come online within ~2s.
            </div>
          )}

          {/* sensor trends for selected node */}
          <div className="min-h-[220px] rounded-lg border border-[#232B3D] bg-[#11151F]">
            <SensorPanel node={selected} />
          </div>

          {/* intervention ranking summary */}
          {state && state.ranked.length > 0 && (
            <div className="rounded-lg border border-[#232B3D] bg-[#11151F] p-3">
              <div className="mb-2 text-[11px] font-bold tracking-wider text-[#8A94A8]">
                INTERVENTION RANKING
              </div>
              {state.ranked.slice(0, 4).map((r) => (
                <button
                  key={r.node_id}
                  onClick={() => {
                    setSelectedNode(r.node_id);
                    setDrawerOpen(true);
                  }}
                  className={`mb-1.5 flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-[11px] transition hover:bg-[#161B27] ${
                    r.label ? "border border-[#FFD700]/50 bg-[#FFD700]/5" : ""
                  }`}
                >
                  <span className={r.label ? "font-bold text-[#FFD700]" : "text-[#E8ECF4]"}>
                    #{r.rank} {r.node_name} {r.label ? "★ FOCUS HERE FIRST" : ""}
                  </span>
                  <span className="font-semibold text-[#00E5FF]">{r.score.toFixed(3)}</span>
                </button>
              ))}
            </div>
          )}

          {/* impact / validation toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowImpact(true)}
              className={`flex-1 rounded-md border px-2 py-1.5 text-[11px] font-semibold transition ${
                showImpact
                  ? "border-[#00E5FF]/50 bg-[#00E5FF]/10 text-[#00E5FF]"
                  : "border-[#232B3D] bg-[#161B27] text-[#8A94A8]"
              }`}
            >
              Impact
            </button>
            <button
              onClick={() => setShowImpact(false)}
              className={`flex-1 rounded-md border px-2 py-1.5 text-[11px] font-semibold transition ${
                !showImpact
                  ? "border-[#00E5FF]/50 bg-[#00E5FF]/10 text-[#00E5FF]"
                  : "border-[#232B3D] bg-[#161B27] text-[#8A94A8]"
              }`}
            >
              Validation
            </button>
          </div>

          <div className="min-h-[190px] rounded-lg border border-[#232B3D] bg-[#11151F]">
            {showImpact ? (
              <BeforeAfterView projection={state?.before_after ?? null} />
            ) : (
              <ValidationMetrics validation={state?.validation_metrics ?? null} />
            )}
          </div>
        </div>

        {/* drawer */}
        <ExplanationDrawer
          open={drawerOpen}
          node={selected}
          intervention={state?.intervention ?? null}
          ranking={state?.ranked ?? []}
          onClose={() => setDrawerOpen(false)}
        />
      </div>
    </div>
  );
}
