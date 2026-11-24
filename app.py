from flask import Flask, render_template, request, redirect, url_for, flash
import os
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'rahasia_stroller'
db_path = os.path.join(os.path.expanduser('~'), 'nota_stroller', 'stroller.db')

# --- FUNGSI DATABASE SQLITE3 ---
def get_db():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS setting (id INTEGER PRIMARY KEY, nama_toko TEXT, alamat TEXT, no_hp TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS stroller (id INTEGER PRIMARY KEY, nama TEXT, harga INTEGER)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS transaksi (id INTEGER PRIMARY KEY, nama_penyewa TEXT, no_wa TEXT, jaminan TEXT, stroller_nama TEXT, lama_sewa INTEGER, total_harga INTEGER, deposit INTEGER, tanggal_sewa TEXT, tanggal_kembali TEXT, denda INTEGER)''')
        
        # Cek jika data setting kosong, buat default
        cur = conn.execute('SELECT count(*) FROM setting')
        if cur.fetchone()[0] == 0:
            conn.execute("INSERT INTO setting (nama_toko, alamat, no_hp) VALUES ('Stroller Sewa', 'Jl. Contoh No. 1', '08123456789')")
            conn.execute("INSERT INTO stroller (nama, harga) VALUES ('Stroller Bayi Lipat', 50000)")
            conn.execute("INSERT INTO stroller (nama, harga) VALUES ('Stroller Cabin Size', 75000)")

init_db()

# --- ROUTES ---
@app.route('/')
def index():
    return redirect(url_for('kasir'))

@app.route('/setting', methods=['GET', 'POST'])
def setting():
    with get_db() as conn:
        if request.method == 'POST':
            conn.execute('UPDATE setting SET nama_toko=?, alamat=?, no_hp=? WHERE id=1', 
                         (request.form['nama_toko'], request.form['alamat'], request.form['no_hp']))
            conn.commit()
            flash('Pengaturan berhasil disimpan!', 'success')
            return redirect(url_for('setting'))
        s = conn.execute('SELECT * FROM setting WHERE id=1').fetchone()
    return render_template('setting.html', s=s)

@app.route('/stroller', methods=['GET', 'POST'])
def daftar_stroller():
    with get_db() as conn:
        if request.method == 'POST':
            conn.execute('INSERT INTO stroller (nama, harga) VALUES (?, ?)', (request.form['nama'], int(request.form['harga'])))
            conn.commit()
            flash('Stroller berhasil ditambahkan!', 'success')
            return redirect(url_for('daftar_stroller'))
        strollers = conn.execute('SELECT * FROM stroller').fetchall()
    return render_template('stroller.html', strollers=strollers)

@app.route('/hapus_stroller/<int:id>')
def hapus_stroller(id):
    with get_db() as conn:
        conn.execute('DELETE FROM stroller WHERE id=?', (id,))
        conn.commit()
    flash('Stroller dihapus!', 'danger')
    return redirect(url_for('daftar_stroller'))

@app.route('/kasir', methods=['GET', 'POST'])
def kasir():
    with get_db() as conn:
        strollers = conn.execute('SELECT * FROM stroller').fetchall()
        if request.method == 'POST':
            st = conn.execute('SELECT * FROM stroller WHERE id=?', (request.form['stroller_id'],)).fetchone()
            lama = int(request.form['lama'])
            total = st['harga'] * lama
            tgl_sewa = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tgl_kembali = (datetime.now() + timedelta(days=lama)).strftime("%Y-%m-%d %H:%M:%S")
            
            cur = conn.execute('''INSERT INTO transaksi (nama_penyewa, no_wa, jaminan, stroller_nama, lama_sewa, total_harga, deposit, tanggal_sewa, tanggal_kembali, denda) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)''', 
                               (request.form['nama'], request.form['wa'], request.form['jaminan'], st['nama'], lama, total, int(request.form.get('deposit', 0)), tgl_sewa, tgl_kembali))
            conn.commit()
            return redirect(url_for('nota', id=cur.lastrowid))
    return render_template('kasir.html', strollers=strollers)

@app.route('/kembalikan/<int:id>', methods=['POST'])
def kembalikan(id):
    with get_db() as conn:
        conn.execute('UPDATE transaksi SET denda=?, tanggal_kembali=? WHERE id=?', 
                     (int(request.form.get('denda', 0)), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id))
        conn.commit()
    flash('Barang berhasil dikembalikan!', 'success')
    return redirect(url_for('riwayat'))

@app.route('/nota/<int:id>')
def nota(id):
    with get_db() as conn:
        trx = conn.execute('SELECT * FROM transaksi WHERE id=?', (id,)).fetchone()
        s = conn.execute('SELECT * FROM setting WHERE id=1').fetchone()
    # Format tanggal untuk ditampilkan di HTML
    trx_dict = dict(trx)
    trx_dict['tanggal_sewa'] = datetime.strptime(trx['tanggal_sewa'], "%Y-%m-%d %H:%M:%S")
    trx_dict['tanggal_kembali'] = datetime.strptime(trx['tanggal_kembali'], "%Y-%m-%d %H:%M:%S")
    return render_template('nota.html', trx=trx_dict, s=s)

@app.route('/riwayat')
def riwayat():
    with get_db() as conn:
        transaksi = conn.execute('SELECT * FROM transaksi ORDER BY id DESC').fetchall()
        total_pendapatan = conn.execute('SELECT SUM(total_harga + COALESCE(denda, 0)) FROM transaksi').fetchone()[0] or 0
    
    # Format tanggal
    trx_list = []
    for t in transaksi:
        t_dict = dict(t)
        t_dict['tanggal_sewa'] = datetime.strptime(t['tanggal_sewa'], "%Y-%m-%d %H:%M:%S")
        if t['tanggal_kembali']:
            t_dict['tanggal_kembali'] = datetime.strptime(t['tanggal_kembali'], "%Y-%m-%d %H:%M:%S")
        trx_list.append(t_dict)
        
    return render_template('riwayat.html', transaksi=trx_list, total_pendapatan=total_pendapatan)

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
