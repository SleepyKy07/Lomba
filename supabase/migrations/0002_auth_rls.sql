-- Tahap 2 — Supabase Auth + RLS (matikan policy anon terbuka).
-- Jalankan di SQL Editor SETELAH 0001_init.sql.
-- Setelah ini frontend WAJIB login (email + password).

-- ===== owner_id untuk audit / pemilik data =====
alter table public.classes
  add column if not exists owner_id uuid;
alter table public.tournaments
  add column if not exists owner_id uuid
  default auth.uid();
alter table public.results
  add column if not exists owner_id uuid
  default auth.uid();
alter table public.meta
  add column if not exists owner_id uuid;

-- Baris seed / lama: owner boleh null; anggota tim masih bisa edit bila policy izinkan.

-- ===== Hapus policy anon Tahap 1 =====
drop policy if exists "anon select classes" on public.classes;
drop policy if exists "anon insert classes" on public.classes;
drop policy if exists "anon update classes" on public.classes;
drop policy if exists "anon delete classes" on public.classes;
drop policy if exists "anon select tournaments" on public.tournaments;
drop policy if exists "anon select results" on public.results;
drop policy if exists "anon select meta" on public.meta;

-- ===== classes: hanya authenticated (tim panitia) =====
-- Master kelas dibaca/ditulis bersama anggota login (bukan publik anon).
drop policy if exists "auth select classes" on public.classes;
create policy "auth select classes"
  on public.classes for select
  to authenticated
  using (true);

drop policy if exists "auth insert classes" on public.classes;
create policy "auth insert classes"
  on public.classes for insert
  to authenticated
  with check (
    owner_id is null
    or owner_id = auth.uid()
  );

drop policy if exists "auth update classes" on public.classes;
create policy "auth update classes"
  on public.classes for update
  to authenticated
  using (owner_id is null or owner_id = auth.uid())
  with check (owner_id is null or owner_id = auth.uid());

drop policy if exists "auth delete classes" on public.classes;
create policy "auth delete classes"
  on public.classes for delete
  to authenticated
  using (owner_id is null or owner_id = auth.uid());

-- ===== tournaments: milik pembuat =====
drop policy if exists "auth select tournaments" on public.tournaments;
create policy "auth select tournaments"
  on public.tournaments for select
  to authenticated
  using (owner_id = auth.uid() or owner_id is null);

drop policy if exists "auth insert tournaments" on public.tournaments;
create policy "auth insert tournaments"
  on public.tournaments for insert
  to authenticated
  with check (owner_id = auth.uid() or owner_id is null);

drop policy if exists "auth update tournaments" on public.tournaments;
create policy "auth update tournaments"
  on public.tournaments for update
  to authenticated
  using (owner_id = auth.uid() or owner_id is null)
  with check (owner_id = auth.uid() or owner_id is null);

drop policy if exists "auth delete tournaments" on public.tournaments;
create policy "auth delete tournaments"
  on public.tournaments for delete
  to authenticated
  using (owner_id = auth.uid() or owner_id is null);

-- ===== results: ikut lomba =====
drop policy if exists "auth select results" on public.results;
create policy "auth select results"
  on public.results for select
  to authenticated
  using (
    exists (
      select 1 from public.tournaments t
      where t.id = tournament_id
        and (t.owner_id = auth.uid() or t.owner_id is null)
    )
  );

drop policy if exists "auth insert results" on public.results;
create policy "auth insert results"
  on public.results for insert
  to authenticated
  with check (
    exists (
      select 1 from public.tournaments t
      where t.id = tournament_id
        and (t.owner_id = auth.uid() or t.owner_id is null)
    )
  );

drop policy if exists "auth update results" on public.results;
create policy "auth update results"
  on public.results for update
  to authenticated
  using (
    exists (
      select 1 from public.tournaments t
      where t.id = tournament_id
        and (t.owner_id = auth.uid() or t.owner_id is null)
    )
  )
  with check (
    exists (
      select 1 from public.tournaments t
      where t.id = tournament_id
        and (t.owner_id = auth.uid() or t.owner_id is null)
    )
  );

drop policy if exists "auth delete results" on public.results;
create policy "auth delete results"
  on public.results for delete
  to authenticated
  using (
    exists (
      select 1 from public.tournaments t
      where t.id = tournament_id
        and (t.owner_id = auth.uid() or t.owner_id is null)
    )
  );

-- ===== meta: authenticated read/write (seq) =====
drop policy if exists "auth select meta" on public.meta;
create policy "auth select meta"
  on public.meta for select
  to authenticated
  using (true);

drop policy if exists "auth update meta" on public.meta;
create policy "auth update meta"
  on public.meta for update
  to authenticated
  using (true)
  with check (true);

drop policy if exists "auth insert meta" on public.meta;
create policy "auth insert meta"
  on public.meta for insert
  to authenticated
  with check (true);
