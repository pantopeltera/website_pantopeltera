import setuptools
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyrebase
import os

# Import library untuk membaca file .env
from dotenv import load_dotenv

# Import library Cloudinary
import cloudinary
import cloudinary.uploader

# Load file .env jika ada (di lokal otomatis terbaca, di Vercel akan membaca env system)
load_dotenv()

app = Flask(__name__)
# Tambahkan baris ini untuk kompatibilitas Vercel/WSGI
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

# 2. Konfigurasi Firebase menggunakan data dari .env
config = {
    "apiKey": os.environ.get("FIREBASE_API_KEY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.environ.get("FIREBASE_APP_ID"),
    "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": os.environ.get("FIREBASE_DATABASE_URL")
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database() # Inisialisasi Realtime Database

@app.route('/')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def handle_auth():
    email = request.form.get('email')
    password = request.form.get('password')
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        session['user'] = user['email']
        return redirect(url_for('dashboard'))
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

# --- ROUTE PROFIL ---
@app.route('/profil')
def profil():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_id = "121-ITERA" 
    user_profile = db.child("users").child(user_id).get().val()
    
    if not user_profile:
        user_profile = {
            "nama": "ANGGITO SUSILO",
            "foto_url": "/static/foto_profil.jpg"
        }
    
    return render_template('profil.html', profil=user_profile)

# --- ROUTE UPDATE DATA KE CLOUDINARY & FIREBASE ---
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
        #  KODE BARU (Gunakan ini):
        except Exception as e:
            # Mengembalikan response JSON jika Cloudinary gagal
            return {"status": "error", "message": f"Cloudinary error: {str(e)}"}, 500

    try:
        db.child("users").child(user_id).update(data_update)
        # Mengembalikan response JSON sukses agar bisa dibaca oleh JavaScript fetch()
        return {
            "status": "success", 
            "nama": nama_baru, 
            "foto_url": data_update.get("foto_url", None)
        }
    except Exception as e:
        # Mengembalikan response JSON jika Firebase gagal
        return {"status": "error", "message": f"Database error: {str(e)}"}, 500

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)