Ada. Malah untuk proyek ini **PRD lebih penting daripada langsung prompt coding**, karena masalah utamanya adalah mendefinisikan **"adil" itu diukur dari apa**. Kalau definisinya kabur, AI bisa bikin scheduler yang kelihatannya pintar tapi sebenarnya cuma mengacak penderitaan.

Berikut PRD yang bisa kamu pakai sebagai dasar project.

# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## 1. Informasi Produk

**Nama Produk:** Tournament Scheme & Fairness Simulator
**Jenis:** Web Application
**Target Pengguna:** Panitia OSIS / panitia kegiatan sekolah
**Skala:** ±28 kelas, ±850+ siswa

---

# 2. Latar Belakang

Dalam kegiatan lomba antar kelas, jumlah peserta setiap lomba tidak selalu sama. Dari sekitar 28 kelas, sebagian kelas dapat memilih untuk tidak mengikuti lomba tertentu.

Selain itu, format pertandingan dapat berbeda-beda, misalnya:

* 1v1
* 2v2
* 3v3
* 4v4
* individu
* kelompok

Kondisi tersebut membuat penyusunan skema pertandingan secara manual menjadi sulit.

Masalah utama yang muncul adalah:

* jumlah peserta tidak selalu sesuai dengan bracket standar
* beberapa peserta dapat memperoleh bye
* jumlah pertandingan setiap kelas dapat berbeda
* waktu istirahat dapat berbeda
* jalur menuju final dapat berbeda
* format pertandingan dengan jumlah pemain berbeda memiliki beban yang berbeda
* satu kelas dapat mengikuti beberapa lomba sehingga berpotensi terjadi bentrok jadwal

Contoh masalah nyata terjadi ketika tersisa 6 kelas dalam sebuah lomba. Panitia mempertimbangkan membagi peserta menjadi tiga pasangan pertandingan, kemudian tiga pemenang bertanding untuk menentukan juara. Muncul pertanyaan apakah skema tersebut memberikan kesempatan yang cukup setara kepada seluruh peserta.

Karena itu diperlukan sebuah sistem yang dapat **menghasilkan, membandingkan, dan menganalisis berbagai kemungkinan skema pertandingan berdasarkan kondisi peserta yang sebenarnya.**

---

# 3. Tujuan Produk

Produk bertujuan membantu panitia:

1. Membuat skema pertandingan secara otomatis.
2. Menghasilkan beberapa alternatif format ketika jumlah peserta tidak ideal.
3. Mengidentifikasi ketidakseimbangan dalam suatu skema.
4. Menghitung distribusi pertandingan setiap kelas.
5. Menghitung player load berdasarkan ukuran tim.
6. Menghitung jalur pertandingan menuju juara.
7. Menghitung waktu istirahat.
8. Mendeteksi bye.
9. Mendeteksi bentrokan jadwal.
10. Mensimulasikan berbagai kemungkinan hasil pertandingan.
11. Membandingkan beberapa skema berdasarkan data yang transparan.

Produk **tidak bertujuan memilih pemenang lomba atau menentukan kelas mana yang lebih kuat.**

---

# 4. Prinsip Utama Produk

## 4.1 Fairness harus dapat dijelaskan

Sistem tidak boleh hanya mengatakan:

> "Skema ini 90% adil."

Sistem harus menjelaskan alasan angka tersebut.

Contoh:

* Match difference: 1
* Rest difference: 20 menit
* Bye difference: 1
* Player-load difference: 2

Dengan demikian panitia dapat memahami konsekuensi setiap skema.

---

## 4.2 Tidak ada satu format yang selalu paling baik

Format terbaik bergantung pada:

* jumlah peserta
* ukuran tim
* jumlah juara
* waktu tersedia
* jumlah arena
* aturan lomba

Sistem harus menyediakan beberapa alternatif apabila memungkinkan.

---

## 4.3 Peserta yang tidak ikut tidak dihitung

Jika tersedia 28 kelas tetapi hanya 23 yang mengikuti lomba, sistem bekerja berdasarkan **23 peserta**, bukan memaksa 28 peserta.

---

# 5. Target Pengguna

### Primary User

Panitia OSIS yang bertugas menyusun:

* peserta
* pertandingan
* jadwal
* bracket
* klasemen

### Secondary User

Panitia atau guru yang ingin memeriksa apakah skema yang dibuat memiliki ketimpangan.

---

# 6. User Stories

### US-01

Sebagai panitia, saya ingin memasukkan daftar kelas yang mengikuti lomba agar sistem hanya menggunakan peserta aktual.

### US-02

Sebagai panitia, saya ingin menentukan format pertandingan seperti 1v1, 3v3, atau 4v4.

### US-03

Sebagai panitia, saya ingin mendapatkan beberapa alternatif skema ketika jumlah peserta tidak cocok dengan bracket standar.

