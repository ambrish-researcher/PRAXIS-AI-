import {
  ArrowRight,
  BrainCircuit,
  Check,
  ChevronRight,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { Mission } from "./types";
export default function MissionIntelligence({ mission }: { mission: Mission }) {
  const specification = mission.compiled_plan;
  if (!specification) return null;
  const graph = mission.execution_graph || [];
  const completed = graph.filter((t) => t.status === "completed").length;
  const source = mission.planner?.source || "offline";
  return (
    <section className="intelligence-brief panel">
      <div className="intelligence-heading">
        <div>
          <span className="eyebrow">
            <BrainCircuit size={14} /> MISSION INTELLIGENCE
          </span>
          <h3>{specification.objective_summary}</h3>
        </div>
        <span
          className={
            "planner-badge " + (source === "offline" ? "" : "model-backed")
          }
        >
          <Sparkles size={13} />
          {source === "offline"
            ? "OFFLINE PLANNER"
            : source.toUpperCase() + " PLANNER"}
        </span>
      </div>
      <div className="intelligence-body">
        <div className="tool-chain" aria-label="Validated tool execution graph">
          {graph.map((task, i) => (
            <div className="tool-chain-item" key={task.id}>
              {i > 0 && <ArrowRight size={14} />}
              <article className={task.status}>
                <span className="eyebrow">{task.id}</span>
                <strong>
                  {task.status === "completed" ? (
                    <Check size={14} />
                  ) : (
                    <span className="task-indicator" />
                  )}
                  {task.tool}
                </strong>
                <small>{task.purpose}</small>
                <span className="tool-dependencies">
                  {task.depends_on.length
                    ? "Requires " + task.depends_on.join(", ")
                    : "Independent input"}
                </span>
              </article>
            </div>
          ))}
        </div>
        <div className="mission-contract">
          <span className="eyebrow">
            <ShieldCheck size={13} /> VALIDATED EXECUTION CONTRACT
          </span>
          <ul>
            {specification.success_criteria.map((criterion, i) => (
              <li key={i}>
                <ChevronRight size={12} />
                {criterion}
              </li>
            ))}
          </ul>
          <div className="mission-progress">
            <span
              style={{
                width: `${graph.length ? (completed / graph.length) * 100 : 0}%`,
              }}
            />
          </div>
          <p>
            {completed} / {graph.length} tools verified{" "}
            <span>
              {mission.planner?.model ||
                "Registered tools · fixed independent verifiers"}
            </span>
          </p>
          {mission.planner?.detail && (
            <p className="planner-detail">{mission.planner.detail}</p>
          )}
          <p className="planner-note">
            Model plans select approved capabilities. Results come from actual
            execution and independent tool checks.
          </p>
        </div>
      </div>
    </section>
  );
}
