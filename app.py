from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'rahasia_stroller'
db_path = os.path.join(os.path.expanduser('~'), 'nota_stroller', 'stroller.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODEL ---
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_toko = db.Column(db.String(100), default="Stroller Sewa")
    alamat = db.Column(db.String(200), default="Jl. Contoh No. 1")
    no_hp = db.Column(db.String(20), default="08123456789")

class Stroller(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    harga = db.Column(db.Integer, nullable=False)

class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_penyewa = db.Column(db.String(100), nullable=False)
    no_wa = db.Column(db.String(20))
    jaminan = db.Column(db.String(100))
    stroller_nama = db.Column(db.String(100))
    lama_sewa = db.Column(db.Integer)
    total_harga = db.Column(db.Integer)
    deposit = db.Column(db.Integer, default=0)
    tanggal_sewa = db.Column(db.DateTime, default=datetime.now)
    # KOLOM BARU UNTUK DENDA
    tanggal_kembali = db.Column(db.DateTime) 
    denda = db.Column(db.Integer, default=0)

# Buat database & data awal
with app.app_context():
    db.create_all()
    if not Setting.query.first():
        db.session.add(Setting())
        db.session.add(Stroller(nama="Stroller Bayi Lipat", harga=50000))
        db.session.add(Stroller(nama="Stroller Cabin Size", harga=75000))
        db.session.commit()

# --- ROUTES ---
@app.route('/')
def index():
    return redirect(url_for('kasir'))

@app.route('/setting', methods=['GET', 'POST'])
def setting():
    s = Setting.query.first()
    if request.method == 'POST':
        s.nama_toko = request.form['nama_toko']
        s.alamat = request.form['alamat']
        s.no_hp = request.form['no_hp']
        db.session.commit()
        flash('Pengaturan berhasil disimpan!', 'success')
        return redirect(url_for('setting'))
    return render_template('setting.html', s=s)

@app.route('/stroller', methods=['GET', 'POST'])
def daftar_stroller():
    if request.method == 'POST':
        nama = request.form['nama']
        harga = int(request.form['harga'])
        db.session.add(Stroller(nama=nama, harga=harga))
        db.session.commit()
        flash('Stroller berhasil ditambahkan!', 'success')
        return redirect(url_for('daftar_stroller'))
    strollers = Stroller.query.all()
    return render_template('stroller.html', strollers=strollers)

@app.route('/hapus_stroller/<int:id>')
def hapus_stroller(id):
    s = Stroller.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('Stroller dihapus!', 'danger')
    return redirect(url_for('daftar_stroller'))

@app.route('/kasir', methods=['GET', 'POST'])
def kasir():
    strollers = Stroller.query.all()
    if request.method == 'POST':
        nama = request.form['nama']
        wa = request.form['wa']
        jaminan = request.form['jaminan']
        stroller_id = int(request.form['stroller_id'])
        lama = int(request.form['lama'])
        deposit = int(request.form.get('deposit', 0))
        
        st = Stroller.query.get(stroller_id)
        total = st.harga * lama
        tgl_sewa = datetime.now()
        # Hitung perkiraan tanggal kembali
        tgl_kembali = tgl_sewa + timedelta(days=lama)
        
        trx = Transaksi(nama_penyewa=nama, no_wa=wa, jaminan=jaminan, 
                        stroller_nama=st.nama, lama_sewa=lama, 
                        total_harga=total, deposit=deposit,
                        tanggal_sewa=tgl_sewa, tanggal_kembali=tgl_kembali)
        db.session.add(trx)
        db.session.commit()
        
        return redirect(url_for('nota', id=trx.id))
        
    return render_template('kasir.html', strollers=strollers)

@app.route('/kembalikan/<int:id>', methods=['POST'])
def kembalikan(id):
    trx = Transaksi.query.get_or_404(id)
    # Ambil input denda dari form
    denda_input = int(request.form.get('denda', 0))
    trx.denda = denda_input
    # Tandai sudah kembali dengan mengubah tanggal kembali ke hari ini
    trx.tanggal_kembali = datetime.now() 
    db.session.commit()
    flash('Barang berhasil dikembalikan!', 'success')
    return redirect(url_for('riwayat'))

@app.route('/nota/<int:id>')
def nota(id):
    trx = Transaksi.query.get_or_404(id)
    s = Setting.query.first()
    return render_template('nota.html', trx=trx, s=s)

@app.route('/riwayat')
def riwayat():
    transaksi = Transaksi.query.order_by(Transaksi.tanggal_sewa.desc()).all()
    # Hitung total pendapatan (total sewa + denda)
    total_pendapatan = sum((t.total_harga or 0) + (t.denda or 0) for t in transaksi)
    return render_template('riwayat.html', transaksi=transaksi, total_pendapatan=total_pendapatan)

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
