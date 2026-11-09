"""Klasifikasi teks berbahasa Indonesia: berpotensi hoaks atau tidak.

Pendekatan bertingkat:
(a) Opsional — bila environment variable SIBERWATCH_USE_HF=1 dan paket
    `transformers` tersedia, dicoba model IndoBERT dari Hugging Face.
    Dibungkus try/except penuh; kegagalan apa pun jatuh ke fallback.
(b) Default & selalu jalan — skor heuristik pola clickbait, klaim ajaib
    tanpa sumber, dan ajakan menyebarkan. Hasilnya DILABELI jelas sebagai
    heuristik awal, bukan vonis kebenaran.

Catatan jujur: classifier ini menilai *pola bahasa* yang umum pada hoaks,
bukan memverifikasi fakta. Verifikasi faktual tetap perlu sumber resmi.
"""

from __future__ import annotations

import os
import re

# (pola regex, bobot, penjelasan)
_PATTERNS: list[tuple[str, int, str]] = [
    (r"sebarkan sebelum dihapus|sebelum dihapus", 18,
     "Ajakan menyebarkan dengan tekanan waktu ('sebelum dihapus')"),
    (r"\bviral\b|viralkan", 8, "Kata pemicu viralitas ('viral')"),
    (r"\bheboh\b|menggegerkan|menggemparkan", 8, "Bahasa sensasional ('heboh'/'menggegerkan')"),
    (r"terbukti (menyembuhkan|ampuh|efektif)", 14,
     "Klaim 'terbukti' tanpa menyebut sumber/bukti"),
    (r"sembuh total|menyembuhkan semua penyakit|segala penyakit", 16,
     "Klaim penyembuhan ajaib untuk semua penyakit"),
    (r"100% ampuh|dijamin sembuh|tanpa efek samping", 14,
     "Jaminan kesembuhan absolut (100%/dijamin/tanpa efek samping)"),
    (r"dalam \d+ (hari|malam|jam) saja|dalam semalam", 8,
     "Janji hasil instan dalam waktu sangat singkat"),
    (r"disembunyikan|menyembunyikan (rahasia|kebenaran|fakta)|sengaja ditutupi", 14,
     "Narasi konspirasi: kebenaran 'disembunyikan' pihak tertentu"),
    (r"dokter (sampai )?(terkejut|kewalahan|bingung)", 10,
     "Klaim 'dokter terkejut' — pola clickbait kesehatan klasik"),
    (r"kata netizen|kata peramal|menurut kabar|konon katanya|beredar pesan", 12,
     "Sumber tidak jelas ('kata netizen'/'konon'/pesan berantai)"),
    (r"bantu (share|sebarkan)|wajib (diteruskan|disebarkan|tonton)|sebar(kan)? (peringatan|sekarang)", 10,
     "Ajakan eksplisit untuk menyebarkan ke semua orang/grup"),
    (r"jangan sampai (ketahuan|ketinggalan|kehabisan)", 8,
     "Tekanan psikologis ('jangan sampai ...')"),
    (r"klik (link|di sini|bit\.ly)|bit\.ly/|t\.ly/", 10,
     "Mengarahkan ke tautan pendek yang tidak jelas tujuannya"),
    (r"gratis untuk \d+ orang|diskon 9\d%|terpilih (dapat|menang)|klaim sekarang", 12,
     "Pola penipuan promo/undian (hadiah gratis, diskon tidak masuk akal)"),
    (r"akan (jauh lebih besar|menyapu|melanda) malam ini", 12,
     "Prediksi bencana tanpa sumber resmi (pola hoaks kebencanaan)"),
    (r"ditangkap|kabur ke luar negeri", 8,
     "Klaim sensasional tentang figur publik tanpa sumber"),
]

_HF_MODEL = os.environ.get("SIBERWATCH_HF_MODEL", "cahya/bert-base-indonesian-1.5G")
_hf_pipeline = None
_hf_tried = False


def _try_hf_classify(text: str) -> dict | None:
    """Coba klasifikasi dengan model Hugging Face. None bila tidak tersedia.

    Model default adalah BERT bahasa Indonesia umum; tanpa fine-tuning
    khusus hoaks, hasilnya hanya eksperimental — karena itu jalur ini
    opt-in lewat SIBERWATCH_USE_HF=1.
    """
    global _hf_pipeline, _hf_tried
    if os.environ.get("SIBERWATCH_USE_HF") != "1":
        return None
    if not _hf_tried:
        _hf_tried = True
        try:
            from transformers import pipeline  # type: ignore

            _hf_pipeline = pipeline("sentiment-analysis", model=_HF_MODEL)
        except Exception:
            _hf_pipeline = None
    if _hf_pipeline is None:
        return None
    try:
        out = _hf_pipeline(text[:512])[0]
        return {
            "label": "Perlu Verifikasi",
            "score": int(round(float(out["score"]) * 100)),
            "reasons": [f"Model HF ({_HF_MODEL}) memberi label mentah "
                        f"'{out['label']}' dengan keyakinan {out['score']:.2f}. "
                        f"Model ini belum di-fine-tune untuk hoaks — perlakukan "
                        f"sebagai sinyal eksperimental saja."],
            "method": "huggingface",
        }
    except Exception:
        return None


def classify_heuristic(text: str) -> dict:
    """Klasifikasi heuristik pola bahasa. Selalu tersedia, tanpa dependensi."""
    lowered = text.lower()
    score = 0
    reasons: list[str] = []

    for pattern, weight, explanation in _PATTERNS:
        if re.search(pattern, lowered):
            score += weight
            reasons.append(f"{explanation} (+{weight})")

    # Huruf kapital berlebihan
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 20:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if caps_ratio > 0.30:
            score += 10
            reasons.append(f"Huruf kapital berlebihan ({caps_ratio:.0%} dari teks) (+10)")

    # Tanda seru berlebihan
    bangs = text.count("!")
    if bangs >= 3:
        pts = min(10, 2 * bangs)
        score += pts
        reasons.append(f"Tanda seru berlebihan ({bangs}x) (+{pts})")

    # Banyak tanda seru/pertanyaan ganda bergaya pesan berantai
    if "!!" in text and re.search(r"\?\?|!!", text):
        pass  # sudah tercakup di atas

    score = min(score, 100)
    if score >= 50:
        label = "Berpotensi Hoaks"
    elif score >= 25:
        label = "Perlu Verifikasi"
    else:
        label = "Kemungkinan Bukan Hoaks"
    if not reasons:
        reasons.append("Tidak ditemukan pola clickbait/klaim tak bersumber yang khas hoaks")

    return {"label": label, "score": score, "reasons": reasons, "method": "heuristik"}


def classify_text(text: str) -> dict:
    """Klasifikasikan satu teks. Mengembalikan dict:
    {label, score (0-100, semakin tinggi semakin berpotensi hoaks),
     reasons (list[str]), method ('heuristik' | 'huggingface')}.

    Jalur Hugging Face hanya dicoba bila SIBERWATCH_USE_HF=1; selain itu
    (dan bila gagal) selalu memakai heuristik.
    """
    text = (text or "").strip()
    if not text:
        return {"label": "Perlu Verifikasi", "score": 0,
                "reasons": ["Teks kosong — tidak ada yang bisa dinilai."],
                "method": "heuristik"}
    hf = _try_hf_classify(text)
    if hf is not None:
        return hf
    return classify_heuristic(text)
