import { useMemo } from "react";
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
import { AlertTriangle, HelpCircle, ShieldCheck, Siren } from "lucide-react";
import type { EnvironmentState, StateNode } from "../../lib/api";

// Generalized dependency graph: renders whatever nodes/edges the polled
// /state payload carries for this environment — no fixed N1-N6 layout
// (build prompt Section 5.5). Positions come from the backend (set at
// creation time and persisted in the nodes table).

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
    icon: <HelpCircle size={16} />,
  },
};

function NodeCard({ data }: NodeProps) {
  const d = data as {
    id: number;
    label: string;
    nodeType: string;
    status: string;
    current_value: number | null;
    unit: string;
    anomaly_score: number;
    at_risk?: boolean;
    eta_seconds?: number | null;
    warm_up?: boolean;
    focus?: boolean;
    selected?: boolean;
    onSelect: (id: number) => void;
  };
  const style = STATUS_STYLE[d.status] ?? STATUS_STYLE.offline;

  return (
    <div
      onClick={() => d.onSelect(d.id)}
      className={`node-card flex h-[92px] w-[178px] cursor-pointer flex-col justify-between rounded-lg p-2.5 ${
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
          {d.nodeType}
        </span>
        <span style={{ color: style.text }}>{style.icon}</span>
      </div>
      <div className="text-[10.5px] font-medium leading-tight text-[#E8ECF4]">
        {d.label}
      </div>
      <div className="flex items-center justify-between text-[9.5px]">
        <span style={{ color: style.text }}>
          {d.status.toUpperCase()}
          {d.current_value !== null ? ` · ${d.current_value.toFixed(1)}${d.unit}` : ""}
          {d.warm_up ? " · warm-up" : ""}
        </span>
        {d.at_risk && (
          <span className="text-[#FFB800]">
            risk ~{Math.round((d.eta_seconds ?? 0) / 60)}m
          </span>
        )}
      </div>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { card: NodeCard };

interface Props {
  state: EnvironmentState | null;
  focusNode: number | null;
  selectedNode: number | null;
  onSelectNode: (id: number) => void;
}

export function DependencyGraph({ state, focusNode, selectedNode, onSelectNode }: Props) {
  const nodes: Node[] = useMemo(() => {
    if (!state) return [];
    return state.nodes.map((n: StateNode) => ({
      id: String(n.id),
      type: "card",
      position: { x: n.position_x, y: n.position_y },
      data: {
        id: n.id,
        label: n.display_name,
        nodeType: n.node_type,
        status: n.status,
        current_value: n.current_value,
        unit: n.bindings[0]?.unit ?? "",
        anomaly_score: n.anomaly_score,
        at_risk: n.at_risk,
        eta_seconds: n.eta_seconds,
        warm_up: n.warm_up,
        focus: focusNode === n.id,
        selected: selectedNode === n.id,
        onSelect: onSelectNode,
      },
      draggable: false,
    }));
  }, [state, focusNode, selectedNode, onSelectNode]);

  const edges: Edge[] = useMemo(() => {
    if (!state) return [];
    const nameOf = (id: number) =>
      state.nodes.find((n) => n.id === id)?.display_name ?? String(id);
    return state.edges.map((e) => ({
      id: `e${e.id}`,
      source: String(e.source),
      target: String(e.target),
      animated: e.active_cascade,
      className: e.active_cascade ? "cascade-edge" : "",
      style: {
        stroke: e.active_cascade ? "#FF3B3B" : "#2A3550",
        strokeWidth: e.active_cascade ? 3 : 2,
      },
      label: `${e.relationship_type} · ${e.criticality.toFixed(2)}`,
      labelStyle: { fill: "#8A94A8", fontSize: 9 },
      labelBgStyle: { fill: "#0B0E14" },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: e.active_cascade ? "#FF3B3B" : "#2A3550",
      },
      // tooltip aid for small graphs: edge label keeps relationship type
      "aria-label": `${nameOf(e.source)} -> ${nameOf(e.target)}`,
    }));
  }, [state]);

  const onNodeClick = useMemo(
    () => (_: unknown, node: Node) => onSelectNode(node.data.id as number),
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
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        minZoom={0.3}
        maxZoom={1.5}
      >
        <Background color="#1A2132" variant={BackgroundVariant.Dots} gap={22} size={1} />
      </ReactFlow>
      {state?.nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-[#5A6472]">
          This environment has no nodes yet — add some in the Environment Builder.
        </div>
      )}
    </div>
  );
}
