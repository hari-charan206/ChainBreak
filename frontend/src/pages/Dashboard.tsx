import { useCallback, useEffect, useState } from "react";
import { api, type BeforeAfterPayload, type CascadePayload,
         type ExplanationPayload, type GraphPayload,
         type RankedIntervention, type ReplayState, type SensorPayload,
         type ValidationPayload } from "../lib/api";
import { usePolling } from "../hooks/usePolling";
import { StatusBar } from "../components/StatusBar/StatusBar";
import { DependencyGraph } from "../components/DependencyGraph/DependencyGraph";
import { SensorPanel } from "../components/SensorPanel/SensorPanel";
import { ExplanationDrawer } from "../components/ExplanationDrawer/ExplanationDrawer";
import { BeforeAfterView } from "../components/BeforeAfterView/BeforeAfterView";
import { ValidationMetrics } from "../components/ValidationMetrics/ValidationMetrics";

const POLL_MS = 2000; // contract: ~2s, no faster

export default function Dashboard() {
  const [selectedNode, setSelectedNode] = useState<string | null>("N3");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showImpact, setShowImpact] = useState(false);
  const [fullMetrics, setFullMetrics] = useState<Record<string, unknown> | null>(null);

  // ---- 2s polling state ----
  const graph = usePolling<GraphPayload>(api.graph, POLL_MS);
  const replay = usePolling<ReplayState>(api.replayState, POLL_MS);
  const cascade = usePolling<CascadePayload>(api.cascade, POLL_MS);
  const ranking = usePolling<{ ranked: RankedIntervention[]; note: string | null }>(
    api.ranking, POLL_MS,
  );
  const impact = usePolling<BeforeAfterPayload>(api.beforeAfter, POLL_MS);
  const validation = usePolling<ValidationPayload>(api.validation, POLL_MS);
  const sensor = usePolling<SensorPayload | null>(
    useCallback(() => (selectedNode ? api.sensors(selectedNode) : Promise.resolve(null)),
      [selectedNode]),
    POLL_MS,
  );
  const explanation = usePolling<ExplanationPayload | null>(
    useCallback(
      () => (drawerOpen && selectedNode ? api.explanation(selectedNode) : Promise.resolve(null)),
      [drawerOpen, selectedNode],
    ),
    POLL_MS,
  );

  // fetch full-dataset metrics once, on demand only
  useEffect(() => {
    if (fullMetrics === null) {
      api.fullValidation().then((m) => m && setFullMetrics(m));
    }
  }, [fullMetrics]);

  const focusNode = ranking?.ranked?.[0]?.label === "FOCUS HERE FIRST"
    ? ranking.ranked[0].node_id
    : null;

  const handleStart = async () => {
    setBusy(true);
    await api.replayStart();
    setBusy(false);
  };
  const handleStop = async () => {
    setBusy(true);
    await api.replayStop();
    setBusy(false);
  };
  const handleReset = async () => {
    setBusy(true);
    await api.replayReset();
    setShowImpact(false);
    setBusy(false);
  };
  const handleSimulate = async () => {
    setBusy(true);
    await api.simulateFailure();
    setBusy(false);
  };
  const handleApply = async (nodeId: string) => {
    setBusy(true);
    await api.applyIntervention(nodeId);
    setDrawerOpen(false);
    setShowImpact(true);
    setBusy(false);
  };

  const replayRunning = replay?.running ?? false;

  return (
    <div className="flex h-screen flex-col bg-[#0B0E14]">
      <StatusBar
        graph={graph}
        replay={replay}
        onStart={handleStart}
        onStop={handleStop}
        onReset={handleReset}
        onSimulateFailure={handleSimulate}
        busy={busy}
      />

      <div className="flex min-h-0 flex-1">
        {/* left/center graph */}
        <div className="relative min-w-0 flex-1">
          <DependencyGraph
            graph={graph}
            focusNode={focusNode}
            selectedNode={selectedNode}
            onSelectNode={(id) => {
              setSelectedNode(id);
              setDrawerOpen(true);
            }}
          />
        </div>

        {/* right panel */}
        <div className="flex w-[340px] shrink-0 flex-col gap-3 overflow-y-auto border-l border-[#232B3D] bg-[#0B0E14] p-3">
          {/* warning banner */}
          {cascade?.active_edges && cascade.active_edges.length > 0 && (
            <div className="rounded-md border border-[#FF3B3B]/50 bg-[#FF3B3B]/10 px-3 py-2 text-[11px] font-semibold text-[#FF3B3B]">
              ⚠ Cascade in progress: {cascade.active_edges.join(" → ")}
            </div>
          )}
          {cascade?.synthetic && (
            <div className="rounded-md border border-[#FFB800]/40 bg-[#FFB800]/5 px-3 py-2 text-[10px] leading-snug text-[#FFB800]">
              Disclosure: {cascade.note}
            </div>
          )}

          {/* replay CTA */}
          {!replayRunning && (
            <div className="rounded-md border border-[#00E5FF]/30 bg-[#00E5FF]/5 px-3 py-2 text-[11px] text-[#8A94A8]">
              Replay ready from locked window {replay?.locked_start ?? ""} at{" "}
              {replay?.locked_multiplier ?? 30}x. Press Start replay.
            </div>
          )}

          {/* sensor trends for selected node */}
          <div className="min-h-[220px] rounded-lg border border-[#232B3D] bg-[#11151F]">
            <SensorPanel sensor={sensor} />
          </div>

          {/* intervention ranking summary */}
          {ranking?.ranked && ranking.ranked.length > 0 && (
            <div className="rounded-lg border border-[#232B3D] bg-[#11151F] p-3">
              <div className="mb-2 text-[11px] font-bold tracking-wider text-[#8A94A8]">
                INTERVENTION RANKING
              </div>
              {ranking.ranked.slice(0, 4).map((r) => (
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
                    #{r.rank} {r.node_id} {r.label ? "★ FOCUS HERE FIRST" : ""}
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
              <BeforeAfterView impact={impact} />
            ) : (
              <ValidationMetrics validation={validation} fullMetrics={fullMetrics} />
            )}
          </div>
        </div>

        {/* drawer */}
        <ExplanationDrawer
          open={drawerOpen}
          explanation={explanation}
          ranking={ranking?.ranked ?? []}
          onApply={handleApply}
          onClose={() => setDrawerOpen(false)}
          busy={busy}
        />
      </div>
    </div>
  );
}
