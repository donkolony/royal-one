import React, { useState } from "react";
import { Button, ErrorBanner, Modal } from "../ui";
import { api } from "../../lib/api";
import { useAct } from "../../lib/hooks";

const inp = "mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600 text-sm";
const F = ({ label, children }: { label: string; children: React.ReactNode }) => <label className="block text-sm"><span className="font-medium">{label}</span>{children}</label>;
const cents = (v: string) => Math.round(Number(v || 0) * 100);
const done = (id: string) => [["client-goals", id], ["client-items", id], ["client-reminders", id], ["clientDashboard", id], ["client", id], ["advisorDashboard"], ["opportunities"], ["client-health", id], ["audit"]];

interface Props { clientId: string; open: boolean; onClose: () => void; categories?: string[] }

export function AddGoalModal({ clientId, open, onClose, categories = [] }: Props) {
  const [f, setF] = useState({ title: "", category: categories[0] ?? "other", target: "", current: "", date: "" });
  const m = useAct(() => api.post("/goals", { client_ids: [clientId], title: f.title.trim(), category: f.category, target_amount_cents: cents(f.target), current_amount_cents: cents(f.current), ...(f.date ? { target_date: f.date } : {}) }), done(clientId), onClose);
  return (
    <Modal open={open} onClose={onClose} title="Add a goal" size="sm" footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button disabled={!f.title.trim() || Number(f.target) <= 0} loading={m.isPending} onClick={() => m.mutate()}>Add goal</Button></>}>
      <div className="space-y-3">
        <F label="Title"><input className={inp} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} maxLength={120} /></F>
        <F label="Category"><select className={inp} value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{categories.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}</select></F>
        <div className="grid grid-cols-2 gap-3"><F label="Target (rand)"><input className={inp} inputMode="decimal" value={f.target} onChange={(e) => setF({ ...f, target: e.target.value })} /></F><F label="Saved so far (rand)"><input className={inp} inputMode="decimal" value={f.current} onChange={(e) => setF({ ...f, current: e.target.value })} /></F></div>
        <F label="Target date (optional)"><input type="date" min={new Date().toISOString().slice(0, 10)} className={inp} value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></F>
        {m.error ? <ErrorBanner error={m.error} /> : null}
      </div>
    </Modal>
  );
}

export function AddItemModal({ clientId, open, onClose, assets = [], liabilities = [] }: Props & { assets?: string[]; liabilities?: string[] }) {
  const [f, setF] = useState({ kind: "asset", category: assets[0] ?? "cash", label: "", amount: "" });
  const cats = f.kind === "asset" ? assets : liabilities;
  const m = useAct(() => api.post("/financial-items", { client_id: clientId, kind: f.kind, category: f.category, label: f.label.trim(), amount_cents: cents(f.amount), as_of_date: new Date().toISOString().slice(0, 10) }), done(clientId), onClose);
  return (
    <Modal open={open} onClose={onClose} title="Add a balance-sheet item" size="sm" footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button disabled={!f.label.trim() || Number(f.amount) <= 0} loading={m.isPending} onClick={() => m.mutate()}>Add</Button></>}>
      <div className="space-y-3">
        <F label="Type"><select className={inp} value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value, category: (e.target.value === "asset" ? assets : liabilities)[0] })}><option value="asset">Asset</option><option value="liability">Liability</option></select></F>
        <F label="Category"><select className={inp} value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{cats.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}</select></F>
        <F label="Description"><input className={inp} value={f.label} onChange={(e) => setF({ ...f, label: e.target.value })} maxLength={120} /></F>
        <F label="Amount (rand)"><input className={inp} inputMode="decimal" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></F>
        {m.error ? <ErrorBanner error={m.error} /> : null}
      </div>
    </Modal>
  );
}

export function AddReminderModal({ clientId, open, onClose }: Props) {
  const [f, setF] = useState({ title: "", date: "", audience: "advisor" });
  const m = useAct(() => api.post("/reminders", { client_id: clientId, type: "custom", title: f.title.trim(), due_date: f.date, audience: f.audience }), done(clientId), onClose);
  return (
    <Modal open={open} onClose={onClose} title="Add a reminder" size="sm" footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button disabled={!f.title.trim() || !f.date} loading={m.isPending} onClick={() => m.mutate()}>Add reminder</Button></>}>
      <div className="space-y-3">
        <F label="What to remember"><input className={inp} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} maxLength={160} /></F>
        <F label="Due date"><input type="date" className={inp} value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></F>
        <F label="Who sees it"><select className={inp} value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })}><option value="advisor">Me only</option><option value="client">The client</option><option value="both">Both of us</option></select></F>
        {m.error ? <ErrorBanner error={m.error} /> : null}
      </div>
    </Modal>
  );
}

export function NeedsForm({ clientId, dependants, income }: { clientId: string; dependants: number | null | undefined; income: number | null | undefined }) {
  const [d, setD] = useState(dependants?.toString() ?? "");
  const [i, setI] = useState(income ? String(income / 100) : "");
  const m = useAct(() => api.patch(`/clients/${clientId}`, { dependants: d === "" ? null : Number(d), annual_income_cents: i === "" ? null : cents(i) }), done(clientId));
  return (
    <form className="mt-3 flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <F label="Dependants"><input className={inp + " w-24"} inputMode="numeric" value={d} onChange={(e) => setD(e.target.value.replace(/[^0-9]/g, ""))} /></F>
      <F label="Annual income (rand)"><input className={inp + " w-40"} inputMode="decimal" value={i} onChange={(e) => setI(e.target.value)} /></F>
      <Button type="submit" size="sm" variant="secondary" loading={m.isPending}>Save</Button>
      {m.error ? <div className="w-full"><ErrorBanner error={m.error} /></div> : null}
    </form>
  );
}
