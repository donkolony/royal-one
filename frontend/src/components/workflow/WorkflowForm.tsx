import React, { useMemo, useState } from "react";
import { Plus, X } from "lucide-react";
import { Button, ErrorBanner } from "../ui";
import { describeError } from "../../lib/errors";
import type { RequestField, RequestTypeDef } from "../../lib/typesExt";

type Values = Record<string, unknown>;
interface PolicyOption { id: string; product_name: string; policy_number: string; category: string }

interface Props {
  workflow: RequestTypeDef;
  policies: PolicyOption[];
  submitting?: boolean;
  error?: unknown;
  onSubmit: (payload: Values, note: string) => void;
  onCancel: () => void;
}

const input = "mt-1 w-full rounded-md border-charcoal-300 dark:bg-charcoal-900 dark:border-charcoal-600 text-sm";

/**
 * Renders ANY request workflow from its field definitions (GET /requests/types). A new request type in the backend config appears
 * here with no new code. The server validates again; its field errors are shown next to the field they belong to.
 */
export function WorkflowForm({ workflow, policies, submitting, error, onSubmit, onCancel }: Props) {
  const [values, setValues] = useState<Values>({});
  const [note, setNote] = useState("");
  const info = error ? describeError(error) : null;
  const fieldErrors = useMemo(() => {
    const m: Record<string, string> = {};
    info?.details.forEach((d) => { m[d.field.replace(/^payload\./, "")] = d.message; });
    return m;
  }, [info]);
  const set = (name: string, v: unknown) => setValues((s) => ({ ...s, [name]: v }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: Values = {};
    for (const f of workflow.fields) {
      const v = values[f.name];
      if (v === undefined || v === "" || (Array.isArray(v) && v.length === 0)) continue;
      payload[f.name] = v;
    }
    onSubmit(payload, note.trim());
  };

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <p className="text-sm text-charcoal-600 dark:text-charcoal-300">{workflow.description}</p>
      {workflow.fields.map((f) => (
        <FieldInput key={f.name} field={f} value={values[f.name]} onChange={(v) => set(f.name, v)} policies={policies} error={fieldErrors[f.name]} />
      ))}
      <label className="block text-sm">
        <span className="font-medium text-charcoal-700 dark:text-charcoal-200">Anything else your adviser should know (optional)</span>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={1000} className={input} />
      </label>
      {info && Object.keys(fieldErrors).length === 0 ? <ErrorBanner error={error} /> : null}
      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button type="submit" loading={submitting}>Send request</Button>
      </div>
    </form>
  );
}

function FieldInput({ field: f, value, onChange, policies, error }: { field: RequestField; value: unknown; onChange: (v: unknown) => void; policies: PolicyOption[]; error?: string }) {
  const id = `f-${f.name}`;
  const label = (
    <span className="font-medium text-charcoal-700 dark:text-charcoal-200">
      {f.label}{f.required ? <span className="text-accent-600" aria-hidden="true"> *</span> : <span className="text-charcoal-400 font-normal"> (optional)</span>}
    </span>
  );
  const err = error ? <p role="alert" className="mt-1 text-xs text-accent-600">{error}</p> : null;
  const invalid = error ? { "aria-invalid": true as const, "aria-describedby": `${id}-err` } : {};
  const wrap = (child: React.ReactNode) => <div className="text-sm"><label htmlFor={id}>{label}</label>{child}<div id={`${id}-err`}>{err}</div></div>;

  switch (f.type) {
    case "string":
      return wrap(<input id={id} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} maxLength={f.max_length} className={input} {...invalid} />);
    case "text":
      return wrap(<textarea id={id} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} rows={3} maxLength={f.max_length} className={input} {...invalid} />);
    case "date":
      return wrap(<input id={id} type="date" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} className={input} {...invalid} />);
    case "integer":
      return wrap(<input id={id} type="number" inputMode="numeric" min={f.min} max={f.max} value={(value as number | undefined) ?? ""} onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} className={input} {...invalid} />);
    case "boolean":
      return <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} /><span>{f.label}</span></label>;
    case "enum":
      return wrap(
        <select id={id} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} className={input} {...invalid}>
          <option value="">Choose…</option>
          {(f.options ?? []).map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
        </select>,
      );
    case "uuid": {
      const list = policies.filter((p) => (f.ref === "motor_policy" ? p.category === "motor" : true));
      return wrap(
        <select id={id} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} className={input} {...invalid}>
          <option value="">Choose a policy…</option>
          {list.map((p) => <option key={p.id} value={p.id}>{p.product_name} ({p.policy_number})</option>)}
        </select>,
      );
    }
    case "string_list":
      return wrap(<textarea id={id} rows={3} placeholder="One per line" value={((value as string[]) ?? []).join("\n")} onChange={(e) => onChange(e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))} className={input} {...invalid} />);
    case "date_list": {
      const list = (value as string[]) ?? [""];
      return (
        <fieldset className="text-sm">
          <legend>{label}</legend>
          <div className="mt-1 space-y-2">
            {list.map((d, i) => (
              <div key={i} className="flex gap-2"><input aria-label={`${f.label} ${i + 1}`} type="date" value={d} onChange={(e) => onChange(list.map((x, j) => (j === i ? e.target.value : x)))} className={input + " mt-0"} />
                {list.length > 1 && <button type="button" aria-label="Remove date" onClick={() => onChange(list.filter((_, j) => j !== i))}><X className="w-4 h-4" /></button>}</div>
            ))}
            {list.length < (f.max_items ?? 3) && <button type="button" onClick={() => onChange([...list, ""])} className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"><Plus className="w-3 h-3" />Add another date</button>}
          </div>
          {err}
        </fieldset>
      );
    }
    case "object_list": {
      const rows = (value as Values[]) ?? [{}];
      return (
        <fieldset className="text-sm">
          <legend>{label}</legend>
          <div className="mt-1 space-y-3">
            {rows.map((row, i) => (
              <div key={i} className="rounded-md border border-charcoal-200 dark:border-charcoal-700 p-3 space-y-2">
                {(f.item_fields ?? []).map((sf) => (
                  <FieldInput key={sf.name} field={{ ...sf, name: `${f.name}-${i}-${sf.name}` }} value={row[sf.name]} policies={policies}
                    onChange={(v) => onChange(rows.map((r, j) => (j === i ? { ...r, [sf.name]: sf.type === "integer" && v !== "" ? Number(v) : v } : r)))} />
                ))}
                {rows.length > 1 && <button type="button" onClick={() => onChange(rows.filter((_, j) => j !== i))} className="text-xs text-accent-600 hover:underline">Remove</button>}
              </div>
            ))}
            {rows.length < (f.max_items ?? 10) && <button type="button" onClick={() => onChange([...rows, {}])} className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"><Plus className="w-3 h-3" />Add a row</button>}
          </div>
          {err}
        </fieldset>
      );
    }
    default:
      return null;
  }
}
