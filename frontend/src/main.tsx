import React, {
  Suspense,
  lazy,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  ArrowRight,
  Plus,
  Command,
  Orbit,
  Activity,
  FlaskConical,
  Layers3,
  Fingerprint,
  FileText,
  ChevronRight,
  X,
  Check,
  Download,
  Search,
  ShieldCheck,
  Plug,
  Play,
  Square,
  RotateCcw,
  AlertTriangle,
  Menu,
  ExternalLink,
} from "lucide-react";
import type { Mission, Event, Skill, Node, Evidence } from "./types";
import "@fontsource-variable/manrope";
import "@fontsource-variable/dm-sans";
import "./style.css";
const Universe = lazy(() => import("./Universe"));
const emptyNodes: Node[] = [];
const terminal = ["COMPLETED", "FAILED", "CANCELLED"];
const samples = {
  software: {
    objective:
      "Build a functional calculator web application with safe arithmetic, test it, improve the parser, and deliver the verified source.",
    csv: "",
    sources: "",
  },
  data: {
    objective:
      "Analyze this CSV dataset, identify anomalous revenue observations, compare detection strategies, and produce an evidence-backed report.",
    csv: "day,revenue,orders\nMon,100,10\nTue,110,11\nWed,95,9\nThu,102,10\nFri,108,11\nSat,99,10\nSun,105,10\nMon,98,9\nTue,980,12",
    sources: "",
  },
  research: {
    objective:
      "Research battery lifetime evidence, compare sources and investigate contradictions in reported lifetime.",
    csv: "",
    sources: JSON.stringify(
      [
        {
          title: "Laboratory report A",
          text: "This report describes a controlled battery experiment. Battery lifetime = 120 hours. The battery lifetime measurement used a constant load and 20 degree ambient temperature.",
          url: "https://example.org/report-a",
          published_at: "2026-01-10",
        },
        {
          title: "Laboratory report B",
          text: "This report describes a different controlled battery experiment. Battery lifetime = 90 hours. Battery lifetime may change with load and ambient temperature; these conditions were not reported.",
          url: "https://example.org/report-b",
          published_at: "2026-02-10",
        },
      ],
      null,
      2,
    ),
  },
};
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch("/api" + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!r.ok) {
    let detail = "Request failed";
    try {
      const d = await r.json();
      detail =
        typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail);
    } catch {}
    throw new Error(detail);
  }
  return r.json();
}
function Mark() {
  return (
    <span className="mark" aria-hidden="true">
      <i />
      <i />
      <i />
    </span>
  );
}
function State({ value }: { value: string }) {
  return (
    <span className={"state " + value.toLowerCase()}>
      <span />
      {value.replaceAll("_", " ")}
    </span>
  );
}
function App() {
  const [entered, setEntered] = useState(false),
    [missions, setMissions] = useState<Mission[]>([]),
    [selected, setSelected] = useState<string | null>(null),
    [tab, setTab] = useState("Overview"),
    [events, setEvents] = useState<Event[]>([]),
    [skills, setSkills] = useState<Skill[]>([]),
    [integrations, setIntegrations] = useState<
      { id: string; state: string; detail: string; model?: string }[]
    >([]),
    [health, setHealth] = useState<{
      worker: boolean;
      sandbox: boolean;
    } | null>(null);
  const [error, setError] = useState(""),
    [modal, setModal] = useState(false),
    [domain, setDomain] = useState<"software" | "data" | "research">("data"),
    [objective, setObjective] = useState(samples.data.objective),
    [csv, setCsv] = useState(samples.data.csv),
    [sources, setSources] = useState(""),
    [busy, setBusy] = useState(false),
    [node, setNode] = useState<Node | null>(null),
    [query, setQuery] = useState(""),
    [kind, setKind] = useState("all"),
    [mobileNav, setMobileNav] = useState(false);
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement | null;
    const trap = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setModal(false);
        return;
      }
      if (e.key !== "Tab") return;
      const elements = dialog.current?.querySelectorAll<HTMLElement>(
        "button:not(:disabled), input, select, textarea, a[href]",
      );
      if (!elements?.length) return;
      const first = elements[0],
        last = elements[elements.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trap);
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", trap);
      document.body.style.overflow = oldOverflow;
      previous?.focus();
    };
  }, [modal]);
  const mission = missions.find((m) => m.id === selected) || null;
  async function refresh() {
    try {
      const [ms, ss, ii, hh] = await Promise.all([
        api<Mission[]>("/missions"),
        api<Skill[]>("/skills"),
        api<typeof integrations>("/integrations"),
        api<typeof health>("/health"),
      ]);
      setMissions((old) =>
        JSON.stringify(old) === JSON.stringify(ms) ? old : ms,
      );
      setSkills(ss);
      setIntegrations((old) =>
        ii.map((i) => {
          const o = old.find((x) => x.id === i.id);
          return o?.state === "ready" ? o : i;
        }),
      );
      setHealth(hh);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 2500);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!selected) {
      setEvents([]);
      return;
    }
    let disposed = false;
    let cursor = 0;
    setEvents([]);
    const es = new EventSource(`/api/missions/${selected}/events?stream=true`);
    es.onmessage = (e) => {
      const item = JSON.parse(e.data) as Event;
      if (!disposed) {
        cursor = Math.max(cursor, item.seq);
        setEvents((old) =>
          old.some((x) => x.seq === item.seq) ? old : [...old, item],
        );
        refresh();
      }
    };
    es.onerror = () => {
      es.close();
    };
    const poll = setInterval(() => {
      api<Event[]>(`/missions/${selected}/events?after=${cursor}`)
        .then((items) => {
          if (disposed) return;
          for (const i of items) cursor = Math.max(cursor, i.seq);
          setEvents((old) => [
            ...old,
            ...items.filter((i) => !old.some((x) => x.seq === i.seq)),
          ]);
        })
        .catch(() => {});
    }, 2500);
    return () => {
      disposed = true;
      es.close();
      clearInterval(poll);
    };
  }, [selected]);
  const nodes = useMemo<Node[]>(() => {
    if (!mission) return [];
    const root = {
      id: mission.id,
      label: mission.objective,
      kind: "mission",
      detail: `${mission.domain} · ${mission.state}`,
    };
    return [
      root,
      ...mission.plan.map((p) => ({
        id: p.id,
        label: p.label,
        kind: "task",
        detail: p.detail || p.status,
        parent: p.dependencies.length
          ? `task-${p.dependencies[0]}`
          : mission.id,
      })),
      {
        id: "tool-" + mission.domain,
        label: mission.domain + " adapter",
        kind: "tool",
        detail: "Registered bounded workflow tool",
        parent: mission.id,
      },
      ...mission.evidence.map((e) => ({
        id: e.id,
        label: e.title,
        kind: "evidence",
        detail: e.content,
        parent: e.relationships[0]?.target || mission.id,
      })),
      ...mission.decisions.map((d) => ({
        id: d.id,
        label: d.selected_action,
        kind: "decision",
        detail: d.explanation,
        parent: d.evidence_ids[0] || mission.id,
      })),
      ...mission.experiments.map((e) => ({
        id: e.id,
        label: e.hypothesis,
        kind: "experiment",
        detail: JSON.stringify(e.metrics, null, 2),
        parent: mission.id,
      })),
      ...mission.artifacts.map((a) => ({
        id: a.name,
        label: a.name,
        kind: "artifact",
        detail: `${a.size} bytes · SHA256 ${a.sha256}`,
        parent: mission.id,
      })),
      ...(mission.skill_id
        ? [
            {
              id: mission.skill_id,
              label: "Reusable verified strategy",
              kind: "skill",
              detail: "Independently evaluated on each mission",
              parent: mission.id,
            },
          ]
        : []),
    ];
  }, [mission]);
  const filteredNodes = useMemo(
    () => nodes.filter((n) => kind === "all" || n.kind === kind),
    [nodes, kind],
  );
  function chooseExample(d: typeof domain) {
    setDomain(d);
    setObjective(samples[d].objective);
    setCsv(samples[d].csv);
    setSources(samples[d].sources);
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const parsed = domain === "research" ? JSON.parse(sources) : [];
      if (!Array.isArray(parsed))
        throw new Error("Sources must be a JSON array");
      const m = await api<Mission>("/missions", {
        method: "POST",
        body: JSON.stringify({
          objective,
          domain,
          csv_data: domain === "data" ? csv : "",
          sources: parsed,
        }),
      });
      setSelected(m.id);
      setModal(false);
      setTab("Overview");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function action(name: string) {
    if (!mission) return;
    setBusy(true);
    try {
      await api(`/missions/${mission.id}/${name}`, { method: "POST" });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function openMission(m: Mission) {
    setSelected(m.id);
    setTab("Overview");
    setNode(null);
  }
  const launch = () => {
    setEntered(true);
    setModal(true);
  };
  const nav = [
    "Overview",
    "Intelligence graph",
    "Execution theater",
    "Experiments",
    "Skill library",
    "Evidence",
    "Integrations",
  ];
  return (
    <>
      {!entered ? (
        <div className="landing">
          <header className="landing-nav">
            <a className="brand" href="#" aria-label="PRAXIS home">
              <Mark />
              PRAXIS<span>AI</span>
            </a>
            <nav>
              <a href="#method">The architecture</a>
              <a href="#capabilities">Capabilities</a>
              <button className="text-button" onClick={() => setEntered(true)}>
                Open workspace <ArrowUpRight size={16} />
              </button>
            </nav>
          </header>
          <main>
            <section className="hero">
              <div className="hero-copy">
                <div className="eyebrow">
                  <span className="live-dot" /> AUTONOMOUS INTELLIGENCE / V.01
                </div>
                <h1>
                  Intelligence.
                  <br />
                  Put to <em>work.</em>
                </h1>
                <p>
                  From a question to a verified result.
                  <br />
                  One environment to execute, experiment,
                  <br />
                  and evolve—with evidence at every step.
                </p>
                <button
                  className="primary large"
                  onClick={() => setEntered(true)}
                >
                  Enter the workspace <ArrowUpRight size={19} />
                </button>
                <span className="hero-note">Built to show its work.</span>
              </div>
              <div className="hero-object">
                <Suspense
                  fallback={
                    <div className="scene-loading">
                      Assembling intelligence core…
                    </div>
                  }
                >
                  <Universe hero nodes={emptyNodes} />
                </Suspense>
                <div className="object-label">
                  <span>01 / INTELLIGENCE CORE</span>
                  <span>
                    DRAG TO EXPLORE <Orbit size={13} />
                  </span>
                </div>
              </div>
              <div className="hero-bottom">
                <span>UNDERSTAND. EXECUTE. VERIFY. EVOLVE.</span>
                <span>SCROLL TO DISCOVER ↓</span>
              </div>
            </section>
            <section className="method" id="method">
              <div className="eyebrow">A CONTINUOUS LEARNING LOOP</div>
              <h2>
                Answers are a beginning.
                <br />
                <span>Evidence is the difference.</span>
              </h2>
              <div className="method-grid">
                {[
                  [
                    "01",
                    "Understand & plan",
                    "Turn an objective into a bounded, dependency-aware execution plan.",
                  ],
                  [
                    "02",
                    "Execute & observe",
                    "Watch actual tools run. Inspect source data, artifacts, and failures.",
                  ],
                  [
                    "03",
                    "Experiment & verify",
                    "Compare measured strategies. Keep correctness as the acceptance gate.",
                  ],
                  [
                    "04",
                    "Learn & transfer",
                    "Save verified procedures and independently evaluate their next use.",
                  ],
                ].map(([n, title, detail]) => (
                  <article key={n}>
                    <span className="mono muted">{n} /</span>
                    <h3>{title}</h3>
                    <p>{detail}</p>
                  </article>
                ))}
              </div>
            </section>
            <section className="capabilities" id="capabilities">
              <div>
                <div className="eyebrow">THREE DOMAINS. ONE WORKSPACE.</div>
                <h2>
                  Real work.
                  <br />
                  Visible outcomes.
                </h2>
                <p>
                  Purpose-built adapters, explicit boundaries.
                  <br />
                  Explore the workflows that work today.
                </p>
              </div>
              <div>
                {(
                  [
                    [
                      "software",
                      "Software engineering",
                      "Generate, test, revise, and export a calculator web app.",
                    ],
                    [
                      "data",
                      "Data investigation",
                      "Run SQL statistics and anomaly experiments on your CSV.",
                    ],
                    [
                      "research",
                      "Research & experimentation",
                      "Compare supplied sources, trace quotations, retain uncertainty.",
                    ],
                  ] as const
                ).map(([d, title, desc]) => (
                  <button
                    key={d}
                    className="capability-row"
                    onClick={() => {
                      chooseExample(d);
                      launch();
                    }}
                  >
                    <span>
                      <strong>{title}</strong>
                      <small>{desc}</small>
                    </span>
                    <ArrowUpRight />
                  </button>
                ))}
              </div>
            </section>
          </main>
          <footer>
            <a className="brand" href="#">
              <Mark />
              PRAXIS
            </a>
            <span>Intelligence in motion. Evidence at rest.</span>
            <span>RESEARCH PREVIEW · 2026</span>
          </footer>
        </div>
      ) : (
        <div className="workspace">
          <aside className={"sidebar " + (mobileNav ? "mobile-open" : "")}>
            <button className="brand" onClick={() => setEntered(false)}>
              <Mark />
              PRAXIS<span>AI</span>
            </button>
            <div className="workspace-label">
              PERSONAL WORKSPACE <span>⌘ K</span>
            </div>
            <button className="new-mission" onClick={() => setModal(true)}>
              <Plus size={16} /> New mission <span>↗</span>
            </button>
            <nav aria-label="Workspace">
              {nav.map((item, i) => {
                const Icon = [
                  Command,
                  Orbit,
                  Activity,
                  FlaskConical,
                  Layers3,
                  Fingerprint,
                  Plug,
                ][i];
                return (
                  <button
                    key={item}
                    className={tab === item ? "active" : ""}
                    onClick={() => {
                      setTab(item);
                      setMobileNav(false);
                    }}
                  >
                    <Icon size={17} />
                    {item}
                    {item === "Experiments" && (
                      <span>{mission?.experiments.length || 0}</span>
                    )}
                  </button>
                );
              })}
            </nav>
            <div className="recent-head">
              RECENT MISSIONS <span>{missions.length}</span>
            </div>
            <div className="recent-list">
              {missions.slice(0, 7).map((m) => (
                <button
                  key={m.id}
                  className={m.id === selected ? "selected" : ""}
                  onClick={() => openMission(m)}
                >
                  <span className={"mini-dot " + m.state.toLowerCase()} />
                  <span>{m.objective}</span>
                </button>
              ))}
              {!missions.length && (
                <p>
                  No missions yet.
                  <br />
                  Your first question starts here.
                </p>
              )}
            </div>
            <div className="sidebar-bottom">
              <div>
                <ShieldCheck size={16} />
                <span>
                  Local execution environment
                  <small>
                    {health?.worker ? "Worker online" : "Worker unavailable"} ·{" "}
                    {health?.sandbox ? "Sandbox ready" : "Sandbox unavailable"}
                  </small>
                </span>
                <span className={health?.worker ? "live-dot" : "offline-dot"} />
              </div>
              <span className="version">
                PRAXIS RESEARCH PREVIEW <span>v0.1</span>
              </span>
            </div>
          </aside>
          <div className="workspace-main">
            <header className="topbar">
              <button
                className="icon-button mobile-toggle"
                aria-label="Toggle navigation"
                onClick={() => setMobileNav(!mobileNav)}
              >
                <Menu size={20} />
              </button>
              <span className="breadcrumb">
                Workspace <ChevronRight size={14} /> <strong>{tab}</strong>
              </span>
              <div>
                <span className="local-badge">
                  <span
                    className={health?.worker ? "live-dot" : "offline-dot"}
                  />
                  {health?.worker ? "SYSTEM OPERATIONAL" : "CONNECTING"}
                </span>
                <button className="avatar" aria-label="Local user">
                  P
                </button>
              </div>
            </header>
            {error && (
              <div className="error-banner" role="alert">
                <AlertTriangle size={16} />
                {error}
                <button onClick={() => setError("")} aria-label="Dismiss error">
                  <X size={16} />
                </button>
              </div>
            )}
            <main className="content">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    MISSION CONTROL /{" "}
                    {tab === "Overview"
                      ? "01"
                      : String(nav.indexOf(tab) + 1).padStart(2, "0")}
                  </div>
                  <h1>
                    {tab === "Overview"
                      ? mission
                        ? "Mission overview"
                        : "Make the next leap."
                      : tab}
                  </h1>
                  <p>
                    {tab === "Overview"
                      ? "A question. A plan. A result you can stand behind."
                      : "Every observation connected to the work that produced it."}
                  </p>
                </div>
                <button className="primary" onClick={() => setModal(true)}>
                  <Plus size={16} /> New mission
                </button>
              </div>
              {tab === "Overview" && (
                <>
                  {!mission ? (
                    <>
                      <section className="command-card">
                        <div className="command-copy">
                          <span className="eyebrow">
                            YOUR NEXT BREAKTHROUGH STARTS HERE
                          </span>
                          <h2>
                            What do you want
                            <br />
                            to <em>figure out?</em>
                          </h2>
                          <p>
                            Give PRAXIS an objective. Follow the execution.
                            <br />
                            Inspect the evidence. Build on what works.
                          </p>
                          <button
                            className="primary"
                            onClick={() => setModal(true)}
                          >
                            Create your first mission <ArrowUpRight size={17} />
                          </button>
                        </div>
                        <div className="command-art">
                          <Suspense
                            fallback={
                              <div className="scene-loading">
                                Loading scene…
                              </div>
                            }
                          >
                            <Universe hero nodes={emptyNodes} />
                          </Suspense>
                          <span className="mono">
                            BOUNDED AUTONOMY. MEASURABLE OUTCOMES.
                          </span>
                        </div>
                      </section>
                      <div className="stat-row">
                        {[
                          [
                            "MISSIONS EXECUTED",
                            missions.filter((m) => m.state === "COMPLETED")
                              .length,
                            "Verified outcomes",
                          ],
                          [
                            "EVIDENCE RECORDS",
                            missions.reduce((n, m) => n + m.evidence.length, 0),
                            "Traceable observations",
                          ],
                          [
                            "VERIFIED SKILLS",
                            skills.filter((s) => s.verified).length,
                            "Reusable strategies",
                          ],
                          [
                            "ACTIVE MISSIONS",
                            missions.filter((m) => !terminal.includes(m.state))
                              .length,
                            "In the execution loop",
                          ],
                        ].map(([label, value, sub]) => (
                          <article key={label}>
                            <span className="eyebrow">{label}</span>
                            <strong>{value}</strong>
                            <small>{sub}</small>
                          </article>
                        ))}
                      </div>
                      <div className="section-heading">
                        <h2>Start with a direction</h2>
                        <span>
                          SUPPORTED CAPABILITIES <ArrowUpRight size={14} />
                        </span>
                      </div>
                      <div className="workflow-cards">
                        {(
                          [
                            [
                              "software",
                              "01",
                              "Software engineering",
                              "From specification to tested source.",
                              "CODE → TEST → IMPROVE",
                            ],
                            [
                              "data",
                              "02",
                              "Data investigation",
                              "Find the signal. Question the anomaly.",
                              "QUERY → EXPERIMENT → VERIFY",
                            ],
                            [
                              "research",
                              "03",
                              "Research & experimentation",
                              "Trace the sources. Compare the claims.",
                              "RETRIEVE → COMPARE → EXPLAIN",
                            ],
                          ] as const
                        ).map(([d, n, title, desc, loop]) => (
                          <button
                            key={d}
                            onClick={() => {
                              chooseExample(d);
                              setModal(true);
                            }}
                          >
                            <div>
                              <span className="mono">{n} /</span>
                              <ArrowUpRight size={19} />
                            </div>
                            {d === "software" ? (
                              <Command size={30} />
                            ) : d === "data" ? (
                              <Activity size={30} />
                            ) : (
                              <Orbit size={30} />
                            )}
                            <h3>{title}</h3>
                            <p>{desc}</p>
                            <span className="workflow-loop">{loop}</span>
                          </button>
                        ))}
                      </div>
                      <div className="section-heading">
                        <h2>Mission history</h2>
                        <span>{missions.length} TOTAL</span>
                      </div>
                      <MissionList missions={missions} onSelect={openMission} />
                    </>
                  ) : (
                    <>
                      <section className="mission-summary">
                        <div>
                          <State value={mission.state} />
                          <span className="mono muted">
                            {mission.domain.toUpperCase()} /{" "}
                            {mission.id.slice(0, 8)}
                          </span>
                        </div>
                        <h2>{mission.objective}</h2>
                        {mission.error && (
                          <p className="failure-text">{mission.error}</p>
                        )}
                        {mission.result && (
                          <p>
                            {mission.result.summary}
                            <br />
                            <span className="verified-text">
                              <Check size={15} />
                              {mission.result.verification}
                            </span>
                          </p>
                        )}
                        <div className="mission-actions">
                          <button
                            className="secondary"
                            onClick={() => {
                              setSelected(null);
                              setNode(null);
                            }}
                          >
                            All missions
                          </button>
                          {!terminal.includes(mission.state) && (
                            <button
                              className="secondary"
                              disabled={busy}
                              onClick={() => action("cancel")}
                            >
                              <Square size={13} /> Cancel mission
                            </button>
                          )}
                          {mission.state === "FAILED" && (
                            <button
                              className="secondary"
                              disabled={busy || mission.attempts >= 3}
                              onClick={() => action("retry")}
                            >
                              <RotateCcw size={14} /> Retry
                            </button>
                          )}
                        </div>
                      </section>
                      {mission.state === "WAITING_FOR_APPROVAL" && (
                        <section className="approval">
                          <ShieldCheck size={25} />
                          <div>
                            <h3>Your approval is required</h3>
                            <p>
                              Execute generated calculator tests in Docker: no
                              network, read-only source, non-root user, 128 MB
                              memory and bounded runtime. The host has no
                              execution fallback.
                            </p>
                          </div>
                          <button
                            className="primary"
                            disabled={busy}
                            onClick={() => action("approve")}
                          >
                            Approve sandbox execution <ArrowRight size={16} />
                          </button>
                        </section>
                      )}
                      <div className="mission-columns">
                        <section className="panel">
                          <div className="panel-heading">
                            <h3>Execution plan</h3>
                            <span className="mono">
                              {
                                mission.plan.filter(
                                  (p) => p.status === "completed",
                                ).length
                              }
                              /{mission.plan.length} COMPLETE
                            </span>
                          </div>
                          {mission.plan.length ? (
                            mission.plan.map((p, i) => (
                              <div
                                className={"plan-step " + p.status}
                                key={p.id}
                              >
                                <span>
                                  {p.status === "completed" ? (
                                    <Check size={14} />
                                  ) : (
                                    i + 1
                                  )}
                                </span>
                                <div>
                                  <strong>{p.label}</strong>
                                  <small>
                                    {p.detail || "Waiting for dependencies"}
                                  </small>
                                </div>
                                <span className="mono">{p.status}</span>
                              </div>
                            ))
                          ) : (
                            <div className="empty compact">
                              The worker will construct the plan after input
                              validation and any required approval.
                            </div>
                          )}
                        </section>
                        <section className="panel graph-preview">
                          <div className="panel-heading">
                            <h3>Intelligence graph</h3>
                            <button
                              className="text-button"
                              onClick={() => setTab("Intelligence graph")}
                            >
                              Explore <ArrowUpRight size={14} />
                            </button>
                          </div>
                          <Suspense
                            fallback={
                              <div className="scene-loading">
                                Loading graph…
                              </div>
                            }
                          >
                            <Universe
                              nodes={nodes}
                              onSelect={(n) => {
                                setNode(n);
                                setTab("Intelligence graph");
                              }}
                            />
                          </Suspense>
                          <span className="graph-caption">
                            {nodes.length} REAL NODES · DRAG TO ORBIT
                          </span>
                        </section>
                      </div>
                      <section className="panel artifacts">
                        <div className="panel-heading">
                          <h3>Deliverables</h3>
                          <span className="mono">
                            {mission.artifacts.length} ARTIFACTS
                          </span>
                        </div>
                        {mission.artifacts.length ? (
                          mission.artifacts.map((a) => (
                            <a
                              key={a.name}
                              href={`/api/missions/${mission.id}/artifacts/${a.name}`}
                              download
                            >
                              <FileText size={18} />
                              <span>
                                <strong>{a.name}</strong>
                                <small>
                                  {a.size.toLocaleString()} bytes · SHA256{" "}
                                  {a.sha256.slice(0, 16)}…
                                </small>
                              </span>
                              <Download size={17} />
                            </a>
                          ))
                        ) : (
                          <p className="empty compact">
                            Verified outputs appear here as the mission
                            progresses.
                          </p>
                        )}
                      </section>
                      {mission.result && (
                        <div className="limitations">
                          <ShieldCheck size={17} />
                          <span>{mission.result.limitations.join(" · ")}</span>
                        </div>
                      )}
                      <section className="panel">
                        <div className="panel-heading">
                          <h3>Decision inspector</h3>
                          <span className="mono">OBSERVABLE RATIONALE</span>
                        </div>
                        {mission.decisions.map((d) => (
                          <details className="decision" key={d.id}>
                            <summary>
                              {d.selected_action}
                              <ChevronRight size={16} />
                            </summary>
                            <p>{d.explanation}</p>
                            <dl>
                              <dt>Objective</dt>
                              <dd>{d.objective}</dd>
                              <dt>Alternatives</dt>
                              <dd>{d.alternatives.join(" / ")}</dd>
                              <dt>Constraints</dt>
                              <dd>{d.constraints.join(" · ")}</dd>
                              <dt>Execution</dt>
                              <dd>{d.execution_result}</dd>
                              <dt>Verification</dt>
                              <dd>{d.verification_result}</dd>
                              <dt>Linked evidence</dt>
                              <dd>
                                {d.evidence_ids.map((id) => (
                                  <button
                                    className="inline-link"
                                    key={id}
                                    onClick={() => {
                                      setTab("Evidence");
                                      setQuery(id);
                                    }}
                                  >
                                    {id.slice(0, 8)}
                                  </button>
                                ))}
                              </dd>
                              <dt>Uncertainty</dt>
                              <dd>{d.uncertainty}</dd>
                            </dl>
                          </details>
                        ))}
                        {!mission.decisions.length && (
                          <p className="empty compact">
                            Decisions will link measured evidence, alternatives,
                            and uncertainty.
                          </p>
                        )}
                      </section>
                    </>
                  )}
                </>
              )}
              {tab === "Intelligence graph" && (
                <>
                  {mission ? (
                    <>
                      <div className="graph-toolbar">
                        <span>
                          <Orbit size={16} /> {filteredNodes.length} nodes
                        </span>
                        <label>
                          Filter{" "}
                          <select
                            value={kind}
                            onChange={(e) => setKind(e.target.value)}
                          >
                            {[
                              "all",
                              "mission",
                              "task",
                              "tool",
                              "evidence",
                              "decision",
                              "experiment",
                              "artifact",
                              "skill",
                            ].map((k) => (
                              <option key={k}>{k}</option>
                            ))}
                          </select>
                        </label>
                        <span className="muted">
                          Drag to orbit · Scroll to zoom · Click to inspect
                        </span>
                      </div>
                      <div className="graph-layout">
                        <section className="panel full-graph">
                          <Suspense
                            fallback={
                              <div className="scene-loading">
                                Loading graph…
                              </div>
                            }
                          >
                            <Universe
                              nodes={filteredNodes}
                              onSelect={setNode}
                            />
                          </Suspense>
                        </section>
                        <section className="panel node-inspector">
                          <div className="panel-heading">
                            <h3>{node ? "Node inspector" : "Select a node"}</h3>
                          </div>
                          {node ? (
                            <>
                              <span className="eyebrow">{node.kind}</span>
                              <h3>{node.label}</h3>
                              <pre>{node.detail}</pre>
                            </>
                          ) : (
                            <p>
                              Explore the graph or choose an item below.
                              Connections reflect task dependencies and evidence
                              provenance.
                            </p>
                          )}
                          <div className="node-list">
                            {filteredNodes.map((n) => (
                              <button
                                className={node?.id === n.id ? "selected" : ""}
                                key={n.id}
                                onClick={() => setNode(n)}
                              >
                                <span className={"node-dot " + n.kind} />
                                <span>{n.label}</span>
                                <ChevronRight size={13} />
                              </button>
                            ))}
                          </div>
                        </section>
                      </div>
                    </>
                  ) : (
                    <Empty
                      title="An intelligence universe, grounded in your work."
                      text="Select a mission or start a new one to explore its execution graph."
                      onClick={() => setModal(true)}
                    />
                  )}
                </>
              )}
              {tab === "Execution theater" && (
                <section className="panel">
                  <div className="panel-heading">
                    <h3>Live execution stream</h3>
                    <span className="mono">
                      {mission ? (
                        <State value={mission.state} />
                      ) : (
                        "NO MISSION SELECTED"
                      )}
                    </span>
                  </div>
                  {events.length ? (
                    <ol className="event-list">
                      {events.map((e) => (
                        <li key={e.seq} className={e.kind}>
                          <span className="event-time">
                            {new Date(e.at).toLocaleTimeString()}
                          </span>
                          <span className="event-dot" />
                          <div>
                            <span className="eyebrow">
                              {e.kind} / {e.seq}
                            </span>
                            <p>{e.message}</p>
                            {Object.keys(e.data).length > 0 && (
                              <details>
                                <summary>Inspect event payload</summary>
                                <pre>{JSON.stringify(e.data, null, 2)}</pre>
                              </details>
                            )}
                          </div>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="empty">
                      No execution events. Select a mission to follow its
                      durable event stream.
                    </p>
                  )}
                </section>
              )}
              {tab === "Experiments" && (
                <>
                  {mission?.experiments.length ? (
                    mission.experiments.map((e, i) => (
                      <section className="panel experiment" key={e.id}>
                        <div className="panel-heading">
                          <span className="eyebrow">
                            EXPERIMENT {String(i + 1).padStart(2, "0")}
                          </span>
                          <State value={e.accepted ? "COMPLETED" : "FAILED"} />
                        </div>
                        <h2>{e.hypothesis}</h2>
                        <div className="experiment-comparison">
                          <div>
                            <span className="eyebrow">BASELINE</span>
                            <h3>{e.baseline}</h3>
                          </div>
                          <ArrowRight />
                          <div>
                            <span className="eyebrow">CANDIDATE</span>
                            <h3>{e.candidates.join(", ")}</h3>
                          </div>
                        </div>
                        <Metrics metrics={e.metrics} />
                        <dl>
                          <dt>Procedure</dt>
                          <dd>{e.procedure}</dd>
                          <dt>Acceptance criteria</dt>
                          <dd>{e.acceptance_criteria}</dd>
                          <dt>Diagnosis & limits</dt>
                          <dd>{e.failure_analysis}</dd>
                          <dt>Verification</dt>
                          <dd>{e.verification_status}</dd>
                        </dl>
                      </section>
                    ))
                  ) : (
                    <Empty
                      title="Improvement is an experiment."
                      text="Run a mission to compare strategies against actual measurements and correctness checks."
                      onClick={() => setModal(true)}
                    />
                  )}
                </>
              )}
              {tab === "Skill library" && (
                <>
                  {skills.length ? (
                    <div className="skill-grid">
                      {skills.map((s) => (
                        <section className="panel skill" key={s.id}>
                          <div className="panel-heading">
                            <Layers3 size={21} />
                            <span className="tag">
                              v{s.version} ·{" "}
                              {s.verified ? "VERIFIED" : "UNVERIFIED"}
                            </span>
                          </div>
                          <span className="eyebrow">{s.domain}</span>
                          <h2>{s.name}</h2>
                          <p>{s.purpose}</p>
                          <dl>
                            <dt>Preconditions</dt>
                            <dd>{s.preconditions}</dd>
                            <dt>Tests</dt>
                            <dd>{s.tests.join(" · ")}</dd>
                            <dt>Known limitations</dt>
                            <dd>{s.limitations}</dd>
                          </dl>
                          <details>
                            <summary>
                              Structured procedure & version history
                            </summary>
                            <pre>
                              {JSON.stringify(
                                { procedure: s.procedure, history: s.history },
                                null,
                                2,
                              )}
                            </pre>
                          </details>
                          <div className="skill-evaluations">
                            <span className="eyebrow">
                              {s.evaluations.length} INDEPENDENT MISSION
                              EVALUATIONS
                            </span>
                            {s.evaluations.map((ev, i) => (
                              <button
                                key={i}
                                onClick={() => {
                                  setSelected(ev.mission_id);
                                  setTab("Overview");
                                }}
                              >
                                <span>
                                  {ev.passed ? (
                                    <Check size={15} />
                                  ) : (
                                    <X size={15} />
                                  )}{" "}
                                  {i === 0
                                    ? "Initial validation"
                                    : "Transfer evaluation"}
                                </span>
                                <span className="mono">
                                  {ev.mission_id.slice(0, 8)} ↗
                                </span>
                              </button>
                            ))}
                          </div>
                        </section>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="A library built by doing."
                      text="Completed software and data workflows persist verified strategies. Run a second mission to test transfer independently."
                      onClick={() => setModal(true)}
                    />
                  )}
                </>
              )}
              {tab === "Evidence" && (
                <>
                  <div className="evidence-search">
                    <Search size={17} />
                    <input
                      aria-label="Search evidence"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search evidence, source text, or record ID…"
                    />
                  </div>
                  {missions
                    .flatMap((m) =>
                      m.evidence.map((e) => ({ ...e, mission_id: m.id })),
                    )
                    .filter((e) =>
                      `${e.id} ${e.title} ${e.content}`
                        .toLowerCase()
                        .includes(query.toLowerCase()),
                    )
                    .map((e) => (
                      <EvidenceCard
                        key={e.id}
                        evidence={e}
                        onMission={() => {
                          setSelected(e.mission_id);
                          setTab("Overview");
                        }}
                      />
                    ))}
                  {!missions.some((m) => m.evidence.length) && (
                    <Empty
                      title="Every finding has a source."
                      text="Run a mission to build a searchable record of source provenance, calculations, and verification."
                      onClick={() => setModal(true)}
                    />
                  )}
                </>
              )}
              {tab === "Integrations" && (
                <>
                  <div className="integration-notice">
                    <ShieldCheck size={20} />
                    <p>
                      Provider keys stay on the server. External inference can
                      suggest plans; the execution engine uses bounded
                      capability adapters. A configured integration is not a
                      verified integration.
                    </p>
                  </div>
                  <div className="integration-grid">
                    {integrations.map((i) => (
                      <section className="panel integration" key={i.id}>
                        <Plug size={24} />
                        <span className="tag">
                          {i.state.replaceAll("_", " ")}
                        </span>
                        <h2>
                          {{
                            nvidia: "NVIDIA Nemotron",
                            nightshift: "Meterless Nightshift",
                            meterless_agent_engine: "Meterless Agent Engine",
                            zetaris: "Zetaris",
                          }[i.id] || i.id}
                        </h2>
                        {i.model && <code>{i.model}</code>}
                        <p>{i.detail}</p>
                        {["nvidia", "nightshift"].includes(i.id) && (
                          <button
                            className="secondary"
                            onClick={async () => {
                              try {
                                const result = await api<{
                                  state: string;
                                  detail: string;
                                }>(`/integrations/${i.id}/health`, {
                                  method: "POST",
                                });
                                setIntegrations((old) =>
                                  old.map((x) =>
                                    x.id === i.id ? { ...x, ...result } : x,
                                  ),
                                );
                              } catch (e) {
                                setError((e as Error).message);
                              }
                            }}
                          >
                            Run real health check <ArrowUpRight size={14} />
                          </button>
                        )}
                      </section>
                    ))}
                  </div>
                </>
              )}
            </main>
            <footer className="workspace-footer">
              <span>
                <Mark /> EVIDENCE-GROUNDED INTELLIGENCE
              </span>
              <span>
                Local workspace · No external actions without permission
              </span>
            </footer>
          </div>
        </div>
      )}
      {modal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setModal(false);
          }}
        >
          <section
            ref={dialog}
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="mission-title"
            onKeyDown={(e) => {
              if (e.key === "Escape") setModal(false);
            }}
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">START SOMETHING MEASURABLE</span>
                <h2 id="mission-title">A new mission.</h2>
              </div>
              <button
                className="icon-button"
                aria-label="Close dialog"
                onClick={() => setModal(false)}
              >
                <X />
              </button>
            </div>
            <form onSubmit={submit}>
              <label htmlFor="domain">Capability</label>
              <select
                id="domain"
                value={domain}
                onChange={(e) => chooseExample(e.target.value as typeof domain)}
              >
                <option value="data">Data investigation — CSV</option>
                <option value="software">
                  Software — calculator application
                </option>
                <option value="research">Research — supplied documents</option>
              </select>
              <label htmlFor="objective">What do you want to accomplish?</label>
              <textarea
                autoFocus
                id="objective"
                rows={3}
                required
                minLength={10}
                maxLength={4000}
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              />
              {domain === "data" && (
                <>
                  <div className="input-heading">
                    <label htmlFor="csv">Dataset (CSV, 5–10,000 rows)</label>
                    <label className="file-label">
                      Import CSV
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            if (file.size > 1000000) {
                              setError("CSV exceeds 1 MB");
                              return;
                            }
                            setCsv(await file.text());
                          }
                        }}
                      />
                    </label>
                  </div>
                  <textarea
                    id="csv"
                    className="code-input"
                    rows={7}
                    required
                    value={csv}
                    onChange={(e) => setCsv(e.target.value)}
                  />
                </>
              )}
              {domain === "research" && (
                <>
                  <label htmlFor="sources">
                    Sources (JSON array with title, text, optional url and
                    published_at)
                  </label>
                  <textarea
                    id="sources"
                    className="code-input"
                    rows={8}
                    required
                    value={sources}
                    onChange={(e) => setSources(e.target.value)}
                  />
                  <p className="form-note">
                    Example sources are illustrative supplied documents. URLs
                    are provenance labels and are not fetched.
                  </p>
                </>
              )}
              {domain === "software" && (
                <p className="form-note">
                  Supported today: arithmetic calculator web applications
                  generated with a bounded template strategy. Testing requires
                  your explicit approval and a local Docker sandbox.
                </p>
              )}
              <div className="form-footer">
                <span>
                  <ShieldCheck size={15} /> Local, bounded execution
                </span>
                <button className="primary" disabled={busy} type="submit">
                  {busy ? "Creating…" : "Launch mission"}{" "}
                  <ArrowUpRight size={16} />
                </button>
              </div>
              {error && (
                <p role="alert" className="failure-text">
                  {error}
                </p>
              )}
            </form>
          </section>
        </div>
      )}
    </>
  );
}
function MissionList({
  missions,
  onSelect,
}: {
  missions: Mission[];
  onSelect: (m: Mission) => void;
}) {
  return (
    <section className="mission-table">
      {missions.length ? (
        missions.map((m) => (
          <button key={m.id} onClick={() => onSelect(m)}>
            <span className="table-icon">
              {m.domain === "data" ? (
                <Activity size={18} />
              ) : m.domain === "research" ? (
                <Orbit size={18} />
              ) : (
                <Command size={18} />
              )}
            </span>
            <span>
              <strong>{m.objective}</strong>
              <small>
                {m.domain} · {new Date(m.created_at).toLocaleDateString()}
              </small>
            </span>
            <State value={m.state} />
            <ArrowUpRight size={16} />
          </button>
        ))
      ) : (
        <div className="history-empty">
          <span className="empty-icon">
            <Activity size={21} />
          </span>
          <span>
            Your mission history is a blank canvas.
            <small>Completed work and verified results will live here.</small>
          </span>
          <span className="mono">READY WHEN YOU ARE ↗</span>
        </div>
      )}
    </section>
  );
}
function Empty({
  title,
  text,
  onClick,
}: {
  title: string;
  text: string;
  onClick: () => void;
}) {
  return (
    <section className="empty-state">
      <Orbit size={36} />
      <h2>{title}</h2>
      <p>{text}</p>
      <button className="primary" onClick={onClick}>
        New mission <Plus size={16} />
      </button>
    </section>
  );
}
function Metrics({ metrics }: { metrics: Record<string, unknown> }) {
  return (
    <div className="metrics">
      {Object.entries(metrics).map(([key, value]) => (
        <div key={key}>
          <span className="eyebrow">{key.replaceAll("_", " ")}</span>
          {typeof value === "object" ? (
            <pre>{JSON.stringify(value, null, 2)}</pre>
          ) : (
            <strong>{String(value)}</strong>
          )}
        </div>
      ))}
    </div>
  );
}
function EvidenceCard({
  evidence: e,
  onMission,
}: {
  evidence: Evidence;
  onMission: () => void;
}) {
  return (
    <section className="panel evidence-card">
      <div className="panel-heading">
        <span className="eyebrow">SOURCE / {e.id.slice(0, 8)}</span>
        <button className="text-button" onClick={onMission}>
          View mission <ArrowUpRight size={14} />
        </button>
      </div>
      <h3>{e.title}</h3>
      <div className="source-meta">
        <code>{e.locator}</code>
        <time>{new Date(e.observed_at).toLocaleString()}</time>
      </div>
      <details>
        <summary>Inspect source content</summary>
        <pre>{e.content}</pre>
      </details>
      <p className="muted">{e.uncertainty}</p>
      {e.relationships.map((r, i) => (
        <span key={i} className="relationship">
          {r.type} → {r.target.slice(0, 8)}
        </span>
      ))}
      <p className="hash">SHA256 {e.sha256}</p>
    </section>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
