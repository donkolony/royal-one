import React, { useState } from "react";
import { Plus, X } from "lucide-react";
import { Badge, Button, ErrorBanner, Modal } from "../ui";
import { api } from "../../lib/api";
import { useAct } from "../../lib/hooks";
import type { AdviceDraft } from "../../lib/typesExt";

const TYPES: [string, string][] = [["review", "Annual review"], ["advice", "Advice meeting"], ["consultation", "Consultation"], ["claim_support", "Claims support"]];
const CATS = ["life", "disability", "funeral", "personal_other", "motor", "health", "commercial", "investment", "retirement"];
const inp = "mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600 text-sm";

/**
 * Record advice. The system DRAFTS a summary from the adviser's notes; nothing is saved until the adviser has read it, edited it if
 * needed, and explicitly approved it. The original draft is kept beside the approved text so the record shows what was changed.
 */
export function AdviceModal({ clientId, clientName, open, onClose }: { clientId: string; clientName: string; open: boolean; onClose: () => void }) {
  const [type, setType] = useState("review");
  const [goals, setGoals] = useState("");
  const [products, setProducts] = useState<{ product: string; category: string }[]>([{ product: "", category: "life" }]);
  const [rec, setRec] = useState("");
  const [draft, setDraft] = useState<AdviceDraft | null>(null);
  const [text, setText] = useState("");
  const [approved, setApproved] = useState(false);
  const [ack, setAck] = useState(false);

  const notes = () => ({
    client_id: clientId, interaction_type: type, needs_goals: goals.split("\n").map((g) => g.trim()).filter(Boolean),
    products_considered: products.filter((p) => p.product.trim()).map((p) => ({ product: p.product.trim(), category: p.category })), recommendation: rec.trim(),
  });
  const makeDraft = useAct(() => api.post<AdviceDraft>("/advice-records/draft", notes()), [], (d) => { setDraft(d); setText(d.draft.summary); setApproved(false); });
  const save = useAct(
    () => api.post("/advice-records", { ...notes(), final_summary: text.trim(), ai_draft: draft?.draft.summary ?? null, draft_source: draft?.draft.source ?? null, approved, client_acknowledged: ack, acknowledgement_method: ack ? "in_meeting" : null }),
    [["client-compliance", clientId], ["client-timeline", clientId], ["business-health"], ["compliance-overview"], ["client-health", clientId], ["audit"]],
    () => { setDraft(null); setGoals(""); setRec(""); setProducts([{ product: "", category: "life" }]); setApproved(false); setAck(false); onClose(); },
  );
  const canDraft = rec.trim().length >= 3;

  return (
    <Modal open={open} onClose={onClose} title={`Record advice: ${clientName}`} size="lg"
      footer={draft ? <><Button variant="ghost" onClick={() => setDraft(null)}>Back to notes</Button><Button disabled={!approved || text.trim().length < 20} loading={save.isPending} onClick={() => save.mutate()}>Save advice record</Button></>
        : <><Button variant="ghost" onClick={onClose}>Cancel</Button><Button disabled={!canDraft} loading={makeDraft.isPending} onClick={() => makeDraft.mutate()}>Draft the summary</Button></>}>
      {!draft ? (
        <div className="space-y-4 text-sm">
          <label className="block"><span className="font-medium">What kind of interaction?</span><select value={type} onChange={(e) => setType(e.target.value)} className={inp}>{TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="block"><span className="font-medium">Needs and goals discussed (one per line)</span><textarea rows={3} value={goals} onChange={(e) => setGoals(e.target.value)} className={inp} /></label>
          <fieldset><legend className="font-medium">Products considered</legend>
            {products.map((p, i) => (
              <div key={i} className="mt-1 flex gap-2"><input aria-label={`Product ${i + 1}`} placeholder="Product" value={p.product} onChange={(e) => setProducts(products.map((x, j) => (j === i ? { ...x, product: e.target.value } : x)))} className={inp + " mt-0"} />
                <select aria-label={`Category ${i + 1}`} value={p.category} onChange={(e) => setProducts(products.map((x, j) => (j === i ? { ...x, category: e.target.value } : x)))} className={inp + " mt-0 w-44"}>{CATS.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}</select>
                {products.length > 1 && <button type="button" aria-label="Remove product" onClick={() => setProducts(products.filter((_, j) => j !== i))}><X className="w-4 h-4" /></button>}</div>
            ))}
            <button type="button" onClick={() => setProducts([...products, { product: "", category: "life" }])} className="mt-1 inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"><Plus className="w-3 h-3" />Add a product</button>
          </fieldset>
          <label className="block"><span className="font-medium">Your recommendation</span><textarea rows={3} value={rec} onChange={(e) => setRec(e.target.value)} className={inp} /></label>
          {makeDraft.error ? <ErrorBanner error={makeDraft.error} /> : null}
        </div>
      ) : (
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap items-center gap-2"><Badge variant={draft.draft.source === "ai" ? "info" : "default"}>{draft.draft.source === "ai" ? "AI-polished draft" : "Standard draft"}</Badge><span className="text-charcoal-500">{draft.note}</span></div>
          {draft.warnings.map((w) => <p key={w} role="status" className="rounded bg-amber-50 text-amber-900 p-2 text-xs">{w}</p>)}
          <label className="block"><span className="font-medium">Summary (edit it until it is right)</span><textarea rows={8} value={text} onChange={(e) => { setText(e.target.value); setApproved(false); }} className={inp} /></label>
          <label className="flex items-start gap-2"><input type="checkbox" checked={approved} onChange={(e) => setApproved(e.target.checked)} className="mt-0.5" /><span><strong>I have read this summary and I approve it as the record of the meeting.</strong> It is saved in my name.</span></label>
          <label className="flex items-start gap-2"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-0.5" /><span>The client acknowledged this summary in the meeting. (Otherwise they are asked to confirm it in the app.)</span></label>
          {save.error ? <ErrorBanner error={save.error} /> : null}
        </div>
      )}
    </Modal>
  );
}
