import { useNavigate } from "react-router-dom";
import { Activity, LogOut, Radio } from "lucide-react";
import type { EnvironmentState } from "../../lib/api";
import { useAuth } from "../../hooks/useAuth";

interface Props {
  state: EnvironmentState | null;
  environmentName: string | null;
}

const STATUS_META: Record<string, { color: string; label: string }> = {
  healthy: { color: "#00E5FF", label: "Healthy" },
  warning: { color: "#FFB800", label: "Warning" },
  failed: { color: "#FF3B3B", label: "Failed" },
  offline: { color: "#5A6472", label: "Offline" },
};

// Live status bar. Section 6.1: NO start/pause/reset/simulate-failure
// controls — node state changes only when real MQTT data says so.
export function StatusBar({ state, environmentName }: Props) {
  const { email, logout } = useAuth();
  const navigate = useNavigate();

  const counts = state
    ? state.nodes.reduce<Record<string, number>>((acc, n) => {
        acc[n.status] = (acc[n.status] ?? 0) + 1;
        return acc;
      }, {})
    : {};
  const order = ["failed", "warning", "healthy", "offline"];
  const liveCount = state
    ? state.nodes.reduce((a, n) => a + n.bindings.length, 0)
    : 0;

  return (
    <div className="flex items-center justify-between border-b border-[#232B3D] bg-[#11151F] px-5 py-3">
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-[#00E5FF]" />
          <span className="text-sm font-bold tracking-wide">ChainBreak</span>
          {environmentName && (
            <span className="rounded border border-[#232B3D] px-1.5 py-0.5 text-[10px] text-[#8A94A8]">
              {environmentName}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs">
          {order.filter((s) => counts[s]).map((status) => (
            <div key={status} className="flex items-center gap-1.5">
              <span
                className={
                  status === "warning"
                    ? "inline-block h-2.5 w-2.5 rounded-full"
                    : status === "failed"
                      ? "inline-block h-2.5 w-2.5 rotate-45"
                      : status === "offline"
                        ? "inline-block h-2.5 w-2.5 rounded-full"
                        : "inline-block h-2.5 w-2.5 rounded-full"
                }
                style={{
                  background: STATUS_META[status]?.color ?? "#5A6472",
                  border: status === "offline" ? "1px dashed #5A6472" : "none",
                }}
              />
              <span className="text-[#8A94A8]">
                {counts[status]} {STATUS_META[status]?.label ?? status}
              </span>
            </div>
          ))}
          <span className="flex items-center gap-1 text-[10px] text-[#5A6472]">
            <Radio size={10} />
            {liveCount} bound sensor{liveCount === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs text-[#8A94A8]">
        <span>{email}</span>
        <button
          onClick={() => { logout(); navigate("/login"); }}
          className="flex items-center gap-1 rounded-md border border-[#232B3D] bg-[#161B27] px-2.5 py-1 text-[11px] font-semibold text-[#8A94A8] transition hover:text-[#E8ECF4]"
        >
          <LogOut size={12} /> Sign out
        </button>
      </div>
    </div>
  );
}
