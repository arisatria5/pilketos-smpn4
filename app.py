import streamlit as st
import pandas as pd
import json
import os
from github import Github # Library untuk konek ke GitHub

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pilketos Online", page_icon="🗳️", layout="wide")

# --- DATABASE KONFIGURASI ---
# File ini akan dibuat/dibaca langsung dari GitHub
FILE_DATA_JSON = "database_pilketos.json"

# Link DPT (Read Only)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"

# --- FUNGSI GOOGLE DRIVE ---
def get_drive_image(url_or_id):
    """Mengubah Link Sharing Google Drive menjadi Direct Image URL"""
    if not url_or_id: return None
    
    # 1. Ambil ID File dari URL panjang
    file_id = url_or_id
    if "drive.google.com" in url_or_id:
        if "/d/" in url_or_id:
            file_id = url_or_id.split("/d/")[1].split("/")[0]
        elif "id=" in url_or_id:
            file_id = url_or_id.split("id=")[1].split("&")[0]
            
    # 2. Gunakan Endpoint lh3.googleusercontent.com (Lebih stabil untuk image hosting)
    return f"https://lh3.googleusercontent.com/d/{file_id}"

# --- FUNGSI GITHUB DATABASE ---
def init_github():
    """Koneksi ke GitHub"""
    try:
        token = st.secrets["github"]["token"]
        repo_name = st.secrets["github"]["repo_name"]
        g = Github(token)
        repo = g.get_repo(repo_name)
        return repo
    except Exception as e:
        st.error(f"Gagal koneksi GitHub: {e}. Cek secrets.toml!")
        return None

def load_data_from_github():
    """Membaca Database JSON dari GitHub"""
    repo = init_github()
    if not repo: return None
    
    try:
        contents = repo.get_contents(FILE_DATA_JSON)
        data = json.loads(contents.decoded_content.decode())
        return data
    except:
        # Jika file belum ada, buat struktur default
        default_data = {
            "config": {
                "school_name": "SMPN 4 Mendoyo",
                "logo_drive_url": "" # Link Logo di Drive
            },
            "candidates": {
                str(i): {"nama": f"Calon {i}", "foto_drive_url": ""} for i in range(1, 7)
            },
            "votes": {str(i): 0 for i in range(1, 7)},
            "used_tokens": []
        }
        return default_data

def save_data_to_github(data, message="Update data"):
    """Menyimpan/Update Database JSON ke GitHub"""
    repo = init_github()
    if not repo: return
    
    content = json.dumps(data, indent=2)
    try:
        # Coba update file jika ada
        contents = repo.get_contents(FILE_DATA_JSON)
        repo.update_file(contents.path, message, content, contents.sha)
        st.success("✅ Data berhasil disimpan ke GitHub!")
    except:
        # Jika belum ada, buat file baru
        try:
            repo.create_file(FILE_DATA_JSON, "Init database", content)
            st.success("✅ Database baru dibuat di GitHub!")
        except Exception as e:
            st.error(f"Gagal menyimpan: {e}")

