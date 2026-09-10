import { Line, LineChart, ReferenceLine, ResponsiveContainer, YAxis } from "recharts";
import type { StateNode } from "../../lib/api";

// Sparkline trends per bound sensor (Recharts). Values AND thresholds come
// from the backend payload; no client-side thresholding (Section 13).

interface Props {
  node: StateNode | null;
}

export function SensorPanel({ node }: Props) {
  if (!node) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-[#5A6472]">
        Select a node to view its live sensor trends
      </div>
    );
  }

  const colorOf = (s: string) =>
    s === "failed" ? "#FF3B3B" : s === "warning" ? "#FFB800" : "#00E5FF";

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-3">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-bold tracking-wider text-[#00E5FF]">
          {node.display_name} sensors
        </span>
        {node.last_updated && (
          <span className="text-[10px] text-[#8A94A8]">
            {node.last_updated.slice(11, 19)} UTC
          </span>
        )}
      </div>

      {node.bindings.length === 0 && (
        <div className="rounded-md border border-dashed border-[#232B3D] p-3 text-[10px] text-[#5A6472]">
          No sensor bound to this node yet — add one in the Environment Builder.
        </div>
      )}

      {node.bindings.map((b) => {
        const points = b.trend.map((v, i) => ({ i, v }));
        const stroke = colorOf(b.state);
        return (
          <div
            key={b.topic}
            className="rounded-lg border border-[#232B3D] bg-[#161B27] p-2.5"
          >
            <div className="mb-1 flex items-baseline justify-between gap-2">
              <span className="truncate text-[10px] font-semibold text-[#8A94A8]" title={b.topic}>
                {b.topic}
              </span>
              <span className="text-[11px] font-bold" style={{ color: stroke }}>
                {b.last_value !== null ? b.last_value.toFixed(2) : "--"}
                {b.unit ? ` ${b.unit}` : ""}
              </span>
            </div>
            <div className="h-10">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={points}>
                  <YAxis hide domain={["dataMin - 0.5", "dataMax + 0.5"]} />
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke={stroke}
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  {/* thresholds from the backend payload, never computed here */}
                  {b.warning_threshold !== null && (
                    <ReferenceLine
                      y={b.warning_threshold}
                      stroke="#FFB800"
                      strokeDasharray="4 3"
                      strokeWidth={1}
                    />
                  )}
                  {b.failure_threshold !== null && (
                    <ReferenceLine
                      y={b.failure_threshold}
                      stroke="#FF3B3B"
                      strokeDasharray="4 3"
                      strokeWidth={1}
                    />
                  )}
                  {points.length > 1 && (
                    <ReferenceLine x={points.length - 1} stroke="#232B3D" />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-1 flex items-center justify-between text-[9px] text-[#5A6472]">
              <span>
                {b.warm_up
                  ? `warm-up · ${b.samples} samples`
                  : `IF calibrated · ${b.samples} samples`}
              </span>
              <span>
                warn {b.warning_threshold ?? "--"} / fail {b.failure_threshold ?? "--"}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
