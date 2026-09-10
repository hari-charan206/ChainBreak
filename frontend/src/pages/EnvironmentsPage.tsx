import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Clock, Pencil, Plus, Trash2 } from "lucide-react";
import { api, type EnvironmentSummary } from "../lib/api";
import { usePolling } from "../hooks/usePolling";
import { useAuth } from "../hooks/useAuth";

// Environment Picker (Section 5.4): list of the logged-in user's
// environments with name, node count, last-active timestamp and a
// status-summary chip.

export default function EnvironmentsPage() {
  const { email, logout } = useAuth();
  const navigate = useNavigate();
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const list = usePolling<{ environments: EnvironmentSummary[] }>(
    useCallback(() => api.environments(), []),
    5000,
  );

  const envs = list?.environments ?? [];

  const openDelete = (env: EnvironmentSummary) => {
    setDeletingId(env.id);
  };

  const confirmDelete = async () => {
    if (deletingId === null) return;
    await api.deleteEnvironment(deletingId);
    setDeletingId(null);
    // list refreshes on the next poll tick
  };

  return (
    <div className="min-h-screen bg-[#0B0E14] px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold tracking-wide text-[#E8ECF4]">ChainBreak</span>
            <span className="rounded border border-[#232B3D] px-1.5 py-0.5 text-[10px] text-[#5A6472]">
              environments
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-[#8A94A8]">
            <span>{email}</span>
            <button
              onClick={logout}
              className="rounded-md border border-[#232B3D] px-2.5 py-1 text-[11px] font-semibold text-[#8A94A8] transition hover:border-[#FF3B3B]/50 hover:text-[#FF3B3B]"
            >
              Sign out
            </button>
          </div>
        </div>

        <div className="mb-6 flex items-end justify-between">
          <div>
            <h1 className="text-xl font-bold text-[#E8ECF4]">Your environments</h1>
            <p className="mt-1 text-xs text-[#8A94A8]">
              Each environment is its own node/edge/sensor graph. Live data comes only from MQTT.
            </p>
          </div>
          <Link
            to="/environments/new"
            className="flex items-center gap-1.5 rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/15 px-3.5 py-2 text-xs font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25"
          >
            <Plus size={14} /> New environment
          </Link>
        </div>

        {list === null ? (
          <div className="rounded-lg border border-[#232B3D] bg-[#11151F] p-8 text-center text-xs text-[#5A6472]">
            Loading environments… (is the backend running on :8089?)
          </div>
        ) : envs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[#232B3D] bg-[#11151F] p-10 text-center">
            <div className="text-sm font-semibold text-[#E8ECF4]">No environments yet</div>
            <div className="mx-auto mt-1 max-w-sm text-xs text-[#5A6472]">
              Create one, add a few nodes, connect them, and bind a Wokwi sensor topic to watch the AI layer go live.
            </div>
            <Link
              to="/environments/new"
              className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-[#00E5FF]/50 bg-[#00E5FF]/15 px-3.5 py-2 text-xs font-bold text-[#00E5FF] transition hover:bg-[#00E5FF]/25"
            >
              <Plus size={14} /> Create your first environment
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {envs.map((env) => (
              <div
                key={env.id}
                className="group flex w-full items-center justify-between rounded-lg border border-[#232B3D] bg-[#11151F] px-5 py-4 text-left transition hover:border-[#00E5FF]/50"
              >
                <button
                  onClick={() => navigate(`/dashboard/${env.id}`)}
                  className="flex flex-1 items-center justify-between gap-4 text-left"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[#E8ECF4]">{env.name}</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                          env.status_summary === "all healthy"
                            ? "border-[#00E5FF]/40 text-[#00E5FF]"
                            : env.status_summary === "no nodes yet"
                              ? "border-[#5A6472]/60 text-[#5A6472]"
                              : "border-[#FFB800]/50 text-[#FFB800]"
                        }`}
                      >
                        {env.status_summary}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-[11px] text-[#8A94A8]">
                      <span>{env.industry_template}</span>
                      <span>·</span>
                      <span>{env.node_count} nodes</span>
                      <span>·</span>
                      <span className="flex items-center gap-1">
                        <Clock size={10} />
                        {env.last_active ? new Date(env.last_active + "Z").toLocaleString() : "no live data yet"}
                      </span>
                    </div>
                  </div>
                  <ArrowRight size={16} className="text-[#5A6472] transition group-hover:text-[#00E5FF]" />
                </button>
                <div className="ml-3 flex shrink-0 items-center gap-1">
                  <button
                    onClick={() => navigate(`/environments/new?env=${env.id}`)}
                    title="Edit environment"
                    className="rounded-md border border-[#232B3D] p-1.5 text-[#5A6472] transition hover:border-[#00E5FF]/50 hover:text-[#00E5FF]"
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    onClick={() => openDelete(env)}
                    title="Delete environment"
                    className="rounded-md border border-[#232B3D] p-1.5 text-[#5A6472] transition hover:border-[#FF3B3B]/50 hover:text-[#FF3B3B]"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* delete confirmation */}
      {deletingId !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
          onClick={() => setDeletingId(null)}
        >
          <div
            className="w-full max-w-sm rounded-xl border border-[#232B3D] bg-[#11151F] p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-sm font-bold text-[#E8ECF4]">Delete environment?</h3>
            <p className="mt-2 text-xs leading-relaxed text-[#8A94A8]">
              This permanently removes the environment and all of its nodes,
              edges, sensor bindings and stored live readings. This cannot be
              undone.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setDeletingId(null)}
                className="rounded-md border border-[#232B3D] bg-[#161B27] px-3.5 py-2 text-xs font-semibold text-[#8A94A8] transition hover:text-[#E8ECF4]"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="rounded-md border border-[#FF3B3B]/50 bg-[#FF3B3B]/15 px-3.5 py-2 text-xs font-bold text-[#FF3B3B] transition hover:bg-[#FF3B3B]/25"
              >
                Delete permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
