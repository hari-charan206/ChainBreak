import { Activity, AlertTriangle, Pause, Play, RotateCcw, Zap } from "lucide-react";
import type { GraphPayload, ReplayState } from "../../lib/api";

interface Props {
  graph: GraphPayload | null;
  replay: ReplayState | null;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onSimulateFailure: () => void;
  busy: boolean;
}

const STATUS_META: Record<string, { color: string; label: string }> = {
  healthy: { color: "#00E5FF", label: "Healthy" },
  warning: { color: "#FFB800", label: "Warning" },
  failed: { color: "#FF3B3B", label: "Failed" },
  offline: { color: "#5A6472", label: "Offline" },
};

export function StatusBar({ graph, replay, onStart, onStop, onReset,
                            onSimulateFailure, busy }: Props) {
  const counts = graph
    ? graph.nodes.reduce<Record<string, number>>((acc, n) => {
        acc[n.status] = (acc[n.status] ?? 0) + 1;
        return acc;
      }, {})
    : {};

  return (
    <div className="flex items-center justify-between border-b border-[#232B3D] bg-[#11151F] px-5 py-3">
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-[#00E5FF]" />
          <span className="text-sm font-bold tracking-wide">ChainBreak</span>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {Object.entries(counts).map(([status, count]) => (
            <div key={status} className="flex items-center gap-1.5">
              <span
                className={
                  status === "warning" ? "inline-block h-2.5 w-2.5 rounded-full"
                  : status === "failed" ? "inline-block h-2.5 w-2.5 rotate-45"
                  : "inline-block h-2.5 w-2.5 rounded-full"
                }
                style={{
                  background: STATUS_META[status]?.color ?? "#5A6472",
                  border: status === "offline" ? "1px dashed #5A6472" : "none",
                }}
              />
              <span className="text-[#8A94A8]">{count} {STATUS_META[status]?.label ?? status}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {replay && (
          <span className="text-xs text-[#8A94A8]">
            t = {replay.timestamp.slice(11, 19)} · row {replay.position}/{replay.total_rows} · {replay.multiplier}x
          </span>
        )}
        <button
          onClick={onStart}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-md border border-[#00E5FF]/40 bg-[#00E5FF]/10 px-3 py-1.5 text-xs font-semibold text-[#00E5FF] transition hover:bg-[#00E5FF]/20 disabled:opacity-50"
        >
          <Play size={13} /> Start replay
        </button>
        <button
          onClick={onStop}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-md border border-[#232B3D] bg-[#161B27] px-3 py-1.5 text-xs font-semibold text-[#8A94A8] transition hover:text-[#E8ECF4] disabled:opacity-50"
        >
          <Pause size={13} /> Pause
        </button>
        <button
          onClick={onReset}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-md border border-[#232B3D] bg-[#161B27] px-3 py-1.5 text-xs font-semibold text-[#8A94A8] transition hover:text-[#E8ECF4] disabled:opacity-50"
        >
          <RotateCcw size={13} /> Reset
        </button>
        <button
          onClick={onSimulateFailure}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-md border border-[#FF3B3B]/50 bg-[#FF3B3B]/15 px-3 py-1.5 text-xs font-bold text-[#FF3B3B] transition hover:bg-[#FF3B3B]/25 disabled:opacity-50"
        >
          <Zap size={13} /> Simulate Failure
        </button>
      </div>
    </div>
  );
}
