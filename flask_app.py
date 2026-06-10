from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from datetime import datetime

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
    
    if email == "pantopeltera@gmail.com" and password == "pantaupelanggaran":
        session['user'] = email
        return redirect(url_for('dashboard'))
        
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

# --- ROUTE RENDERING HALAMAN GRAFIK ---
@app.route('/grafik')
def grafik():
    if 'user' not in session:
        return redirect(url_for('login'))
    # Halaman html sekarang akan langsung dimuat, data akan ditarik oleh JavaScript Fetch secara real-time
    return render_template('grafik.html')

# --- ROUTE API DATA REAL-TIME UNTUK CHART.JS ---
@app.route('/api/statistik-pelanggaran')
def api_statistik_pelanggaran():
    labels = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
    
    # Inisialisasi array hitungan dari angka 0
    values_helm = [0, 0, 0, 0, 0]
    values_arah = [0, 0, 0, 0, 0]
    
    # Pemetaan nama hari ke indeks array data grafik
    hari_mapping = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4
    }

    # 1. KONDISI LOKAL: Menghitung data pelanggaran real-time dari Firebase
    if USING_PYREBASE:
        try:
            # Mengambil data dari node "all_pelanggaran" (sesuaikan dengan nama node Firebase Anda)
            semua_pelanggaran = db.child("all_pelanggaran").get().val()
            
            if semua_pelanggaran:
                for key, item in semua_pelanggaran.items():
                    jenis = item.get("jenis_pelanggaran")  # Contoh data: "Tidak Menggunakan Helm" / "Melawan Arah"
                    waktu_str = item.get("waktu")          # Contoh data: "2026-06-11 14:20:00"
                    
                    try:
                        # Parsing string waktu untuk mendapatkan nama hari
                        tanggal_obj = datetime.strptime(waktu_str, "%Y-%m-%d %H:%M:%S")
                        nama_hari = tanggal_obj.strftime("%A")
                        
                        if nama_hari in hari_mapping:
                            indeks = hari_mapping[nama_hari]
                            
                            if jenis == "Tidak Menggunakan Helm":
                                values_helm[indeks] += 1
                            elif jenis == "Melawan Arah":
                                values_arah[indeks] += 1
                    except Exception:
                        pass
        except Exception as e:
            print("Gagal mengambil statistik database:", str(e))
            
    # 2. KONDISI CLOUD VERCEL: Mengosongkan data grafik default (0 Semua) agar tidak bergerak acak
    else:
        values_helm = [0, 0, 0, 0, 0]
        values_arah = [0, 0, 0, 0, 0]

    return jsonify({
        "labels": labels,
        "values_helm": values_helm,
        "values_arah": values_arah
    })

# --- ROUTE PROFIL ---
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
            
    if not user_profile:
        user_profile = {
            "nama": session.get('profile_name', "PANTOPELTERA"),
            "foto_url": session.get('profile_foto', "https://res.cloudinary.com/dsrbo4fgu/image/upload/v1/pantopeltera_profil/user_121-ITERA")
        }
    
    return render_template('profil.html', profil=user_profile)

# --- ROUTE UPDATE DATA PROFIL ---
@app.route('/update-profil', methods=['POST'])
def update_profil():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user_id = "121-ITERA"
    nama_baru = request.form.get('nama_lengkap')
    file_foto = request.files.get('foto_profil')
    
    data_update = {"nama": nama_baru}
    foto_url_sekarang = session.get('profile_foto', "https://res.cloudinary.com/dsrbo4fgu/image/upload/v1/pantopeltera_profil/user_121-ITERA")
    
    if file_foto and file_foto.filename != '':
        try:
            upload_result = cloudinary.uploader.upload(
                file_foto,
                folder = "pantopeltera_profil",
                public_id = f"user_{user_id}",
                transformation = [{'fetch_format': "auto", 'quality': "auto"}]
            )
            foto_url_sekarang = upload_result.get("secure_url")
            data_update["foto_url"] = foto_url_sekarang
        except Exception as e:
            return {"status": "error", "message": f"Cloudinary error: {str(e)}"}, 500

    session['profile_name'] = nama_baru
    session['profile_foto'] = foto_url_sekarang

    if USING_PYREBASE:
        try:
            db.child("users").child(user_id).update(data_update)
        except Exception as e:
            return {"status": "error", "message": f"Database error: {str(e)}"}, 500
            
    return {
        "status": "success", 
        "nama": nama_baru, 
        "foto_url": foto_url_sekarang
    }

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('profile_name', None)
    session.pop('profile_foto', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)