import streamlit as st
import pandas as pd
import json
import io
import time
from github import Github

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="E-Voting", 
    page_icon="🗳️", 
    layout="wide",
    initial_sidebar_state="collapsed" # Sidebar tertutup agar fokus ke pemilihan
)

# --- DATABASE ---
FILE_DATA_JSON = "database_pilketos.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"
PLACEHOLDER_IMG = "https://via.placeholder.com/300x200.png?text=No+Foto"

# --- CSS PROFESSIONAL UI ---
st.markdown("""
<style>
    /* 1. BACKGROUND BERSIH */
    .stApp {
        background-color: #f1f5f9; /* Abu-abu kebiruan sangat muda */
    }

    /* 2. CARD LOGIN (CENTERED) */
    .login-container {
        background-color: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        text-align: center;
        max-width: 400px;
        margin: auto;
    }

    /* 3. KARTU KANDIDAT (EFEK 3D HALUS) */
    .card-html {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
        overflow: hidden; /* Agar gambar tidak keluar border */
    }
    
    .card-html:hover {
        transform: translateY(-5px); /* Efek naik saat hover */
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        border-color: #cbd5e1;
    }

    /* 4. FOTO KANDIDAT FIX */
    .fixed-img {
        width: 100%;
        height: 120px !important;  /* Tinggi Pas */
        object-fit: cover;
        object-position: top center;
        border-bottom: 1px solid #f1f5f9;
    }

    /* 5. TYPOGRAPHY */
    .cand-number {
        font-size: 12px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 5px;
        text-align: center;
    }
    .cand-name {
        font-size: 15px;
        font-weight: 700;
        color: #1e293b;
        text-align: center;
        padding: 5px 10px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* 6. TOMBOL PILIH */
    .stButton button {
        width: 100%;
        border-radius: 0 0 12px 12px; /* Radius bawah mengikuti kartu */
        background-color: #3b82f6; /* Biru Modern */
        color: white;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1rem;
        margin-top: -8px; /* Rapatkan ke atas */
    }
    .stButton button:hover {
        background-color: #2563eb;
        color: white;
    }
    
    /* 7. HILANGKAN PADDING BAWAAN BIAR RAPI */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
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

# --- APP START ---
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'page' not in st.session_state: st.session_state.page = 'home'
DB = st.session_state.db
LOGO = get_drive_image(DB['config']['logo_drive_url'])

# --- SIDEBAR (Minimalis) ---
with st.sidebar:
    st.markdown("### Menu Navigasi")
    menu = st.radio("Pilih Mode:", ["Bilik Suara", "Panel Admin"], label_visibility="collapsed")
    st.markdown("---")
    if LOGO: st.image(LOGO, width=100)
    st.caption(f"{DB['config']['school_name']}")
    st.caption("© 2025 E-Voting System")

# ==========================================
# HALAMAN BILIK SUARA (USER)
# ==========================================
if menu == "Bilik Suara":
    
    # 1. LOGIN SCREEN (CENTERED & RAPI)
    if 'user_token' not in st.session_state:
        # Gunakan Column untuk menengahkan konten login
        c_left, c_center, c_right = st.columns([1, 2, 1])
        
        with c_center:
            st.markdown("<br><br>", unsafe_allow_html=True) # Spacer
            with st.container():
                st.markdown(f"""
                <div class="login-container">
                    <h2 style='margin:0; color:#333;'>🔐 Login Pemilih</h2>
                    <p style='color:#666;'>Masukkan Token yang tertera pada kartu.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Input di Streamlit tidak bisa masuk dalam HTML div diatas secara langsung,
                # jadi kita taruh tepat di bawahnya agar visualnya menyatu.
                token = st.text_input("Token", placeholder="12345", label_visibility="collapsed").strip()
                
                if st.button("MASUK SEKARANG", type="primary"):
                    latest = load_data()
                    if latest: DB = latest
                    
                    if token in DB['used_tokens']:
                        st.error("⚠️ Token ini sudah digunakan!")
                    else:
                        dpt = load_dpt()
                        user = dpt[dpt['Token'] == token]
                        if not user.empty:
                            st.session_state.user_token = token
                            st.session_state.user_name = user.iloc[0]['Nama']
                            st.rerun()
                        else:
                            st.error("❌ Token tidak terdaftar.")

    # 2. VOTING SCREEN (GRID RAPI)
    else:
        # Header Info Pemilih
        st.info(f"👤 Pemilih Aktif: **{st.session_state.user_name}** | Silakan tentukan pilihan Anda.")
        
        cands = DB['candidates']
        
        # --- ROW 1 (1-3) ---
        cols1 = st.columns(3)
        for i in range(1, 4):
            cid = str(i)
            with cols1[i-1]:
                info = cands[cid]
                url = get_drive_image(info['foto_drive_url']) or PLACEHOLDER_IMG
                
                # TAMPILAN KARTU HTML
                st.markdown(f"""
                <div class="card-html">
                    <img src="{url}" class="fixed-img">
                    <div class="cand-number">NO URUT {cid}</div>
                    <div class="cand-name">{info['nama']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # TOMBOL STREAMLIT MENEMPEL DI BAWAH KARTU
                if st.button(f"PILIH {cid}", key=f"v{cid}"):
                    # Logic Simpan
                    cur = load_data()
                    cur['votes'][cid] += 1
                    cur['used_tokens'].append(st.session_state.user_token)
                    save_data(cur, f"Vote {cid} by {st.session_state.user_name}")
                    
                    st.session_state.db = cur
                    del st.session_state.user_token
                    
                    # Feedback Visual
                    st.success("Suara Berhasil Disimpan!")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()

        # --- ROW 2 (4-6) ---
        cols2 = st.columns(3)
        for i in range(4, 7):
            cid = str(i)
            with cols2[i-4]:
                info = cands[cid]
                url = get_drive_image(info['foto_drive_url']) or PLACEHOLDER_IMG
                
                st.markdown(f"""
                <div class="card-html">
                    <img src="{url}" class="fixed-img">
                    <div class="cand-number">NO URUT {cid}</div>
                    <div class="cand-name">{info['nama']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"PILIH {cid}", key=f"v{cid}"):
                    cur = load_data()
                    cur['votes'][cid] += 1
                    cur['used_tokens'].append(st.session_state.user_token)
                    save_data(cur, f"Vote {cid} by {st.session_state.user_name}")
                    st.session_state.db = cur
                    del st.session_state.user_token
                    st.success("Suara Berhasil Disimpan!")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()

# ==========================================
# HALAMAN PANEL ADMIN
# ==========================================
elif menu == "Panel Admin":
    st.title("⚙️ Dashboard Admin")
    
    # Login Admin Sederhana
    with st.expander("Verifikasi Akses Admin", expanded=True):
        pin = st.text_input("PIN Admin", type="password")
    
    if pin == st.secrets["admin"]["pin"]:
        
        # LIVE TOGGLE
        col_live, _ = st.columns([1, 4])
        with col_live:
            if st.toggle("🔴 Mode Live Update"):
                st.session_state.db = load_data()
                time.sleep(5)
                st.rerun()

        # TABS
        tab1, tab2, tab3 = st.tabs(["🏫 Sekolah & Kandidat", "📊 Data & Statistik", "⚠️ Reset System"])
        
        # TAB 1: EDIT DATA
        with tab1:
            with st.container():
                st.subheader("Identitas Sekolah")
                c_id1, c_id2 = st.columns([1,1])
                new_name = c_id1.text_input("Nama Sekolah", DB['config']['school_name'])
                new_logo = c_id2.text_input("Link Logo (Drive)", DB['config']['logo_drive_url'])
                if st.button("Simpan Identitas"):
                    DB['config']['school_name'] = new_name; DB['config']['logo_drive_url'] = new_logo
                    save_data(DB, "Update Config"); st.rerun()
            
            st.divider()
            
            st.subheader("Data Kandidat")
            for c, v in DB['candidates'].items():
                with st.container():
                    col_img, col_form = st.columns([1, 5])
                    with col_img:
                        prev = get_drive_image(v['foto_drive_url']) or PLACEHOLDER_IMG
                        st.image(prev, use_column_width=True)
                    with col_form:
                        c_nm, c_ft = st.columns(2)
                        DB['candidates'][c]['nama'] = c_nm.text_input(f"Nama {c}", v['nama'], key=f"n{c}")
                        DB['candidates'][c]['foto_drive_url'] = c_ft.text_input(f"Foto {c}", v['foto_drive_url'], key=f"f{c}")
            
            if st.button("Simpan Semua Kandidat", type="primary"):
                save_data(DB, "Update Candidates"); st.rerun()

        # TAB 2: STATISTIK
        with tab2:
            dpt_df = load_dpt()
            total_dpt = len(dpt_df)
            total_suara = sum(DB['votes'].values())
            
            # KPI Cards
            k1, k2, k3 = st.columns(3)
            k1.metric("Total DPT", total_dpt)
            k2.metric("Suara Masuk", total_suara)
            pct = (total_suara/total_dpt*100) if total_dpt else 0
            k3.metric("Partisipasi", f"{pct:.1f}%")
            
            st.progress(pct/100)
            
            # Tabel
            data_tabel = [{"No": k, "Nama": v['nama'], "Perolehan": DB['votes'][k]} for k, v in DB['candidates'].items()]
            st.dataframe(pd.DataFrame(data_tabel), use_container_width=True, hide_index=True)
            
            # Export
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as writer:
                pd.DataFrame(data_tabel).to_excel(writer, sheet_name="Rekap", index=False)
                pd.DataFrame({"Token Terpakai": DB['used_tokens']}).to_excel(writer, sheet_name="Log", index=False)
            st.download_button("📥 Download Laporan Excel", buf.getvalue(), "Laporan_Pilketos.xlsx", "application/vnd.ms-excel")

        # TAB 3: RESET
        with tab3:
            st.error("Zona Bahaya: Tindakan ini tidak dapat dibatalkan.")
            if st.button("RESET SEMUA DATA (Mulai dari Nol)", type="primary"):
                DB['votes'] = {str(i): 0 for i in range(1, 7)}
                DB['used_tokens'] = []
                save_data(DB, "FACTORY RESET")
                st.success("Sistem Berhasil Direset!")
                st.rerun()

    elif pin:
        st.error("PIN Administrator salah.")
