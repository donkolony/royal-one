-- Workflow engine support (docs/AUDIT.md build step 4, brief section C).
--
--   * requests.type is no longer a database CHECK: request types live in ONE config file (backend/app/domain/workflows.py) and
--     are validated by the service, so adding a simple request type is a config entry, not a migration.
--   * request_events: the timeline of a request, the same idea as claim_events, so the client never has to chase.
--   * notifications: in-app only (docs/api.md 1.9). One row per person to tell.

alter table requests drop constraint if exists requests_type_check;

create table request_events (
  id uuid primary key default gen_random_uuid(),
  request_id uuid not null references requests (id) on delete cascade,
  type text not null,                          -- created, status_changed, note, identity_reused, forwarded, insurer_update
  title text not null,
  message text,
  visible_to_client boolean not null default true,
  from_status text,
  to_status text,
  actor_id uuid references profiles (id),      -- NULL = the system (or the simulated provider, which says so in the title)
  created_at timestamptz not null default clock_timestamp()
);
create index request_events_idx on request_events (request_id, created_at);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  recipient_id uuid not null references profiles (id) on delete cascade,
  kind text not null,                          -- claim_update, request_update, new_claim, new_request, reminder, ...
  title text not null,
  body text,
  link jsonb,                                  -- {resource: claim|request|client, id}
  client_id uuid references clients (id) on delete cascade,
  created_at timestamptz not null default clock_timestamp(),
  read_at timestamptz
);
create index notifications_recipient_idx on notifications (recipient_id, created_at desc);
create index notifications_unread_idx on notifications (recipient_id) where read_at is null;

select rs_lock_down('public.request_events');
select rs_lock_down('public.notifications');

create policy request_events_read on request_events for select to authenticated using (
  exists (select 1 from requests r where r.id = request_events.request_id)               -- requests policy applies here too
  and (rs_role() <> 'client' or visible_to_client)
);
create policy notifications_read on notifications for select to authenticated using (recipient_id = auth.uid());
