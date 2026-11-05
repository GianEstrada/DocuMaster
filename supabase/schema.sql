-- Ejecutar una vez en Supabase: SQL Editor > New query.
-- RLS activo y sin políticas: solo el backend (service role) puede leer/escribir.

create table if not exists public.arrendador (
    id integer primary key default 1 check (id = 1),
    nombre text not null,
    rfc text not null,
    updated_at timestamptz not null default now()
);

create table if not exists public.contratos (
    id uuid primary key default gen_random_uuid(),
    folio text not null unique,
    cliente text not null,
    total numeric(14, 2) not null,
    datos jsonb not null,
    created_at timestamptz not null default now()
);

create index if not exists contratos_created_at_idx on public.contratos (created_at desc);

alter table public.arrendador enable row level security;
alter table public.contratos enable row level security;

insert into public.arrendador (id, nombre, rfc)
values (1, 'NOMBRE DEL ARRENDADOR', 'XAXX010101000')
on conflict (id) do nothing;
