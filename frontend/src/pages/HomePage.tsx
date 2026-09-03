import { Link } from "react-router-dom"
import {
  ArrowRight,
  Ban,
  Database,
  GitBranch,
  IndianRupee,
  Lock,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react"

import { BrandMark } from "@/components/BrandMark"
import { Button } from "@/components/ui/button"
import { DEMO_LOGIN } from "@/lib/session"

const PIPELINE = [
  { n: "01", title: "Ingest", body: "CSV or XLSX merchant tables become a single EventContext per failure." },
  { n: "02", title: "Predict", body: "Recovery and churn models score the event. They never pick an action." },
  { n: "03", title: "Prioritize", body: "ERV = amount × recovery probability. Ranked book, not a FIFO queue." },
  { n: "04", title: "Diagnose", body: "LangGraph node. LLM optional; a deterministic fallback always runs." },
  { n: "05", title: "Select", body: "The model may pick only from already-eligible candidate IDs." },
  { n: "06", title: "Guard", body: "Policy is code. Invalid AI actions cannot execute." },
  { n: "07", title: "Act", body: "Simulated payment and messaging tools. No live Razorpay calls." },
  { n: "08", title: "Learn", body: "Outcomes become explainable signals — policy does not rewrite itself." },
]

const FEATURES = [
  {
    icon: Target,
    title: "Revenue at risk, ranked",
    body: "Open failures are scored with recovery probability, churn, LTV, and urgency. The queue is ordered by expected rupees, not ticket age.",
  },
  {
    icon: GitBranch,
    title: "Bounded recovery agent",
    body: "A LangGraph workflow diagnoses the event and selects one intervention. Candidate generation is deterministic — no invented retries on expired cards.",
  },
  {
    icon: ShieldCheck,
    title: "Guardrails that block",
    body: "Cooldown, max interventions, closed events, unknown actions, and allowlists are code, not a prompt. BLOCK means no tool runs.",
  },
  {
    icon: Sparkles,
    title: "Inspectable execution",
    body: "Every run writes a workflow ID, execution ID, outcome, amount recovered, and an audit timeline. Tools never hit a live payment API in this MVP.",
  },
  {
    icon: IndianRupee,
    title: "Outcome intelligence",
    body: "See which actions recovered, for which failure reasons, versus model expectation. Small samples are labeled. Dataset labels stay separate.",
  },
  {
    icon: Database,
    title: "File-first merchant data",
    body: "Upload CSV/XLSX. Invalid files are rejected and do not replace the active book. Extra packs live under data/new-data for manual tests.",
  },
]

export function HomePage() {
  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <BrandMark compact />
          <nav className="hidden items-center gap-7 text-sm text-muted-foreground md:flex">
            <a href="#product" className="hover:text-foreground">
              Product
            </a>
            <a href="#how" className="hover:text-foreground">
              How it works
            </a>
            <a href="#agent" className="hover:text-foreground">
              Agent stack
            </a>
            <a href="#demo" className="hover:text-foreground">
              Demo
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm">
              <Link to="/login">Sign in</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/login">
                Open console
                <ArrowRight />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <section className="marketing-grid relative overflow-hidden border-b border-border">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:py-24">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              <span className="size-1.5 rounded-full bg-emerald-700" />
              Payments recovery for Indian merchants
            </p>
            <h1 className="mt-6 max-w-xl text-[2.35rem] font-semibold leading-[1.08] tracking-tight md:text-6xl">
              Recover failed revenue with a guarded decision.
            </h1>
            <p className="mt-5 max-w-lg text-base leading-relaxed text-muted-foreground md:text-lg">
              Declines pile up as exceptions. RevenueOS turns them into a ranked recovery book:
              understand the event, score recoverability and churn, prioritize by expected rupees,
              then let a bounded agent choose one eligible action — validated before anything
              simulated is executed.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link to="/login">Launch merchant console</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <a href="#how">See the recovery loop</a>
              </Button>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Demo · {DEMO_LOGIN.email} · {DEMO_LOGIN.password} · lands on the seeded dataset
            </p>
          </div>
          <ConsolePreview />
        </div>
      </section>

      <section id="product" className="border-b border-border bg-card">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 py-10 sm:grid-cols-3">
          <Fact k="Seeded merchant book" v="3,000 customers · 3,200 events · 420 open" />
          <Fact k="Lead opportunity" v="EVT_000861 · HIGH · ERV ₹2,714.55" />
          <Fact k="Decision stack" v="sklearn scores · LangGraph agent · code guardrails" />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-20">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Product
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">
            Built like a payments product. Orchestrated like an ops desk.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground md:text-base">
            Same cream canvas, navy type, and metric cards as the console — so the homepage is the
            product, not a separate dark theme.
          </p>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((item) => (
            <article
              key={item.title}
              className="rounded-xl border border-border bg-card p-5 shadow-[0_1px_0_rgba(15,23,42,0.04)]"
            >
              <item.icon className="size-4 text-primary" />
              <h3 className="mt-3 text-base font-semibold tracking-tight">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="how" className="border-y border-border bg-muted/40">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            How it works
          </p>
          <h2 className="mt-2 max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
            How a rupee moves through the system
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground md:text-base">
            Each failed payment or at-risk subscription becomes one EventContext. Models predict.
            The risk engine ranks. The agent decides among actions that are already legal.
            Guardrails are the last word.
          </p>
          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE.map((step) => (
              <article key={step.n} className="rounded-xl border border-border bg-card p-4">
                <p className="font-mono text-[11px] text-primary">{step.n}</p>
                <h3 className="mt-2 text-sm font-semibold">{step.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="agent" className="bg-primary text-primary-foreground">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-foreground/60">
            Agent stack
          </p>
          <h2 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">
            Where the agent is — and where it is not
          </h2>
          <p className="mt-4 max-w-3xl text-sm leading-relaxed text-primary-foreground/75 md:text-base">
            This is not a sklearn notebook with a UI. Recovery and churn models only produce
            probabilities. The recovery loop is a LangGraph state machine: diagnose → predict →
            risk → candidates → select → guardrail → execute → observe. The optional LLM is
            untrusted input. There is no RAG corpus — merchant truth is tabular EventContext.
          </p>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            <Note
              title="Used"
              body="LangGraph StateGraph, langchain_core RunnableConfig, optional chat-completions LLM, simulated tools, audit trail."
            />
            <Note
              title="Not used"
              body="RAG, embeddings, vector DB, autonomous policy mutation, live payment APIs, reinforcement learning."
            />
            <Note
              title="Why that split"
              body="If someone asks whether the AI can bypass guardrails, the answer is no. Eligibility and BLOCK are code."
            />
          </div>
        </div>
      </section>

      <section id="demo" className="mx-auto max-w-6xl px-5 py-20">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-center">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Walk the demo
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">
              Same book the console already uses.
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Sign in, land on Overview, then inspect EVT_000861. The agent run is simulated and
              auditable. Extra packs under data/new-data can be uploaded from Data after you log in.
            </p>
            <Button asChild size="lg" className="mt-8">
              <Link to="/login">
                Start with demo credentials
                <ArrowRight />
              </Link>
            </Button>
          </div>
          <ol className="grid gap-3 sm:grid-cols-2">
            {[
              { n: "01", t: "Sign in", d: "Use the demo pair. Overview shows at-risk rupees vs agent recoveries." },
              { n: "02", t: "Opportunities", d: "Confirm EVT_000861 is the top HIGH event in the ranked book." },
              { n: "03", t: "Inspect & run", d: "Read recovery, churn, ERV, then run the recovery agent once." },
              { n: "04", t: "Activity", d: "Persisted workflow, expected vs observed, learning signals." },
            ].map((step) => (
              <li key={step.n} className="rounded-xl border border-border bg-card p-5">
                <p className="font-mono text-[11px] text-primary">{step.n}</p>
                <p className="mt-2 text-sm font-semibold">{step.t}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{step.d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 sm:flex-row sm:items-center sm:justify-between">
          <BrandMark compact />
          <p className="text-xs text-muted-foreground">
            Local file-first MVP · simulated execution · not a production payment platform
          </p>
        </div>
      </footer>
    </div>
  )
}

function Fact({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{k}</p>
      <p className="mt-1 text-sm font-medium">{v}</p>
    </div>
  )
}

function Note({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-white/15 bg-white/5 p-5">
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-primary-foreground/70">{body}</p>
    </div>
  )
}

function ConsolePreview() {
  return (
    <div className="relative">
      <div className="absolute -inset-4 rounded-[28px] bg-primary/5 blur-2xl" aria-hidden />
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-[0_24px_80px_-32px_rgba(30,58,95,0.45)]">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-700" />
            <span className="text-xs font-medium">Revenue intelligence</span>
          </div>
          <span className="text-[11px] text-muted-foreground">Dataset demo · 420 open</span>
        </div>
        <div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-4">
          <MiniMetric label="At risk" value="₹12.4L" />
          <MiniMetric label="Expected" value="₹4.81L" />
          <MiniMetric label="Open" value="420" />
          <MiniMetric label="Lead ERV" value="₹2,715" emphasis />
        </div>
        <div className="border-t border-border px-4 py-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold">Top opportunities</p>
            <p className="text-[11px] text-muted-foreground">Highest ERV first</p>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="text-[10px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="pb-2 font-medium">Event</th>
                <th className="pb-2 font-medium">Priority</th>
                <th className="pb-2 font-medium text-right">ERV</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              <tr className="border-t border-primary/20 bg-primary/[0.04]">
                <td className="py-2.5 font-medium">EVT_000861</td>
                <td>
                  <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                    HIGH
                  </span>
                </td>
                <td className="text-right">₹2,714.55</td>
              </tr>
              <tr className="border-t border-border text-muted-foreground">
                <td className="py-2">EVT_000742</td>
                <td>MEDIUM</td>
                <td className="text-right">₹1,108.20</td>
              </tr>
              <tr className="border-t border-border text-muted-foreground">
                <td className="py-2">EVT_000319</td>
                <td>MEDIUM</td>
                <td className="text-right">₹864.40</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-4 border-t border-border bg-muted/50 px-4 py-3 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Lock className="size-3" /> Guarded
          </span>
          <span className="inline-flex items-center gap-1">
            <Ban className="size-3" /> No live charges
          </span>
          <span className="hidden sm:inline">LangGraph · sklearn · simulated tools</span>
        </div>
      </div>
    </div>
  )
}

function MiniMetric({
  label,
  value,
  emphasis,
}: {
  label: string
  value: string
  emphasis?: boolean
}) {
  return (
    <div className={`rounded-lg border px-3 py-2.5 ${emphasis ? "border-primary/30 bg-card" : "border-border bg-muted/40"}`}>
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold tabular-nums">{value}</p>
    </div>
  )
}
