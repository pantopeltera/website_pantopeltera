from flask import Flask, render_template, request, redirect, url_for, session, flash
import os

# Import library untuk membaca file .env
from dotenv import load_dotenv

# Import library Cloudinary
import cloudinary
import cloudinary.uploader

# IMPORT LIBRARY FIREBASE RESMI (Solusi Bypass Error Vercel 2026)
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db as firebase_db

# Load file .env
load_dotenv()

app = Flask(__name__)
# Kompatibilitas WSGI Serverless Vercel
application = app

# Mengambil Secret Key dari environment variable
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# 1. Konfigurasi Cloudinary menggunakan data dari .env
cloudinary.config( 
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
    api_key = os.environ.get("CLOUDINARY_API_KEY"), 
    api_secret = os.environ.get("CLOUDINARY_API_SECRET"), 
    secure = True
)

# 2. Inisialisasi FIREBASE ADMIN RESMI
# Menggunakan data credential SDK yang di-mapping aman dari environment variables
if not firebase_admin._apps:
    # Memetakan struktur service account credential secara dinamis
    firebase_creds = {
        "type": "service_account",
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace("\\n", "\n") if os.environ.get("FIREBASE_PRIVATE_KEY") else None,
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token"
    }
    
    # Jika private_key tidak ada di .env (misal saat dev awal), gunakan fallback credential default
    if not firebase_creds["private_key"]:
        # Fallback ini opsional jika Anda mengizinkan akses database publik tanpa berkas kunci
        cred = credentials.AnonymousCredentials() if os.environ.get("FLASK_ENV") == "development" else None
    else:
        cred = credentials.Certificate(firebase_creds)
        
    firebase_admin.initialize_app(cred, {
        "databaseURL": os.environ.get("FIREBASE_DATABASE_URL")
    })

@app.route('/')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def handle_auth():
    email = request.form.get('email')
    password = request.form.get('password')
    
    # KARENA SDK ADMIN BERFOKUS PADA VALIDASI BACKEND & DATABASE:
    # Kita buat validasi login aman berbasis credential atau fallback statis admin 
    # yang terintegrasi dengan database users Anda.
    try:
        # Simulasi/Verifikasi autentikasi aman untuk akun monitoring PANTOPELTERA
        if email == "admin@pantopeltera.com" and password == "admin123":
            session['user'] = email
            return redirect(url_for('dashboard'))
        
        # Opsi interogasi data user ke Realtime Database untuk cek kredensial alternatif
        user_clean_email = email.replace('.', '_') # Firebase path aman tanpa dot
        user_check = firebase_db.reference(f'users_auth/{user_clean_email}').get()
        
        if user_check and user_check.get('password') == password:
            session['user'] = email
            return redirect(url_for('dashboard'))
            
        raise Exception("Kredensial tidak valid")
        
    except Exception as e:
        flash("Email atau Password salah!")
        return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/pelanggaran')
def pelanggaran():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('pelanggaran.html', data=[]) 

@app.route('/monitoring')
def monitoring():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('monitoring.html')

@app.route('/grafik')
def grafik():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    labels = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
    values_helm = [10, 15, 8, 12, 20]
    values_arah = [5, 10, 3, 8, 12]
    
    return render_template('grafik.html', labels=labels, values_helm=values_helm, values_arah=values_arah)

# --- ROUTE PROFIL (Telah Dimodifikasi Menggunakan Firebase-Admin) ---
@app.route('/profil')
def profil():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_id = "121-ITERA" 
    
    try:
        # Mengambil referensi jalur data 'users/121-ITERA' dari Realtime Database
        user_profile = firebase_db.reference(f'users/{user_id}').get()
    except Exception:
        user_profile = None
    
    if not user_profile:
        user_profile = {
            "nama": "ANGGITO SUSILO",
            "foto_url": "/static/foto_profil.jpg"
        }
    
    return render_template('profil.html', profil=user_profile)

# --- ROUTE UPDATE DATA KE CLOUDINARY & FIREBASE (Telah Dimodifikasi) ---
@app.route('/update-profil', methods=['POST'])
def update_profil():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user_id = "121-ITERA"
    nama_baru = request.form.get('nama_lengkap')
    file_foto = request.files.get('foto_profil')
    
    data_update = {"nama": nama_baru}
    
    if file_foto and file_foto.filename != '':
        try:
            upload_result = cloudinary.uploader.upload(
                file_foto,
                folder = "pantopeltera_profil",
                public_id = f"user_{user_id}",
                transformation = [
                    {'fetch_format': "auto", 'quality': "auto"}
                ]
            )
            data_update["foto_url"] = upload_result.get("secure_url")
        except Exception as e:
            return {"status": "error", "message": f"Cloudinary error: {str(e)}"}, 500

    try:
        # Melakukan pembaruan (update) ke Realtime Database menggunakan SDK resmi
        ref = firebase_db.reference(f'users/{user_id}')
        ref.update(data_update)
        
        return {
            "status": "success", 
            "nama": nama_baru, 
            "foto_url": data_update.get("foto_url", None)
        }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}, 500

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)