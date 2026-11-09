"""Skor risiko bot/buzzer berbasis heuristik perilaku yang transparan.

Logika murni Python (tanpa streamlit/pandas) supaya mudah di-unit-test dan
diaudit: setiap akun yang dinilai WAJIB menghasilkan daftar alasan yang
menjelaskan dari mana skornya berasal. Tidak ada black box.

Faktor yang dinilai (total maksimum 100):
- Usia akun            : maks 25 poin
- Rasio following/followers : maks 20 poin
- Frekuensi posting    : maks 20 poin
- Keseragaman konten   : maks 20 poin
- Ledakan aktivitas    : maks 15 poin
"""

from __future__ import annotations


def _age_points(age_days: int) -> tuple[int, str | None]:
    if age_days < 30:
        return 25, f"Usia akun sangat muda ({age_days} hari, < 30 hari)"
    if age_days < 90:
        return 18, f"Usia akun muda ({age_days} hari, < 90 hari)"
    if age_days < 180:
        return 10, f"Usia akun relatif baru ({age_days} hari, < 180 hari)"
    if age_days < 365:
        return 5, f"Usia akun di bawah 1 tahun ({age_days} hari)"
    return 0, None


def _ratio_points(followers: int, following: int) -> tuple[int, str | None]:
    ratio = following / max(followers, 1)
    if ratio > 10:
        return 20, (f"Rasio following/followers sangat timpang "
                    f"({following} following vs {followers} followers, rasio {ratio:.1f}x)")
    if ratio > 5:
        return 15, (f"Rasio following/followers timpang "
                    f"({following} following vs {followers} followers, rasio {ratio:.1f}x)")
    if ratio > 2:
        return 8, (f"Following jauh lebih banyak daripada followers "
                   f"(rasio {ratio:.1f}x)")
    return 0, None


def _frequency_points(posts_per_day: float) -> tuple[int, str | None]:
    if posts_per_day > 50:
        return 20, f"Frekuensi posting ekstrem ({posts_per_day:g} posting/hari, > 50)"
    if posts_per_day > 30:
        return 15, f"Frekuensi posting sangat tinggi ({posts_per_day:g} posting/hari, > 30)"
    if posts_per_day > 15:
        return 8, f"Frekuensi posting tinggi ({posts_per_day:g} posting/hari, > 15)"
    if posts_per_day > 8:
        return 3, f"Frekuensi posting di atas rata-rata ({posts_per_day:g} posting/hari)"
    return 0, None


def _uniformity_points(uniform_content_pct: float) -> tuple[int, str | None]:
    if uniform_content_pct > 80:
        return 20, (f"Konten sangat seragam ({uniform_content_pct:g}% posting bertema sama, "
                    f"khas akun kampanye/buzzer)")
    if uniform_content_pct > 60:
        return 13, f"Konten cenderung seragam ({uniform_content_pct:g}% posting bertema sama)"
    if uniform_content_pct > 40:
        return 6, f"Konten agak seragam ({uniform_content_pct:g}% posting bertema sama)"
    return 0, None


def _burst_points(burst_ratio: float) -> tuple[int, str | None]:
    if burst_ratio > 5:
        return 15, (f"Ledakan aktivitas ekstrem (aktivitas terkini {burst_ratio:g}x "
                    f"dari biasanya — pola amplifikasi mendadak)")
    if burst_ratio > 3:
        return 10, (f"Ledakan aktivitas tinggi (aktivitas terkini {burst_ratio:g}x "
                    f"dari biasanya)")
    if burst_ratio > 2:
        return 5, (f"Aktivitas meningkat tidak wajar (aktivitas terkini "
                   f"{burst_ratio:g}x dari biasanya)")
    return 0, None


def risk_level(score: int) -> str:
    """Label tingkat risiko dari skor 0-100."""
    if score >= 70:
        return "Tinggi"
    if score >= 40:
        return "Sedang"
    return "Rendah"


def score_account(account: dict) -> dict:
    """Hitung skor risiko bot/buzzer satu akun.

    Parameters
    ----------
    account : dict dengan kunci
        username (str), age_days (int), followers (int), following (int),
        posts_per_day (float), uniform_content_pct (float), burst_ratio (float).

    Returns
    -------
    dict: {username, score, level, reasons (list[str]), breakdown (dict faktor->poin)}
    """
    factors = [
        ("usia_akun", _age_points(int(account["age_days"]))),
        ("rasio_follow", _ratio_points(int(account["followers"]), int(account["following"]))),
        ("frekuensi_posting", _frequency_points(float(account["posts_per_day"]))),
        ("keseragaman_konten", _uniformity_points(float(account["uniform_content_pct"]))),
        ("ledakan_aktivitas", _burst_points(float(account["burst_ratio"]))),
    ]

    score = 0
    reasons: list[str] = []
    breakdown: dict[str, int] = {}
    for name, (points, reason) in factors:
        breakdown[name] = points
        score += points
        if reason:
            reasons.append(f"{reason} (+{points} poin)")

    score = min(score, 100)
    if not reasons:
        reasons.append("Tidak ditemukan pola perilaku berisiko yang signifikan "
                       "(akun tampak organik)")

    return {
        "username": account["username"],
        "score": score,
        "level": risk_level(score),
        "reasons": reasons,
        "breakdown": breakdown,
    }


def score_accounts(accounts: list[dict]) -> list[dict]:
    """Skor banyak akun sekaligus, diurutkan dari skor tertinggi."""
    results = [score_account(a) for a in accounts]
    return sorted(results, key=lambda r: r["score"], reverse=True)
