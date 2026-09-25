"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BoltIcon,
  GearIcon,
  GridIcon,
  InfoIcon,
  MoonIcon,
  RefreshIcon,
  SunIcon,
} from "./icons";

type View = "overview" | "setup" | "about";

type Status = {
  ok?: boolean;
  bot_running?: boolean;
  token_configured?: boolean;
  agent_id?: string;
  token_masked?: string;
  ollama_model?: string | null;
  ollama_base_url?: string | null;
  notify_configured?: boolean;
  notify_chat_id?: string | null;
  model_provider?: string;
  provider_label?: string;
  model_name?: string;
  provider_needs_key?: boolean;
  provider_key_configured?: boolean;
  allowlist_active?: boolean;
  allowlist_ids?: number[];
  detected_owner_id?: number | null;
  detected_owner_name?: string | null;
  detected_owner_username?: string | null;
  detected_owner_allowed?: boolean;
};

type DiagnoseCheck = {
  id: string;
  label: string;
  ok: boolean;
  detail: string;
};

type Diagnose = {
  ok?: boolean;
  checks?: DiagnoseCheck[];
};

type ProviderInfo = {
  id: string;
  display_name: string;
  description: string;
  kind: string;
  needs_key: boolean;
  key_configured: boolean;
  base_url: string;
  signup_url: string;
  default_model: string;
};

const VIEW_META: Record<View, { icon: React.ReactNode; title: string; sub: string }> = {
  overview: { icon: <GridIcon className="h-[22px] w-[22px]" />, title: "Overview", sub: "Telegram bridge · multi-provider · one-time setup" },
  setup: { icon: <GearIcon className="h-[22px] w-[22px]" />, title: "Setup", sub: "Configure once — then it just runs" },
  about: { icon: <InfoIcon className="h-[22px] w-[22px]" />, title: "About", sub: "Aether Core console" },
};

const NAV: { id: View; label: string; icon: React.ReactNode; section: "main" | "system" }[] = [
  { id: "overview", label: "Overview", icon: <GridIcon className="h-[18px] w-[18px]" />, section: "main" },
  { id: "setup", label: "Setup", icon: <GearIcon className="h-[18px] w-[18px]" />, section: "main" },
  { id: "about", label: "About", icon: <InfoIcon className="h-[18px] w-[18px]" />, section: "system" },
];

