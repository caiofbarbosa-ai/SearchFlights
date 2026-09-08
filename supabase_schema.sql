-- Flight Monitoring MVP — schema Supabase (Decisão 4 do design.md)
-- Executar no SQL Editor do projeto Supabase.

create extension if not exists "pgcrypto";

create table if not exists daily_executions (
    id uuid primary key default gen_random_uuid(),
    execution_date date not null,
    google_status text,
    smiles_status text,
    azul_status text,
    rss_status text,
    telegram_status text,
    overall_status text,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    error_details jsonb
);

create table if not exists daily_flight_quotes (
    id uuid primary key default gen_random_uuid(),
    execution_id uuid references daily_executions(id) on delete cascade,
    execution_date date not null,
    source text not null check (source in ('google', 'smiles', 'azul')),
    origin text not null,
    destination text not null,
    departure_date date,
    return_date date,
    status text not null,
    cash_price_brl numeric,
    miles integer,
    hybrid_miles integer,
    cash_component_brl numeric,
    airline text,
    duration_minutes integer,
    stops integer,
    passengers integer default 2,
    price_is_per_passenger boolean default false,
    raw_sample jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_quotes_exec
    on daily_flight_quotes (execution_id);

create table if not exists daily_promotions (
    id uuid primary key default gen_random_uuid(),
    article_url text unique not null,
    title text,
    source_feed text,
    published_at timestamptz,
    matched_keywords text[],
    created_at timestamptz not null default now()
);

-- RLS + políticas permissivas para a publishable key (projeto pessoal;
-- as únicas "chaves de escrita" são seus próprios scripts).
alter table daily_executions enable row level security;
alter table daily_flight_quotes enable row level security;
alter table daily_promotions enable row level security;

create policy "executions_all" on daily_executions
    for all to anon, authenticated using (true) with check (true);
create policy "quotes_all" on daily_flight_quotes
    for all to anon, authenticated using (true) with check (true);
create policy "promotions_all" on daily_promotions
    for all to anon, authenticated using (true) with check (true);


-- Adendo 07/09: coluna do híbrido Smiles&Money/Azul (combo milhas + reais)
alter table daily_flight_quotes add column if not exists hybrid_miles integer;
alter table daily_flight_quotes add column if not exists cash_component_brl numeric;
