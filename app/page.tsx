import { useEffect, useMemo, useState } from "react";
import logo from "../assets/one-plus-i.png";

type Level = "Beginner" | "Intermediate" | "Advanced";
type Tab = "learn" | "lab" | "checkpoint";
type Checkpoint = {
  question: string;
  options: string[];
  answer: number;
};
type Lesson = {
  id: string;
  level: Level;
  step: string;
  title: string;
  description: string;
  time: string;
  outcome: string;
  summary: string;
  exercise: string;
  failures: string[];
  notebook: string;
  refs: string[];
  code: string;
  checkpoints: Checkpoint[];
};

const base =
  "https://github.com/mahsa-teimourikia/gen-ai-guardrails/blob/main/";
const progressKey = "guardrails-field-guide-progress-v1";

const lessons: Lesson[] = [
  {
    id: "b1",
    level: "Beginner",
    step: "01",
    title: "What are GenAI guardrails?",
    description:
      "Define the operating envelope and place controls at input, retrieval, policy, execution, output, and operational boundaries.",
    time: "45–60 min",
    outcome:
      "Classify guardrail decisions, compare deterministic and model-based controls, and explain why authorization must live at an application boundary.",
    summary:
      "Guardrails constrain, validate, observe, and recover AI behavior. The lab uses an internal HR/IT support assistant to make each boundary observable, from tenant-filtered retrieval to approved payroll actions and audit-safe decisions.",
    exercise:
      "Run the frozen HR/IT examples, compare a detector outage with a policy decision, and reproduce the ordering failure where a side effect occurs before authorization.",
    failures: [
      "Trusting a refusal prompt as authorization",
      "Letting a relevant document cross a tenant boundary",
      "Running a detector after a sensitive side effect",
      "Logging raw PII instead of audit-safe evidence",
    ],
    notebook: "curriculum/beginner/01-what-are-guardrails/what_are_guardrails.ipynb",
    refs: [
      "curriculum/beginner/01-what-are-guardrails/README.md#the-operating-envelope-model",
      "curriculum/beginner/01-what-are-guardrails/README.md#execution-rails",
    ],
    code: `operating_envelope = {
    "inputs": allowed_inputs,
    "capabilities": permitted_tools,
    "outputs": acceptable_outputs,
    "side_effects": safe_actions,
}
decision = policy.evaluate(request, evidence)`,
    checkpoints: [
      {
        question: "Which boundary can enforce a payroll approval?",
        options: ["Execution rail", "A system prompt alone", "A decorative UI label"],
        answer: 0,
      },
      {
        question: "What belongs in an operating envelope?",
        options: ["Allowed inputs", "Permitted capabilities", "A promise that the model is safe"],
        answer: 0,
      },
      {
        question: "Which evidence makes a decision auditable?",
        options: ["Reason codes and a trace ID", "Only the final answer", "An unversioned prompt"],
        answer: 0,
      },
    ],
  },
  {
    id: "b2",
    level: "Beginner",
    step: "02",
    title: "The guardrail lifecycle",
    description:
      "Move from policy definition through trust boundaries, observation, decisions, constrained execution, recovery, measurement, and improvement.",
    time: "45–60 min",
    outcome:
      "Compare shadow, alert, and enforcement modes and measure how policy v2 changes decisions without losing evidence.",
    summary:
      "The lifecycle lab turns one HR/IT policy into a deterministic pipeline. Frozen traffic shows how a request moves through shadow, alert, and enforcement modes, then measures the effect of a policy change.",
    exercise:
      "Change one policy or threshold, run all three modes, and compare alerts, blocks, false positives, and false negatives. Add the failure as a regression case.",
    failures: [
      "Changing policy without versioned evidence",
      "Measuring only the final answer",
      "Skipping recovery and reconciliation",
      "Enforcing globally without a shadow baseline",
    ],
    notebook: "curriculum/beginner/02-guardrail-lifecycle/guardrail_lifecycle.ipynb",
    refs: [
      "curriculum/beginner/02-guardrail-lifecycle/README.md#8-measure",
      "curriculum/beginner/02-guardrail-lifecycle/README.md#a-staged-rollout",
    ],
    code: `for mode in ("shadow", "alert", "enforce"):
    decisions = run_policy_v2(traffic, mode=mode)
    metrics = measure(decisions)
    print(mode, metrics["blocked"], metrics["false_negatives"])`,
    checkpoints: [
      {
        question: "What should a shadow run do?",
        options: ["Observe decisions without blocking", "Delete the trace", "Disable policy versioning"],
        answer: 0,
      },
      {
        question: "Why measure numerators and denominators?",
        options: ["Rates need their population defined", "It makes every metric perfect", "It replaces regression cases"],
        answer: 0,
      },
      {
        question: "What is policy v2 evidence?",
        options: ["A versioned decision record", "A hidden prompt edit", "A screenshot without inputs"],
        answer: 0,
      },
    ],
  },
  {
    id: "i1",
    level: "Intermediate",
    step: "01",
    title: "Best practices for production guardrails",
    description:
      "Turn risk registers and policy boundaries into defense-in-depth controls with budgets, circuit breakers, review, and release gates.",
    time: "45–60 min",
    outcome:
      "Build an evidence-backed release checklist and distinguish a safety-critical change from ordinary prompt copy.",
    summary:
      "Production guardrails need owners, explicit trust boundaries, layered checks, safe failure, versioned artifacts, and an incident playbook. The runnable lab exercises budgets, circuit breakers, detector failure, change control, and release evidence.",
    exercise:
      "Repair the failing manifest and adversarial checks, trip a budget or circuit breaker, and explain why a benchmark score alone cannot release a safety-critical change.",
    failures: [
      "Relying on correlated model judges",
      "Allowing prompt text to grant permissions",
      "Running without budgets or a kill switch",
      "Promoting a change without regression evidence",
    ],
    notebook: "curriculum/intermediate/01-best-practices/best_practices.ipynb",
    refs: [
      "curriculum/intermediate/01-best-practices/README.md#11-use-budgets-and-circuit-breakers",
      "curriculum/intermediate/01-best-practices/README.md#release-checklist",
    ],
    code: `if budget.exhausted() or circuit_breaker.open:
    return Decision.BLOCK
if not release_gate.all_required_checks_pass():
    return Decision.ESCALATE`,
    checkpoints: [
      {
        question: "Which controls bound production operations?",
        options: ["Budgets", "Circuit breakers", "Unbounded retries"],
        answer: 0,
      },
      {
        question: "What needs review?",
        options: ["Safety-critical threshold changes", "Only spelling changes", "Any raw secret in a trace"],
        answer: 0,
      },
      {
        question: "What makes a release gate useful?",
        options: ["Evidence from every required evaluation layer", "One average benchmark", "An undocumented exception"],
        answer: 0,
      },
    ],
  },
  {
    id: "i2",
    level: "Intermediate",
    step: "02",
    title: "Scenario cookbook",
    description:
      "Apply typed extraction, approval-gated writes, idempotent execution, reconciliation, and moderation thresholds to concrete scenarios.",
    time: "45–60 min",
    outcome:
      "Route malformed or low-confidence records safely and constrain an agent before and after an external write.",
    summary:
      "The cookbook keeps policy close to consequences: extraction invariants reject malformed claims, the agent previews and approves writes, and moderation uses frozen scores as a policy signal rather than a live classifier.",
    exercise:
      "Add an extraction candidate with a broken invariant, enable the agent kill switch, and change one moderation threshold while observing the per-category false-positive and false-negative tests.",
    failures: [
      "Accepting unknown extraction fields",
      "Writing before approval or budget checks",
      "Retrying without an idempotency key",
      "Treating moderation scores as authorization",
    ],
    notebook: "curriculum/intermediate/02-scenario-cookbook/scenario_cookbook.ipynb",
    refs: [
      "curriculum/intermediate/02-scenario-cookbook/README.md#data-extraction-pipeline",
      "curriculum/intermediate/02-scenario-cookbook/README.md#agent-that-writes-to-external-systems",
    ],
    code: `candidate = ExpenseClaimV2.model_validate(raw)
if not invariants_hold(candidate):
    return escalate(candidate)
action = approve_gate(preview(candidate))
return executor.run(action, idempotency_key=action.key)`,
    checkpoints: [
      {
        question: "What does typed extraction preserve?",
        options: ["Schema and cross-field invariants", "Unknown fields silently", "A guarantee that source text is true"],
        answer: 0,
      },
      {
        question: "What prevents a duplicate external write?",
        options: ["Idempotency", "A longer system prompt", "Ignoring the receipt"],
        answer: 0,
      },
      {
        question: "What can a moderation threshold decide?",
        options: ["Allow, transform, escalate, or block", "Grant a user a new role", "Replace authorization"],
        answer: 0,
      },
    ],
  },
  {
    id: "a1",
    level: "Advanced",
    step: "01",
    title: "Evaluation and red teaming",
    description:
      "Build taxonomies, expose metric numerators and denominators, calibrate judges, run authorized probes, and gate releases.",
    time: "45–60 min",
    outcome:
      "Explain blocked attempts versus unauthorized actions, choose thresholds with expected loss, and convert red-team findings into regression cases.",
    summary:
      "Evaluation is evidence, not a single score. This lab slices frozen cases by policy, language, tenant, and risk tier, calibrates deterministic/state/judge/human graders, and compares shadow and canary decisions before release.",
    exercise:
      "Add a multilingual adversarial case, inspect each numerator and denominator, compare judge labels with the human reference, and sweep thresholds using expected-loss costs.",
    failures: [
      "Optimizing only the overall average",
      "Calling blocked attempts unauthorized actions",
      "Using an uncalibrated judge as ground truth",
      "Choosing thresholds without false-negative cost",
    ],
    notebook: "curriculum/advanced/01-evaluation-and-red-teaming/evaluation_and_red_teaming.ipynb",
    refs: [
      "curriculum/advanced/01-evaluation-and-red-teaming/README.md#metrics",
      "curriculum/advanced/01-evaluation-and-red-teaming/README.md#threshold-selection",
    ],
    code: `expected_loss = (
    false_negative_cost + false_positive_cost + friction_cost
)
release = bypasses == 0 and unauthorized_actions == 0`,
    checkpoints: [
      {
        question: "What does a denominator tell you?",
        options: ["Which cases a rate covers", "That a detector is unbiased", "Which prompt will bypass policy"],
        answer: 0,
      },
      {
        question: "How should a judge be calibrated?",
        options: ["Against blind human-labeled examples", "By its confidence alone", "By deleting disagreements"],
        answer: 0,
      },
      {
        question: "What belongs in expected loss?",
        options: ["False-negative cost", "False-positive friction", "Only raw accuracy"],
        answer: 0,
      },
    ],
  },
  {
    id: "a2",
    level: "Advanced",
    step: "02",
    title: "Security and privacy",
    description:
      "Keep claims untrusted, bind tools to trusted identity, minimize PII, protect secrets, verify artifacts, and preserve incident evidence.",
    time: "45–60 min",
    outcome:
      "Show that execution-time authorization blocks stale plans, detector misses cannot grant capability, and audit evidence detects tampering.",
    summary:
      "The security lab treats the HR/IT assistant as an application security system. It combines trusted state, provenance, PII vault controls, redaction, hash-chained audit logs, artifact verification, evaluation access, and incident response.",
    exercise:
      "Revoke a role after plan check, try an authorized high-score escalation, deny re-identification with the wrong purpose, tamper with an audit event, and inspect the incident bundle.",
    failures: [
      "Letting retrieved claims change authority",
      "Using an injection score as a permission",
      "Sending raw PII across an external boundary",
      "Accepting an artifact or log after tampering",
    ],
    notebook: "curriculum/advanced/02-security-and-privacy/security_and_privacy.ipynb",
    refs: [
      "curriculum/advanced/02-security-and-privacy/README.md#authorization-is-not-a-guardrail-score",
      "curriculum/advanced/02-security-and-privacy/README.md#incident-response",
    ],
    code: `planned = plan_check(plan, session, trusted_state, capabilities)
trusted_state.revoked_sessions.add(session.session_id)
executed = execute(plan, session, trusted_state, capabilities, score, threshold)
assert executed.reason_codes == ["session_revoked"]`,
    checkpoints: [
      {
        question: "When must authorization run?",
        options: ["At execution time", "Only when the plan is drafted", "After the side effect"],
        answer: 0,
      },
      {
        question: "What should cross an external boundary?",
        options: ["Masked text", "Raw token values", "An unverified secret fragment"],
        answer: 0,
      },
      {
        question: "What detects an altered audit event?",
        options: ["Hash-chain verification", "A higher detector score", "A longer prompt"],
        answer: 0,
      },
    ],
  },
  {
    id: "a3",
    level: "Advanced",
    step: "03",
    title: "Agent and tool capstone",
    description:
      "Bound a new-hire onboarding agent with dynamic capabilities, approvals, budgets, receipts, verification, and reconciliation.",
    time: "60–90 min",
    outcome:
      "Run frozen trajectories for two tenants and prove zero unauthorized actions with complete audit evidence and a passing release gate.",
    summary:
      "The capstone is deliberately not a live planner. Frozen trajectories make every proposed step inspectable while Pydantic argument validation, phase-scoped exposure, execution-time authorization, and trusted resources constrain side effects.",
    exercise:
      "Approve the pending fingerprint, replay an existing receipt, trigger budget and loop terminals, block tool-output instructions, and tamper with approvals to watch the evidence-based gate fail.",
    failures: [
      "Exposing a notify tool before provisioning",
      "Consuming side-effect budget before replay detection",
      "Trusting tool-output instructions as plan steps",
      "Treating receipts as proof without verification",
    ],
    notebook: "curriculum/advanced/03-agent-tool-capstone/agent_tool_capstone.ipynb",
    refs: [
      "curriculum/advanced/03-agent-tool-capstone/README.md#dynamic-capability-exposure",
      "curriculum/advanced/03-agent-tool-capstone/README.md#trajectory-evaluation-and-capstone-gate",
    ],
    code: `capabilities = exposed_capabilities(session, state, phase, tools)
decision = run_trajectory(trajectory, session, state, capabilities, budget)
evidence = audit_side_effects(results, state, capabilities)`,
    checkpoints: [
      {
        question: "What can expose a side-effect tool?",
        options: ["Trusted role and current phase", "A tool-output instruction", "A matching tool name alone"],
        answer: 0,
      },
      {
        question: "What makes a side effect replay-safe?",
        options: ["A receipt keyed by fingerprint", "Ignoring the previous result", "Consuming budget twice"],
        answer: 0,
      },
      {
        question: "What should happen after verification mismatch?",
        options: ["Escalate for reconciliation", "Pretend the write succeeded", "Add a new capability"],
        answer: 0,
      },
    ],
  },
];

