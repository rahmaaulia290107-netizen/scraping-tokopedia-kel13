
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Dashboard Review Tokopedia", page_icon="📊", layout="wide")

# ====== BAGIAN YANG BOLEH KAMU UBAH ======
FILE_BAWAAN = "review_tokopedia_200.csv"
# =========================================

# Kata umum yang nggak menarik buat dihitung
STOPWORDS = set("""
yang dan di ke dari ini itu untuk dengan aku saya ga gak nggak tidak tapi juga udah sudah
banget bgt sama pada atau ada jadi karena kalau kalo lagi aja saja nya sih deh lebih sangat
mau akan bisa buat dalam oleh kok nih ya yg dg dr krn tp jg udh sdh pas cuma cm masih belum
banyak sekali dulu semoga the and bahan manfaat jenis produk
""".split())


def hitung_kata(teks_series, top=15):
    """Hitung kata yang paling sering muncul."""
    hitung = Counter()
    for teks in teks_series:
        for kata in re.findall(r"[a-zA-Z]+", str(teks).lower()):
            if len(kata) > 2 and kata not in STOPWORDS:
                hitung[kata] += 1
    return pd.Series(dict(hitung.most_common(top)), dtype="int64")


# ---------- 1. Muat data ----------
st.title("📊 Dashboard Review Tokopedia")

file_upload = st.sidebar.file_uploader("Upload CSV (opsional)", type="csv")
if file_upload is not None:
    df = pd.read_csv(file_upload)
elif Path(FILE_BAWAAN).exists():
    df = pd.read_csv(FILE_BAWAAN)
else:
    st.info(f"File {FILE_BAWAAN} nggak ketemu. Taruh di folder yang sama, atau upload lewat sidebar.")
    st.stop()

df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
df["isi_review"] = df["isi_review"].fillna("")
df = df.dropna(subset=["tanggal"])

# ---------- 2. Filter di sidebar ----------
st.sidebar.header("Filter")

rating_pilihan = st.sidebar.multiselect("Rating", [5, 4, 3, 2, 1], default=[5, 4, 3, 2, 1])

varian_semua = sorted(df["varian"].dropna().unique())
varian_pilihan = st.sidebar.multiselect("Varian", varian_semua, default=varian_semua)

tgl_min = df["tanggal"].min().date()
tgl_max = df["tanggal"].max().date()
rentang = st.sidebar.date_input("Rentang tanggal", (tgl_min, tgl_max),
                                min_value=tgl_min, max_value=tgl_max)

kata_cari = st.sidebar.text_input("Cari kata di isi review")

mask = df["rating"].isin(rating_pilihan) & df["varian"].isin(varian_pilihan)
if isinstance(rentang, (tuple, list)) and len(rentang) == 2:
    mask &= df["tanggal"].dt.date.between(rentang[0], rentang[1])
if kata_cari:
    mask &= df["isi_review"].str.contains(kata_cari, case=False, na=False, regex=False)

data = df[mask]

if data.empty:
    st.warning("Nggak ada review yang cocok dengan filter. Longgarin filternya ya.")
    st.stop()

# ---------- 3. Angka ringkasan ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total review", len(data))
k2.metric("Rata-rata rating", f"{data['rating'].mean():.2f}")
k3.metric("% bintang 5", f"{(data['rating'] == 5).mean() * 100:.0f}%")
k4.metric("Total like", int(data["jumlah_like"].sum()))

# ---------- 4. Grafik ----------
kiri, kanan = st.columns(2)

with kiri:
    st.subheader("Jumlah review per rating")
    per_rating = data["rating"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    st.bar_chart(per_rating)

with kanan:
    st.subheader("Jumlah review per varian")
    st.bar_chart(data["varian"].value_counts())

kiri2, kanan2 = st.columns(2)

per_hari = (
    data.assign(hari=data["tanggal"].dt.normalize())
    .groupby("hari")
    .agg(jumlah=("id_review", "count"), rata_rating=("rating", "mean"))
)

with kiri2:
    st.subheader("Jumlah review per hari")
    st.line_chart(per_hari["jumlah"])

with kanan2:
    st.subheader("Rata-rata rating per hari")
    st.line_chart(per_hari["rata_rating"])

st.subheader("Kata yang paling sering muncul di review")
kata = hitung_kata(data["isi_review"])
if kata.empty:
    st.write("Belum ada teks review yang bisa dihitung.")
else:
    st.bar_chart(kata)

# ---------- 5. Tabel ----------
st.subheader("Daftar review")
kolom_tampil = ["tanggal", "nama_user", "rating", "varian", "isi_review", "jumlah_like", "jumlah_foto"]
tabel = data[kolom_tampil].sort_values("tanggal", ascending=False)
st.dataframe(tabel)

st.download_button(
    "⬇️ Download hasil filter (CSV)",
    data=tabel.to_csv(index=False).encode("utf-8-sig"),
    file_name="review_terfilter.csv",
    mime="text/csv",
)
