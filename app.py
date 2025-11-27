import streamlit as st
import pandas as pd
import json
import os
import io
import time # Tambahan library waktu
from github import Github

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pilketos Online", page_icon="🗳️", layout="wide")

# --- DATABASE KONFIGURASI ---
FILE_DATA_JSON = "database_pilketos.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"

# --- CSS CUSTOM (TAMPILAN DIPERKECIL) ---
st.markdown("""
<style>
    /* Mengatur Ukuran Foto Kandidat LEBIH KECIL */
    .candidate-img img {
        height: 130px !important; /* Ukuran diperkecil dari 180px ke 130px */
        object-fit: contain !important;
        border-radius: 8px;
    }
    
    /* Mengatur Kartu Kandidat lebih padat */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: #f9f9f9;
        border-radius: 8px;
        padding: 8px; /* Padding diperkecil */
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Judul Nama Kandidat Kecil */
    .big-name { 
        font-size: 14px; /* Font diperkecil */
        font-weight: bold; 
        margin-top: 5px; 
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* Tombol Pilih */
    .stButton button { 
        width: 100%; 
        font-size: 12px; /* Tombol diperkecil */
        padding: 0.2rem 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNGSI GOOGLE DRIVE ---
def get_drive_image(url_or_id):
    if not url_or_id: return None
    file_id = url_or_id
    if "drive.google.com" in url_or_id:
        if "/d/" in url_or_id:
            file_id = url_or_id.split("/d/")[1].split("/")[0]
        elif "id=" in url_or_id:
            file_id = url_or_id.split("id=")[1].split("&")[0]
    return f"https://lh3.googleusercontent.com/d/{file_id}"

# --- FUNGSI GITHUB DATABASE ---
def init_github():
    try:
        token = st.secrets["github"]["token"]
        repo_name = st.secrets["github"]["repo_name"]
        g = Github(token)
        repo = g.get_repo(repo_name)
        return repo
    except Exception as e:
        st.error(f"Gagal koneksi GitHub. Cek secrets.toml! Error: {e}")
        return None

def load_data_from_github():
    repo = init_github()
    if not repo: return None
    try:
        contents = repo.get_contents(FILE_DATA_JSON)
        data = json.loads(contents.decoded_content.decode())
        return data
    except:
        default_data = {
            "config": {
                "school_name": "SMPN 4 Mendoyo",
                "logo_drive_url": "" 
            },
            "candidates": {
                str(i): {"nama": f"Calon {i}", "foto_drive_url": ""} for i in range(1, 7)
            },
            "votes": {str(i): 0 for i in range(1, 7)},
            "used_tokens": []
        }
        return default_data

def save_data_to_github(data, message="Update data"):
    repo = init_github()
    if not repo: return
    content = json.dumps(data, indent=2)
    try:
        contents = repo.get_contents(FILE_DATA_JSON)
        repo.update_file(contents.path, message, content, contents.sha)
    except:
        try:
            repo.create_file(FILE_DATA_JSON, "Init database", content)
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
    with st.spinner('Menghubungkan ke Database...'):
        st.session_state.db = load_data_from_github()

if 'page' not in st.session_state: st.session_state.page = 'home'

DB = st.session_state.db
SCHOOL_NAME = DB['config']['school_name']
LOGO_URL = get_drive_image(DB['config']['logo_drive_url'])

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    if LOGO_URL:
        st.image(LOGO_URL, width=100)
    else:
        st.header("🗳️")
        
    st.markdown(f"**{SCHOOL_NAME}**")
    st.caption("Sistem E-Voting Terintegrasi")
    st.markdown("---")
    
    menu = st.radio("Navigasi", ["Bilik Suara", "Panel Admin"])
    
    st.markdown("---")
    # Hitung total suara realtime
    total_suara = sum(DB['votes'].values())
    st.metric("Total Suara Masuk", total_suara)

# ==========================================
# HALAMAN: BILIK SUARA
# ==========================================
if menu == "Bilik Suara":
    
    if 'user_token' not in st.session_state:
        st.title("🔐 Masuk Bilik Suara")
        st.write(f"Selamat datang di pemilihan {SCHOOL_NAME}")
        
        col1, col2 = st.columns([2,1])
        with col1:
            token_input = st.text_input("Masukkan Token Pemilih", placeholder="Contoh: 12345")
            if st.button("Verifikasi Token"):
                # Reload DB untuk memastikan list token terpakai paling baru
                latest_db = load_data_from_github()
                if latest_db:
                    st.session_state.db = latest_db
                    DB = st.session_state.db

                if token_input in DB['used_tokens']:
                    st.error("Token ini sudah digunakan!")
                else:
                    df = load_dpt()
                    user = df[df['Token'] == token_input]
                    if not user.empty:
                        st.session_state.user_token = token_input
                        st.session_state.user_name = user.iloc[0]['Nama']
                        st.rerun()
                    else:
                        st.error("Token tidak ditemukan di DPT!")
    
    else:
        st.subheader(f"👋 Hai, {st.session_state.user_name}")
        st.caption("Silakan pilih salah satu kandidat.")
        
        # Grid 3 Kolom
        cols = st.columns(3)
        candidates = DB['candidates']
        
        for idx, (cid, info) in enumerate(candidates.items()):
            with cols[idx % 3]:
                with st.container():
                    img_url = get_drive_image(info['foto_drive_url'])
                    
                    # DIV Custom CSS Image
                    st.markdown('<div class="candidate-img">', unsafe_allow_html=True)
                    if img_url:
                        st.image(img_url, use_column_width=True)
                    else:
                        st.markdown(f"<div style='height:130px; background:#e0e0e0; display:flex; align-items:center; justify-content:center; border-radius:8px;'><h1>{cid}</h1></div>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='big-name' style='text-align:center;'>{info['nama']}</div>", unsafe_allow_html=True)
                    
                    if st.button(f"PILIH NO {cid}", key=f"btn_{cid}", type="primary"):
                        # Pastikan load DB terbaru sebelum simpan agar tidak menimpa suara orang lain
                        current_db = load_data_from_github()
                        if current_db:
                            current_db['votes'][cid] += 1
                            current_db['used_tokens'].append(st.session_state.user_token)
                            
                            with st.spinner("Merekam suara..."):
                                save_data_to_github(current_db, f"Vote from {st.session_state.user_name}")
                                
                            # Update Session State lokal
                            st.session_state.db = current_db
                            
                            del st.session_state.user_token
                            st.success("Terima Kasih! Suara direkam.")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Gagal koneksi database. Silakan coba lagi.")

# ==========================================
# HALAMAN: PANEL ADMIN
# ==========================================
elif menu == "Panel Admin":
    st.title("⚙️ Panel Admin")
    
    pin = st.text_input("Masukkan PIN Admin", type="password")
    if pin == st.secrets["admin"]["pin"]:
        
        tab1, tab2, tab3 = st.tabs(["Identitas & Upload", "Data Suara & Export", "Reset"])
        
        with tab1:
            st.subheader("Identitas Sekolah")
            with st.form("form_sekolah"):
                new_name = st.text_input("Nama Sekolah", value=SCHOOL_NAME)
                new_logo = st.text_input("Link Logo (Google Drive)", value=DB['config']['logo_drive_url'])
                if st.form_submit_button("Simpan Identitas"):
                    DB['config']['school_name'] = new_name
                    DB['config']['logo_drive_url'] = new_logo
                    save_data_to_github(DB, "Update Identitas Sekolah")
                    st.rerun()
            
            st.divider()
            st.subheader("Data Kandidat")
            candidates = DB['candidates']
            with st.form("form_kandidat"):
                for cid, info in candidates.items():
                    col_a, col_b = st.columns([1, 4])
                    with col_a:
                        prev_url = get_drive_image(info['foto_drive_url'])
                        if prev_url: st.image(prev_url, width=60)
                        else: st.write("No Pic")
                    with col_b:
                        st.markdown(f"**Kandidat {cid}**")
                        candidates[cid]['nama'] = st.text_input(f"Nama", value=info['nama'], key=f"n_{cid}")
                        candidates[cid]['foto_drive_url'] = st.text_input(f"Link Foto", value=info['foto_drive_url'], key=f"p_{cid}")
                    st.markdown("---")
                if st.form_submit_button("Simpan Kandidat"):
                    DB['candidates'] = candidates
                    save_data_to_github(DB, "Update Kandidat")
                    st.rerun()

        with tab2:
            st.subheader("Progress Pemilihan")
            
            # --- FITUR AUTO UPDATE ---
            col_refresh, col_status = st.columns([2, 1])
            with col_refresh:
                auto_refresh = st.toggle("🔴 Aktifkan Live Update (Realtime)", value=False)
            
            if auto_refresh:
                with col_status:
                    st.caption("Memperbarui data setiap 5 detik...")
                # Logic: Tarik data baru dari GitHub
                new_data = load_data_from_github()
                if new_data:
                    st.session_state.db = new_data
                    DB = st.session_state.db
                time.sleep(5) # Tunggu 5 detik
                st.rerun() # Refresh halaman
            # -------------------------
            
            # Hitung DPT dari Google Sheets
            df_dpt = load_dpt()
            total_dpt = len(df_dpt)
            suara_masuk = sum(DB['votes'].values())
            
            if total_dpt > 0:
                persentase = suara_masuk / total_dpt
            else:
                persentase = 0.0

            st.markdown(f"""
                <p><strong>Partisipasi: {suara_masuk} dari {total_dpt} DPT ({round(persentase*100, 1)}%)</strong></p>
                <div style="width: 100%; background-color: #ddd; border-radius: 15px; margin-bottom: 20px;">
                    <div style="width: {persentase*100}%; background-color: #28a745; height: 30px; border-radius: 15px; text-align: center; line-height: 30px; color: white;">
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.subheader("Perolehan Suara")
            data_votes = []
            for cid, count in DB['votes'].items():
                nama_kandidat = DB['candidates'][cid]['nama']
                data_votes.append({"No Urut": cid, "Nama Kandidat": nama_kandidat, "Jumlah Suara": count})
            
            df_votes = pd.DataFrame(data_votes)
            st.dataframe(df_votes, use_container_width=True)
            
            st.subheader("Download Laporan")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_votes.to_excel(writer, sheet_name='Rekap Suara', index=False)
                df_used = pd.DataFrame({"Token Terpakai": DB['used_tokens']})
                df_used.to_excel(writer, sheet_name='Log Token', index=False)
                
            buffer.seek(0)
            st.download_button(
                label="📥 Download Rekap Excel (.xlsx)",
                data=buffer,
                file_name="Rekap_Pilketos.xlsx",
                mime="application/vnd.ms-excel"
            )

        with tab3:
            st.error("Area Berbahaya")
            st.warning("Tindakan ini akan menghapus semua perolehan suara menjadi 0 dan mereset status token.")
            if st.button("RESET SEMUA SUARA & TOKEN"):
                DB['votes'] = {str(i): 0 for i in range(1, 7)}
                DB['used_tokens'] = []
                save_data_to_github(DB, "RESET DATA")
                st.success("Data berhasil direset!")
                st.rerun()

    elif pin:
        st.error("PIN Salah!")
