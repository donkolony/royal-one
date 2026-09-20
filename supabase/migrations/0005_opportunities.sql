-- Opportunity Radar (docs/AUDIT.md build step 2, brief section A).
--
--   * clients.dependants and clients.annual_income_cents: two OPTIONAL, adviser-entered fields. The under-insurance rule needs
--     them; without them that rule does not run (it never guesses). Listed on the privacy page.
--   * policies.category gains 'disability' (disability / income protection).
--   * life_events: things an adviser notes that create a natural reason to talk (new baby, marriage, ...).
--   * opportunities + opportunity_events: detected by rules (app/services/radar.py), with a full lifecycle.
--   * reminders can point at an opportunity (the "Create task" button).

alter table clients add column dependants smallint check (dependants is null or dependants between 0 and 20);
alter table clients add column annual_income_cents bigint check (annual_income_cents is null or annual_income_cents >= 0);

alter table policies drop constraint policies_category_check;
alter table policies add constraint policies_category_check check (category in
  ('motor', 'life', 'health', 'funeral', 'personal_other', 'commercial', 'investment', 'retirement', 'disability'));

alter table reminders drop constraint reminders_related_resource_check;
alter table reminders add constraint reminders_related_resource_check check
  (related_resource is null or related_resource in ('policy', 'claim', 'client', 'opportunity'));

-- ---------------------------------------------------------------- life events
create table life_events (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  kind text not null check (kind in ('new_baby', 'marriage', 'new_vehicle', 'property_purchase', 'divorce', 'job_change')),
  occurred_on date not null,
  note text check (note is null or length(note) <= 300),
  recorded_by uuid references profiles (id),
  created_at timestamptz not null default now()
);
create index life_events_client_idx on life_events (client_id, occurred_on desc);

-- ---------------------------------------------------------------- opportunities
create table opportunities (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  signal text not null check (signal in (
    'under_insured_life', 'goal_behind', 'life_event', 'missing_cover', 'single_product', 'lapsed_cover', 'expiring_document')),
  dedupe_key text not null unique,            -- signal + client + subject + period: the same fact never surfaces twice
  title text not null,
  why_now text not null,                      -- deterministic wording built from the evidence
  suggested_action text not null,
  talking_points jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '{}'::jsonb,   -- the actual numbers and fields that triggered it
  is_touchpoint boolean not null default false,  -- a reason to talk that carries no estimated sale
  est_annual_premium_cents bigint not null default 0 check (est_annual_premium_cents >= 0),
  est_annual_value_cents bigint not null default 0 check (est_annual_value_cents >= 0),   -- DEMO ESTIMATE, see radar_config.py
  value_formula text not null,
  status text not null default 'open' check (status in ('open', 'snoozed', 'actioned', 'won', 'lost', 'expired')),
  snoozed_until date,
  outcome_reason text,
  won_value_cents bigint check (won_value_cents is null or won_value_cents >= 0),
  task_reminder_id uuid references reminders (id) on delete set null,
  surfaced_at timestamptz not null default now(),
  actioned_at timestamptz,
  closed_at timestamptz,
  closed_by uuid references profiles (id),
  last_seen_at timestamptz not null default now(),   -- the last time the rule still found this to be true
  updated_at timestamptz not null default now()
);
create index opportunities_client_idx on opportunities (client_id, status);
create index opportunities_status_idx on opportunities (status, est_annual_value_cents desc);

create table opportunity_events (
  id uuid primary key default gen_random_uuid(),
  opportunity_id uuid not null references opportunities (id) on delete cascade,
  kind text not null check (kind in (
    'surfaced', 'task_created', 'draft_generated', 'outreach_logged', 'snoozed', 'unsnoozed', 'won', 'lost', 'reopened', 'expired')),
  actor_id uuid references profiles (id),     -- NULL = the system
  channel text check (channel is null or channel in ('email', 'whatsapp', 'call', 'meeting')),
  note text,
  created_at timestamptz not null default clock_timestamp()
);
create index opportunity_events_idx on opportunity_events (opportunity_id, created_at);

-- ---------------------------------------------------------------- row-level security
select rs_lock_down('public.life_events');
select rs_lock_down('public.opportunities');
select rs_lock_down('public.opportunity_events');

-- A client may see the life events recorded about them. Opportunities are internal commercial notes: staff only.
create policy life_events_read on life_events for select to authenticated using (rs_can_see_client(client_id));
create policy opportunities_read on opportunities for select to authenticated using (
  rs_role() in ('advisor', 'owner') and rs_can_see_client(client_id)
);
create policy opportunity_events_read on opportunity_events for select to authenticated using (
  exists (select 1 from opportunities o where o.id = opportunity_events.opportunity_id)
);
