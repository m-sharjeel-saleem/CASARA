-- CASARA multi-tenant schema (Supabase / Postgres).
-- Tenant boundary = a GitHub App installation. Users see only installations they own.
--
-- Apply: paste into the Supabase SQL editor, or `supabase db push` with the CLI.

-- ---------------------------------------------------------------------------
-- installations: one row per GitHub App installation (the tenant).
-- owner_user_id links the install to the GitHub user who created it (set after
-- OAuth login, when we can match the GitHub account id to auth.users).
-- ---------------------------------------------------------------------------
create table if not exists public.installations (
    id              bigint primary key,            -- GitHub installation id
    account         text not null,                 -- org/user login that installed it
    account_type    text,                          -- "Organization" | "User"
    account_id      bigint,                         -- GitHub account id (for ownership match)
    owner_user_id   uuid references auth.users (id) on delete set null,
    repo_count      integer default 0,
    plan            text not null default 'free',  -- billing tier (Phase 4)
    suspended       boolean not null default false,
    created_at      timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- reviews: one row per PR review, scoped to an installation.
-- findings stored as jsonb (same denormalized design as the SQLite MVP).
-- ---------------------------------------------------------------------------
create table if not exists public.reviews (
    id              text primary key,              -- uuid hex (12) from the pipeline
    installation_id bigint references public.installations (id) on delete cascade,
    repo            text not null,
    pr_number       integer not null,
    pr_title        text,
    author          text,
    head_sha        text,
    status          text,                          -- pending|running|completed|failed
    risk_score      real default 0,
    gated           boolean default false,
    summary         text,
    findings        jsonb not null default '[]'::jsonb,
    created_at      timestamptz not null default now(),
    completed_at    timestamptz
);

create index if not exists reviews_installation_idx on public.reviews (installation_id);
create index if not exists reviews_created_idx on public.reviews (created_at desc);

-- ---------------------------------------------------------------------------
-- usage_counters: per-installation monthly review count (Phase 4 billing cap).
-- ---------------------------------------------------------------------------
create table if not exists public.usage_counters (
    installation_id bigint references public.installations (id) on delete cascade,
    period          text not null,                 -- 'YYYY-MM'
    reviews_run     integer not null default 0,
    primary key (installation_id, period)
);

-- ===========================================================================
-- Row-Level Security: users may READ only data for installations they own.
-- The backend uses the service-role key (which bypasses RLS) to WRITE review
-- results from the webhook pipeline; end users only ever read through the API.
-- ===========================================================================
alter table public.installations  enable row level security;
alter table public.reviews        enable row level security;
alter table public.usage_counters enable row level security;

-- Owners can see their installations.
create policy installations_owner_read on public.installations
    for select using (owner_user_id = auth.uid());

-- Owners can see reviews for installations they own.
create policy reviews_owner_read on public.reviews
    for select using (
        installation_id in (
            select id from public.installations where owner_user_id = auth.uid()
        )
    );

-- Owners can see their own usage.
create policy usage_owner_read on public.usage_counters
    for select using (
        installation_id in (
            select id from public.installations where owner_user_id = auth.uid()
        )
    );

-- NOTE: no INSERT/UPDATE policies for the anon/auth role on purpose — all writes
-- happen server-side with the service-role key, which bypasses RLS.
