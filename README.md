# SIBERWATCH — Dashboard Deteksi Buzzer/Bot & Klasifikasi Hoaks Bahasa Indonesia

Prototipe untuk **Kartika Cyber Hackathon 2026** (PUSSIBERAD × CODEPOLITAN),
kategori **Cognitive Domain (Siber Sosial)** · Tim **ELARCV** (solo).
Deadline submission: 15 November 2026.

## Apa yang dilakukan

1. **Skor risiko bot/buzzer** per akun (0–100) dari heuristik perilaku yang
   transparan — usia akun, rasio following/followers, frekuensi posting,
   keseragaman konten, ledakan aktivitas. Setiap skor disertai **daftar alasan**
   yang bisa diaudit, bukan black box.
2. **Klasifikasi narasi** berbahasa Indonesia: *Berpotensi Hoaks* / *Perlu
   Verifikasi* / *Kemungkinan Bukan Hoaks*, lengkap dengan penjelasan pola
   bahasa yang memicu penilaian.
3. **Jaringan amplifikasi**: visualisasi akun-akun yang mengangkat
   hashtag/narasi yang sama — kluster akun berisiko tinggi pada narasi yang
   sama mengindikasikan amplifikasi terkoordinasi.
4. **Panel early warning**: topik dengan pertumbuhan posting tercepat dalam
   2 hari terakhir.

## Kejujuran metode (penting)

- **Skor bot = heuristik perilaku.** Ambang dan bobotnya ditetapkan manual
  berdasarkan pola umum akun buzzer; belum dikalibrasi dengan dataset
  berlabel nyata.
- **Klasifikasi hoaks = heuristik pola bahasa** (clickbait, klaim ajaib tanpa
  sumber, ajakan menyebarkan, dst.) — ini *default* dan selalu aktif. Ia
  menilai **pola bahasa**, bukan kebenaran fakta. Jalur model Hugging Face
  (IndoBERT) tersedia sebagai opsi eksperimental (`SIBERWATCH_USE_HF=1`),
  tetapi modelnya belum di-fine-tune untuk deteksi hoaks sehingga hasilnya
  bukan patokan.
- **Semua data adalah data contoh fiktif** (`data/accounts.csv`,
  `data/posts.csv`) yang dibuat manual untuk demonstrasi — tidak ada
  scraping, tidak ada data pribadi, tidak ada klaim atas akun nyata.
  Kolom `label` pada accounts.csv adalah label pola contoh dari pembuat
  data, hanya untuk membandingkan hasil skor saat demo.
- Prototipe **belum tersambung ke API platform** media sosial mana pun.

## Struktur repo

```
siberwatch/
├── app.py                  # Aplikasi Streamlit (4 tampilan)
├── requirements.txt
├── README.md
├── data/
│   ├── accounts.csv        # 30 akun contoh (buzzer, abu-abu, organik)
│   └── posts.csv           # 42 posting contoh berbahasa Indonesia
└── siberwatch/
    ├── __init__.py
    ├── bot_score.py        # Heuristik skor bot + alasan (Python murni)
    ├── hoax_classifier.py  # Klasifikasi narasi (heuristik; HF opsional)
    ├── network_viz.py      # Jaringan akun (plotly; networkx opsional)
    └── data.py             # Loader data + tren topik + pertumbuhan (pandas)
```

## Menjalankan secara lokal

Butuh Python 3.10+.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Lalu buka http://localhost:8501 — pilih tampilan dari sidebar:
**Dashboard · Analisis Akun · Analisis Narasi · Jaringan**.

Catatan lingkungan pengembangan saat ini: `streamlit` dan `networkx` belum
terpasang di mesin dev, jadi aplikasi belum dijalankan end-to-end di sini;
logika inti (skor, klasifikasi, tren, jaringan) sudah diuji langsung tanpa
Streamlit. `networkx` bersifat opsional — tanpa itu grafik jaringan memakai
layout melingkar bawaan. Untuk menguji logika inti saja:

```bash
python3 -c "from siberwatch import data, bot_score; \
print(bot_score.score_accounts(data.load_accounts())[:3])"
```

## Deploy gratis

**Streamlit Community Cloud**
1. Push repo ini ke GitHub (publik).
2. Buka https://share.streamlit.io → *New app* → pilih repo, branch, dan
   file `app.py`.
3. Deploy — dependensi diambil otomatis dari `requirements.txt`.

**Hugging Face Spaces**
1. Buat Space baru dengan SDK **Streamlit**.
2. Upload/push semua file repo (termasuk folder `data/` dan `siberwatch/`).
3. Space akan menjalankan `app.py` secara otomatis.

## Rencana pengembangan berikutnya

- Kalibrasi bobot skor bot dengan dataset akun berlabel.
- Fine-tuning IndoBERT pada dataset hoaks Indonesia terbuka agar jalur
  model menjadi patokan utama, menggantikan heuristik.
- Konektor data resmi (API platform) dengan mode hanya-baca dan
  penghormatan terhadap ketentuan layanan platform.
- Ekspor laporan pemantauan (PDF/CSV) untuk analis.
