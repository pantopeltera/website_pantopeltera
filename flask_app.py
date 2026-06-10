from flask import Flask, render_template, request, redirect, url_for, session, flash
import os

# Import library untuk membaca file .env
from dotenv import load_dotenv

# Import library Cloudinary
import cloudinary
import cloudinary.uploader

load_dotenv()

app = Flask(__name__)
application = app

# Mengambil Secret Key murni
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "pantopelterarahasia123")

# 1. Konfigurasi Cloudinary
try:
    cloudinary.config( 
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
        api_key = os.environ.get("CLOUDINARY_API_KEY"), 
        api_secret = os.environ.get("CLOUDINARY_API_SECRET"), 
        secure = True
    )
except Exception:
    pass

# 2. Deteksi otomatis ekosistem Pyrebase (Aman dari Crash C-Extensions di Cloud)
USING_PYREBASE = False
try:
    import pyrebase
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
    # Cek apakah semua key dasar ada di .env lokal
    if config["apiKey"]:
        firebase = pyrebase.initialize_app(config)
        auth = firebase.auth()
        db = firebase.database()
        USING_PYREBASE = True
except Exception:
    USING_PYREBASE = False

@app.route('/')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def handle_auth():
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Jalur Utama Akun Monitoring PANTOPELTERA (Selalu Berhasil di Lokal & Cloud)
    if email == "pantopeltera@gmail.com" and password == "pantaupelanggaran":
        session['user'] = email
        return redirect(url_for('dashboard'))
        
    # Jalur Cadangan Firebase (Aktif di Lokal Laptop Anda)
    if USING_PYREBASE:
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user['email']
            return redirect(url_for('dashboard'))
        except Exception:
            pass

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

# --- ROUTE PROFIL (Sudah Dimodifikasi Mengunci Tampilan Utama Vercel) ---
@app.route('/profil')
def profil():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_id = "121-ITERA" 
    user_profile = None
    
    if USING_PYREBASE:
        try:
            user_profile = db.child("users").child(user_id).get().val()
        except Exception:
            pass
            
    # Mengunci data default profil agar saat di-refresh di Vercel tidak kembali ke awal
    if not user_profile:
        user_profile = {
            "nama": "PANTOPELTERA",
            "foto_url": "https://res.cloudinary.com/dsrbo4fgu/image/upload/v1/pantopeltera_profil/user_121-ITERA"
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
    foto_url_baru = None
    
    if file_foto and file_foto.filename != '':
        try:
            upload_result = cloudinary.uploader.upload(
                file_foto,
                folder = "pantopeltera_profil",
                public_id = f"user_{user_id}",
                transformation = [{'fetch_format': "auto", 'quality': "auto"}]
            )
            foto_url_baru = upload_result.get("secure_url")
            data_update["foto_url"] = foto_url_baru
        except Exception as e:
            return {"status": "error", "message": f"Cloudinary error: {str(e)}"}, 500

    if USING_PYREBASE:
        try:
            db.child("users").child(user_id).update(data_update)
        except Exception as e:
            return {"status": "error", "message": f"Database error: {str(e)}"}, 500
            
    return {
        "status": "success", 
        "nama": nama_baru, 
        "foto_url": foto_url_baru if foto_url_baru else "https://res.cloudinary.com/dsrbo4fgu/image/upload/v1/pantopeltera_profil/user_121-ITERA"
    }

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)