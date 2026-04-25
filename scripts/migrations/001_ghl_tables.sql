-- GHL tables: contacts, opportunities (structured), notes (text + embeddings)
-- Run this in Supabase: Dashboard → SQL Editor → paste → Run

-- Contacts: structured, no embeddings
create table if not exists ghl_contacts (
  id uuid primary key default gen_random_uuid(),
  source_id text not null unique,
  location_id text not null,
  first_name text,
  last_name text,
  full_name text,
  email text,
  phone text,
  contact_type text,
  tags text[] default '{}',
  source text,
  city text,
  state text,
  country text,
  assigned_to text,
  dnd boolean default false,
  date_added timestamptz,
  date_updated timestamptz,
  metadata jsonb default '{}'::jsonb,
  _synced_at timestamptz default now()
);

create index if not exists ghl_contacts_email on ghl_contacts (email);
create index if not exists ghl_contacts_phone on ghl_contacts (phone);
create index if not exists ghl_contacts_tags on ghl_contacts using gin (tags);
create index if not exists ghl_contacts_date_added on ghl_contacts (date_added desc);
create index if not exists ghl_contacts_synced_at on ghl_contacts (_synced_at desc);
alter table ghl_contacts enable row level security;

-- Opportunities: structured, no embeddings
create table if not exists ghl_opportunities (
  id uuid primary key default gen_random_uuid(),
  source_id text not null unique,
  name text,
  pipeline_id text,
  pipeline_name text,
  stage_id text,
  stage_name text,
  status text,
  monetary_value numeric default 0,
  contact_id text,
  contact_name text,
  contact_email text,
  contact_phone text,
  contact_tags text[] default '{}',
  last_stage_change_at timestamptz,
  created_at timestamptz,
  _synced_at timestamptz default now()
);

create index if not exists ghl_opportunities_pipeline on ghl_opportunities (pipeline_id);
create index if not exists ghl_opportunities_stage on ghl_opportunities (stage_id);
create index if not exists ghl_opportunities_status on ghl_opportunities (status);
create index if not exists ghl_opportunities_contact on ghl_opportunities (contact_id);
create index if not exists ghl_opportunities_created_at on ghl_opportunities (created_at desc);
alter table ghl_opportunities enable row level security;

-- Notes: text-bearing with semantic search
create table if not exists ghl_notes (
  id uuid primary key default gen_random_uuid(),
  source_id text not null unique,
  contact_id text not null,
  contact_name text,
  body text not null,
  metadata jsonb default '{}'::jsonb,
  embedding vector(1024),
  search_tsv tsvector generated always as (to_tsvector('english', coalesce(body, ''))) stored,
  embedding_model text default 'voyage-3-large',
  date_added timestamptz,
  _synced_at timestamptz default now()
);

create index if not exists ghl_notes_embedding_hnsw on ghl_notes using hnsw (embedding vector_cosine_ops);
create index if not exists ghl_notes_tsv_gin on ghl_notes using gin (search_tsv);
create index if not exists ghl_notes_contact on ghl_notes (contact_id);
create index if not exists ghl_notes_synced_at on ghl_notes (_synced_at desc);
alter table ghl_notes enable row level security;