### US-04

Sebagai panitia, saya ingin mengetahui apakah suatu kelas mendapatkan bye.

### US-05

Sebagai panitia, saya ingin mengetahui jumlah pertandingan setiap kelas.

### US-06

Sebagai panitia, saya ingin mengetahui waktu istirahat setiap kelas.

### US-07

Sebagai panitia, saya ingin mengetahui beban pemain berdasarkan ukuran tim.

### US-08

Sebagai panitia, saya ingin mengetahui apakah terdapat bentrokan jadwal.

### US-09

Sebagai panitia, saya ingin mengubah jadwal secara manual dan melihat dampaknya terhadap fairness.

### US-10

Sebagai panitia, saya ingin membandingkan beberapa skema sebelum memilih salah satunya.

---

# 7. Fitur Utama

## F-01 — Master Kelas

Sistem menyediakan daftar kelas.

Data minimum:

```text
id
nama_kelas
tingkat
jurusan
```

Jumlah awal yang ditargetkan: ±28 kelas.

---

## F-02 — Pembuatan Lomba

Data:

```text
nama_lomba
format
peserta
jumlah_juara
durasi
waktu_istirahat_minimum
jumlah_arena
tanggal
jam_mulai
jam_selesai
```

---

## F-03 — Pemilihan Peserta

Panitia dapat memilih kelas yang mengikuti lomba.

Contoh:

```text
Total kelas: 28
Ikut lomba: 23
Tidak ikut: 5
```

---

## F-04 — Tournament Generator

Sistem menghasilkan kemungkinan format:

* knockout
* round robin
* group stage
* group stage + knockout
* preliminary round + knockout

Generator harus memperhatikan jumlah peserta aktual.

---

# 8. Fairness Engine

Fairness Engine merupakan komponen inti aplikasi.

## 8.1 Match Distribution

Mengukur:

```text
minimum match
maximum match
average match
maximum difference
```

---

## 8.2 Player Load

Rumus dasar:

```text
Player Load =
jumlah pertandingan × jumlah pemain per tim
```

Contoh:

4v4 × 3 pertandingan = 12 player-load.

---

## 8.3 Championship Path

Mengukur jumlah kemenangan yang diperlukan untuk mencapai:

* semifinal
* final
* juara

Sistem harus mendeteksi apabila peserta tertentu memiliki jalur yang lebih pendek.

---

## 8.4 Bye Analysis

Sistem mendeteksi:

* peserta yang mendapatkan bye
* jumlah bye
* ronde tempat bye terjadi
* pengaruh bye terhadap jumlah pertandingan
* pengaruh bye terhadap jalur menuju juara

---

## 8.5 Rest Analysis

Mengukur:

```text
minimum rest
maximum rest
average rest
rest difference
```

Sistem memberikan warning apabila waktu istirahat berada di bawah batas minimum.

---

## 8.6 Schedule Conflict

Sistem harus mendeteksi:

### Internal conflict

Satu kelas dijadwalkan dalam dua pertandingan bersamaan.

### Cross-event conflict

Satu kelas mengikuti beberapa lomba dan dijadwalkan dalam dua lomba pada waktu yang sama atau terlalu berdekatan.

---

# 9. Probability Engine

Probability Engine digunakan untuk melihat kemungkinan hasil dari suatu skema.

## Mode 1 — Equal Probability

Setiap peserta memiliki peluang menang yang sama.

Contoh:

6 peserta:

```text
A = 16.67%
B = 16.67%
C = 16.67%
D = 16.67%
E = 16.67%
F = 16.67%
```

## Mode 2 — Custom Probability

Panitia dapat memasukkan probabilitas secara manual.

Contoh:

```text
A = 60%
B = 40%
```

Sistem harus menjelaskan bahwa hasil bergantung pada input probabilitas.

## Mode 3 — Monte Carlo

Untuk skema dengan jumlah kemungkinan sangat besar, sistem dapat menjalankan simulasi berulang.

Contoh:

```text
10.000 simulations
```

Output:

```text
A → Juara 1: 17.2%
B → Juara 1: 16.5%
...
```

Angka tersebut merupakan hasil simulasi berdasarkan model probabilitas yang dipilih, bukan prediksi kemampuan nyata peserta.

---

# 10. What-If Analysis

Pengguna dapat mengubah kondisi tanpa membuat lomba baru.

Contoh:

```text
23 peserta
↓
1 kelas keluar
↓
22 peserta
```

Sistem menghitung ulang:

* format
* bracket
* bye
* pertandingan
* jadwal
* fairness
* probability

Contoh parameter yang dapat diubah:

* jumlah peserta
* peserta tertentu
* format
* jumlah arena
* durasi pertandingan
* waktu istirahat
* jumlah juara

---

# 11. Scenario Comparison

Sistem dapat menampilkan beberapa alternatif secara berdampingan.

