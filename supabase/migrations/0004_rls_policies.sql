-- Per-role row-level security (docs/AUDIT.md R7, build step 1).
--
-- The backend connects with a privileged role and enforces scoping in code (docs/ARCHITECT.md section 4). These policies
-- are the second, independent layer: anyone who reaches Postgres with a Supabase-issued JWT (for example over PostgREST with
-- the public anon key) sees exactly what the API would show them, and can WRITE nothing.
--
--   client  -> their own rows
--   advisor -> rows of the clients assigned to them
--   owner   -> every client's rows
--   anon    -> nothing
--
-- Policies are SELECT-only. All writes go through the backend; write privileges are revoked from anon and authenticated.
-- Every later migration that adds a table must call rs_lock_down() and add its policy (tests/test_rls.py fails otherwise).

-- ---------------------------------------------------------------- Supabase compatibility on plain Postgres
-- On Supabase these already exist and are left alone. On a stock Postgres (the test database) they are created so the same
-- policies can be exercised: auth.uid() reads the JWT subject the way Supabase does.
do $$
begin
  if not exists (select 1 from pg_namespace where nspname = 'auth') then
    create schema auth;
  end if;
  if not exists (
    select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'auth' and p.proname = 'uid'
  ) then
    execute $f$
      create function auth.uid() returns uuid language sql stable as $b$
        select coalesce(
          nullif(current_setting('request.jwt.claim.sub', true), ''),
          (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
        )::uuid
      $b$
    $f$;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
end $$;

grant usage on schema public to anon, authenticated;
grant usage on schema auth to anon, authenticated;

-- ---------------------------------------------------------------- helpers (security definer: they read profiles/clients past RLS)
create function rs_role() returns text
  language sql stable security definer set search_path = public as
$$ select role from profiles where id = auth.uid() $$;

create function rs_can_see_client(cid uuid) returns boolean
  language sql stable security definer set search_path = public as
$$
  select auth.uid() is not null and (
    cid = auth.uid()
    or exists (select 1 from clients c where c.id = cid and c.adviser_id = auth.uid())
    or exists (select 1 from profiles p where p.id = auth.uid() and p.role = 'owner')
  )
$$;

-- Turn on RLS for a table, take everything away from anon, and leave authenticated read-only (rows still limited by policy).
create function rs_lock_down(tbl regclass) returns void language plpgsql as
$$
begin
  execute format('alter table %s enable row level security', tbl);
  execute format('revoke all on %s from anon', tbl);
  execute format('revoke insert, update, delete, truncate, references, trigger on %s from authenticated', tbl);
  execute format('grant select on %s to authenticated', tbl);
end
$$;

do $$
declare t text;
begin
  foreach t in array array[
    'profiles', 'clients', 'insurers', 'policies', 'financial_items', 'goals', 'goal_participants', 'reminders',
    'claims', 'claim_events', 'requests', 'attachments', 'documents', 'document_chunks', 'assistant_conversations',
    'assistant_messages', 'email_threads', 'email_messages', 'audit_log', 'schema_migrations'
  ] loop
    perform rs_lock_down(format('public.%I', t)::regclass);
  end loop;
end $$;

-- ---------------------------------------------------------------- policies
create policy profiles_read on profiles for select to authenticated using (
  id = auth.uid()
  or rs_can_see_client(id)
  or exists (select 1 from clients c where c.id = auth.uid() and c.adviser_id = profiles.id)   -- a client sees their adviser
);
create policy clients_read on clients for select to authenticated using (rs_can_see_client(id));
create policy insurers_read on insurers for select to authenticated using (true);              -- reference data
create policy policies_read on policies for select to authenticated using (rs_can_see_client(client_id));
create policy financial_items_read on financial_items for select to authenticated using (rs_can_see_client(client_id));
create policy goal_participants_read on goal_participants for select to authenticated using (rs_can_see_client(client_id));
create policy goals_read on goals for select to authenticated using (
  exists (select 1 from goal_participants gp where gp.goal_id = goals.id and rs_can_see_client(gp.client_id))
);
create policy reminders_read on reminders for select to authenticated using (
  rs_can_see_client(client_id) and (rs_role() <> 'client' or audience in ('client', 'both'))
);
create policy claims_read on claims for select to authenticated using (
  rs_can_see_client(client_id) and (client_id = auth.uid() or status <> 'draft')                -- drafts are private to the client
);
create policy claim_events_read on claim_events for select to authenticated using (
  exists (select 1 from claims c where c.id = claim_events.claim_id)                            -- claims policy applies here too
  and (rs_role() <> 'client' or visible_to_client)
);
create policy requests_read on requests for select to authenticated using (rs_can_see_client(client_id));
create policy attachments_read on attachments for select to authenticated using (
  exists (select 1 from claims c where c.id = attachments.claim_id)
  or exists (select 1 from requests r where r.id = attachments.request_id)
);
create policy documents_read on documents for select to authenticated using (rs_role() = 'advisor');
create policy document_chunks_read on document_chunks for select to authenticated using (rs_role() = 'advisor');
create policy assistant_conversations_read on assistant_conversations for select to authenticated using (advisor_id = auth.uid());
create policy assistant_messages_read on assistant_messages for select to authenticated using (
  exists (select 1 from assistant_conversations c where c.id = assistant_messages.conversation_id)
);
create policy email_threads_read on email_threads for select to authenticated using (advisor_id = auth.uid());
create policy email_messages_read on email_messages for select to authenticated using (
  exists (select 1 from email_threads t where t.id = email_messages.thread_id)
);
create policy audit_log_read on audit_log for select to authenticated using (
  rs_role() = 'owner' or (rs_role() = 'advisor' and client_id is not null and rs_can_see_client(client_id))
);
-- schema_migrations: RLS on, no policy = invisible to anon and authenticated.
