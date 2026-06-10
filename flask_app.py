from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import requests  # Digunakan untuk menembak REST API Firebase di Vercel cloud
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

# --- ROUTE RENDERING HALAMAN LOG PELANGGARAN ---
@app.route('/pelanggaran')
def pelanggaran():
    if 'user' not in session:
        return redirect(url_for('login'))
    # Halaman html sekarang akan langsung dimuat, data list akan ditarik oleh JavaScript Fetch secara real-time
    return render_template('pelanggaran.html', data=[]) 

# --- ROUTE API DATA DAFTAR DETEKSI REAL-TIME UNTUK PELANGGARAN.HTML ---
@app.route('/api/list-pelanggaran')
def api_list_pelanggaran():
    daftar_pelanggaran = []
    semua_pelanggaran = None

    # 1. KONDISI LOKAL LAPTOP: Ambil data dari library Pyrebase
    if USING_PYREBASE:
        try:
            semua_pelanggaran = db.child("all_pelanggaran").get().val()
        except Exception as e:
            print("Gagal mengambil data list lokal:", str(e))
            
    # 2. KONDISI CLOUD VERCEL: Menggunakan Firebase REST API via requests
    else:
        try:
            db_url = os.environ.get("FIREBASE_DATABASE_URL")
            if db_url:
                if db_url.endswith('/'):
                    db_url = db_url[:-1]
                response = requests.get(f"{db_url}/all_pelanggaran.json", timeout=5)
                if response.status_code == 200:
                    semua_pelanggaran = response.json()
        except Exception as e:
            print("Gagal mengambil data list REST API Vercel:", str(e))

    # 3. PROSES STRUKTUR DATA
    if semua_pelanggaran:
        for key, item in semua_pelanggaran.items():
            if not item:
                continue
            daftar_pelanggaran.append({
                "jenis": item.get("jenis_pelanggaran", "Pelanggaran"),
                "waktu": item.get("waktu", "Waktu tidak diketahui"),
                "img": item.get("foto_url", "https://res.cloudinary.com/dsrbo4fgu/image/upload/v1/pantopeltera_profil/user_121-ITERA")
            })
        # Balik urutan list agar log terbaru berada di paling atas panel kiri
        daftar_pelanggaran.reverse()

    return jsonify(daftar_pelanggaran)

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
    return render_template('grafik.html')

# --- ROUTE API DATA REAL-TIME UNTUK CHART.JS ---
@app.route('/api/statistik-pelanggaran')
def api_statistik_pelanggaran():
    labels = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
    values_helm = [0, 0, 0, 0, 0]
    values_arah = [0, 0, 0, 0, 0]
    
    hari_mapping = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4
    }

    semua_pelanggaran = None

    if USING_PYREBASE:
        try:
            semua_pelanggaran = db.child("all_pelanggaran").get().val()
        except Exception as e:
            print("Gagal mengambil statistik database lokal (Pyrebase):", str(e))
    else:
        try:
            db_url = os.environ.get("FIREBASE_DATABASE_URL")
            if db_url:
                if db_url.endswith('/'):
                    db_url = db_url[:-1]
                response = requests.get(f"{db_url}/all_pelanggaran.json", timeout=5)
                if response.status_code == 200:
                    semua_pelanggaran = response.json()
        except Exception as e:
            print("Gagal mengambil data dari REST API Firebase di Vercel:", str(e))

    if semua_pelanggaran:
        for key, item in semua_pelanggaran.items():
            if not item:
                continue
            jenis = item.get("jenis_pelanggaran")
            waktu_str = item.get("waktu")
            
            try:
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