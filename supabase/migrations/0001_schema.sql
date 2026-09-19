-- Royal Square Platform: core schema.
-- Design notes are in docs/ARCHITECT.md section 5.
--
-- Conventions
--   * Enums are text columns with CHECK constraints (easier to migrate than enum types).
--   * Money is bigint cents.
--   * Row-level security is ENABLED on every table with NO policies (default deny). The Supabase anon
--     key is public, so this is what stops the browser reading tables directly. The backend connects
--     with a privileged role and enforces access rules itself (docs/ARCHITECT.md section 4).
--   * Everything here is plain PostgreSQL, so it also runs on a stock Postgres for tests. Pieces that
--     only exist on Supabase (auth.users, storage.buckets) are applied conditionally.

-- ---------------------------------------------------------------- identity
create table profiles (
  id uuid primary key,                      -- equals auth.users.id on Supabase
  role text not null check (role in ('client', 'advisor')),
  full_name text not null,
  email text not null unique,
  phone text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table clients (
  id uuid primary key references profiles (id) on delete cascade,
  adviser_id uuid not null references profiles (id),
  date_of_birth date,
  drivers_licence_expiry date,
  client_since date,
  last_annual_review_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index clients_adviser_idx on clients (adviser_id);

-- ---------------------------------------------------------------- reference data
create table insurers (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  -- Used only to recognise insurer senders in the (simulated) mailbox.
  email_domains text[] not null default '{}'
);

-- ---------------------------------------------------------------- policies and finances
create table policies (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  insurer_id uuid not null references insurers (id),
  category text not null check (category in
    ('motor', 'life', 'health', 'funeral', 'personal_other', 'commercial', 'investment', 'retirement')),
  product_name text not null,
  policy_number text not null,
  status text not null default 'active' check (status in ('active', 'pending', 'lapsed', 'cancelled')),
  asset_description text,
  cover_amount_cents bigint check (cover_amount_cents is null or cover_amount_cents >= 0),
  current_value_cents bigint check (current_value_cents is null or current_value_cents >= 0),
  premium_cents bigint check (premium_cents is null or premium_cents >= 0),
  premium_frequency text check (premium_frequency is null or premium_frequency in ('monthly', 'annual')),
  start_date date,
  renewal_date date,
  valuation_certificate_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index policies_client_idx on policies (client_id);

create table financial_items (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  kind text not null check (kind in ('asset', 'liability')),
  category text not null check (category in (
    'property', 'vehicle', 'cash', 'investments', 'retirement', 'business', 'other_asset',
    'home_loan', 'vehicle_finance', 'credit_card', 'personal_loan', 'other_liability')),
  label text not null,
  amount_cents bigint not null check (amount_cents > 0),
  as_of_date date not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index financial_items_client_idx on financial_items (client_id);

-- ---------------------------------------------------------------- goals
create table goals (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  category text not null check (category in
    ('retirement', 'education', 'property', 'emergency_fund', 'travel', 'debt_repayment', 'other')),
  status text not null default 'active' check (status in ('active', 'achieved', 'archived')),
  target_amount_cents bigint not null check (target_amount_cents > 0),
  current_amount_cents bigint not null default 0 check (current_amount_cents >= 0),
  target_date date,
  created_by uuid not null references profiles (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table goal_participants (
  goal_id uuid not null references goals (id) on delete cascade,
  client_id uuid not null references clients (id) on delete cascade,
  primary key (goal_id, client_id)
);
create index goal_participants_client_idx on goal_participants (client_id);

-- ---------------------------------------------------------------- reminders
create table reminders (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  type text not null,                       -- open set: new types are added in code
  title text not null,
  description text,
  due_date date not null,
  audience text not null check (audience in ('client', 'advisor', 'both')),
  status text not null default 'pending' check (status in ('pending', 'done', 'dismissed')),
  source text not null check (source in ('rule', 'manual')),
  related_resource text check (related_resource is null or related_resource in ('policy', 'claim', 'client')),
  related_id uuid,
  -- Makes computed-on-read generation idempotent. NULL for manual reminders.
  dedupe_key text unique,
  completed_at timestamptz,
  completed_by uuid references profiles (id),
  created_by uuid references profiles (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index reminders_client_idx on reminders (client_id, status, due_date);

-- ---------------------------------------------------------------- claims
create sequence claim_reference_seq;

create table claims (
  id uuid primary key default gen_random_uuid(),
  reference text unique,                    -- CLM-<year>-<number>, assigned at submit
  client_id uuid not null references clients (id) on delete cascade,
  policy_id uuid references policies (id) on delete set null,
  insurer_id uuid references insurers (id),
  status text not null default 'draft' check (status in (
    'draft', 'submitted', 'registered', 'assessment', 'quotes', 'authorised', 'in_repair', 'completed', 'closed')),
  status_changed_at timestamptz not null default now(),

  incident_occurred_at timestamptz,
  incident_location_text text,
  incident_location_lat double precision check (incident_location_lat is null or incident_location_lat between -90 and 90),
  incident_location_lng double precision check (incident_location_lng is null or incident_location_lng between -180 and 180),
  incident_description text,

  police_reported boolean,
  police_case_number text,
  police_station text,
  police_reported_at timestamptz,

  driver_is_policyholder boolean,
  driver_full_name text,
  driver_relationship text,
  vehicle_use text check (vehicle_use is null or vehicle_use in ('personal', 'business')),

  witnesses jsonb not null default '[]'::jsonb,
  third_parties jsonb not null default '[]'::jsonb,

  insurer_claim_number text,
  insurer_handler_name text,
  insurer_handler_email text,
  insurer_handler_phone text,

  repair_repairer_name text,
  repair_repairer_phone text,
  repair_quote_amount_cents bigint check (repair_quote_amount_cents is null or repair_quote_amount_cents >= 0),
  repair_authorised_amount_cents bigint check (repair_authorised_amount_cents is null or repair_authorised_amount_cents >= 0),
  repair_drop_off_date date,
  repair_estimated_completion_date date,
  repair_completed_at timestamptz,

  hire_car_status text not null default 'not_required' check (hire_car_status in (
    'not_required', 'requested', 'arranged', 'delivered', 'return_arranged', 'returned')),
  hire_car_provider text,
  hire_car_delivery_date date,
  hire_car_return_date date,

  review_rating smallint check (review_rating is null or review_rating between 1 and 5),
  review_comment text,
  review_submitted_at timestamptz,

  submitted_at timestamptz,
  closed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index claims_client_status_idx on claims (client_id, status);

create table claim_events (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references claims (id) on delete cascade,
  type text not null check (type in (
    'created', 'submitted', 'status_changed', 'insurer_details_updated', 'note', 'repair_update',
    'hire_car_updated', 'repair_date_chosen', 'attachment_added', 'review_submitted')),
  title text not null,
  message text,
  visible_to_client boolean not null default true,
  from_status text,
  to_status text,
  actor_id uuid references profiles (id),   -- NULL = system
  -- clock_timestamp(), not now(): several events can be written in one transaction and must stay ordered.
  created_at timestamptz not null default clock_timestamp()
);
create index claim_events_claim_idx on claim_events (claim_id, created_at);

-- ---------------------------------------------------------------- client requests
create table requests (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients (id) on delete cascade,
  type text not null check (type in (
    'address_change', 'bank_details_change', 'policy_document', 'border_letter', 'irp5',
    'consultation', 'client_information')),
  status text not null default 'submitted' check (status in ('submitted', 'in_progress', 'completed', 'declined')),
  payload jsonb not null default '{}'::jsonb,
  client_note text,
  adviser_response text,
  handled_by uuid references profiles (id),
  submitted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);
create index requests_client_status_idx on requests (client_id, status);

-- ---------------------------------------------------------------- attachments (claims or requests)
create table attachments (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid references claims (id) on delete cascade,
  request_id uuid references requests (id) on delete cascade,
  kind text not null check (kind in (
    'road_photo', 'vehicle_photo', 'people_photo', 'plate_or_disc_photo', 'id_document',
    'witness_voice_note', 'drivers_licence', 'accident_sketch', 'other')),
  label text,
  storage_path text not null,
  filename text not null,
  content_type text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  uploaded_by uuid not null references profiles (id),
  uploaded_at timestamptz not null default now(),
  -- Exactly one parent. Two nullable foreign keys instead of a polymorphic id keeps integrity in the database.
  constraint attachments_one_parent check ((claim_id is null) <> (request_id is null))
);
create index attachments_claim_idx on attachments (claim_id);
create index attachments_request_idx on attachments (request_id);

-- ---------------------------------------------------------------- RAG library
create table documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  category text not null check (category in ('policy_wording', 'internal_process', 'company_policy', 'regulation')),
  insurer_id uuid references insurers (id),
  page_count integer not null default 0,
  version_label text,
  is_synthetic boolean not null default true,
  source_note text,
  storage_path text,
  status text not null default 'processing' check (status in ('indexed', 'processing', 'failed')),
  content_hash text not null unique,
  indexed_at timestamptz,
  created_at timestamptz not null default now()
);

create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents (id) on delete cascade,
  page integer not null check (page >= 1),  -- 1-based; a chunk never spans two pages
  chunk_index integer not null,
  content text not null,
  tsv tsvector generated always as (to_tsvector('english', content)) stored,
  unique (document_id, page, chunk_index)
);
create index document_chunks_tsv_idx on document_chunks using gin (tsv);
create index document_chunks_doc_idx on document_chunks (document_id, page);
-- No embedding column yet: it is added once an embedding model is chosen and verified
-- (docs/ARCHITECT.md section 8.4).

create table assistant_conversations (
  id uuid primary key default gen_random_uuid(),
  advisor_id uuid not null references profiles (id) on delete cascade,
  title text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index assistant_conversations_advisor_idx on assistant_conversations (advisor_id, updated_at desc);

create table assistant_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references assistant_conversations (id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  grounded boolean,
  citations jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default clock_timestamp()
);
create index assistant_messages_conv_idx on assistant_messages (conversation_id, created_at);

-- ---------------------------------------------------------------- simulated mailbox
-- Backs MockEmailProvider. Flags and automatic links are computed on read; only a manual link is stored.
create table email_threads (
  id uuid primary key default gen_random_uuid(),
  advisor_id uuid not null references profiles (id) on delete cascade,   -- whose mailbox
  subject text not null,
  unread boolean not null default true,
  manual_client_id uuid references clients (id) on delete set null,
  manual_claim_id uuid references claims (id) on delete set null,
  created_at timestamptz not null default now()
);
create index email_threads_advisor_idx on email_threads (advisor_id);

create table email_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references email_threads (id) on delete cascade,
  from_name text,
  from_email text not null,
  to_recipients jsonb not null default '[]'::jsonb,   -- [{name, email}]
  cc_recipients jsonb not null default '[]'::jsonb,
  sent_at timestamptz not null,
  body_text text not null,
  has_attachments boolean not null default false
);
create index email_messages_thread_idx on email_messages (thread_id, sent_at);

-- ---------------------------------------------------------------- row-level security: default deny
do $$
declare t text;
begin
  foreach t in array array[
    'profiles', 'clients', 'insurers', 'policies', 'financial_items', 'goals', 'goal_participants',
    'reminders', 'claims', 'claim_events', 'requests', 'attachments', 'documents', 'document_chunks',
    'assistant_conversations', 'assistant_messages', 'email_threads', 'email_messages'
  ] loop
    execute format('alter table %I enable row level security', t);
  end loop;
end $$;

-- ---------------------------------------------------------------- Supabase-only pieces (skipped on plain Postgres)
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'auth' and table_name = 'users') then
    alter table profiles add constraint profiles_auth_user_fk
      foreign key (id) references auth.users (id) on delete cascade;
  end if;
end $$;

do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'storage' and table_name = 'buckets') then
    -- Private buckets: no public access, no storage policies. Files are only reachable through
    -- signed URLs issued by the backend.
    insert into storage.buckets (id, name, public) values ('attachments', 'attachments', false)
      on conflict (id) do nothing;
    insert into storage.buckets (id, name, public) values ('rag-docs', 'rag-docs', false)
      on conflict (id) do nothing;
  end if;
exception when others then
  raise notice 'Could not create storage buckets in SQL (%). Create private buckets "attachments" and "rag-docs" in the Supabase dashboard.', sqlerrm;
end $$;
