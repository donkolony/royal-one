import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, Plus, X } from "lucide-react";
import { Button, Card, ErrorBanner, PageHeader, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { useAct, useGet } from "@/lib/hooks";
import { humanize, itemsOf } from "@/lib/utils";
import type { Claim, Insurer, Page, Policy } from "@/lib/types";

const STEPS = ["Your policy", "What happened", "Police and people", "Photos and documents", "Check and send"];
const MISSING: Record<string, string> = {
  insurer_id: "Choose your insurer.", "incident.occurred_at": "Enter the date and time of the incident.", "incident.location_text": "Enter where it happened.",
  "incident.description": "Describe what happened.", "police.reported": "Say whether you reported it to the police.", "police.case_number": "Enter the police case number.",
  "driver.is_policyholder": "Say whether the policyholder was driving.", "driver.full_name": "Enter the driver's name.",
  "driver.relationship_to_policyholder": "Say how the driver is related to the policyholder.", vehicle_use: "Say whether the vehicle was used for personal or business use.",
  "attachments.photo": "Add at least one photo.", "attachments.drivers_licence": "Upload the driver's licence.",
};
const SLOTS: { kind: string; label: string; help?: string }[] = [
  { kind: "vehicle_photo", label: "Photos of the vehicles and the damage", help: "At least one photo is required." },
  { kind: "road_photo", label: "The road and the direction of travel" },
  { kind: "plate_or_disc_photo", label: "Licence plates and registration discs" },
  { kind: "drivers_licence", label: "Driver's licence" },
  { kind: "accident_sketch", label: "Sketch of the accident (optional)" },
];
type Person = { name: string; phone?: string };
type Third = { name: string; phone?: string; vehicle_registration?: string; insurer_name?: string; policy_number?: string };
type ClaimX = Claim & { identity?: { drivers_licence: { reused: boolean; state: string; expiry_date: string | null } } };

const inp = "mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600 text-sm";
const Field = ({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) => (
  <label className="block text-sm"><span className="font-medium text-charcoal-700 dark:text-charcoal-200">{label}</span>{children}{hint && <span className="block text-xs text-charcoal-500 mt-1">{hint}</span>}</label>
);
const Radio = ({ value, onChange, options }: { value: boolean | null | undefined; onChange: (v: boolean) => void; options: [boolean, string][] }) => (
  <div className="mt-1 flex gap-4">{options.map(([v, l]) => <label key={l} className="inline-flex items-center gap-2 text-sm"><input type="radio" checked={value === v} onChange={() => onChange(v)} />{l}</label>)}</div>
);

/**
 * Register a motor claim: a real, saved-as-you-go draft. Anything the client has already given us is not asked for again: a verified,
 * unexpired driver's licence from the identity vault is attached automatically, and the upload step says so.
 */
export default function RegisterClaim() {
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const draftId = params.get("draft");
  const [step, setStep] = useState(draftId ? 1 : 0);
  const [insurerId, setInsurerId] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [f, setF] = useState<{ occurred_at: string; location_text: string; description: string; police_reported: boolean | null; case_number: string; station: string;
    is_policyholder: boolean | null; driver_name: string; relationship: string; vehicle_use: string; witnesses: Person[]; third_parties: Third[] }>({
    occurred_at: "", location_text: "", description: "", police_reported: null, case_number: "", station: "", is_policyholder: null, driver_name: "", relationship: "",
    vehicle_use: "", witnesses: [], third_parties: [] });
  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((s) => ({ ...s, [k]: v }));

  const insurers = useGet<{ items: Insurer[] }>(["insurers"], "/insurers");
  const policies = useGet<Page<Policy>>(["policies-motor"], "/policies?category=motor&limit=20");
  const claimQ = useGet<ClaimX>(["claim-draft", draftId], `/claims/${draftId}`, { enabled: !!draftId });
  const claim = claimQ.data;
  const hydrated = useRef(false);
  useEffect(() => {
    if (!claim || hydrated.current) return;
    hydrated.current = true;
    setF({
      occurred_at: claim.incident.occurred_at ? claim.incident.occurred_at.slice(0, 16) : "", location_text: claim.incident.location_text ?? "", description: claim.incident.description ?? "",
      police_reported: claim.police.reported, case_number: claim.police.case_number ?? "", station: claim.police.station ?? "", is_policyholder: claim.driver.is_policyholder,
      driver_name: claim.driver.full_name ?? "", relationship: claim.driver.relationship_to_policyholder ?? "", vehicle_use: claim.vehicle_use ?? "",
      witnesses: (claim.witnesses ?? []).map((w) => ({ name: w.name, phone: w.phone ?? "" })), third_parties: (claim.third_parties ?? []).map((t) => ({ name: t.name, phone: t.phone ?? "", vehicle_registration: t.vehicle_registration ?? "", insurer_name: t.insurer_name ?? "", policy_number: t.policy_number ?? "" })),
    });
  }, [claim]);

  const refresh = [["claim-draft", draftId ?? ""], ["dashboard"]];
  const start = useAct(() => api.post<ClaimX>("/claims", { ...(policyId ? { policy_id: policyId } : {}), ...(insurerId && !policyId ? { insurer_id: insurerId } : {}) }), [],
    (c) => { hydrated.current = false; setParams({ draft: c.id }); setStep(1); });
  const save = useAct((body: Record<string, unknown>) => api.patch<ClaimX>(`/claims/${draftId}`, body), refresh);
  const send = useAct(() => api.post<ClaimX>(`/claims/${draftId}/submit`), [["dashboard"], ["notifications"]], (c) => nav(`/claims/${c.id}`));
  const upload = useAct((v: { file: File; kind: string }) => api.upload(`/claims/${draftId}/attachments`, v.file, { kind: v.kind as never }), refresh);
  const remove = useAct((id: string) => api.del(`/claims/${draftId}/attachments/${id}`), refresh);

  const iso = (v: string) => (v ? new Date(v).toISOString() : null);
  const payloadFor = (s: number): Record<string, unknown> | null => {
    if (s === 1) return { incident: { occurred_at: iso(f.occurred_at), location_text: f.location_text || null, description: f.description || null } };
    if (s === 2) return {
      police: { reported: f.police_reported, case_number: f.police_reported ? f.case_number || null : null, station: f.station || null },
      driver: { is_policyholder: f.is_policyholder, full_name: f.driver_name || null, relationship_to_policyholder: f.is_policyholder === false ? f.relationship || null : null },
      vehicle_use: f.vehicle_use || null,
      witnesses: f.witnesses.filter((w) => w.name.trim()).map((w) => ({ name: w.name.trim(), phone: w.phone || null })),
      third_parties: f.third_parties.filter((t) => t.name.trim()).map((t) => ({ name: t.name.trim(), phone: t.phone || null, vehicle_registration: t.vehicle_registration || null, insurer_name: t.insurer_name || null, policy_number: t.policy_number || null })),
    };
    return null;
  };
  const next = async () => {
    const body = payloadFor(step);
    try {
      if (body) await save.mutateAsync(body);
      setStep((s) => Math.min(s + 1, 4));
    } catch {
      // Keep the current step and display the mutation error so answers can be corrected.
    }
  };

  if (insurers.isLoading || policies.isLoading || (draftId && claimQ.isLoading)) return <Skeleton className="h-96 w-full" />;
  const motor = itemsOf(policies.data);
  const lic = claim?.identity?.drivers_licence;
  const missing = claim?.missing_fields ?? [];
  const attachments = claim?.attachments ?? [];

  return (
    <div className="p-4 md:p-8 max-w-3xl space-y-6">
      <PageHeader title="Register a claim" subtitle="Your answers are saved as you go, so you can leave and come back to this draft." />
      <ol className="flex gap-1" aria-label="Progress">
        {STEPS.map((s, i) => <li key={s} aria-current={i === step ? "step" : undefined} className={`flex-1 text-center text-[11px] leading-tight py-1.5 rounded ${i < step ? "bg-green-500 text-white" : i === step ? "bg-brand-500 text-white" : "bg-charcoal-100 dark:bg-charcoal-700 text-charcoal-500"}`}>{s}</li>)}
      </ol>
      {claimQ.error ? <ErrorBanner error={claimQ.error} /> : null}

      {step === 0 && (
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Which policy is this claim on?</h2>
          {motor.length > 0 ? (
            <Field label="Your motor policy">
              <select value={policyId} onChange={(e) => { setPolicyId(e.target.value); setInsurerId(""); }} className={inp}>
                <option value="">Choose a policy…</option>
                {motor.map((p) => <option key={p.id} value={p.id}>{p.product_name} · {p.insurer.name} ({p.policy_number})</option>)}
              </select>
            </Field>
          ) : null}
          {!policyId && (
            <Field label={motor.length ? "…or choose your insurer" : "Your insurer"}>
              <select value={insurerId} onChange={(e) => setInsurerId(e.target.value)} className={inp}>
                <option value="">Choose an insurer…</option>
                {itemsOf(insurers.data).map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
            </Field>
          )}
          {start.error ? <ErrorBanner error={start.error} /> : null}
          <Button disabled={!policyId && !insurerId} loading={start.isPending} onClick={() => start.mutate()}>Start my claim</Button>
        </Card>
      )}

      {step === 1 && (
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">What happened?</h2>
          <Field label="When did it happen?"><input type="datetime-local" max={new Date().toISOString().slice(0, 16)} value={f.occurred_at} onChange={(e) => set("occurred_at", e.target.value)} className={inp} /></Field>
          <Field label="Where did it happen?" hint="The address, or the nearest cross streets."><input value={f.location_text} onChange={(e) => set("location_text", e.target.value)} maxLength={300} className={inp} /></Field>
          <Field label="What happened?" hint="At least 10 characters."><textarea rows={4} value={f.description} onChange={(e) => set("description", e.target.value)} maxLength={4000} className={inp} /></Field>
        </Card>
      )}

      {step === 2 && (
        <Card className="space-y-5">
          <h2 className="text-lg font-semibold">Police, driver and other people</h2>
          <Field label="Did you report it to the police?"><Radio value={f.police_reported} onChange={(v) => set("police_reported", v)} options={[[true, "Yes"], [false, "Not yet"]]} /></Field>
          {f.police_reported && <div className="grid sm:grid-cols-2 gap-3"><Field label="Police case number"><input value={f.case_number} onChange={(e) => set("case_number", e.target.value)} className={inp} /></Field><Field label="Police station (optional)"><input value={f.station} onChange={(e) => set("station", e.target.value)} className={inp} /></Field></div>}
          <Field label="Was the policyholder driving?"><Radio value={f.is_policyholder} onChange={(v) => set("is_policyholder", v)} options={[[true, "Yes"], [false, "No"]]} /></Field>
          <div className="grid sm:grid-cols-2 gap-3">
            <Field label="Driver's full name"><input value={f.driver_name} onChange={(e) => set("driver_name", e.target.value)} className={inp} /></Field>
            {f.is_policyholder === false && <Field label="How are they related to you?"><input value={f.relationship} onChange={(e) => set("relationship", e.target.value)} className={inp} /></Field>}
          </div>
          <Field label="Was the vehicle used for personal or business use?"><select value={f.vehicle_use} onChange={(e) => set("vehicle_use", e.target.value)} className={inp}><option value="">Choose…</option><option value="personal">Personal</option><option value="business">Business</option></select></Field>

          <fieldset><legend className="text-sm font-medium">Witnesses</legend>
            {f.witnesses.map((w, i) => (
              <div key={i} className="mt-2 flex gap-2"><input aria-label={`Witness ${i + 1} name`} placeholder="Name" value={w.name} onChange={(e) => set("witnesses", f.witnesses.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} className={inp + " mt-0"} />
                <input aria-label={`Witness ${i + 1} phone`} placeholder="Phone" value={w.phone ?? ""} onChange={(e) => set("witnesses", f.witnesses.map((x, j) => (j === i ? { ...x, phone: e.target.value } : x)))} className={inp + " mt-0"} />
                <button type="button" aria-label="Remove witness" onClick={() => set("witnesses", f.witnesses.filter((_, j) => j !== i))}><X className="w-4 h-4" /></button></div>
            ))}
            <button type="button" onClick={() => set("witnesses", [...f.witnesses, { name: "" }])} className="mt-2 inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"><Plus className="w-3 h-3" />Add a witness</button>
          </fieldset>
          <fieldset><legend className="text-sm font-medium">Other vehicles or people involved</legend>
            {f.third_parties.map((t, i) => (
              <div key={i} className="mt-2 grid sm:grid-cols-2 gap-2 rounded-md border border-charcoal-200 dark:border-charcoal-700 p-3">
                {(["name", "phone", "vehicle_registration", "insurer_name", "policy_number"] as const).map((k) => (
                  <input key={k} aria-label={`Party ${i + 1} ${humanize(k)}`} placeholder={humanize(k)} value={t[k] ?? ""} onChange={(e) => set("third_parties", f.third_parties.map((x, j) => (j === i ? { ...x, [k]: e.target.value } : x)))} className={inp + " mt-0"} />
                ))}
                <button type="button" onClick={() => set("third_parties", f.third_parties.filter((_, j) => j !== i))} className="text-xs text-accent-600 text-left hover:underline">Remove</button>
              </div>
            ))}
            <button type="button" onClick={() => set("third_parties", [...f.third_parties, { name: "" }])} className="mt-2 inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"><Plus className="w-3 h-3" />Add another party</button>
          </fieldset>
        </Card>
      )}

      {step === 3 && (
        <Card className="space-y-5">
          <h2 className="text-lg font-semibold">Photos and documents</h2>
          {SLOTS.map((s) => {
            const mine = attachments.filter((a) => a.kind === s.kind);
            const reused = s.kind === "drivers_licence" && lic?.reused;
            return (
              <div key={s.kind} className="border-b border-charcoal-100 dark:border-charcoal-700 pb-4 last:border-0">
                <p className="text-sm font-medium">{s.label}</p>
                {reused ? (
                  <p className="mt-1 flex items-start gap-2 text-sm text-green-800 dark:text-green-200"><CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />We already have your verified driver's licence{lic?.expiry_date ? ` (valid until ${lic.expiry_date})` : ""}. You do not need to upload it again.</p>
                ) : (
                  <>
                    {s.help && <p className="text-xs text-charcoal-500">{s.help}</p>}
                    {s.kind === "drivers_licence" && lic && lic.state !== "missing" && <p className="text-xs text-amber-700 dark:text-amber-300">Your licence on file is {lic.state}, so please upload a current one.</p>}
                    <ul className="mt-1 text-sm space-y-1">{mine.map((a) => <li key={a.id} className="flex items-center gap-2">{a.filename}<button type="button" aria-label={`Remove ${a.filename}`} onClick={() => remove.mutate(a.id)}><X className="w-3.5 h-3.5 text-accent-600" /></button></li>)}</ul>
                    <input type="file" aria-label={`Add ${s.label}`} accept="image/jpeg,image/png,image/webp,application/pdf" className="mt-2 text-sm" onChange={(e) => { const file = e.target.files?.[0]; if (file) upload.mutate({ file, kind: s.kind }); e.target.value = ""; }} />
                  </>
                )}
              </div>
            );
          })}
          {(upload.error || remove.error) ? <ErrorBanner error={upload.error || remove.error} /> : null}
          {upload.isPending && <p role="status" className="text-sm text-charcoal-500">Uploading…</p>}
        </Card>
      )}

      {step === 4 && (
        <Card className="space-y-4">
          <h2 className="text-lg font-semibold">Check and send</h2>
          {missing.length > 0 ? (
            <div role="alert" className="rounded-md bg-amber-50 dark:bg-amber-900/30 text-amber-900 dark:text-amber-100 p-3 text-sm">
              <p className="font-semibold">Still needed before you can send this:</p>
              <ul className="list-disc pl-5 mt-1">{missing.map((m) => <li key={m}>{MISSING[m] ?? m}</li>)}</ul>
            </div>
          ) : <p className="flex items-center gap-2 text-sm text-green-800 dark:text-green-200"><CheckCircle2 className="w-4 h-4" aria-hidden="true" />Everything we need is here.</p>}
          <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div><dt className="text-xs uppercase text-charcoal-500">Where and when</dt><dd>{claim?.incident.location_text ?? "–"} · {claim?.incident.occurred_at ? new Date(claim.incident.occurred_at).toLocaleString("en-ZA") : "–"}</dd></div>
            <div><dt className="text-xs uppercase text-charcoal-500">Police case</dt><dd>{claim?.police.case_number ?? "–"}</dd></div>
            <div><dt className="text-xs uppercase text-charcoal-500">Driver</dt><dd>{claim?.driver.full_name ?? "–"}</dd></div>
            <div><dt className="text-xs uppercase text-charcoal-500">Documents</dt><dd>{attachments.length} attached{lic?.reused ? " (licence from your identity vault)" : ""}</dd></div>
          </dl>
          {send.error ? <ErrorBanner error={send.error} /> : null}
        </Card>
      )}

      {step > 0 && (
        <div className="flex justify-between">
          <Button variant="ghost" onClick={() => setStep((s) => Math.max(1, s - 1))} disabled={step === 1}>Back</Button>
          {step < 4 ? <Button onClick={() => void next()} loading={save.isPending}>Save and continue</Button>
            : <Button onClick={() => send.mutate()} disabled={missing.length > 0} loading={send.isPending}>Send to Royal Square</Button>}
        </div>
      )}
      {save.error ? <ErrorBanner error={save.error} /> : null}
    </div>
  );
}