Contoh:

| Metrik                 | Skema A | Skema B | Skema C |
| ---------------------- | ------: | ------: | ------: |
| Total pertandingan     |      22 |      25 |      30 |
| Match difference       |       1 |       2 |       0 |
| Rest difference        |    20 m |    40 m |    15 m |
| Bye                    |       2 |       0 |       0 |
| Player-load difference |       2 |       4 |       3 |
| Conflict               |       0 |       1 |       0 |

Tidak memberikan label "pemenang" secara subjektif. Panitia memilih berdasarkan kebutuhan kegiatan.

---

# 12. Manual Adjustment

Panitia dapat:

* mengganti lawan
* memindahkan jadwal
* memindahkan arena
* mengubah peserta
* memberikan atau menghapus bye

Setelah perubahan, sistem otomatis menjalankan ulang analisis.

---

# 13. Output

Output minimal:

### Bracket

Visualisasi hubungan pertandingan.

### Schedule

```text
08:00
A vs B
Lapangan 1

08:00
C vs D
Lapangan 2
```

### Fairness Analysis

```text
Match distribution
Player load
Bye
Rest
Path to championship
Conflict
```

### Probability

Menampilkan kemungkinan hasil berdasarkan model probabilitas yang dipilih.

---

# 14. Non-Functional Requirements

## Performance

Untuk ±28 kelas, generator harus dapat menghasilkan skema secara cepat pada perangkat biasa.

## Usability

Panitia yang tidak memiliki kemampuan programming harus dapat menggunakan aplikasi.

## Transparency

Setiap hasil fairness harus dapat dijelaskan.

## Flexibility

Sistem harus mendukung berbagai format lomba.

## Maintainability

Tournament Engine dan Fairness Engine harus dipisahkan dari UI.

---

# 15. Data Model Awal

### Class

```text
id
name
```

### Tournament

```text
id
name
format
team_size
winner_count
duration
minimum_rest
arena_count
```

### TournamentParticipant

```text
tournament_id
class_id
```

### Match

```text
id
tournament_id
round
participant_a
participant_b
scheduled_time
arena
status
```

### Result

```text
match_id
winner
score_a
score_b
```

### FairnessMetric

```text
tournament_id
metric_name
value
```

---

# 16. Contoh Skenario Utama

## Skenario: 6 kelas tersisa

Input:

```text
Peserta: A B C D E F
Juara: 3
```

Sistem menghasilkan beberapa kemungkinan:

### Alternatif A

```text
Group A
A B C

Group B
D E F
```

Setiap peserta bermain 2 kali pada fase grup.

Kemudian juara grup masuk final.

### Alternatif B

Knockout dengan preliminary round.

### Alternatif C

Round robin penuh.

Sistem menghitung:

* total pertandingan
* jumlah pertandingan setiap kelas
* waktu yang diperlukan
* waktu istirahat
* jalur menuju juara
* bye
* kemungkinan hasil

Panitia kemudian memilih format berdasarkan kebutuhan kegiatan.

---

# 17. MVP

Versi pertama tidak perlu langsung memiliki semua fitur.

### MVP Phase 1

* Master kelas
* Buat lomba
* Pilih peserta
* 1v1 / 2v2 / 3v3 / 4v4
* Knockout
* Group stage
* Bye detection
* Match distribution
* Rest calculation
* Visual bracket
* Schedule generator

### Phase 2

* Scenario comparison
* What-if analysis
* Cross-event conflict
* Player-load analysis
* Manual adjustment

### Phase 3

* Probability engine
* Monte Carlo simulation
* Advanced scheduler
* Multi-lomba optimization

---

# 18. Success Criteria

Produk dianggap berhasil jika panitia dapat:

1. Memasukkan 28 kelas.
2. Memilih subset kelas untuk suatu lomba.
3. Menghasilkan skema untuk jumlah peserta yang tidak ideal.
4. Melihat semua bye.
5. Melihat jumlah pertandingan setiap kelas.
6. Melihat waktu istirahat.
7. Melihat player load.
8. Melihat bentrokan jadwal.
9. Membandingkan beberapa skema.
10. Menguji skenario dengan jumlah peserta yang berubah.

Kasus khusus **6 peserta** harus dapat dianalisis karena merupakan salah satu kasus nyata yang menjadi dasar kebutuhan produk.

---

# 19. Prinsip Pengembangan

Jangan memulai dari desain visual.

Urutan pengerjaan:

```text
Data Model
    ↓
Tournament Engine
    ↓
Fairness Engine
    ↓
Scheduler
    ↓
Probability Engine
    ↓
Test Cases
    ↓
UI
    ↓
Database
    ↓
Deployment
```

Prioritas utama adalah **akurasi algoritma dan transparansi hasil**, bukan banyaknya fitur atau tampilan yang terlihat canggih.
