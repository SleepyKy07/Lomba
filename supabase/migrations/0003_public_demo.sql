-- 0003 — Mode publik: TANPA login.
-- Jalankan di SQL Editor Supabase SETELAH 0001 + 0002.
-- RLS dimatikan -> role anon & authenticated bisa baca/tulis (demo sekolah).
-- Frontend tidak lagi memakai Supabase Auth (nav "Masuk" dihapus).
-- Untuk kembali ke mode login: jalankan ulang 0002_auth_rls.sql
--   (setelah delete policy lama) atau create policy + enable row level security.

alter table public.classes   disable row level security;
alter table public.tournaments disable row level security;
alter table public.results   disable row level security;
alter table public.meta      disable row level security;