const levels: Record<Level, { color: string; tagline: string }> = {
  Beginner: { color: "mint", tagline: "Build the control model" },
  Intermediate: { color: "gold", tagline: "Design production patterns" },
  Advanced: { color: "coral", tagline: "Prove secure operation" },
};

export default function Home() {
  const [level, setLevel] = useState<"All" | Level>("All");
  const [selected, setSelected] = useState(lessons[0]);
  const [tab, setTab] = useState<Tab>("learn");
  const [completed, setCompleted] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<number, number>>({});

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(progressKey);
      if (saved) setCompleted(JSON.parse(saved) as string[]);
    } catch {
      // Local progress is optional.
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(progressKey, JSON.stringify(completed));
    } catch {
      // Local progress is optional.
    }
  }, [completed]);

  const filtered = useMemo(
    () => (level === "All" ? lessons : lessons.filter((lesson) => lesson.level === level)),
    [level],
  );
  const score = selected.checkpoints.reduce(
    (total, checkpoint, index) => total + (answers[index] === checkpoint.answer ? 1 : 0),
    0,
  );
  const select = (lesson: Lesson) => {
    setSelected(lesson);
    setTab("learn");
    setAnswers({});
    window.setTimeout(
      () => document.getElementById("lesson-workspace")?.scrollIntoView({ behavior: "smooth" }),
      0,
    );
  };
  const toggleComplete = () => {
    setCompleted((current) =>
      current.includes(selected.id)
        ? current.filter((id) => id !== selected.id)
        : [...current, selected.id],
    );
  };

  return (
    <main>
      <nav className="nav">
        <a className="brand" href="#top">
          <img src={logo} alt="One+i" />
          <span>GUARDRAILS / <em>FIELD GUIDE</em></span>
        </a>
        <div className="nav-links">
          <a href="#curriculum">Curriculum</a>
          <a href="/gen-ai-guardrails/quiz/">Full quiz</a>
          <a className="repo" href="https://github.com/mahsa-teimourikia/gen-ai-guardrails" target="_blank" rel="noreferrer">Open repo ↗</a>
        </div>
      </nav>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="eyebrow">THE OPEN-SOURCE PATH · FROM POLICY TO PROOF</div>
          <h1>Build systems<br /><span>that know why.</span></h1>
          <p className="hero-lede">
            A notebook-first learning hub for GenAI guardrails: learn the boundary,
            run the deterministic lab, change one variable, measure the effect, and
            preserve the evidence.
          </p>
          <div className="hero-actions">
            <a className="button primary" href="#curriculum">Start the curriculum <span>↓</span></a>
            <a className="text-link" href="/gen-ai-guardrails/quiz/">Take the full quiz ↗</a>
          </div>
          <div className="hero-meta">
            <span><b>{lessons.length}</b> guided lessons</span>
            <span><b>3</b> learning altitudes</span>
            <span><b>1</b> evidence loop</span>
          </div>
        </div>
        <div className="hero-art" aria-label="Guardrail control loop illustration">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="core"><span>WHY</span><small>evidence first</small></div>
          <div className="node node-a">01<br /><b>DEFINE</b></div>
          <div className="node node-b">02<br /><b>CONSTRAIN</b></div>
          <div className="node node-c">03<br /><b>VERIFY</b></div>
          <div className="art-caption">A safe answer is only<br /><strong>as good as its controls.</strong></div>
        </div>
      </section>

      <section className="signal">
        <div><span className="signal-icon">↗</span><b>FOLLOW THE REPO</b><p>Every card points to the actual README, notebook, and executable lab.</p></div>
        <div><span className="signal-icon">⌁</span><b>LEARN IN LOOPS</b><p>Read the concept. Run the lab. Change one thing. Inspect the failure.</p></div>
        <div><span className="signal-icon">◌</span><b>KEEP THE EVIDENCE</b><p>Tests, reason codes, receipts, and release gates make controls observable.</p></div>
      </section>

      <section id="curriculum" className="curriculum">
        <div className="section-intro">
          <div><div className="eyebrow">THE CURRICULUM MAP</div><h2>One path.<br /><span>Three altitudes.</span></h2></div>
          <p>Start with the control model, turn it into production patterns, then prove security and bounded agent execution with deterministic evidence.</p>
        </div>
        <div className="progress-summary" aria-live="polite">{completed.length} of {lessons.length} lessons complete</div>
        <div className="level-tabs">
          <button className={level === "All" ? "active" : ""} onClick={() => setLevel("All")}>All <span>· {lessons.length}</span></button>
          {(Object.keys(levels) as Level[]).map((item) => (
            <button key={item} className={level === item ? "active" : ""} onClick={() => setLevel(item)}>{item} <span>· {levels[item].tagline}</span></button>
          ))}
        </div>
        <div className="curriculum-grid">
          {filtered.map((lesson) => (
            <button className={`subject-card ${selected.id === lesson.id ? "selected" : ""}`} key={lesson.id} onClick={() => select(lesson)}>
              <div className="card-top"><span className={`pill ${levels[lesson.level].color}`}>{lesson.level} · {lesson.step}</span><span className="duration">{lesson.time}</span>{completed.includes(lesson.id) && <span className="completed-mark" aria-label="Completed">✓</span>}</div>
              <div className="card-number">{lesson.step}</div><h3>{lesson.title}</h3><p>{lesson.description}</p><span className="card-arrow">→</span>
            </button>
          ))}
        </div>
      </section>

      <section id="lesson-workspace" className="workspace">
        <div className="workspace-heading"><div><div className="eyebrow">LESSON {selected.step} · {selected.level.toUpperCase()}</div><h2>{selected.title}</h2></div><div className="session-count"><span className="dot" /> {selected.time} <span>·</span> repo-grounded</div></div>
        <div className="lesson-tabs">
          <button className={tab === "learn" ? "active" : ""} onClick={() => setTab("learn")}>01 / Learn</button>
          <button className={tab === "lab" ? "active" : ""} onClick={() => setTab("lab")}>02 / Lab</button>
          <button className={tab === "checkpoint" ? "active" : ""} onClick={() => setTab("checkpoint")}>03 / Checkpoint</button>
        </div>
        <div className="workspace-body">
          {tab === "learn" && (
            <div className="lesson-layout">
              <div className="lesson-copy"><div className="eyebrow">OUTCOME</div><p className="outcome">{selected.outcome}</p><button className="complete-lesson" onClick={toggleComplete}>{completed.includes(selected.id) ? "Completed ✓" : "Mark lesson complete"}</button><div className="material-actions"><a className="button primary" href={base + selected.refs[0]} target="_blank" rel="noreferrer">Read lesson material ↗</a><a className="notebook-link inline-link" href={base + selected.notebook} target="_blank" rel="noreferrer">Open companion notebook ↗</a></div><div className="eyebrow">THE IDEA</div><p className="big-copy">{selected.summary}</p><div className="failure-strip"><span className="eyebrow">WATCH FOR</span>{selected.failures.map((failure) => <span key={failure}>× {failure}</span>)}</div></div>
              <div className="diagram"><div className="diagram-label">THE STUDY LOOP</div><div className="flow"><div className="flow-box">Read<small>concept</small></div><i>→</i><div className="flow-box active-box">Run<small>notebook</small></div><i>→</i><div className="flow-box">Change<small>one thing</small></div></div><div className="diagram-note">Make the failure visible.<br /><span>Then turn the fix into a test.</span></div><div className="reference-list"><span className="eyebrow">SOURCE MATERIAL</span>{selected.refs.map((ref, index) => <a key={ref} href={base + ref} target="_blank" rel="noreferrer"><span>0{index + 1}</span>{ref} ↗</a>)}</div></div>
            </div>
          )}
          {tab === "lab" && <div className="lab-layout"><div className="lesson-copy"><div className="eyebrow">PRACTICAL LAB</div><p className="big-copy">{selected.exercise}</p><a className="notebook-link" href={base + selected.notebook} target="_blank" rel="noreferrer">Run the guided notebook ↗</a><div className="lab-note"><b>Study ritual from the repo</b><br />Use the notebook as the primary lab: run it, change one variable, run the tests, and explain one failure mode.</div></div><pre><code>{selected.code}</code></pre></div>}
          {tab === "checkpoint" && <div className="quiz workspace-single-column"><div className="quiz-head"><div><div className="eyebrow">CHECKPOINT QUIZ</div><p>Choose the answer that follows the lesson’s executable controls.</p></div><div className="score">{Object.keys(answers).length ? `${score}/${selected.checkpoints.length}` : "—"}<small>score</small></div></div>{selected.checkpoints.map((checkpoint, index) => <div className="question" key={checkpoint.question}><b>{String(index + 1).padStart(2, "0")} / {checkpoint.question}</b><div className="options">{checkpoint.options.map((option, optionIndex) => <button key={option} onClick={() => setAnswers({ ...answers, [index]: optionIndex })} className={answers[index] === optionIndex ? (optionIndex === checkpoint.answer ? "correct" : "wrong") : ""}>{option}<span>{answers[index] === optionIndex ? (optionIndex === checkpoint.answer ? "✓" : "×") : ""}</span></button>)}</div></div>)}</div>}
        </div>
      </section>

      <section className="footer-cta"><div className="eyebrow">THE REPO’S RULE OF THUMB</div><h2>Read the idea.<br /><span>Run the evidence.</span></h2><p>Use the companion notebooks and tests to make each control observable. Then take the full cross-course knowledge check.</p><a className="button dark" href="/gen-ai-guardrails/quiz/">Open the full quiz ↗</a></section>
      <footer><div className="footer-brand"><img src={logo} alt="One+i" /><span>Learning with One+i · responsible AI, real-world impact</span></div><a href="https://oneplusi.io" target="_blank" rel="noreferrer">oneplusi.io ↗</a><a href="https://github.com/mahsa-teimourikia/gen-ai-guardrails" target="_blank" rel="noreferrer">github ↗</a></footer>
    </main>
  );
}
