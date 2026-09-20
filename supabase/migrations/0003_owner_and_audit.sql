-- Foundation for the Revenue & Compliance Operating System (docs/AUDIT.md build step 1).
--
--   1. A third role, `owner`: the firm's owner sees every client (docs/AUDIT.md, assumptions).
--   2. `audit_log`: one append-only, hash-chained record of every meaningful event.
--
-- Tamper evidence is DEMO LEVEL: UPDATE, DELETE and TRUNCATE are refused by triggers, and each row stores the SHA-256 of
-- its content plus the previous row's hash (computed by the backend, see app/services/audit.py), so an edit made by
-- someone who bypasses the triggers shows up in GET /audit/verify. A database administrator can still drop the triggers;
-- this is not a substitute for external log shipping.

-- ---------------------------------------------------------------- owner role
alter table profiles drop constraint if exists profiles_role_check;
alter table profiles add constraint profiles_role_check check (role in ('client', 'advisor', 'owner'));

-- ---------------------------------------------------------------- audit log
create table audit_log (
  id bigint generated always as identity primary key,
  occurred_at timestamptz not null,
  actor_id uuid,                              -- NULL = the system itself
  actor_role text not null check (actor_role in ('client', 'advisor', 'owner', 'system')),
  action text not null,                       -- dotted verb, for example claim.submitted
  entity_type text not null,
  entity_id text,
  client_id uuid,                             -- the data subject, when there is one (for filtering and per-client packs)
  summary text not null,                      -- one human-readable line. Never document text, bank numbers or email bodies
  details jsonb not null default '{}'::jsonb, -- before/after or extra facts (ids, statuses, counts). Same rule as summary
  ip text,
  user_agent text,
  request_id text,
  prev_hash text not null,                    -- hash of the previous row ('' for the first)
  hash text not null
);
create index audit_log_client_idx on audit_log (client_id, id desc);
create index audit_log_actor_idx on audit_log (actor_id, id desc);
create index audit_log_action_idx on audit_log (action, id desc);
create index audit_log_time_idx on audit_log (occurred_at desc);

create function audit_log_guard() returns trigger language plpgsql as $$
begin
  -- The demo reset (scripts/seed.py --reset, POST /demo/reset) sets this for one transaction only.
  if current_setting('app.audit_reset', true) = 'on' then
    if tg_op = 'DELETE' then return old; end if;
    if tg_op = 'UPDATE' then return new; end if;
    return null;                              -- TRUNCATE (statement trigger)
  end if;
  raise exception 'audit_log is append-only (% refused)', tg_op using errcode = 'insufficient_privilege';
end $$;

create trigger audit_log_no_change before update or delete on audit_log
  for each row execute function audit_log_guard();
create trigger audit_log_no_truncate before truncate on audit_log
  for each statement execute function audit_log_guard();

alter table audit_log enable row level security;
