-- 0004 — Ganti master kelas: 26 kelas SMK (kelas 10/11/12 - TSM/TKR/TKJ).
-- Jalankan di SQL Editor SETELAH 0001 (dan 0003 mode publik).
-- Hapus seed lama XII-01..28, ganti daftar dari Kelas.txt (26 baris).

delete from public.classes;

insert into public.classes (id, name, tingkat, jurusan) values
  ('10-TSM-1', '10 TSM 1', '10', 'TSM'),
  ('10-TSM-2', '10 TSM 2', '10', 'TSM'),
  ('10-TSM-3', '10 TSM 3', '10', 'TSM'),
  ('10-TKR-1', '10 TKR 1', '10', 'TKR'),
  ('10-TKR-2', '10 TKR 2', '10', 'TKR'),
  ('10-TKJ-1', '10 TKJ 1', '10', 'TKJ'),
  ('10-TKJ-2', '10 TKJ 2', '10', 'TKJ'),
  ('10-TKJ-3', '10 TKJ 3', '10', 'TKJ'),
  ('10-TKJ-4', '10 TKJ 4', '10', 'TKJ'),
  ('10-TKJ-5', '10 TKJ 5', '10', 'TKJ'),
  ('11-TSM-1', '11 TSM 1', '11', 'TSM'),
  ('11-TSM-2', '11 TSM 2', '11', 'TSM'),
  ('11-TKR-1', '11 TKR 1', '11', 'TKR'),
  ('11-TKR-2', '11 TKR 2', '11', 'TKR'),
  ('11-TKJ-1', '11 TKJ 1', '11', 'TKJ'),
  ('11-TKJ-2', '11 TKJ 2', '11', 'TKJ'),
  ('11-TKJ-3', '11 TKJ 3', '11', 'TKJ'),
  ('11-TKJ-4', '11 TKJ 4', '11', 'TKJ'),
  ('11-TKJ-5', '11 TKJ 5', '11', 'TKJ'),
  ('12-TSM-1', '12 TSM 1', '12', 'TSM'),
  ('12-TSM-2', '12 TSM 2', '12', 'TSM'),
  ('12-TKR-1', '12 TKR 1', '12', 'TKR'),
  ('12-TKR-2', '12 TKR 2', '12', 'TKR'),
  ('12-TKJ-1', '12 TKJ 1', '12', 'TKJ'),
  ('12-TKJ-2', '12 TKJ 2', '12', 'TKJ'),
  ('12-TKJ-3', '12 TKJ 3', '12', 'TKJ')
on conflict (id) do update set
  name = excluded.name,
  tingkat = excluded.tingkat,
  jurusan = excluded.jurusan;