export default function SetupPage() {
  const [view, setView] = useState<View>("overview");
  const [status, setStatus] = useState<Status | null>(null);
  const [dark, setDark] = useState(true);
  const [result, setResult] = useState("– idle –");
  const [resultClass, setResultClass] = useState<"idle" | "ok" | "err">("idle");
  const [busy, setBusy] = useState(false);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [diagnose, setDiagnose] = useState<Diagnose | null>(null);
  const [probeModels, setProbeModels] = useState<string[]>([]);
  const [form, setForm] = useState({
    telegram_token: "",
    agent_id: "",
    provider: "",
    model: "",
    api_key: "",
    notify_chat_id: "",
  });

  const prefilled = useCallback((s: Status) => {
    setForm((f) => ({
      ...f,
      agent_id: f.agent_id || s.agent_id || "",
      provider: f.provider || s.model_provider || "ollama",
      model: f.model || s.model_name || "",
      notify_chat_id: f.notify_chat_id || (s.notify_configured ? s.notify_chat_id || "" : ""),
    }));
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [sr, pr, dr] = await Promise.all([
        fetch("/setup/status", { cache: "no-store" }),
        fetch("/setup/providers", { cache: "no-store" }),
        fetch("/setup/diagnose", { cache: "no-store" }),
      ]);
      const s: Status = await sr.json();
      const p = await pr.json();
      const d: Diagnose = await dr.json();
      setStatus(s);
      setProviders(Array.isArray(p?.providers) ? p.providers : []);
      setDiagnose(d);
      prefilled(s);
    } catch {
      setStatus(null);
    }
  }, [prefilled]);

  useEffect(() => {
    const t = localStorage.getItem("aether-theme");
    const isDark = t !== "light";
    document.documentElement.classList.toggle("dark", isDark);
    setDark(isDark);
    refresh();
    const iv = setInterval(refresh, 5000);
    return () => clearInterval(iv);
  }, [refresh]);

  function toggleTheme() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("aether-theme", next ? "dark" : "light");
    setDark(next);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await fetch("/api/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, action: "start" }),
      });
      const j = await r.json();
      setResult(JSON.stringify(j, null, 2));
      setResultClass(j.ok ? "ok" : "err");
      if (j.ok) setForm((f) => ({ ...f, telegram_token: "" }));
      refresh();
    } catch (err) {
      setResult(JSON.stringify({ ok: false, error: "fetch failed", detail: String(err) }, null, 2));
      setResultClass("err");
    } finally {
      setBusy(false);
    }
  }

  async function onStop() {
    setBusy(true);
    try {
      const r = await fetch("/api/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "stop" }),
      });
      const j = await r.json();
      setResult(JSON.stringify(j, null, 2));
      setResultClass("ok");
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function onAllowOwner(userId: number) {
    setBusy(true);
    try {
      const r = await fetch("/api/setup/allow-owner", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      const j = await r.json();
      setResult(JSON.stringify(j, null, 2));
      setResultClass(j.ok ? "ok" : "err");
      refresh();
    } catch (err) {
      setResult(JSON.stringify({ ok: false, error: "fetch failed", detail: String(err) }, null, 2));
      setResultClass("err");
    } finally {
      setBusy(false);
    }
  }

  async function onProbe() {
    setBusy(true);
    try {
      const r = await fetch("/api/setup/probe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: form.provider, api_key: form.api_key }),
      });
      const j = await r.json();
      setResult(JSON.stringify(j, null, 2));
      setResultClass(j.ok ? "ok" : "err");
      if (j.ok && Array.isArray(j.models)) {
        setProbeModels(j.models);
      }
      return j;
    } catch (err) {
      setResult(JSON.stringify({ ok: false, error: "fetch failed", detail: String(err) }, null, 2));
      setResultClass("err");
      return { ok: false, error: "fetch failed" };
    } finally {
      setBusy(false);
    }
  }

  const on = status?.bot_running ?? false;
  const tokenOk = status?.token_configured ?? false;
  const meta = VIEW_META[view];

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* ======================= SIDEBAR (9router shell) ======================= */}
      <aside className="flex shrink-0 flex-row items-center gap-3 border-b border-line-subtle bg-sidebar/85 px-4 py-3 backdrop-blur-xl md:sticky md:top-0 md:h-screen md:w-72 md:flex-none md:flex-col md:items-stretch md:gap-0 md:border-b-0 md:border-r md:px-0 md:py-0">
        {/* macOS traffic lights */}
        <div className="hidden md:flex md:gap-2 md:px-6 md:pt-5 md:pb-2">
          <span className="h-3 w-3 rounded-full bg-[#FF5F56]" />
          <span className="h-3 w-3 rounded-full bg-[#FFBD2E]" />
          <span className="h-3 w-3 rounded-full bg-[#27C93F]" />
        </div>

        {/* Brand */}
        <div className="flex items-center gap-3 md:flex-col md:items-start md:gap-3 md:px-6 md:pb-5 md:pt-4">
          <div className="flex h-9 w-9 flex-none items-center justify-center rounded-[10px] bg-gradient-to-br from-brand to-brand-deep shadow-warm">
            <BoltIcon className="h-5 w-5 stroke-white" />
          </div>
          <div className="md:flex md:flex-col md:gap-0.5">
            <h1 className="text-[17px] font-semibold tracking-tight">Aether</h1>
            <span className="text-xs text-muted">v0.1.0</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex flex-1 items-center gap-1 overflow-x-auto md:flex-col md:items-stretch md:overflow-y-auto md:px-4">
          <p className="hidden px-3 pb-1.5 pt-3.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted/60 md:block">
            Main
          </p>
          {NAV.filter((n) => n.section === "main").map((n) => (
            <NavButton key={n.id} item={n} active={view === n.id} onClick={() => setView(n.id)} />
          ))}
          <p className="hidden px-3 pb-1.5 pt-3.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted/60 md:block">
            System
          </p>
          {NAV.filter((n) => n.section === "system").map((n) => (
            <NavButton key={n.id} item={n} active={view === n.id} onClick={() => setView(n.id)} />
          ))}
        </nav>

        <div className="hidden border-t border-line-subtle px-6 py-4 text-[11px] text-subtle md:block">
          Aether Core · local-first agent · public console
        </div>
      </aside>

      {/* ======================= MAIN (9router shell) ======================= */}
      <main className="flex min-w-0 flex-1 flex-col bg-gradient-to-b from-bg-alt to-bg">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-line-subtle bg-surface/95 px-4 py-3 backdrop-blur-xl md:px-8">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex-none text-brand">{meta.icon}</span>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold tracking-tight leading-tight md:text-2xl">
                {meta.title}
              </h1>
              <p className="hidden truncate text-[13px] text-muted md:block">{meta.sub}</p>
            </div>
          </div>
          <div className="flex flex-none items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold ${
                status === null
                  ? "border-line bg-surface-2 text-muted"
                  : on
                    ? "border-ok/40 bg-ok/10 text-ok"
                    : "border-bad/40 bg-bad/10 text-bad"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full bg-current ${
                  status !== null ? "shadow-[0_0_8px_currentColor]" : ""
                }`}
              />
              {status === null ? "Status offline" : on ? "Bot running" : "Bot stopped"}
            </span>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface text-muted transition-colors hover:border-brand hover:text-brand"
              onClick={refresh}
              title="Refresh"
            >
              <RefreshIcon className="h-4 w-4" />
            </button>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface text-muted transition-colors hover:border-brand hover:text-brand"
              onClick={toggleTheme}
              title="Toggle theme"
            >
              {dark ? <MoonIcon className="h-4 w-4" /> : <SunIcon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        <div className="w-full max-w-[1000px] px-4 py-6 md:px-8 md:py-8">
          {view === "overview" && (
            <Overview
              status={status}
              on={on}
              tokenOk={tokenOk}
              diagnose={diagnose}
              busy={busy}
              onAllowOwner={onAllowOwner}
            />
          )}
          {view === "setup" && (
            <SetupView
              form={form}
              setForm={setForm}
              busy={busy}
              onSubmit={onSubmit}
              onStop={onStop}
              onProbe={onProbe}
              result={result}
              resultClass={resultClass}
              providers={providers}
              probeModels={probeModels}
            />
          )}
          {view === "about" && <About />}
        </div>
      </main>
    </div>
  );
}

function NavButton({
  item,
  active,
  onClick,
}: {
  item: (typeof NAV)[number];
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-[7px] text-left text-[13px] font-medium transition-colors ${
        active
          ? "bg-brand/10 text-brand"
          : "text-muted hover:bg-surface-2 hover:text-main"
      }`}
    >
      <span className={`flex-none ${active ? "text-brand" : ""}`}>{item.icon}</span>
      <span className="whitespace-nowrap">{item.label}</span>
    </button>
  );
}

