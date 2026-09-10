import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { AlertTriangle, ShieldCheck, Siren } from "lucide-react";
import type { GraphPayload } from "../../lib/api";

// Fixed N1-N6 layout (CONTRACT.md Section 4-5). Nodes come from /api/graph;
// the frontend never invents nodes/edges (Section 13).

const LAYOUT: Record<string, { x: number; y: number }> = {
  N1: { x: 40, y: 180 },
  N2: { x: 250, y: 180 },
  N3: { x: 460, y: 180 },
  N4: { x: 670, y: 180 },
  N5: { x: 880, y: 180 },
  N6: { x: 1090, y: 180 },
};

const STATUS_STYLE: Record<
  string,
  { border: string; bg: string; text: string; icon: JSX.Element }
> = {
  healthy: {
    border: "1.5px solid #00E5FF",
    bg: "rgba(0,229,255,0.06)",
    text: "#00E5FF",
    icon: <ShieldCheck size={16} />,
  },
  warning: {
    border: "1.5px dashed #FFB800",
    bg: "rgba(255,184,0,0.10)",
    text: "#FFB800",
    icon: <AlertTriangle size={16} />,
  },
  failed: {
    border: "3px solid #FF3B3B",
    bg: "rgba(255,59,59,0.14)",
    text: "#FF3B3B",
    icon: <Siren size={16} />,
  },
  offline: {
    border: "1.5px dotted #5A6472",
    bg: "rgba(90,100,114,0.10)",
    text: "#5A6472",
    icon: <AlertTriangle size={16} />,
  },
};

function NodeCard({ data }: NodeProps) {
  const d = data as {
    id: string;
    label: string;
    status: string;
    anomaly_score?: number;
    at_risk?: boolean;
    eta_seconds?: number | null;
    focus?: boolean;
    selected?: boolean;
    onSelect: (id: string) => void;
  };
  const style = STATUS_STYLE[d.status] ?? STATUS_STYLE.healthy;

  return (
    <div
      onClick={() => d.onSelect(d.id)}
      className={`node-card flex h-[86px] w-[172px] cursor-pointer flex-col justify-between rounded-lg p-2.5 ${
        d.focus ? "focus-first" : ""
      }`}
      style={{
        border: d.focus ? undefined : style.border,
        background: style.bg,
        transform: d.selected ? "scale(1.04)" : undefined,
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold tracking-wider" style={{ color: style.text }}>
          {d.id}
        </span>
        <span style={{ color: style.text }}>{style.icon}</span>
      </div>
      <div className="text-[10.5px] font-medium leading-tight text-[#E8ECF4]">
        {d.label}
      </div>
      <div className="flex items-center justify-between text-[9.5px]">
        <span style={{ color: style.text }}>
          {d.status.toUpperCase()}
          {d.anomaly_score !== undefined ? ` · ${d.anomaly_score.toFixed(2)}` : ""}
        </span>
        {d.at_risk && (
          <span className="text-[#FFB800]">risk ~{Math.round((d.eta_seconds ?? 0) / 30)}s</span>
        )}
      </div>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { card: NodeCard };

interface Props {
  graph: GraphPayload | null;
  focusNode: string | null;
  selectedNode: string | null;
  onSelectNode: (id: string) => void;
}

export function DependencyGraph({ graph, focusNode, selectedNode, onSelectNode }: Props) {
  const nodes: Node[] = useMemo(() => {
    if (!graph) return [];
    return graph.nodes.map((n) => ({
      id: n.id,
      type: "card",
      position: LAYOUT[n.id] ?? { x: 0, y: 0 },
      data: {
        id: n.id,
        label: n.display_name,
        status: n.status,
        anomaly_score: n.anomaly_score,
        at_risk: n.at_risk,
        eta_seconds: n.eta_seconds,
        focus: focusNode === n.id,
        selected: selectedNode === n.id,
        onSelect: onSelectNode,
      },
      draggable: false,
    }));
  }, [graph, focusNode, selectedNode, onSelectNode]);

  const edges: Edge[] = useMemo(() => {
    if (!graph) return [];
    return graph.edges.map((e) => ({
      id: `${e.from}-${e.to}`,
      source: e.from,
      target: e.to,
      animated: e.active_cascade,
      className: e.active_cascade ? "cascade-edge" : "",
      style: {
        stroke: e.active_cascade ? "#FF3B3B" : "#2A3550",
        strokeWidth: e.active_cascade ? 3 : 2,
      },
      label: `crit ${e.criticality.toFixed(1)}`,
      labelStyle: { fill: "#8A94A8", fontSize: 9 },
      labelBgStyle: { fill: "#0B0E14" },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: e.active_cascade ? "#FF3B3B" : "#2A3550",
      },
    }));
  }, [graph]);

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => onSelectNode(node.id as string),
    [onSelectNode],
  );

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        minZoom={0.5}
        maxZoom={1.5}
      >
        <Background color="#1A2132" variant={BackgroundVariant.Dots} gap={22} size={1} />
      </ReactFlow>
      {graph?.synthetic && (
        <div className="absolute bottom-3 left-3 max-w-md rounded-md border border-[#FFB800]/40 bg-[#161B27] px-3 py-2 text-[11px] text-[#FFB800]">
          Disclosure: N3 anomaly is real SWaT attack data; downstream
          propagation shown is the model's predicted trajectory (synthetic),
          per our documented fallback.
        </div>
      )}
    </div>
  );
}
