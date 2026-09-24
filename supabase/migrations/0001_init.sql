-- Tournament Scheme & Fairness Simulator — skema Supabase (Tahap 1)
-- Jalankan di: Supabase Dashboard -> SQL Editor
-- Catatan keamanan:
--   * RLS WAJIB aktif di semua tabel.
--   * Frontend hanya boleh memakai anon/public key (bukan service_role).
--   * Policy anon di bawah = setara aplikasi LAN terbuka lama (Tahap 1).
--     Saat auth ditambahkan (tahap berikut): matikan policy anon, pakai auth.uid().

-- ===== classes (master kelas) =====
create table if not exists public.classes (
  id text primary key,
  name text not null,
  tingkat text not null default '',
  jurusan text not null default ''
);

-- ===== tournaments (definisi lomba) =====
create table if not exists public.tournaments (
  id text primary key,
  name text not null,
  format text not null,
  team_size integer not null default 4,
  winner_count integer not null default 1,
  duration_min integer not null default 30,
  minimum_rest_min integer not null default 10,
  arena_count integer not null default 2,
  date text not null default '',
  start_time text not null default '08:00',
  end_time text not null default '17:00',
  participant_ids jsonb not null default '[]'::jsonb,
  manual_scheme jsonb,
  manual_scheduled jsonb,
  qualify_per_group integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ===== results (skor per match; 1 baris = 1 match) =====
create table if not exists public.results (
  tournament_id text not null references public.tournaments (id) on delete cascade,
  match_id text not null,
  winner text,
  score_a integer not null default 0,
  score_b integer not null default 0,
  updated_at timestamptz not null default now(),
  primary key (tournament_id, match_id)
);

-- ===== meta (seq lomba, dst.) =====
create table if not exists public.meta (
  key text primary key,
  value text not null
);

-- ===== RLS =====
alter table public.classes enable row level security;
alter table public.tournaments enable row level security;
alter table public.results enable row level security;
alter table public.meta enable row level security;

-- Tahap 1: anon read/write classes (open, seperti mode LAN lama).
drop policy if exists "anon select classes" on public.classes;
create policy "anon select classes"
  on public.classes for select
  to anon, authenticated
  using (true);

drop policy if exists "anon insert classes" on public.classes;
create policy "anon insert classes"
  on public.classes for insert
  to anon, authenticated
  with check (true);

drop policy if exists "anon update classes" on public.classes;
create policy "anon update classes"
  on public.classes for update
  to anon, authenticated
  using (true)
  with check (true);

drop policy if exists "anon delete classes" on public.classes;
create policy "anon delete classes"
  on public.classes for delete
  to anon, authenticated
  using (true);

-- Tahap 1: tournaments/results/meta — read dulu (stat beranda); write menyusul tahap fitur lomba.
drop policy if exists "anon select tournaments" on public.tournaments;
create policy "anon select tournaments"
  on public.tournaments for select
  to anon, authenticated
  using (true);

drop policy if exists "anon select results" on public.results;
create policy "anon select results"
  on public.results for select
  to anon, authenticated
  using (true);

drop policy if exists "anon select meta" on public.meta;
create policy "anon select meta"
  on public.meta for select
  to anon, authenticated
  using (true);

-- ===== Seed: 28 kelas default (idempotent) + seq =====
insert into public.classes (id, name, tingkat, jurusan)
select
  'XII-' || lpad(i::text, 2, '0'),
  'XII-' || lpad(i::text, 2, '0'),
  'XII',
  ''
from generate_series(1, 28) as i
on conflict (id) do nothing;

insert into public.meta (key, value) values ('seq', '0')
on conflict (key) do nothing;
