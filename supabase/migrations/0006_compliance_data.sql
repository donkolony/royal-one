-- Compliance data model (docs/AUDIT.md build steps 3, 5, 6): identity vault, consents, advice records.
--
-- Created together because the owner's Business Health view scores all three (compliance health) and the client-health
-- indicator reads them. Write paths and screens arrive with build steps 5 and 6.
--
--   * identity_documents: verified identity documents captured ONCE, with verification metadata and an expiry date. The files
--     live in the private `attachments` bucket under identity/<client_id>/...; only signed URLs ever leave the backend.
--     Verification is SIMULATED behind an interface (app/services/identity.py): `verifier` names the adapter used.
--   * identity_reuse_log: which claim / request / review re-used a stored document instead of asking again, and when.
--   * consents: an append-only history; the current state is the latest row per client and purpose.
--   * advice_records: what was discussed and recommended. An AI may DRAFT the summary; a human must approve it before a row
--     exists (there is no "draft" status: an unapproved draft is never stored).

create table identity_documents (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  doc_type text not null check (doc_type in ('id_document', 'drivers_licence', 'proof_of_address')),
  filename text not null,
  content_type text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  storage_path text not null,
  status text not null default 'pending' check (status in ('pending', 'verified', 'rejected', 'superseded')),
  verification_source text check (verification_source is null or verification_source in ('uploaded', 'simulated_verification')),
  verifier text,                               -- adapter name, for example demo_simulated. Never a claim of a real KYC check
  verified_by uuid references profiles (id),   -- the adviser who confirmed the document
  verified_at timestamptz,
  issued_date date,
  expiry_date date,
  rejected_reason text,
  uploaded_by uuid not null references profiles (id),
  uploaded_at timestamptz not null default now()
);
create index identity_documents_client_idx on identity_documents (client_id, doc_type, status);

create table identity_reuse_log (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references identity_documents (id) on delete cascade,
  client_id uuid not null references clients (id) on delete cascade,
  used_for text not null check (used_for in ('claim', 'request', 'application', 'review')),
  used_for_id uuid,
  used_by uuid references profiles (id),
  used_at timestamptz not null default now()
);
create index identity_reuse_log_doc_idx on identity_reuse_log (document_id, used_at desc);
create index identity_reuse_log_client_idx on identity_reuse_log (client_id, used_at desc);

create table consents (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  purpose text not null check (purpose in ('data_processing', 'marketing', 'insurer_sharing')),
  status text not null check (status in ('granted', 'withdrawn')),
  notice_version text not null,                -- which privacy notice text the client saw
  method text not null check (method in ('in_app', 'in_person', 'written')),
  recorded_by uuid references profiles (id),
  recorded_at timestamptz not null default now()
);
create index consents_client_idx on consents (client_id, purpose, recorded_at desc);

create table advice_records (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  adviser_id uuid not null references profiles (id),
  interaction_type text not null check (interaction_type in ('review', 'advice', 'consultation', 'claim_support')),
  needs_goals jsonb not null default '[]'::jsonb,           -- list of strings the client wanted
  products_considered jsonb not null default '[]'::jsonb,   -- list of {product, category, provider?}
  recommendation text not null,
  ai_draft text,                                            -- what the drafting assistant produced, kept for the record
  draft_source text check (draft_source is null or draft_source in ('template', 'ai')),
  final_summary text not null,                              -- the text the adviser approved
  edited_from_draft boolean not null default false,
  client_acknowledged boolean not null default false,
  acknowledged_at timestamptz,
  acknowledgement_method text check (acknowledgement_method is null or acknowledgement_method in ('in_meeting', 'in_app', 'verbal')),
  approved_by uuid not null references profiles (id),
  approved_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index advice_records_client_idx on advice_records (client_id, created_at desc);

-- ---------------------------------------------------------------- row-level security (a client may see their own records)
select rs_lock_down('public.identity_documents');
select rs_lock_down('public.identity_reuse_log');
select rs_lock_down('public.consents');
select rs_lock_down('public.advice_records');

create policy identity_documents_read on identity_documents for select to authenticated using (rs_can_see_client(client_id));
create policy identity_reuse_log_read on identity_reuse_log for select to authenticated using (rs_can_see_client(client_id));
create policy consents_read on consents for select to authenticated using (rs_can_see_client(client_id));
create policy advice_records_read on advice_records for select to authenticated using (rs_can_see_client(client_id));
