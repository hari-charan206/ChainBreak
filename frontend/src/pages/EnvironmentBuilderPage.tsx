import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Cable, Database, Network, Pencil, Plus, X } from "lucide-react";
import { api, type EnvironmentDetail } from "../lib/api";

// Environment Builder (Section 5.3): simple forms, no drag-and-drop graph
// editor (MVP constraint carried over from v3). Used for BOTH creating a
// new environment and editing an existing one (/environments/new?env=ID):
// rename env, add/edit/delete nodes, connect/delete edges, bind/delete
// sensors, adjust binding thresholds.

const TEMPLATES = ["Water Treatment", "Manufacturing", "HVAC", "Custom"];
const NODE_TYPES = ["sensor", "pump", "valve", "control_unit", "custom"];
const RELATIONSHIPS = ["feeds", "controls", "depends_on"];

export default function EnvironmentBuilderPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editEnvId = searchParams.get("env");

  const [envId, setEnvId] = useState<number | null>(
    editEnvId ? Number(editEnvId) : null,
  );
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("Custom");
  const [detail, setDetail] = useState<EnvironmentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // node form (also used for editing an existing node)
  const [editingNodeId, setEditingNodeId] = useState<number | null>(null);
  const [nodeName, setNodeName] = useState("");
  const [nodeType, setNodeType] = useState("sensor");

  // edge form
  const [edgeSource, setEdgeSource] = useState("");
  const [edgeTarget, setEdgeTarget] = useState("");
  const [relationship, setRelationship] = useState("feeds");
  const [criticality, setCriticality] = useState(0.5);

  // binding form
  const [bindNode, setBindNode] = useState("");
  const [topic, setTopic] = useState("");
  const [unit, setUnit] = useState("");
  const [baseline, setBaseline] = useState("");
  const [warnOverride, setWarnOverride] = useState("");
  const [failOverride, setFailOverride] = useState("");

  const refresh = useCallback(async () => {
    if (envId === null) return;
    const d = await api.environment(envId);
    if (d) {
      setDetail(d);
      setName(d.name);
      setTemplate(d.industry_template);
    }
  }, [envId]);

  useEffect(() => { void refresh(); }, [refresh]);

  const nodes = detail?.nodes ?? [];
  const edges = detail?.edges ?? [];
  const bindings = detail?.sensor_bindings ?? [];

  const fail = (fallback: string) => {
    setError(fallback);
  };

  const createEnv = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await api.createEnvironment(name, template);
    setBusy(false);
    if (!res.ok || !res.data || typeof res.data !== "object" || !("id" in res.data)) {
      const detailMsg =
        res.data && typeof res.data === "object" && "detail" in res.data
          ? String((res.data as { detail: unknown }).detail)
          : `could not create environment (HTTP ${res.status})`;
      fail(detailMsg);
      return;
    }
    const id = (res.data as { id: number }).id;
    setEnvId(id);
    // swap the URL to edit mode so a refresh keeps working on this env
    navigate(`/environments/new?env=${id}`, { replace: true });
  };

  const saveEnvMeta = async (e: FormEvent) => {
    e.preventDefault();
    if (envId === null) return;
    setBusy(true); setError(null);
    const res = await api.updateEnvironment(envId, { name, industry_template: template });
    setBusy(false);
    if (!res.ok) {
      const detailMsg =
        res.data && typeof res.data === "object" && "detail" in res.data
          ? String((res.data as { detail: unknown }).detail)
          : "could not rename environment";
      fail(detailMsg);
      return;
    }
    await refresh();
  };

  const addOrUpdateNode = async (e: FormEvent) => {
    e.preventDefault();
    if (envId === null) return;
    setBusy(true); setError(null);
    const res = editingNodeId !== null
      ? await api.updateNode(envId, editingNodeId, {
          display_name: nodeName, node_type: nodeType })
      : await api.addNode(envId, { display_name: nodeName, node_type: nodeType });
    setBusy(false);
    if (!res.ok) { fail("could not save node"); return; }
    setNodeName(""); setNodeType("sensor"); setEditingNodeId(null);
    await refresh();
  };

  const startEditNode = (id: number) => {
    const n = nodes.find((x) => x.id === id);
    if (!n) return;
    setEditingNodeId(n.id);
    setNodeName(n.display_name);
    setNodeType(n.node_type);
  };

  const deleteNode = async (id: number) => {
    if (envId === null || !window.confirm("Delete this node (and its edges/bindings)?")) return;
    const res = await api.deleteNode(envId, id);
    if (!res.ok) { fail("could not delete node"); return; }
    if (editingNodeId === id) { setEditingNodeId(null); setNodeName(""); }
    await refresh();
  };

  const connect = async (e: FormEvent) => {
    e.preventDefault();
    if (envId === null || !edgeSource || !edgeTarget) return;
    setBusy(true); setError(null);
    const res = await api.addEdge(envId, {
      source: Number(edgeSource),
      target: Number(edgeTarget),
      relationship_type: relationship,
      criticality,
    });
    setBusy(false);
    if (!res.ok) {
      const detailMsg =
        res.data && typeof res.data === "object" && "detail" in res.data
          ? String((res.data as { detail: unknown }).detail)
          : "could not connect nodes";
      fail(detailMsg);
      return;
    }
    await refresh();
  };

  const deleteEdge = async (id: number) => {
    if (envId === null) return;
    const res = await api.deleteEdge(envId, id);
    if (!res.ok) { fail("could not delete edge"); return; }
    await refresh();
  };

  const bind = async (e: FormEvent) => {
    e.preventDefault();
    if (envId === null || !bindNode || !topic) return;
    setBusy(true); setError(null);
    const res = await api.addBinding(envId, {
      node_id: Number(bindNode),
      mqtt_topic: topic,
      unit,
      baseline: baseline === "" ? null : Number(baseline),
      warning_threshold: warnOverride === "" ? null : Number(warnOverride),
      failure_threshold: failOverride === "" ? null : Number(failOverride),
    });
    setBusy(false);
    if (!res.ok) {
      const detailMsg =
        res.data && typeof res.data === "object" && "detail" in res.data
          ? String((res.data as { detail: unknown }).detail)
          : "could not bind sensor";
      fail(detailMsg);
      return;
    }
    setTopic(""); setUnit(""); setBaseline(""); setWarnOverride(""); setFailOverride("");
    await refresh();
  };

  const deleteBinding = async (id: number) => {
    if (envId === null || !window.confirm("Unbind this sensor topic?")) return;
    const res = await api.deleteBinding(envId, id);
    if (!res.ok) { fail("could not unbind sensor"); return; }
    await refresh();
  };

  const selectedWarn = useMemo(() => {
    const b = Number(baseline);
    return Number.isFinite(b) && baseline !== "" ? (b * 1.2).toFixed(1) : "baseline × 1.2";
  }, [baseline]);
  const selectedFail = useMemo(() => {
    const b = Number(baseline);
    return Number.isFinite(b) && baseline !== "" ? (b * 1.5).toFixed(1) : "baseline × 1.5";
  }, [baseline]);

  return (
    <div className="min-h-screen bg-[#0B0E14] px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Network size={18} className="text-[#00E5FF]" />
            <span className="text-sm font-bold tracking-wide text-[#E8ECF4]">
              {envId === null ? "Environment Builder" : "Edit Environment"}
            </span>
          </div>
          <Link to="/environments" className="text-[11px] text-[#5A6472] hover:text-[#8A94A8]">
            ← Back to environments
          </Link>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-[#FF3B3B]/50 bg-[#FF3B3B]/10 px-3 py-2 text-[11px] font-semibold text-[#FF3B3B]">
            {error}
          </div>
        )}

        {/* step 1 — create OR rename */}
        {envId === null ? (
          <form onSubmit={createEnv} className="rounded-xl border border-[#232B3D] bg-[#11151F] p-6">
            <h2 className="mb-1 text-sm font-bold text-[#E8ECF4]">1 · Name your environment</h2>
            <p className="mb-4 text-[11px] text-[#8A94A8]">
              The template only changes default icon/label suggestions — not logic.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Demo Water Plant"
                className="flex-1 rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-sm text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60"
              />
              <select
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-sm text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60"
              >
                {TEMPLATES.map((t) => <option key={t}>{t}</option>)}
              </select>
              <button
                type="submit"
                disabled={busy}
                className="rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/15 px-4 py-2 text-sm font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25 disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </form>
        ) : (
          <>
            <div className="mb-6 rounded-xl border border-[#00E5FF]/30 bg-[#00E5FF]/5 px-5 py-4">
              <form onSubmit={saveEnvMeta} className="flex flex-wrap items-center gap-2">
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="min-w-[180px] flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-sm font-bold text-[#E8ECF4] outline-none transition hover:border-[#232B3D] focus:border-[#00E5FF]/60"
                />
                <select
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-2 py-1.5 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60"
                >
                  {TEMPLATES.map((t) => <option key={t}>{t}</option>)}
                </select>
                <button
                  type="submit"
                  disabled={busy}
                  className="flex items-center gap-1 rounded-md border border-[#232B3D] bg-[#161B27] px-2.5 py-1.5 text-[11px] font-semibold text-[#8A94A8] transition hover:border-[#00E5FF]/50 hover:text-[#00E5FF] disabled:opacity-50"
                >
                  <Pencil size={11} /> Save name
                </button>
              </form>
              <div className="mt-1.5 px-2 text-[11px] text-[#8A94A8]">
                {nodes.length} nodes · {edges.length} edges · {bindings.length} bindings — saved automatically.{" "}
                {nodes.length > 0 && (
                  <button
                    onClick={() => navigate(`/dashboard/${envId}`)}
                    className="font-semibold text-[#00E5FF] hover:underline"
                  >
                    Open dashboard →
                  </button>
                )}
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              {/* step 2 — nodes: add / edit / delete */}
              <form onSubmit={addOrUpdateNode} className="rounded-xl border border-[#232B3D] bg-[#11151F] p-5">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-[#E8ECF4]">
                  <Plus size={14} className="text-[#00E5FF]" />
                  2 · {editingNodeId !== null ? "Edit node" : "Add a block/node"}
                </h2>
                <div className="flex gap-2">
                  <input
                    required
                    value={nodeName}
                    onChange={(e) => setNodeName(e.target.value)}
                    placeholder="e.g. Cooling Pump"
                    className="flex-1 rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-sm text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60"
                  />
                  <select
                    value={nodeType}
                    onChange={(e) => setNodeType(e.target.value)}
                    className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-2 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60"
                  >
                    {NODE_TYPES.map((t) => <option key={t}>{t}</option>)}
                  </select>
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded-md border border-[#232B3D] bg-[#161B27] px-3 py-2 text-xs font-bold text-[#E8ECF4] transition hover:border-[#00E5FF]/50 disabled:opacity-50"
                  >
                    {editingNodeId !== null ? "Save" : "Add"}
                  </button>
                  {editingNodeId !== null && (
                    <button
                      type="button"
                      onClick={() => { setEditingNodeId(null); setNodeName(""); setNodeType("sensor"); }}
                      className="rounded-md border border-[#232B3D] px-2 py-2 text-xs text-[#5A6472] transition hover:text-[#E8ECF4]"
                    >
                      Cancel
                    </button>
                  )}
                </div>
                {nodes.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {nodes.map((n) => (
                      <span
                        key={n.id}
                        className={`flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] ${
                          editingNodeId === n.id
                            ? "border-[#00E5FF]/60 text-[#00E5FF]"
                            : "border-[#232B3D] text-[#8A94A8]"
                        }`}
                      >
                        {n.display_name} · {n.node_type}
                        <button
                          type="button"
                          onClick={() => startEditNode(n.id)}
                          title="Edit node"
                          className="text-[#5A6472] transition hover:text-[#00E5FF]"
                        >
                          <Pencil size={10} />
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteNode(n.id)}
                          title="Delete node"
                          className="text-[#5A6472] transition hover:text-[#FF3B3B]"
                        >
                          <X size={11} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </form>

              {/* step 3 — edges: connect / delete */}
              <form onSubmit={connect} className="rounded-xl border border-[#232B3D] bg-[#11151F] p-5">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-[#E8ECF4]">
                  <Cable size={14} className="text-[#00E5FF]" /> 3 · Connect blocks
                </h2>
                {nodes.length < 2 ? (
                  <p className="text-[11px] text-[#5A6472]">Add at least two nodes first.</p>
                ) : (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                      <select value={edgeSource} onChange={(e) => setEdgeSource(e.target.value)} className="flex-1 rounded-md border border-[#232B3D] bg-[#0B0E14] px-2 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60">
                        <option value="">Source node…</option>
                        {nodes.map((n) => <option key={n.id} value={n.id}>{n.display_name}</option>)}
                      </select>
                      <span className="text-[10px] text-[#5A6472]">→</span>
                      <select value={edgeTarget} onChange={(e) => setEdgeTarget(e.target.value)} className="flex-1 rounded-md border border-[#232B3D] bg-[#0B0E14] px-2 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60">
                        <option value="">Target node…</option>
                        {nodes.map((n) => <option key={n.id} value={n.id}>{n.display_name}</option>)}
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <select value={relationship} onChange={(e) => setRelationship(e.target.value)} className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-2 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60">
                        {RELATIONSHIPS.map((r) => <option key={r}>{r}</option>)}
                      </select>
                      <label className="flex flex-1 items-center gap-2 text-[10px] text-[#8A94A8]">
                        criticality
                        <input
                          type="range" min={0} max={1} step={0.05}
                          value={criticality}
                          onChange={(e) => setCriticality(Number(e.target.value))}
                          className="flex-1 accent-[#00E5FF]"
                        />
                        <span className="w-7 text-right font-bold text-[#00E5FF]">{criticality.toFixed(2)}</span>
                      </label>
                      <button
                        type="submit"
                        disabled={busy}
                        className="rounded-md border border-[#232B3D] bg-[#161B27] px-3 py-2 text-xs font-bold text-[#E8ECF4] transition hover:border-[#00E5FF]/50 disabled:opacity-50"
                      >
                        Connect
                      </button>
                    </div>
                    {edges.length > 0 && (
                      <div className="space-y-1">
                        {edges.map((e2) => {
                          const s = nodes.find((n) => n.id === e2.source_node_id);
                          const t = nodes.find((n) => n.id === e2.target_node_id);
                          return (
                            <div key={e2.id} className="flex items-center justify-between text-[10px] text-[#5A6472]">
                              <span>
                                {s?.display_name ?? e2.source_node_id} → {t?.display_name ?? e2.target_node_id}
                                {" "}({e2.relationship_type}, crit {e2.criticality.toFixed(2)})
                              </span>
                              <button
                                type="button"
                                onClick={() => deleteEdge(e2.id)}
                                title="Delete edge"
                                className="text-[#5A6472] transition hover:text-[#FF3B3B]"
                              >
                                <X size={11} />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </form>

              {/* step 4 — sensor bindings: bind / delete */}
              <form onSubmit={bind} className="rounded-xl border border-[#232B3D] bg-[#11151F] p-5 lg:col-span-2">
                <h2 className="mb-1 flex items-center gap-2 text-sm font-bold text-[#E8ECF4]">
                  <Database size={14} className="text-[#00E5FF]" /> 4 · Bind a live sensor to a node
                </h2>
                <p className="mb-3 text-[11px] text-[#8A94A8]">
                  The MQTT topic is what your Wokwi sketch publishes to. Leave thresholds empty to use
                  the locked cold-start defaults from your baseline (warning = ×1.2, failure = ×1.5).
                </p>
                {nodes.length === 0 ? (
                  <p className="text-[11px] text-[#5A6472]">Add a node first.</p>
                ) : (
                  <div className="grid gap-2.5 sm:grid-cols-3">
                    <select value={bindNode} onChange={(e) => setBindNode(e.target.value)} className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-2 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60">
                      <option value="">Node…</option>
                      {nodes.map((n) => <option key={n.id} value={n.id}>{n.display_name}</option>)}
                    </select>
                    <input
                      required
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder={`chainbreak/env${envId}/sensor/temp`}
                      className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60 sm:col-span-2"
                    />
                    <input
                      value={unit}
                      onChange={(e) => setUnit(e.target.value)}
                      placeholder="unit (°C, %, mm…)"
                      className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60"
                    />
                    <input
                      value={baseline}
                      onChange={(e) => setBaseline(e.target.value)}
                      inputMode="decimal"
                      placeholder="expected baseline (e.g. 50)"
                      className="rounded-md border border-[#232B3D] bg-[#0B0E14] px-3 py-2 text-xs text-[#E8ECF4] outline-none focus:border-[#00E5FF]/60"
                    />
                    <div className="flex items-center justify-between gap-2 rounded-md border border-[#232B3D] bg-[#161B27] px-3 py-2 text-[10px] text-[#5A6472] sm:col-span-2">
                      <span>warn: <b className="text-[#FFB800]">{selectedWarn}</b> · fail: <b className="text-[#FF3B3B]">{selectedFail}</b> (auto)</span>
                      <span>or override:</span>
                      <input
                        value={warnOverride}
                        onChange={(e) => setWarnOverride(e.target.value)}
                        inputMode="decimal"
                        placeholder="warn"
                        className="w-16 rounded border border-[#232B3D] bg-[#0B0E14] px-1.5 py-1 text-[10px] text-[#E8ECF4] outline-none"
                      />
                      <input
                        value={failOverride}
                        onChange={(e) => setFailOverride(e.target.value)}
                        inputMode="decimal"
                        placeholder="fail"
                        className="w-16 rounded border border-[#232B3D] bg-[#0B0E14] px-1.5 py-1 text-[10px] text-[#E8ECF4] outline-none"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={busy}
                      className="rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/15 px-4 py-2 text-xs font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25 disabled:opacity-50"
                    >
                      Bind sensor
                    </button>
                  </div>
                )}
                {bindings.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {bindings.map((b) => {
                      const n = nodes.find((x) => x.id === b.node_id);
                      return (
                        <div key={b.id} className="flex items-center justify-between text-[10px] text-[#5A6472]">
                          <span>
                            <span className="text-[#8A94A8]">{n?.display_name ?? b.node_id}</span>
                            {" "}← <code className="text-[#00E5FF]/80">{b.mqtt_topic}</code>
                            {b.warning_threshold !== null && (
                              <> · warn {b.warning_threshold} / fail {b.failure_threshold}{b.unit ? ` ${b.unit}` : ""}</>
                            )}
                          </span>
                          <button
                            type="button"
                            onClick={() => deleteBinding(b.id)}
                            title="Unbind sensor"
                            className="text-[#5A6472] transition hover:text-[#FF3B3B]"
                          >
                            <X size={11} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
