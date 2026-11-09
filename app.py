"""SIBERWATCH — Dashboard Deteksi Buzzer/Bot & Klasifikasi Hoaks Bahasa Indonesia.

Kartika Cyber Hackathon 2026 · Kategori Cognitive Domain · Tim ELARCV (solo).

Jalankan:  streamlit run app.py

Semua data pada prototipe ini adalah data contoh fiktif (data/*.csv).
Klasifikasi narasi default memakai heuristik pola bahasa dan DILABELI
sebagai heuristik awal — bukan vonis kebenaran.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from siberwatch import bot_score, data as data_mod, hoax_classifier, network_viz

st.set_page_config(page_title="SIBERWATCH", page_icon="🛡️", layout="wide")

st.title("🛡️ SIBERWATCH")
st.caption("Dashboard Deteksi Buzzer/Bot & Klasifikasi Hoaks Bahasa Indonesia — "
           "Kartika Cyber Hackathon 2026 · Cognitive Domain · Tim ELARCV. "
           "Data yang tampil adalah data contoh fiktif untuk prototipe.")

accounts_df = data_mod.load_accounts_df()
posts_df = data_mod.load_posts_df()
scored = bot_score.score_accounts(data_mod.load_accounts())
score_by_user = {r["username"]: r for r in scored}

menu = st.sidebar.radio(
    "Tampilan",
    ["Dashboard", "Analisis Akun", "Analisis Narasi", "Jaringan"],
)

# ---------------------------------------------------------------- Dashboard
if menu == "Dashboard":
    st.header("Dashboard Pemantauan Isu")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total posting contoh", len(posts_df))
    c2.metric("Akun dipantau", len(accounts_df))
    high = sum(1 for r in scored if r["level"] == "Tinggi")
    c3.metric("Akun risiko bot tinggi", high)

    st.subheader("Tren isu per topik")
    trend = data_mod.topic_trend_df(posts_df)
    try:
        import plotly.express as px

        long = trend.reset_index().melt(id_vars="tanggal", var_name="topik",
                                        value_name="jumlah_posting")
        fig = px.line(long, x="tanggal", y="jumlah_posting", color="topik",
                      markers=True)
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.line_chart(trend)

    st.subheader("⚠️ Panel Early Warning — topik dengan pertumbuhan tercepat")
    growth = data_mod.topic_growth(posts_df, recent_days=2)
    for _, row in growth.iterrows():
        pct = row["pertumbuhan_pct"]
        if pct is not None and pct >= 100:
            st.error(f"**{row['topic']}** — naik {pct:.0f}% "
                     f"({row['posting_sebelumnya']} → {row['posting_terbaru']} posting "
                     f"dalam 2 hari terakhir). Perlu pemeriksaan amplifikasi terkoordinasi.")
        elif pct is not None and pct > 0:
            st.warning(f"**{row['topic']}** — naik {pct:.0f}% "
                       f"({row['posting_sebelumnya']} → {row['posting_terbaru']} posting).")
        else:
            label = "stabil/menurun" if pct is not None else "baru muncul"
            st.info(f"**{row['topic']}** — {label} "
                    f"({row['posting_terbaru']} posting pada 2 hari terakhir).")
    st.dataframe(growth, use_container_width=True)

# ------------------------------------------------------------- Analisis Akun
elif menu == "Analisis Akun":
    st.header("Analisis Akun — Skor Risiko Bot/Buzzer")
    st.write("Skor 0–100 dari heuristik perilaku yang transparan: usia akun, rasio "
             "following/followers, frekuensi posting, keseragaman konten, dan "
             "ledakan aktivitas. Klik akun untuk melihat alasan skornya.")

    table = pd.DataFrame([{
        "username": r["username"],
        "skor_bot": r["score"],
        "tingkat_risiko": r["level"],
        "usia_hari": int(a["age_days"]),
        "followers": int(a["followers"]),
        "following": int(a["following"]),
        "posting_per_hari": a["posts_per_day"],
        "konten_seragam_%": a["uniform_content_pct"],
        "ledakan_aktivitas_x": a["burst_ratio"],
    } for r, a in zip(scored, sorted(
        data_mod.load_accounts(), key=lambda x: -score_by_user[x["username"]]["score"]))])
    st.dataframe(table, use_container_width=True)

    pilihan = st.selectbox("Lihat alasan skor akun:", [r["username"] for r in scored])
    detail = score_by_user[pilihan]
    st.metric(f"Skor {pilihan}", f"{detail['score']} / 100 ({detail['level']})")
    for reason in detail["reasons"]:
        st.write(f"- {reason}")
    st.caption("Rincian poin per faktor: " +
               ", ".join(f"{k}={v}" for k, v in detail["breakdown"].items()))

# ------------------------------------------------------------ Analisis Narasi
elif menu == "Analisis Narasi":
    st.header("Analisis Narasi — Klasifikasi Potensi Hoaks")
    st.warning("Metode default: **heuristik pola bahasa** (clickbait, klaim ajaib "
               "tanpa sumber, ajakan menyebarkan). Ini menilai pola bahasa, BUKAN "
               "memverifikasi fakta — selalu cek sumber resmi untuk keputusan akhir.")

    contoh = posts_df["text"].tolist()
    pilihan_contoh = st.selectbox("Pakai contoh dari data:", ["(tulis sendiri)"] + contoh)
    default_text = "" if pilihan_contoh == "(tulis sendiri)" else pilihan_contoh
    teks = st.text_area("Tempel teks narasi yang ingin dinilai:", value=default_text,
                        height=140)
    if st.button("Klasifikasikan"):
        hasil = hoax_classifier.classify_text(teks)
        if hasil["label"] == "Berpotensi Hoaks":
            st.error(f"**{hasil['label']}** — skor pola hoaks {hasil['score']}/100")
        elif hasil["label"] == "Perlu Verifikasi":
            st.warning(f"**{hasil['label']}** — skor pola hoaks {hasil['score']}/100")
        else:
            st.success(f"**{hasil['label']}** — skor pola hoaks {hasil['score']}/100")
        st.caption(f"Metode: {hasil['method']}")
        for reason in hasil["reasons"]:
            st.write(f"- {reason}")

    st.subheader("Hasil klasifikasi semua posting contoh")
    rows = []
    for _, p in posts_df.iterrows():
        h = hoax_classifier.classify_text(p["text"])
        rows.append({
            "username": p["username"],
            "topik": p["topic"],
            "label": h["label"],
            "skor_hoaks": h["score"],
            "teks": p["text"][:90] + ("…" if len(p["text"]) > 90 else ""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ------------------------------------------------------------------ Jaringan
elif menu == "Jaringan":
    st.header("Jaringan Amplifikasi — Akun yang Mengangkat Narasi yang Sama")
    st.write("Dua akun terhubung bila memakai hashtag yang sama. Kluster rapat dari "
             "akun berisiko tinggi yang mengangkat narasi yang sama adalah indikasi "
             "amplifikasi terkoordinasi.")
    scores = {u: r["score"] for u, r in score_by_user.items()}
    fig = network_viz.make_network_figure(posts_df, scores=scores)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Plotly tidak tersedia — menampilkan tabel relasi sebagai fallback.")
    st.subheader("Kluster narasi per hashtag")
    for tag, users in network_viz.narrative_clusters(posts_df).items():
        risky = [u for u in users if score_by_user.get(u, {}).get("level") == "Tinggi"]
        st.write(f"**{tag}** — {len(users)} akun: {', '.join(users)}")
        if risky:
            st.write(f"  ⚠️ {len(risky)} di antaranya berisiko bot tinggi: "
                     f"{', '.join(risky)}")
    st.subheader("Tabel relasi antarakun")
    st.dataframe(network_viz.relation_table(posts_df), use_container_width=True)
