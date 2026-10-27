export type Evidence = {
  id: string;
  title: string;
  content: string;
  locator: string;
  observed_at: string;
  sha256: string;
  uncertainty: string;
  relationships: { type: string; target: string }[];
};
export type Decision = {
  id: string;
  objective: string;
  selected_action: string;
  alternatives: string[];
  explanation: string;
  constraints: string[];
  evidence_ids: string[];
  execution_result: string;
  verification_result: string;
  uncertainty: string;
};
export type Experiment = {
  id: string;
  hypothesis: string;
  baseline: string;
  candidates: string[];
  procedure: string;
  metrics: Record<string, unknown>;
  accepted: boolean;
  acceptance_criteria: string;
  failure_analysis: string;
  verification_status: string;
};
export type Mission = {
  id: string;
  objective: string;
  domain: string;
  state: string;
  created_at: string;
  plan: {
    id: string;
    label: string;
    status: string;
    dependencies: number[];
    detail?: string;
  }[];
  evidence: Evidence[];
  decisions: Decision[];
  experiments: Experiment[];
  artifacts: { name: string; kind: string; size: number; sha256: string }[];
  result: null | {
    summary: string;
    verification: string;
    limitations: string[];
  };
  error: string | null;
  skill_id: string | null;
  attempts: number;
  planning_mode?: string;
  planner?: {
    source: string;
    model?: string;
    detail?: string;
    latency_ms?: number;
    attempts?: number;
  };
  compiled_plan?: {
    objective_summary: string;
    success_criteria: string[];
    constraints: string[];
    tasks: {
      id: string;
      tool: string;
      purpose: string;
      depends_on: string[];
      options: Record<string, unknown>;
    }[];
  };
  execution_graph?: {
    id: string;
    tool: string;
    purpose: string;
    depends_on: string[];
    status: string;
  }[];
  replan_count?: number;
};
export type Event = {
  seq: number;
  at: string;
  kind: string;
  message: string;
  data: Record<string, unknown>;
};
export type Skill = {
  id: string;
  name: string;
  domain: string;
  version: number;
  purpose: string;
  procedure: Record<string, unknown>;
  preconditions: string;
  tests: string[];
  verified: boolean;
  limitations: string;
  evaluations: { mission_id: string; passed: boolean; at: string }[];
  history: { version: number; action: string; at: string }[];
};
export type Node = {
  id: string;
  label: string;
  kind: string;
  detail: string;
  parent?: string;
  status?: string;
};
