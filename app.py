import os
import sqlite3
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rahasia_stroller")

BASE_DIR = os.path.join(os.path.expanduser("~"), "nota_stroller")
os.makedirs(BASE_DIR, exist_ok=True)
DB_PATH = os.path.join(BASE_DIR, "stroller.db")


# --- FUNGSI DATABASE SQLITE3 ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS setting (
                id INTEGER PRIMARY KEY,
                nama_toko TEXT,
                alamat TEXT,
                no_hp TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stroller (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                harga INTEGER NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS transaksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_penyewa TEXT NOT NULL,
                no_wa TEXT NOT NULL,
                jaminan TEXT NOT NULL,
                stroller_nama TEXT NOT NULL,
                lama_sewa INTEGER NOT NULL,
                total_harga INTEGER NOT NULL,
                deposit INTEGER DEFAULT 0,
                tanggal_sewa TEXT NOT NULL,
                tanggal_kembali TEXT,
                denda INTEGER DEFAULT 0,
                status TEXT DEFAULT 'AKTIF'
            )"""
        )

        # Migrasi ringan jika tabel transaksi lama belum punya kolom status
        cols = [row["name"] for row in conn.execute("PRAGMA table_info(transaksi)").fetchall()]
        if "status" not in cols:
            conn.execute("ALTER TABLE transaksi ADD COLUMN status TEXT DEFAULT 'AKTIF'")

        # Cek jika data setting kosong, buat default
        cur = conn.execute("SELECT COUNT(*) FROM setting")
        if cur.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO setting (id, nama_toko, alamat, no_hp) VALUES (1, ?, ?, ?)",
                ("Stroller Sewa", "Jl. Contoh No. 1", "08123456789"),
            )

        # Cek jika data stroller kosong, buat default
        cur_s = conn.execute("SELECT COUNT(*) FROM stroller")
        if cur_s.fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO stroller (nama, harga) VALUES (?, ?)",
                [
                    ("Stroller Bayi Lipat", 50000),
                    ("Stroller Cabin Size", 75000),
                ],
            )
        conn.commit()


def format_wa(no_wa: str) -> str:
    cleaned = "".join(ch for ch in (no_wa or "") if ch.isdigit())
    if cleaned.startswith("0"):
        return "62" + cleaned[1:]
    if cleaned.startswith("8"):
        return "62" + cleaned
    return cleaned


def parse_dt(val: str):
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


@app.template_filter("rp")
def format_rp(value):
    try:
        return f"Rp {int(value or 0):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "Rp 0"


init_db()


# --- ROUTES ---
@app.route("/")
def index():
    return redirect(url_for("kasir"))


@app.route("/setting", methods=["GET", "POST"])
def setting():
    with get_db() as conn:
        if request.method == "POST":
            nama_toko = (request.form.get("nama_toko") or "").strip()
            alamat = (request.form.get("alamat") or "").strip()
            no_hp = (request.form.get("no_hp") or "").strip()
            if not nama_toko:
                flash("Nama toko wajib diisi.", "danger")
                return redirect(url_for("setting"))

            conn.execute(
                "UPDATE setting SET nama_toko=?, alamat=?, no_hp=? WHERE id=1",
                (nama_toko, alamat, no_hp),
            )
            conn.commit()
            flash("Pengaturan berhasil disimpan!", "success")
            return redirect(url_for("setting"))

        s = conn.execute("SELECT * FROM setting WHERE id=1").fetchone()
    return render_template("setting.html", s=s)


@app.route("/stroller", methods=["GET", "POST"])
def daftar_stroller():
    with get_db() as conn:
        if request.method == "POST":
            nama = (request.form.get("nama") or "").strip()
            try:
                harga = int(request.form.get("harga", 0))
            except ValueError:
                harga = 0

            if not nama or harga <= 0:
                flash("Nama stroller dan harga sewa (lebih dari 0) wajib diisi.", "danger")
                return redirect(url_for("daftar_stroller"))

            conn.execute(
                "INSERT INTO stroller (nama, harga) VALUES (?, ?)",
                (nama, harga),
            )
            conn.commit()
            flash("Stroller berhasil ditambahkan!", "success")
            return redirect(url_for("daftar_stroller"))

        strollers = conn.execute("SELECT * FROM stroller ORDER BY id DESC").fetchall()
    return render_template("stroller.html", strollers=strollers)


@app.route("/hapus_stroller/<int:id>")
def hapus_stroller(id):
    with get_db() as conn:
        conn.execute("DELETE FROM stroller WHERE id=?", (id,))
        conn.commit()
    flash("Stroller dihapus!", "danger")
    return redirect(url_for("daftar_stroller"))


@app.route("/kasir", methods=["GET", "POST"])
def kasir():
    with get_db() as conn:
        strollers = conn.execute("SELECT * FROM stroller ORDER BY nama ASC").fetchall()
        if request.method == "POST":
            nama_penyewa = (request.form.get("nama") or "").strip()
            no_wa = (request.form.get("wa") or "").strip()
            jaminan = (request.form.get("jaminan") or "").strip()
            stroller_id = request.form.get("stroller_id")

            try:
                lama = max(1, int(request.form.get("lama", 1)))
                deposit = max(0, int(request.form.get("deposit") or 0))
            except ValueError:
                flash("Lama sewa dan deposit harus berupa angka.", "danger")
                return redirect(url_for("kasir"))

            st = conn.execute("SELECT * FROM stroller WHERE id=?", (stroller_id,)).fetchone()
            if not st:
                flash("Jenis stroller tidak ditemukan.", "danger")
                return redirect(url_for("kasir"))

            total = int(st["harga"]) * lama
            now = datetime.now()
            tgl_sewa = now.strftime("%Y-%m-%d %H:%M:%S")
            tgl_kembali = (now + timedelta(days=lama)).strftime("%Y-%m-%d %H:%M:%S")

            cur = conn.execute(
                """INSERT INTO transaksi (
                    nama_penyewa, no_wa, jaminan, stroller_nama,
                    lama_sewa, total_harga, deposit, tanggal_sewa,
                    tanggal_kembali, denda, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'AKTIF')""",
                (
                    nama_penyewa,
                    no_wa,
                    jaminan,
                    st["nama"],
                    lama,
                    total,
                    deposit,
                    tgl_sewa,
                    tgl_kembali,
                ),
            )
            conn.commit()
            return redirect(url_for("nota", id=cur.lastrowid))

    return render_template("kasir.html", strollers=strollers)


@app.route("/kembalikan/<int:id>", methods=["POST"])
def kembalikan(id):
    try:
        denda = max(0, int(request.form.get("denda") or 0))
    except ValueError:
        denda = 0

    with get_db() as conn:
        trx = conn.execute("SELECT id FROM transaksi WHERE id=?", (id,)).fetchone()
        if not trx:
            abort(404)

        conn.execute(
            "UPDATE transaksi SET denda=?, tanggal_kembali=?, status='SELESAI' WHERE id=?",
            (denda, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id),
        )
        conn.commit()

    flash("Barang berhasil dikembalikan!", "success")
    return redirect(url_for("riwayat"))


@app.route("/nota/<int:id>")
def nota(id):
    with get_db() as conn:
        trx = conn.execute("SELECT * FROM transaksi WHERE id=?", (id,)).fetchone()
        s = conn.execute("SELECT * FROM setting WHERE id=1").fetchone()

    if not trx:
        abort(404)

    trx_dict = dict(trx)
    trx_dict["tanggal_sewa"] = parse_dt(trx["tanggal_sewa"]) or datetime.now()
    trx_dict["tanggal_kembali"] = parse_dt(trx["tanggal_kembali"])
    trx_dict["wa_link"] = format_wa(trx["no_wa"])

    return render_template("nota.html", trx=trx_dict, s=s)


@app.route("/riwayat")
def riwayat():
    with get_db() as conn:
        transaksi = conn.execute("SELECT * FROM transaksi ORDER BY id DESC").fetchall()
        total_pendapatan = (
            conn.execute("SELECT SUM(total_harga + COALESCE(denda, 0)) FROM transaksi").fetchone()[0]
            or 0
        )

    trx_list = []
    for t in transaksi:
        t_dict = dict(t)
        t_dict["tanggal_sewa"] = parse_dt(t["tanggal_sewa"])
        t_dict["tanggal_kembali"] = parse_dt(t["tanggal_kembali"])
        t_dict["wa_link"] = format_wa(t["no_wa"])
        trx_list.append(t_dict)

    return render_template(
        "riwayat.html", transaksi=trx_list, total_pendapatan=total_pendapatan
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
