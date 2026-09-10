import { Line, LineChart, ReferenceLine, ResponsiveContainer, YAxis } from "recharts";
import type { SensorPayload } from "../../lib/api";

// Sparkline trends per mapped sensor (Recharts). Values come from the
// backend; no client-side thresholding (CONTRACT.md Section 13).

interface Props {
  sensor: SensorPayload | null;
}

export function SensorPanel({ sensor }: Props) {
  if (!sensor) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-[#5A6472]">
        Select a node to view sensor trends
      </div>
    );
  }

  const entries = Object.entries(sensor.tags);

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-3">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-bold tracking-wider text-[#00E5FF]">
          {sensor.node_id} sensors
        </span>
        {sensor.timestamp && (
          <span className="text-[10px] text-[#8A94A8]">
            {sensor.timestamp.slice(11, 19)}
          </span>
        )}
      </div>

      {entries.map(([tag, data]) => {
        const points = data.trend.map((v, i) => ({ i, v }));
        return (
          <div
            key={tag}
            className="rounded-lg border border-[#232B3D] bg-[#161B27] p-2.5"
          >
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-[11px] font-semibold text-[#E8ECF4]">{tag}</span>
              <span className="text-[11px] font-bold text-[#00E5FF]">
                {data.value !== null ? data.value.toFixed(2) : "--"}
              </span>
            </div>
            <div className="h-10">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={points}>
                  <YAxis hide domain={["dataMin - 0.5", "dataMax + 0.5"]} />
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke="#00E5FF"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  {points.length > 1 && (
                    <ReferenceLine x={points.length - 1} stroke="#232B3D" />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })}
    </div>
  );
}
