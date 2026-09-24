/**
 * Konfigurasi Supabase untuk frontend (GitHub Pages).
 * AMAN untuk publik: hanya Project URL + anon/public key.
 * JANGAN PERNAH menaruh service_role key di file ini.
 *
 * Tahap 2: data diakses setelah login (Auth email + RLS authenticated).
 * Anon key tetap dipakai sebagai apikey; Authorization = JWT sesi login.
 *
 * Cara isi:
 * 1. Supabase Dashboard -> Project Settings -> API
 * 2. Salin "Project URL" dan "anon public" (bukan service_role)
 * 3. Ganti placeholder di bawah, commit, deploy.
 */
window.APP_CONFIG = {
  SUPABASE_URL: "https://krqinmcdtwrbmqmiozze.supabase.co",
  SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtycWlubWNkdHdyYm1xbWlvenplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAyNDgzNDgsImV4cCI6MjEwNTgyNDM0OH0.-ESwNL0_2Cu9fgfUcRn9PO0UBG1or455ovqM28RzsY4",
};
