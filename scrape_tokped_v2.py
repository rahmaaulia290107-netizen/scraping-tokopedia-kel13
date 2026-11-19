"""
Scraper review Tokopedia (versi 2)
Beda dari versi 1: ada pengaturan SORT_BY dan FILTER_BY supaya urutan / filter
review bisa diubah (biar rating nggak miring ke bintang 5 doang).
"""

import json
import random
import time
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright

# ====== BAGIAN YANG BOLEH KAMU UBAH ======
URL_PRODUK = "https://www.tokopedia.com/scoraofficial/hero-scora-toner-series-80ml-hydra-calm-cica-toner-phytobright-milky-toner-d-panthenol-barrier-essence-1733122404189439502"
MAX_HALAMAN = 20          # 1 halaman = 10 review. Mulai kecil dulu buat tes.
NAMA_FILE = "review_tokopedia_200.csv"

# Biarkan None kalau mau pakai bawaan Tokopedia ("Paling Membantu").
# Kalau sudah tahu nilainya dari tab Payload, isi di dalam tanda kutip,
# contoh: SORT_BY = "isi_nilai_dari_payload"
SORT_BY = "create_time desc"
FILTER_BY = None
# =========================================


def ubah_tanggal(detik):
    """Ubah angka timestamp (misal 1777684977) jadi tanggal biasa."""
    try:
        return datetime.fromtimestamp(int(detik)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def olah_response(data):
    """Ambil field penting dari 1 response, kembalikan (daftar_baris, ada_halaman_lagi)."""
    isi = data[0]["data"]["productrevGetProductReviewList"]
    baris = []
    for r in isi.get("list", []):
        user = r.get("user") or {}
        like = r.get("likeDislike") or {}
        baris.append({
            "url_produk": URL_PRODUK.split("?")[0],
            "id_review": r.get("id"),
            "user_id": user.get("userID"),
            "nama_user": user.get("fullName"),
            "rating": r.get("productRating"),
            "isi_review": r.get("message"),
            "tanggal": ubah_tanggal(r.get("reviewCreateTime")),
            "waktu_relatif": r.get("reviewCreateTimestamp"),
            "varian": r.get("variantName"),
            "jumlah_like": like.get("totalLike"),
            "jumlah_foto": len(r.get("imageAttachments") or []),
            "balasan_penjual": (r.get("reviewResponse") or {}).get("message", ""),
        })
    return baris, bool(isi.get("hasNext"))


def main():
    if "TEMPEL_LINK" in URL_PRODUK:
        print("Isi dulu URL_PRODUK di bagian atas file ini ya!")
        return

    tangkapan = {}

    def cek_response(response):
        """Dipanggil tiap ada response masuk. Kita cari yang productReviewList."""
        if "req" in tangkapan:
            return
        try:
            req = response.request
            if "graphql" in req.url and "productReviewList" in (req.post_data or ""):
                tangkapan["req"] = req
        except Exception:
            pass

    semua_baris = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.on("response", cek_response)

        print("Membuka halaman produk...")
        page.goto(URL_PRODUK, wait_until="domcontentloaded")
        time.sleep(4)

        for _ in range(6):
            page.mouse.wheel(0, 900)
            time.sleep(1.5)
            if "req" in tangkapan:
                break

        if "req" not in tangkapan:
            try:
                page.get_by_text("Ulasan", exact=True).first.click()
                time.sleep(4)
            except Exception:
                pass

        if "req" not in tangkapan:
            print("Request review belum ketangkap. Coba scroll manual ke bagian "
                  "Ulasan di browser yang kebuka, lalu jalankan ulang.")
            browser.close()
            return

        req = tangkapan["req"]
        payload = json.loads(req.post_data)
        headers = {
            k: v for k, v in req.headers.items()
            if k.lower() not in ("content-length", "host")
        }

        # Terapkan pengaturan urutan / filter kalau diisi
        if SORT_BY is not None:
            payload[0]["variables"]["sortBy"] = SORT_BY
        if FILTER_BY is not None:
            payload[0]["variables"]["filterBy"] = FILTER_BY
        print("Urutan:", payload[0]["variables"].get("sortBy"),
              "| Filter:", repr(payload[0]["variables"].get("filterBy")))

        for nomor in range(1, MAX_HALAMAN + 1):
            payload[0]["variables"]["page"] = nomor
            res = page.context.request.post(req.url, data=payload, headers=headers)

            if not res.ok:
                print(f"Halaman {nomor} gagal (status {res.status}). Berhenti.")
                break

            baris, ada_lagi = olah_response(res.json())
            semua_baris.extend(baris)
            print(f"Halaman {nomor}: dapat {len(baris)} review (total {len(semua_baris)})")

            if not ada_lagi:
                print("Sudah halaman terakhir.")
                break

            time.sleep(random.uniform(2, 4))

        browser.close()

    if semua_baris:
        df = pd.DataFrame(semua_baris)
        df.to_csv(NAMA_FILE, index=False, encoding="utf-8-sig")
        print(f"Selesai! {len(df)} review disimpan di {NAMA_FILE}")
    else:
        print("Nggak ada data yang berhasil diambil.")


if __name__ == "__main__":
    main()
