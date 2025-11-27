import streamlit as st
import pandas as pd
import json
import io
import time
from datetime import datetime
from github import Github

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="E-Voting", 
    page_icon="🗳️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- DATABASE ---
FILE_DATA_JSON = "database_pilketos.json"
# Ganti Link ini jika DPT berubah
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"
PLACEHOLDER_IMG = "https://via.placeholder.com/300x200.png?text=No+Foto"

# --- CSS PROFESSIONAL UI ---
st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    
    /* LOGIN CARD */
    .login-container {
        background-color: white; padding: 40px; border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center;
        max-width: 400px; margin: auto; border: 1px solid #e2e8f0;
    }
    
    /* KARTU KANDIDAT */
    .card-html {
        background-color: white; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px;
        border: 1px solid #e2e8f0; overflow: hidden;
    }
    .fixed-img {
        width: 100%; height: 120px !important; object-fit: cover;
        object-position: top center; border-bottom: 1px solid #f1f5f9;
    }
    .cand-number {
        font-size: 11px; color: #64748b; text-transform: uppercase;
        letter-spacing: 1px; margin-top: 8px; text-align: center;
    }
    .cand-name {
        font-size: 15px; font-weight: 700; color: #1e293b;
        text-align: center; padding: 0 10px 10px 10px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    
    /* TOMBOL */
    .stButton button {
        width: 100%; border-radius: 0 0 12px 12px;
        background-color: #3b82f6; color: white; border: none;
        font-weight: 600; padding: 0.5rem 1rem; margin-top: -8px;
    }
    .stButton button:hover { background-color: #2563eb; color: white; }
    
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# --- UTILS ---
def get_drive_image(url_or_id):
    if not url_or_id: return None
    file_id = url_or_id
    if "drive.google.com" in url_or_id:
        if "/d/" in url_or_id: file_id = url_or_id.split("/d/")[1].split("/")[0]
        elif "id=" in url_or_id: file_id = url_or_id.split("id=")[1].split("&")[0]
    return f"https://lh3.googleusercontent.com/d/{file_id}"

def init_github():
    try: return Github(st.secrets["github"]["token"]).get_repo(st.secrets["github"]["repo_name"])
    except: return None

def load_data():
    repo = init_github()
    if not repo: return None
    try: return json.loads(repo.get_contents(FILE_DATA_JSON).decoded_content.decode())
    except: 
        return {
            "config": {"school_name":"Sekolah","logo_drive_url":""},
            "candidates": {str(i):{"nama":f"Kandidat {i}","foto_drive_url":""} for i in range(1,7)},
            "votes":{str(i):0 for i in range(1,7)}, "used_tokens":[]
        }

def save_data(data, msg="Update"):
    repo = init_github()
    if not repo: return
    content = json.dumps(data, indent=2)
    try: repo.update_file(repo.get_contents(FILE_DATA_JSON).path, msg, content, repo.get_contents(FILE_DATA_JSON).sha)
    except: repo.create_file(FILE_DATA_JSON, "Init", content)

@st.cache_data(ttl=60)
def load_dpt():
    try: 
        df = pd.read_csv(SHEET_URL)
        df['Token'] = df['Token'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

# --- APP LOAD ---
# Load awal
if 'db' not in st.session_state: 
    st.session_state.db = load_data()

# Variable Shortcut
DB = st.session_state.db
LOGO = get_drive_image(DB['config']['logo_drive_url'])

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### Menu Navigasi")
    menu = st.radio("Pilih Mode:", ["Bilik Suara", "Panel Admin"], label_visibility="collapsed")
    st.markdown("---")
    if LOGO: st.image(LOGO, width=100)
    st.caption(f"{DB['config']['school_name']}")

# ==========================================
# HALAMAN BILIK SUARA
# ==========================================
if menu == "Bilik Suara":
    
    if 'user_token' not in st.session_state:
        # LOGIN CENTERED
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container():
                st.markdown(f"""
                <div class="login-container">
                    <h2 style='margin:0; color:#333;'>🔐 Login Pemilih</h2>
                    <p style='color:#666;'>Masukkan Token Pemilihan</p>
                </div>
                """, unsafe_allow_html=True)
                token = st.text_input("Token", placeholder="12345", label_visibility="collapsed").strip()
                
                if st.button("MASUK", type="primary"):
                    # Selalu load data terbaru saat login untuk mencegah double vote
                    fresh_db = load_data()
                    if fresh_db: st.session_state.db = fresh_db; DB = fresh_db
                    
                    if token in DB['used_tokens']:
                        st.error("⚠️ Token sudah digunakan!")
                    else:
                        dpt = load_dpt()
                        user = dpt[dpt['Token'] == token]
                        if not user.empty:
                            st.session_state.user_token = token
                            st.session_state.user_name = user.iloc[0]['Nama']
                            st.rerun()
                        else: st.error("❌ Token tidak valid")

    else:
        # VOTING GRID
        st.info(f"👤 Pemilih: **{st.session_state.user_name}**")
        
        cands = DB['candidates']
        
        # Grid 3 Kolom Responsif
        cols = st.columns(3)
        for i in range(1, 7):
            cid = str(i)
            # Menentukan kolom (0, 1, atau 2)
            col_idx = (i - 1) % 3 
            
            with cols[col_idx]:
                info = cands[cid]
                url = get_drive_image(info['foto_drive_url']) or PLACEHOLDER_IMG
                
                st.markdown(f"""
                <div class="card-html">
                    <img src="{url}" class="fixed-img">
                    <div class="cand-number">NO URUT {cid}</div>
                    <div class="cand-name">{info['nama']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"PILIH {cid}", key=f"btn_{cid}"):
                    # Logic Simpan Suara
                    cur = load_data()
                    cur['votes'][cid] += 1
                    cur['used_tokens'].append(st.session_state.user_token)
                    
                    with st.spinner("Menyimpan suara..."):
                        save_data(cur, f"Voted {cid}")
                    
                    st.session_state.db = cur
                    del st.session_state.user_token
                    st.success("Berhasil!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
            
            # Tambah spasi antar baris jika kelipatan 3
            if i % 3 == 0:
                st.write("")

# ==========================================
# HALAMAN PANEL ADMIN
# ==========================================
elif menu == "Panel Admin":
    st.title("⚙️ Dashboard Admin")
    
    with st.expander("Login Admin", expanded=True):
        pin = st.text_input("PIN", type="password")
    
    if pin == st.secrets["admin"]["pin"]:
        
        # --- LOGIKA LIVE UPDATE YANG BENAR ---
        col_live, col_status = st.columns([1, 3])
        with col_live:
            is_live = st.toggle("🔴 LIVE UPDATE")
        
        if is_live:
            # 1. Paksa Ambil Data Baru
            fresh_db = load_data()
            if fresh_db:
                st.session_state.db = fresh_db
                DB = fresh_db # Update variabel lokal AGAR UI DIBAWAHNYA PAKAI DATA BARU
            
            with col_status:
                st.caption(f"Terakhir update: {datetime.now().strftime('%H:%M:%S')}")

        # TABS
        tab1, tab2, tab3 = st.tabs(["Sekolah", "Statistik", "Reset"])
        
        # TAB 1: IDENTITAS & KANDIDAT
        with tab1:
            c1, c2 = st.columns(2)
            n_name = c1.text_input("Nama Sekolah", DB['config']['school_name'])
            n_logo = c2.text_input("Logo URL (Drive)", DB['config']['logo_drive_url'])
            if st.button("Simpan Info Sekolah"):
                DB['config']['school_name'] = n_name; DB['config']['logo_drive_url'] = n_logo
                save_data(DB, "Update Config"); st.rerun()
            
            st.divider()
            st.subheader("Edit Kandidat")
            for c, v in DB['candidates'].items():
                with st.container():
                    ic1, ic2, ic3 = st.columns([1, 2, 3])
                    prev = get_drive_image(v['foto_drive_url']) or PLACEHOLDER_IMG
                    ic1.image(prev, use_column_width=True)
                    DB['candidates'][c]['nama'] = ic2.text_input(f"Nama {c}", v['nama'], key=f"n{c}")
                    DB['candidates'][c]['foto_drive_url'] = ic3.text_input(f"Foto {c}", v['foto_drive_url'], key=f"f{c}")
            
            if st.button("Simpan Data Kandidat", type="primary"):
                save_data(DB, "Update Candidates"); st.rerun()

        # TAB 2: STATISTIK REALTIME
        with tab2:
            dpt_df = load_dpt()
            total_dpt = len(dpt_df)
            total_suara = sum(DB['votes'].values())
            pct = (total_suara/total_dpt) if total_dpt > 0 else 0
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Total DPT", total_dpt)
            k2.metric("Suara Masuk", total_suara)
            k3.metric("Partisipasi", f"{pct*100:.1f}%")
            
            st.progress(pct)
            
            # Tabel
            rows = [{"No":k, "Nama":v['nama'], "Suara":DB['votes'][k]} for k,v in DB['candidates'].items()]
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as writer:
                df.to_excel(writer, sheet_name="Rekap", index=False)
                pd.DataFrame({"Token": DB['used_tokens']}).to_excel(writer, sheet_name="Log", index=False)
            st.download_button("📥 Download Excel", buf.getvalue(), "Laporan.xlsx", "application/vnd.ms-excel")

        # TAB 3: RESET
        with tab3:
            st.error("Zona Bahaya!")
            if st.button("FACTORY RESET (HAPUS SEMUA)"):
                DB['votes'] = {str(i):0 for i in range(1,7)}
                DB['used_tokens'] = []
                save_data(DB, "RESET")
                st.success("Reset Berhasil"); st.rerun()
        
        # JADWALKAN REFRESH DI AKHIR
        if is_live:
            time.sleep(3) # Update setiap 3 detik
            st.rerun()

    elif pin:
        st.error("PIN Salah")