/* ============================ OVERVIEW ============================ */

function CheckRow({ check }: { check: DiagnoseCheck }) {
  const tone = check.ok ? "ok" : "bad";
  const glyph = check.ok ? "✓" : "✗";
  return (
    <li className="flex items-start gap-2.5 rounded-brand border border-line-subtle bg-bg/60 px-3 py-2 text-[12.5px]">
      <span
        className={`mt-[1px] flex h-[18px] w-[18px] flex-none items-center justify-center rounded-full text-[11px] font-bold ${
          check.ok
            ? "bg-ok/15 text-ok"
            : "bg-bad/15 text-bad"
        }`}
        title={check.ok ? "ok" : "warning"}
      >
        {glyph}
      </span>
      <div className="min-w-0">
        <div className="font-semibold text-main">{check.label}</div>
        <div className={`truncate font-mono text-[11.5px] ${tone === "ok" ? "text-muted" : "text-bad/90"}`}>
          {check.detail}
        </div>
      </div>
    </li>
  );
}

function Overview({
  status,
  on,
  tokenOk,
  diagnose,
  busy,
  onAllowOwner,
}: {
  status: Status | null;
  on: boolean;
  tokenOk: boolean;
  diagnose: Diagnose | null;
  busy: boolean;
  onAllowOwner: (userId: number) => void;
}) {
  const needSetup = !tokenOk || !on;
  const checks = diagnose?.checks ?? [];
  const failCount = checks.filter((c) => !c.ok).length;
  const detected = status?.detected_owner_id ? status.detected_owner_id : null;
  const detectedAllowed = status?.detected_owner_allowed ?? false;
  const nextSteps = [
    !tokenOk && "Get a bot token from @BotFather and save it in Setup.",
    tokenOk && !on && "Press Save & Start Bot once from the Setup tab.",
    status?.provider_needs_key && !status?.provider_key_configured && "Add your provider API key in Setup.",
    status?.allowlist_active === false && "Add your Telegram user id (one click below, or /sethome after saving).",
    status?.notify_configured === false && "Send /sethome from Telegram to receive activation notices.",
  ].filter(Boolean) as string[];

  return (
    <section>
      {needSetup ? (
        <div className="mb-5 flex items-center gap-3 rounded-brand-lg border border-warn/45 bg-warn/10 px-4 py-3.5 text-[13.5px]">
          <span className="flex-none text-lg">⚙️</span>
          <div>
            <b>First-time setup required.</b>{" "}
            <span className="text-muted">
              Add your @BotFather token once — after that this console becomes a live monitor and
              you never touch it again.
            </span>
          </div>
        </div>
      ) : (
        <div className="mb-5 flex items-center gap-3 rounded-brand-lg border border-ok/45 bg-ok/10 px-4 py-3.5 text-[13.5px]">
          <span className="flex-none text-lg">✅</span>
          <div>
            <b>Bridge is active.</b>{" "}
            <span className="text-muted">
              Messages sent to your bot are routed to the agent automatically. No further setup
              needed — this console now just monitors status.
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
        <div className="rounded-brand-lg border border-line-subtle bg-surface p-5 shadow-elev">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
            Telegram Bot
          </h3>
          <div className="mt-3">
            {status === null ? (
              <StatusBadge tone="mut">—</StatusBadge>
            ) : on ? (
              <StatusBadge tone="ok">Running</StatusBadge>
            ) : (
              <StatusBadge tone="bad">Stopped</StatusBadge>
            )}
          </div>
          <p className="mt-1.5 break-all text-xs text-muted">
            agent {status?.agent_id || "—"} · token {tokenOk ? status?.token_masked : "not set"}
          </p>
        </div>

        <div className="rounded-brand-lg border border-line-subtle bg-surface p-5 shadow-elev">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Model</h3>
          <div className="mt-3 font-mono text-xl font-bold tracking-tight">
            {status?.model_name || status?.ollama_model || "—"}
          </div>
          <p className="mt-1.5 text-xs text-muted">
            provider <b className="text-main">{status?.provider_label || status?.model_provider || "—"}</b>
            {status?.provider_key_configured ? " · key ✓" : status?.provider_needs_key ? " · no key yet" : " · local"}
          </p>
          <div className="mt-3 flex justify-between gap-2 text-xs text-muted">
            <span>Base URL</span>
            <b className="break-all text-right font-mono font-semibold text-main">
              {status?.ollama_base_url || "—"}
            </b>
          </div>
        </div>

        <div className="rounded-brand-lg border border-line-subtle bg-surface p-5 shadow-elev">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
            Bot Token
          </h3>
          <div className="mt-3">
            {status === null ? (
              <StatusBadge tone="mut">—</StatusBadge>
            ) : tokenOk ? (
              <StatusBadge tone="ok">Configured</StatusBadge>
            ) : (
              <StatusBadge tone="bad">Missing</StatusBadge>
            )}
          </div>
          <p className="mt-1.5 break-all text-xs text-muted">
            {tokenOk ? `token ${status?.token_masked}` : "get one from @BotFather"}
          </p>
        </div>

        <div className="rounded-brand-lg border border-line-subtle bg-surface p-5 shadow-elev">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
            Activation Notice
          </h3>
          <div className="mt-3">
            {status === null ? (
              <StatusBadge tone="mut">—</StatusBadge>
            ) : status?.notify_configured ? (
              <StatusBadge tone="ok">On</StatusBadge>
            ) : (
              <StatusBadge tone="mut">Not set</StatusBadge>
            )}
          </div>
          <p className="mt-1.5 text-xs text-muted">
            notifies the owner chat when the agent goes live
          </p>
        </div>
      </div>

      {/* ---------- detected owner ---------- */}
      {detected !== null && (
        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-brand-lg border border-line-subtle bg-surface p-4 shadow-elev">
          <div className="min-w-0 flex-1">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
              Detected sender
            </h3>
            <p className="mt-1 truncate text-[13px] text-main">
              {status?.detected_owner_name || status?.detected_owner_username || "—"}
              <span className="ml-2 font-mono text-xs text-muted">id {detected}</span>
            </p>
            <p className="mt-0.5 text-[11.5px] text-subtle">
              first person to message the bot — ready to add to the allowlist
            </p>
          </div>
          {!detectedAllowed ? (
            <button
              disabled={busy}
              onClick={() => onAllowOwner(detected)}
              className="rounded-brand border border-transparent bg-gradient-to-br from-brand to-brand-hover px-3.5 py-1.5 text-[12.5px] font-semibold text-white transition hover:brightness-105 disabled:opacity-60"
            >
              + Allow this user
            </button>
          ) : (
            <StatusBadge tone="ok">allowed ✓</StatusBadge>
          )}
        </div>
      )}

      {/* ---------- diagnose / next steps ---------- */}
      <div className="mt-4 grid gap-4 md:grid-cols-[300px_1fr]">
        <div className="rounded-brand-lg border border-line-subtle bg-surface p-4 shadow-elev">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
            Next steps
          </h3>
          {nextSteps.length === 0 ? (
            <p className="mt-2.5 text-[12.5px] text-ok">🎉 Everything is in place.</p>
          ) : (
            <ol className="mt-2.5 list-decimal space-y-1.5 pl-4 text-[12.5px] leading-snug text-muted">
              {nextSteps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          )}
        </div>

        <div className="rounded-brand-lg border border-line-subtle bg-surface p-4 shadow-elev">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
              Diagnose · health walk
            </h3>
            {diagnose !== null && (
              <span
                className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
                  failCount === 0
                    ? "border-ok/35 bg-ok/10 text-ok"
                    : "border-warn/45 bg-warn/10 text-warn"
                }`}
              >
                {failCount === 0 ? "✓ all good" : `⚠ ${failCount} issue(s)`}
              </span>
            )}
          </div>
          {checks.length === 0 ? (
            <p className="mt-2.5 text-[12.5px] text-muted">No checks yet — refresh.</p>
          ) : (
            <ul className="mt-2.5 space-y-1.5">
              {checks.map((c) => (
                <CheckRow key={c.id} check={c} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

function StatusBadge({ tone, children }: { tone: "ok" | "bad" | "mut"; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
        tone === "ok"
          ? "border-ok/35 bg-ok/10 text-ok"
          : tone === "bad"
            ? "border-bad/35 bg-bad/10 text-bad"
            : "border-line bg-surface-2 text-muted"
      }`}
    >
      <span className="h-[7px] w-[7px] rounded-full bg-current" />
      {children}
    </span>
  );
}

/* ============================ SETUP ============================ */

function SetupView({
  form,
  setForm,
  busy,
  onSubmit,
  onStop,
  onProbe,
  result,
  resultClass,
  providers,
  probeModels,
}: {
  form: {
    telegram_token: string;
    agent_id: string;
    provider: string;
    model: string;
    api_key: string;
    notify_chat_id: string;
  };
  setForm: React.Dispatch<React.SetStateAction<typeof form>>;
  busy: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onStop: () => void;
  onProbe: () => Promise<unknown>;
  result: string;
  resultClass: "idle" | "ok" | "err";
  providers: ProviderInfo[];
  probeModels: string[];
}) {
  const set =
    (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));

  const activeProvider = providers.find((p) => p.id === form.provider);
  const needsKey = activeProvider?.needs_key ?? false;

  const inputCls =
    "mt-1.5 w-full rounded-brand border border-line bg-bg px-3 py-2 font-mono text-[13px] text-main outline-none transition-shadow focus:border-brand focus:ring-[3px] focus:ring-brand/15";

  const modelOptions =
    probeModels.length > 0
      ? probeModels
      : (activeProvider?.default_model ? [activeProvider.default_model] : []);

  return (
    <section>
      <div className="mb-4 flex flex-wrap gap-3.5 text-[12.5px] text-muted">
        <span className="flex items-center gap-2">
          <StepNo n={1} />
          <span>
            <b className="text-main">@BotFather</b> → new bot → copy token{" "}
            <a
              className="text-brand underline-offset-2 hover:underline"
              href="https://t.me/BotFather"
              target="_blank"
              rel="noreferrer"
            >
              open ↗
            </a>
          </span>
        </span>
        <span className="flex items-center gap-2">
          <StepNo n={2} />
          <span>Pick model &amp; test key</span>
        </span>
        <span className="flex items-center gap-2">
          <StepNo n={3} />
          <span>Save &amp; chat with the bot</span>
        </span>
      </div>

      <form onSubmit={onSubmit} className="max-w-[560px] rounded-brand-lg border border-line-subtle bg-surface p-5 shadow-elev">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
          Create or update the bridge
        </h3>

        <label className="mt-3 block text-[12.5px] font-semibold text-muted">
          Telegram Bot Token
          <span className="mt-0.5 block text-[11.5px] font-normal text-subtle">
            from @BotFather — /newbot → name → username → copy the token
          </span>
        </label>
        <input
          value={form.telegram_token}
          onChange={set("telegram_token")}
          placeholder="123456:ABC-DEF…"
          autoComplete="off"
          required
          className="mt-1.5 w-full rounded-brand border border-line bg-bg px-3 py-2 font-mono text-[13px] text-main outline-none transition-shadow focus:border-brand focus:ring-[3px] focus:ring-brand/15"
        />

        <label className="mt-3 block text-[12.5px] font-semibold text-muted">
          Agent ID
          <span className="mt-0.5 block text-[11.5px] font-normal text-subtle">
            all chats are routed to this agent
          </span>
        </label>
        <input
          value={form.agent_id}
          onChange={set("agent_id")}
          placeholder="aria"
          required
          className="mt-1.5 w-full rounded-brand border border-line bg-bg px-3 py-2 font-mono text-[13px] text-main outline-none transition-shadow focus:border-brand focus:ring-[3px] focus:ring-brand/15"
        />

        <label className="mt-3 block text-[12.5px] font-semibold text-muted">
          Model Provider
          <span className="mt-0.5 block text-[11.5px] font-normal text-subtle">
            local Ollama or a remote API (key required)
          </span>
        </label>
        <select
          value={form.provider}
          onChange={set("provider")}
          className="mt-1.5 w-full rounded-brand border border-line bg-bg px-3 py-2 text-[13px] text-main outline-none transition-shadow focus:border-brand focus:ring-[3px] focus:ring-brand/15"
        >
          {providers.length === 0 && <option value="">Loading providers…</option>}
          {providers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.display_name}
              {p.needs_key ? (p.key_configured ? " · key ✓" : " · needs key") : " · local"}
            </option>
          ))}
        </select>
        {activeProvider && activeProvider.needs_key && (
          <p className="mt-1 text-[11.5px] text-subtle">
            {activeProvider.description} — get a key at{" "}
            {activeProvider.signup_url ? (
              <a
                className="text-brand underline-offset-2 hover:underline"
                href={activeProvider.signup_url}
                target="_blank"
                rel="noreferrer"
              >
                {activeProvider.signup_url}
              </a>
            ) : (
              "its console"
            )}
          </p>
        )}

        <label className="mt-3 block text-[12.5px] font-semibold text-muted">
          Model
          <span className="mt-0.5 block text-[11.5px] font-normal text-subtle">
            optional — empty = {activeProvider?.default_model || "provider default"}
            {probeModels.length > 0 ? ` · ${probeModels.length} live model(s) fetched` : ""}
          </span>
        </label>
        <div className="flex gap-2">
          <input
            value={form.model}
            onChange={set("model")}
            placeholder={activeProvider?.default_model || "qwen2.5:0.5b / gpt-4o-mini"}
            list="aether-model-list"
            className={inputCls}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => onProbe()}
            title="Test the connection and fetch the live model list"
            className="mt-1.5 flex-none rounded-brand border border-line bg-surface px-3 py-2 text-[12.5px] font-semibold text-main transition hover:border-brand hover:text-brand disabled:opacity-60"
          >
            ⚡ Test
          </button>
        </div>
        <datalist id="aether-model-list">
          {modelOptions.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>

        {needsKey && (
          <>
            <label className="mt-3 block text-[12.5px] font-semibold text-muted">
              Provider API Key
              <span className="mt-0.5 block text-[11.5px] font-normal text-subtle">
                {activeProvider?.key_configured
                  ? "a key is already configured — leave blank to keep it"
                  : "required for this provider — paste it, then hit ⚡ Test"}
              </span>
            </label>
            <input
              value={form.api_key}
              onChange={set("api_key")}
              placeholder={`${activeProvider?.key_configured ? "sk-•••• (keep existing)" : "sk-…"}`}
              autoComplete="off"
              className={inputCls}
            />
          </>
        )}

        <label className="mt-3 block text-[12.5px] font-semibold text-muted">
          Telegram user ID to notify when active
          <span className="mt-0.5 block text-[11.5px] font-normal text-subtle">
            optional — message the bot, then send /sethome to set it automatically
          </span>
        </label>
        <input
          value={form.notify_chat_id}
          onChange={set("notify_chat_id")}
          placeholder="123456789"
          autoComplete="off"
          className="mt-1.5 w-full rounded-brand border border-line bg-bg px-3 py-2 font-mono text-[13px] text-main outline-none transition-shadow focus:border-brand focus:ring-[3px] focus:ring-brand/15"
        />

        <div className="mt-4 flex gap-2.5">
          <button
            type="submit"
            disabled={busy}
            className="rounded-brand border border-transparent bg-gradient-to-br from-brand to-brand-hover px-4 py-2 text-[13px] font-semibold text-white transition hover:brightness-105 disabled:opacity-60"
          >
            💾 Save &amp; Start Bot
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onStop}
            className="rounded-brand border border-bad/40 bg-bad/10 px-4 py-2 text-[13px] font-semibold text-bad transition hover:brightness-105 disabled:opacity-60"
          >
            🛑 Stop Bot
          </button>
        </div>
      </form>

      <pre
        className={`mt-5 max-w-[560px] overflow-auto rounded-brand-lg border border-line bg-bg-alt p-3.5 font-mono text-xs ${
          resultClass === "ok" ? "text-ok" : resultClass === "err" ? "text-bad" : "text-muted"
        }`}
      >
        {result}
      </pre>
    </section>
  );
}

function StepNo({ n }: { n: number }) {
  return (
    <i className="flex h-5 w-5 flex-none items-center justify-center rounded-full border border-brand/40 bg-brand/15 text-[11px] font-bold not-italic text-brand">
      {n}
    </i>
  );
}

/* ============================ ABOUT ============================ */

function About() {
  return (
    <section>
      <div className="rounded-brand-lg border border-line-subtle bg-surface p-5 shadow-elev">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
          Aether Core · v0.1.0
        </h3>
        <p className="mt-3 text-[13.5px] leading-relaxed text-muted">
          Local-first agent runtime: one fixed agent answers every Telegram message through the
          cognitive engine, backed by a local model (Ollama) or a remote provider (OpenAI,
          Anthropic, OpenRouter, Groq, DeepSeek, xAI, Gemini) — mix-and-match from the Setup tab.
          Setup happens once via the <b className="text-main">Setup</b> tab; this console
          (9Router-style shell, built with Next.js) then monitors the live bridge. Docs and deploy
          notes live in the project README.
        </p>
      </div>
    </section>
  );
}