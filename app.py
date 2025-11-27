import streamlit as st
import pandas as pd
import json
import os
import io
import time
from github import Github

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pilketos Online", page_icon="🗳️", layout="wide")

# --- DATABASE KONFIGURASI ---
FILE_DATA_JSON = "database_pilketos.json"
# Link Google Sheets DPT
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"

# --- CSS CUSTOM (ULTRA COMPACT) ---
st.markdown("""
<style>
    /* 1. MENGURANGI PADDING HALAMAN UTAMA */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    /* 2. FOTO KANDIDAT SANGAT KECIL */
    .candidate-img img {
        height: 70px !important; /* Tinggi foto hanya 70px */
        object-fit: contain !important;
        border-radius: 5px;
        margin-bottom: 2px;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* 3. KARTU KANDIDAT PADAT */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: #f9f9f9;
        border-radius: 8px;
        padding: 5px !important; /* Padding sangat tipis */
        gap: 2px !important; /* Jarak antar elemen dalam kartu dirapatkan */
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* 4. JUDUL NAMA */
    .big-name { 
        font-size: 12px; 
        font-weight: bold; 
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: center;
        margin: 0px !important;
    }
    
    /* 5. TOMBOL PILIH TIPIS */
    .stButton button { 
        width: 100%; 
        font-size: 11px !important;
        padding: 0px !important;
        min-height: 25px !important; /* Memaksa tombol jadi pendek */
        height: 25px !important;
    }
    
    /* 6. MENGHILANGKAN GAP BAWAAN STREAMLIT */
    div[data-testid="column"] {
        gap: 0rem !important;
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

# --- FUNGSI DPT ---
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
                latest_db = load_data_from_github()
                if latest_db:
                    st.session_state.db = latest_db
                    DB = st.session_state.db

                if token_input in DB['used_tokens']:
                    st.error("Token ini SUDAH DIGUNAKAN!")
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
        # Header lebih kecil
        st.markdown(f"**Halo, {st.session_state.user_name}** | Silakan pilih kandidat:", unsafe_allow_html=True)
        
        cols = st.columns(3)
        candidates = DB['candidates']
        
        for idx, (cid, info) in enumerate(candidates.items()):
            with cols[idx % 3]:
                with st.container():
                    img_url = get_drive_image(info['foto_drive_url'])
                    
                    st.markdown('<div class="candidate-img">', unsafe_allow_html=True)
                    if img_url:
                        st.image(img_url, use_column_width=True)
                    else:
                        # Placeholder kecil
                        st.markdown(f"<div style='height:70px; background:#e0e0e0; display:flex; align-items:center; justify-content:center; border-radius:5px;'><h4>{cid}</h4></div>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='big-name'>{info['nama']}</div>", unsafe_allow_html=True)
                    
                    if st.button(f"PILIH NO {cid}", key=f"btn_{cid}", type="primary"):
                        current_db = load_data_from_github()
                        if current_db:
                            current_db['votes'][cid] += 1
                            current_db['used_tokens'].append(st.session_state.user_token)
                            
                            with st.spinner("Merekam..."):
                                save_data_to_github(current_db, f"Vote from {st.session_state.user_name}")
                                
                            st.session_state.db = current_db
                            del st.session_state.user_token
                            st.success("Terekam!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Gagal koneksi.")

# ==========================================
# HALAMAN: PANEL ADMIN
# ==========================================
elif menu == "Panel Admin":
    st.title("⚙️ Panel Admin")
    
    pin = st.text_input("Masukkan PIN Admin", type="password")
    if pin == st.secrets["admin"]["pin"]:
        
        col_title, col_toggle = st.columns([3, 1])
        with col_toggle:
            auto_refresh = st.toggle("🔴 LIVE UPDATE")
        
        if auto_refresh:
            fresh_db = load_data_from_github()
            if fresh_db:
                st.session_state.db = fresh_db
                DB = st.session_state.db
        
        tab1, tab2, tab3 = st.tabs(["Identitas", "Data", "Reset"])
        
        with tab1:
            st.subheader("Identitas")
            with st.form("form_sekolah"):
                new_name = st.text_input("Nama Sekolah", value=SCHOOL_NAME)
                new_logo = st.text_input("Link Logo (Google Drive)", value=DB['config']['logo_drive_url'])
                if st.form_submit_button("Simpan"):
                    DB['config']['school_name'] = new_name
                    DB['config']['logo_drive_url'] = new_logo
                    save_data_to_github(DB, "Update Identitas Sekolah")
                    st.rerun()
            
            st.divider()
            st.subheader("Kandidat")
            candidates = DB['candidates']
            with st.form("form_kandidat"):
                for cid, info in candidates.items():
                    col_a, col_b = st.columns([1, 4])
                    with col_a:
                        prev_url = get_drive_image(info['foto_drive_url'])
                        if prev_url: st.image(prev_url, width=50)
                        else: st.write("-")
                    with col_b:
                        candidates[cid]['nama'] = st.text_input(f"Nama {cid}", value=info['nama'], key=f"n_{cid}")
                        candidates[cid]['foto_drive_url'] = st.text_input(f"Foto {cid}", value=info['foto_drive_url'], key=f"p_{cid}")
                    st.markdown("---")
                if st.form_submit_button("Simpan Kandidat"):
                    DB['candidates'] = candidates
                    save_data_to_github(DB, "Update Kandidat")
                    st.rerun()

        with tab2:
            st.subheader("Progress")
            df_dpt = load_dpt()
            total_dpt = len(df_dpt)
            suara_masuk = sum(DB['votes'].values())
            persentase = (suara_masuk / total_dpt) if total_dpt > 0 else 0.0

            st.markdown(f"""
                <div style="width: 100%; background-color: #e9ecef; border-radius: 10px; margin-bottom: 10px;">
                    <div style="width: {persentase*100}%; background-color: #28a745; height: 25px; border-radius: 10px; text-align: center; color: white; line-height: 25px; font-weight: bold; font-size: 12px;">
                        {round(persentase*100, 1)}% ({suara_masuk}/{total_dpt})
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            data_votes = []
            for cid, count in DB['votes'].items():
                data_votes.append({"No": cid, "Nama": DB['candidates'][cid]['nama'], "Suara": count})
            st.dataframe(pd.DataFrame(data_votes), use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                pd.DataFrame(data_votes).to_excel(writer, sheet_name='Rekap', index=False)
                pd.DataFrame({"Token": DB['used_tokens']}).to_excel(writer, sheet_name='Log', index=False)
            buffer.seek(0)
            
            st.download_button("📥 Download Excel", buffer, "Rekap.xlsx")

        with tab3:
            st.warning("Hapus semua data suara?")
            if st.button("RESET DATA"):
                DB['votes'] = {str(i): 0 for i in range(1, 7)}
                DB['used_tokens'] = []
                save_data_to_github(DB, "RESET DATA")
                st.success("Reset Berhasil!")
                st.rerun()
        
        if auto_refresh:
            time.sleep(5)
            st.rerun()

    elif pin:
        st.error("PIN Salah!")