# --- FUNGSI DPT (GOOGLE SHEETS) ---
@st.cache_data(ttl=60)
def load_dpt():
    try:
        df = pd.read_csv(SHEET_URL)
        df['Token'] = df['Token'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

# --- INITIAL LOAD ---
if 'db' not in st.session_state:
    with st.spinner('Menghubungkan ke Database GitHub...'):
        st.session_state.db = load_data_from_github()

if 'page' not in st.session_state: st.session_state.page = 'home'

# Shortcut Variabel Data
DB = st.session_state.db
SCHOOL_NAME = DB['config']['school_name']
LOGO_URL = get_drive_image(DB['config']['logo_drive_url'])

# --- CSS ---
st.markdown("""
<style>
    .card { background: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 10px;}
    .big-name { font-size: 20px; font-weight: bold; margin-top: 10px; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    if LOGO_URL:
        st.image(LOGO_URL, width=120)
    else:
        st.header("🗳️")
        
    st.markdown(f"### {SCHOOL_NAME}")
    st.caption("Sistem E-Voting Terintegrasi")
    st.markdown("---")
    
    menu = st.radio("Navigasi", ["Bilik Suara", "Panel Admin"])
    
    st.markdown("---")
    # Tampilkan Total Suara (Realtime dari session)
    total_suara = sum(DB['votes'].values())
    st.metric("Total Suara Masuk", total_suara)

# ==========================================
# HALAMAN: BILIK SUARA
# ==========================================
if menu == "Bilik Suara":
    
    # State Login Token
    if 'user_token' not in st.session_state:
        st.title("🔐 Masuk Bilik Suara")
        st.write(f"Selamat datang di pemilihan {SCHOOL_NAME}")
        
        token_input = st.text_input("Masukkan Token Pemilih", placeholder="Contoh: 12345")
        
        if st.button("Verifikasi Token"):
            # Cek apakah token sudah dipakai (dari GitHub DB)
            if token_input in DB['used_tokens']:
                st.error("Token ini sudah digunakan!")
            else:
                # Cek DPT (Google Sheets)
                df = load_dpt()
                user = df[df['Token'] == token_input]
                
                if not user.empty:
                    st.session_state.user_token = token_input
                    st.session_state.user_name = user.iloc[0]['Nama']
                    st.rerun()
                else:
                    st.error("Token tidak ditemukan di DPT!")
    
    else:
        # State Sudah Login -> Tampilkan Kandidat
        st.subheader(f"👋 Hai, {st.session_state.user_name}")
        st.info("Silakan pilih salah satu kandidat. Klik tombol 'PILIH' di bawah foto.")
        
        cols = st.columns(3)
        candidates = DB['candidates']
        
        for idx, (cid, info) in enumerate(candidates.items()):
            with cols[idx % 3]:
                with st.container(border=True):
                    # Tampilkan Foto dari Drive
                    img_url = get_drive_image(info['foto_drive_url'])
                    if img_url:
                        st.image(img_url, use_column_width=True)
                    else:
                        st.markdown(f"<div style='height:200px; background:#ddd; display:flex; align-items:center; justify-content:center;'><h1>{cid}</h1></div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='big-name'>{info['nama']}</div>", unsafe_allow_html=True)
                    st.write("")
                    
                    if st.button(f"PILIH NO {cid}", key=f"btn_{cid}", type="primary"):
                        # UPDATE DATA LOCAL
                        DB['votes'][cid] += 1
                        DB['used_tokens'].append(st.session_state.user_token)
                        
                        # SIMPAN KE GITHUB
                        with st.spinner("Merekam suara ke cloud..."):
                            save_data_to_github(DB, f"Vote from {st.session_state.user_name}")
                        
                        # Logout
                        del st.session_state.user_token
                        st.success("Suara berhasil direkam! Terima kasih.")
                        st.balloons()
                        st.rerun()

# ==========================================
# HALAMAN: PANEL ADMIN
# ==========================================
elif menu == "Panel Admin":
    st.title("⚙️ Pengaturan Sekolah & Kandidat")
    
    pin = st.text_input("Masukkan PIN Admin", type="password")
    if pin == st.secrets["admin"]["pin"]:
        
        tab1, tab2, tab3 = st.tabs(["Identitas Sekolah", "Upload Kandidat", "Data & Reset"])
        
        # TAB 1: Identitas
        with tab1:
            st.subheader("Ubah Identitas")
            with st.form("form_sekolah"):
                new_name = st.text_input("Nama Sekolah", value=SCHOOL_NAME)
                new_logo = st.text_input("Link Logo (Google Drive)", value=DB['config']['logo_drive_url'], placeholder="Tempel Link Google Drive di sini...")
                st.caption("Upload logo ke Folder Drive Anda, klik kanan 'Share' > 'Copy Link', lalu tempel di sini.")
                
                if st.form_submit_button("Simpan Identitas"):
                    DB['config']['school_name'] = new_name
                    DB['config']['logo_drive_url'] = new_logo
                    save_data_to_github(DB, "Update Identitas Sekolah")
                    st.rerun()

        # TAB 2: Kandidat
        with tab2:
            st.subheader("Edit Data Kandidat")
            st.info(f"Untuk Foto: Upload foto ke [Google Drive Folder]({ 'https://drive.google.com/drive/folders/13xYgtj5ZtX-afE8crWa1OQRn1KyXwAfR?usp=sharing' }), Copy Link-nya, dan tempel di bawah.")
            
            candidates = DB['candidates']
            with st.form("form_kandidat"):
                for cid, info in candidates.items():
                    st.markdown(f"**Kandidat No {cid}**")
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        # Preview Kecil
                        prev_url = get_drive_image(info['foto_drive_url'])
                        if prev_url: st.image(prev_url, width=100)
                        else: st.write("No Image")
                    with col_b:
                        new_cname = st.text_input(f"Nama", value=info['nama'], key=f"n_{cid}")
                        new_cphoto = st.text_input(f"Link Foto GDrive", value=info['foto_drive_url'], key=f"p_{cid}")
                        
                        # Update Local Var
                        candidates[cid]['nama'] = new_cname
                        candidates[cid]['foto_drive_url'] = new_cphoto
                    st.divider()
                
                if st.form_submit_button("Simpan Semua Kandidat"):
                    DB['candidates'] = candidates
                    save_data_to_github(DB, "Update Kandidat")
                    st.rerun()

        # TAB 3: Data Suara & Reset
        with tab3:
            st.subheader("Rekap Suara")
            st.json(DB['votes'])
            
            st.divider()
            st.error("Area Berbahaya")
            if st.button("RESET SEMUA SUARA & TOKEN"):
                DB['votes'] = {str(i): 0 for i in range(1, 7)}
                DB['used_tokens'] = []
                save_data_to_github(DB, "RESET DATA")
                st.success("Data berhasil direset!")
                st.rerun()

    elif pin:
        st.error("PIN Salah!")

