"""Pemuatan data contoh + agregasi untuk dashboard (tren isu, early warning).

Data contoh bersifat fiktif dan dibuat manual (lihat data/*.csv) — prototipe
ini belum tersambung ke API platform mana pun.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_accounts_df() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "accounts.csv")
    return df


def load_accounts() -> list[dict]:
    """Data akun sebagai list of dict (untuk bot_score.score_account)."""
    return load_accounts_df().to_dict("records")


def load_posts_df() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "posts.csv", parse_dates=["timestamp"])
    return df


def topic_trend_df(posts: pd.DataFrame) -> pd.DataFrame:
    """Jumlah posting per hari per topik (format lebar untuk grafik garis)."""
    posts = posts.copy()
    posts["tanggal"] = posts["timestamp"].dt.date
    pivot = (posts.groupby(["tanggal", "topic"]).size()
             .unstack(fill_value=0)
             .sort_index())
    return pivot


def topic_growth(posts: pd.DataFrame, recent_days: int = 2) -> pd.DataFrame:
    """Pertumbuhan tiap topik: jendela terbaru vs periode sebelumnya.

    Mengembalikan DataFrame kolom: topic, posting_terbaru, posting_sebelumnya,
    pertumbuhan_pct (None bila periode sebelumnya 0 posting), total.
    Diurutkan dari pertumbuhan terbesar — bahan panel early warning.
    """
    posts = posts.copy()
    posts["tanggal"] = posts["timestamp"].dt.date
    last_day = posts["tanggal"].max()
    days = sorted(posts["tanggal"].unique())
    recent = set(days[-recent_days:])
    rows = []
    for topic, grp in posts.groupby("topic"):
        n_recent = int(grp["tanggal"].isin(recent).sum())
        n_before = int(len(grp) - n_recent)
        growth = None
        if n_before > 0:
            growth = (n_recent - n_before) / n_before * 100.0
        rows.append({
            "topic": topic,
            "posting_terbaru": n_recent,
            "posting_sebelumnya": n_before,
            "pertumbuhan_pct": growth,
            "total": int(len(grp)),
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(
        by=["pertumbuhan_pct", "posting_terbaru"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)
    return df
