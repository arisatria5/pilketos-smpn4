import streamlit as st
import pandas as pd
import json
import os
import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Pilketos SMPN 4 Mendoyo",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KONSTANTA FILE LOKAL (Untuk Database Suara) ---
FILE_VOTES = "votes.json"
FILE_USED_TOKENS = "used_tokens.json"
FILE_CANDIDATES = "candidates.json"
FILE_CONFIG = "config.json"

# --- LINK DATABASE DPT (GOOGLE SHEETS) ---
# Mengubah link pubhtml menjadi csv agar mudah dibaca pandas
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"

# --- CSS CUSTOM (Agar Tampilan Cantik) ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .header-style { font-size:30px; font-weight: bold; color: #2E86C1; text-align: center; margin-bottom: 20px;}
    .success-msg { padding: 20px; background-color: #D4EDDA; color: #155724; border-radius: 10px; text-align: center; }
    .card { background-color: #f9f9f9; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); text-align: center; }
    div.stButton > button:first-child { width: 100%; background-color: #2E86C1; color: white; }
    div.stButton > button:first-child:hover { background-color: #1B4F72; border-color: #1B4F72; }
</style>
""", unsafe_allow_html=True)

# --- FUNGSI MANAJEMEN DATA ---

@st.cache_data(ttl=60) # Cache data selama 60 detik agar tidak terlalu sering request ke Google
def load_dpt_from_sheets():
    try:
        # Membaca CSV langsung dari Google Sheets
        df = pd.read_csv(SHEET_URL)
        # Pastikan kolom Token menjadi string dan bersih dari spasi
        df['Token'] = df['Token'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Gagal memuat Database DPT: {e}")
        return pd.DataFrame()

def init_files():
    # Inisialisasi file JSON lokal jika belum ada
    if not os.path.exists(FILE_VOTES):
        default_votes = {str(i): 0 for i in range(1, 7)}
        with open(FILE_VOTES, "w") as f: json.dump(default_votes, f)
    
    if not os.path.exists(FILE_USED_TOKENS):
        with open(FILE_USED_TOKENS, "w") as f: json.dump([], f)
        
    if not os.path.exists(FILE_CANDIDATES):
        # Data Default Kandidat
        candidates = {str(i): {"nama": f"Kandidat {i}", "foto": None} for i in range(1, 7)}
        with open(FILE_CANDIDATES, "w") as f: json.dump(candidates, f)
        
    if not os.path.exists(FILE_CONFIG):
        with open(FILE_CONFIG, "w") as f: json.dump({"sekolah": "SMPN 4 Mendoyo"}, f)

def get_candidates():
    with open(FILE_CANDIDATES, "r") as f: return json.load(f)

def save_candidates(data):
    with open(FILE_CANDIDATES, "w") as f: json.dump(data, f)

def get_votes():
    with open(FILE_VOTES, "r") as f: return json.load(f)

def add_vote(candidate_id):
    votes = get_votes()
    votes[str(candidate_id)] += 1
    with open(FILE_VOTES, "w") as f: json.dump(votes, f)

def get_used_tokens():
    with open(FILE_USED_TOKENS, "r") as f: return json.load(f)

def mark_token_used(token):
    used = get_used_tokens()
    used.append(str(token))
    with open(FILE_USED_TOKENS, "w") as f: json.dump(used, f)

def reset_all_data():
    if os.path.exists(FILE_VOTES): os.remove(FILE_VOTES)
    if os.path.exists(FILE_USED_TOKENS): os.remove(FILE_USED_TOKENS)
    init_files()

# --- INISIALISASI ---
init_files()
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_info' not in st.session_state: st.session_state.user_info = {}

config = json.load(open(FILE_CONFIG))
NAMA_SEKOLAH = config.get("sekolah", "SMPN 4 Mendoyo")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/color/480/indonesia.png", width=100) # Ganti URL ini dengan logo sekolah online
    st.title("E-VOTING")
    st.markdown(f"**{NAMA_SEKOLAH}**")
    st.markdown("---")
    
    # Hitung Total Suara
    votes = get_votes()
    total_suara = sum(votes.values())
    st.metric("Total Suara Masuk", total_suara)
    
    st.markdown("---")
    if st.button("Panel Admin"):
        st.session_state.page = "admin_login"
        st.rerun()
    
    if st.button("Bilik Suara (Home)"):
        st.session_state.page = "login"
        st.session_state.user_info = {}
        st.rerun()
        
    # Tampilkan Nama Pemilih Aktif di Kiri Bawah
    if st.session_state.page == 'voting' and 'nama' in st.session_state.user_info:
        st.markdown("---")
        st.info(f"👤 Pemilih Aktif:\n\n**{st.session_state.user_info['nama']}**")

# --- HALAMAN 1: LOGIN TOKEN ---
if st.session_state.page == 'login':
    st.markdown(f"<div class='header-style'>PILKETOS {NAMA_SEKOLAH}<br>PERIODE 2025</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("Verifikasi Pemilih")
            token_input = st.text_input("Masukkan Token Anda", placeholder="Contoh: 12345").strip()
            
            if st.button("Masuk Bilik Suara"):
                if token_input:
                    # 1. Cek apakah token sudah dipakai
                    used_tokens = get_used_tokens()
                    if token_input in used_tokens:
                        st.error("❌ Token ini SUDAH DIGUNAKAN untuk memilih.")
                    else:
                        # 2. Cek database Google Sheets
                        df_dpt = load_dpt_from_sheets()
                        
                        # Filter data berdasarkan token
                        user_match = df_dpt[df_dpt['Token'].astype(str) == token_input]
                        
                        if not user_match.empty:
                            nama_pemilih = user_match.iloc[0]['Nama']
                            st.session_state.user_info = {'token': token_input, 'nama': nama_pemilih}
                            st.session_state.page = 'voting'
                            st.toast(f"Selamat datang, {nama_pemilih}!", icon="👋")
                            st.rerun()
                        else:
                            st.error("❌ Token TIDAK DITEMUKAN di Database DPT.")
                else:
                    st.warning("Mohon isi token.")

# --- HALAMAN 2: BILIK SUARA (VOTING) ---
elif st.session_state.page == 'voting':
    nama = st.session_state.user_info.get('nama', 'Siswa')
    st.markdown(f"<h2 style='text-align: center;'>Halo, {nama}. Silakan Tentukan Pilihanmu!</h2>", unsafe_allow_html=True)
    st.warning("⚠️ Pilihan hanya dapat dilakukan satu kali. Pilih dengan bijak.")
    
    candidates = get_candidates()
    
    # Layout Grid (3 Kolom)
    cols = st.columns(3)
    
    for idx, (cand_id, info) in enumerate(candidates.items()):
        # Logika pembagian kolom (modulus 3)
        with cols[idx % 3]:
            with st.container(border=True):
                # Placeholder Foto (Karena online, foto harus URL atau diupload)
                # Di sini kita pakai placeholder icon jika tidak ada foto
                st.markdown(f"<h1 style='text-align: center; color: gray;'>{cand_id}</h1>", unsafe_allow_html=True)
                
                # Nama Kandidat
                st.markdown(f"<h3 style='text-align: center;'>{info['nama']}</h3>", unsafe_allow_html=True)
                
                if st.button(f"PILIH NO {cand_id}", key=f"vote_{cand_id}", use_container_width=True):
                    # Proses Voting
                    add_vote(cand_id)
                    mark_token_used(st.session_state.user_info['token'])
                    
                    st.session_state.page = 'success'
                    st.rerun()

# --- HALAMAN 3: SUKSES MEMILIH ---
elif st.session_state.page == 'success':
    st.balloons()
    st.markdown("""
        <div class='success-msg'>
            <h1>✅ SUARA BERHASIL DISIMPAN</h1>
            <p>Terima kasih telah berpartisipasi dalam Pilketos tahun ini.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("Kembali ke Halaman Login"):
            st.session_state.page = 'login'
            st.session_state.user_info = {}
            st.rerun()

# --- HALAMAN 4: ADMIN LOGIN ---
elif st.session_state.page == 'admin_login':
    st.title("Login Administrator")
    pin = st.text_input("Masukkan PIN Admin", type="password")
    if st.button("Masuk"):
        if pin == "789789":
            st.session_state.page = "admin_panel"
            st.rerun()
        else:
            st.error("PIN Salah")

# --- HALAMAN 5: ADMIN PANEL ---
elif st.session_state.page == 'admin_panel':
    st.title("🎛️ Panel Administrator")
    
    tab1, tab2, tab3 = st.tabs(["Manajemen Kandidat", "Data Suara", "Pengaturan"])
    
    with tab1:
        st.subheader("Edit Nama Kandidat")
        candidates = get_candidates()
        new_data = candidates.copy()
        
        has_changes = False
        for c_id, info in candidates.items():
            new_name = st.text_input(f"Nama Calon No {c_id}", value=info['nama'])
            if new_name != info['nama']:
                new_data[c_id]['nama'] = new_name
                has_changes = True
        
        if has_changes:
            if st.button("Simpan Perubahan Nama"):
                save_candidates(new_data)
                st.success("Data kandidat diperbarui!")
                st.rerun()

    with tab2:
        st.subheader("Rekap Perolehan Suara")
        votes = get_votes()
        df_votes = pd.DataFrame(list(votes.items()), columns=['No Urut', 'Jumlah Suara'])
        
        # Merge dengan nama kandidat
        cands = get_candidates()
        df_votes['Nama Kandidat'] = df_votes['No Urut'].apply(lambda x: cands[x]['nama'])
        
        # Reorder columns
        df_votes = df_votes[['No Urut', 'Nama Kandidat', 'Jumlah Suara']]
        
        st.dataframe(df_votes, use_container_width=True)
        
        # Download Excel
        # Streamlit butuh convert ke CSV/Excel stream
        csv = df_votes.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download CSV",
            csv,
            "rekap_suara.csv",
            "text/csv",
            key='download-csv'
        )

    with tab3:
        st.error("Zona Bahaya")
        if st.button("RESET SEMUA DATA (Suara & Token Terpakai)"):
            reset_all_data()
            st.success("Semua data telah direset!")
            st.rerun()
            
        st.info("ℹ️ Data Pemilih (DPT) diambil secara live dari Google Sheets yang Anda berikan.")
        st.write(f"Link Database: `{SHEET_URL}`")