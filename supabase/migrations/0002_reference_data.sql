-- Reference data. The named insurers are the ones listed in PRD section 1; the PRD says "and others",
-- so an "Other" entry exists. Nothing here says which insurers underwrite which product lines.
insert into insurers (name) values
  ('Sanlam'), ('Old Mutual'), ('Liberty'), ('Momentum'), ('Discovery'), ('Allan Gray'), ('Santam'), ('Other')
on conflict (name) do nothing;
