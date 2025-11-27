import streamlit as st
import pandas as pd
import json
import io
import time
from github import Github

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pilketos", page_icon="🗳️", layout="wide")

# --- DATABASE ---
FILE_DATA_JSON = "database_pilketos.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"

# --- PLACEHOLDER IMAGE ---
PLACEHOLDER_IMG = "https://via.placeholder.com/300x200.png?text=No+Image"

# --- CSS KHUSUS (HARDCODE SIZE) ---
st.markdown("""
<style>
    /* 1. Paksa Margin Halaman Sempit */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* 2. Style Kartu Kandidat HTML */
    .card-html {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        overflow: hidden;
        margin-bottom: 5px;
    }
    
    /* 3. FOTO DIKUNCI MATI UKURANNYA */
    .fixed-img {
        width: 100%;
        height: 120px !important;  /* TINGGI FIX 120PX */
        object-fit: cover;       /* Agar foto tidak gepeng */
        object-position: top;    /* Fokus ke bagian atas (wajah) */
        border-bottom: 1px solid #eee;
    }
    
    /* 4. Nama Kandidat */
    .cand-name {
        padding: 5px;
        font-weight: bold;
        text-align: center;
        font-size: 14px;
        color: #333;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* 5. Tombol Streamlit */
    .stButton button {
        width: 100%;
        margin-top: -5px;
        border-radius: 0 0 8px 8px;
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
    except: return {"config":{"school_name":"Sekolah","logo_drive_url":""},"candidates":{str(i):{"nama":f"C{i}","foto_drive_url":""} for i in range(1,7)},"votes":{str(i):0 for i in range(1,7)},"used_tokens":[]}

def save_data(data, msg="Update"):
    repo = init_github()
    if not repo: return
    content = json.dumps(data, indent=2)
    try: repo.update_file(repo.get_contents(FILE_DATA_JSON).path, msg, content, repo.get_contents(FILE_DATA_JSON).sha)
    except: repo.create_file(FILE_DATA_JSON, "Init", content)

@st.cache_data(ttl=60)
def load_dpt():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame()

# --- APP ---
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'page' not in st.session_state: st.session_state.page = 'home'
DB = st.session_state.db
LOGO = get_drive_image(DB['config']['logo_drive_url'])

with st.sidebar:
    if LOGO: st.image(LOGO, width=80)
    else: st.header("🗳️")
    st.write(f"**{DB['config']['school_name']}**")
    menu = st.radio("Menu", ["Bilik Suara", "Panel Admin"])
    st.markdown("---")
    st.metric("Total Suara", sum(DB['votes'].values()))

# --- BILIK SUARA ---
if menu == "Bilik Suara":
    if 'user_token' not in st.session_state:
        st.subheader("🔐 Login")
        c1, c2 = st.columns([2,1])
        with c1:
            token = st.text_input("Token").strip()
            if st.button("Masuk"):
                latest = load_data()
                if latest: DB = latest
                if token in DB['used_tokens']: st.error("Token Sudah Dipakai!")
                else:
                    dpt = load_dpt()
                    # Pastikan kolom Token dibaca sebagai string
                    dpt['Token'] = dpt['Token'].astype(str).str.strip()
                    user = dpt[dpt['Token'] == token]
                    
                    if not user.empty:
                        st.session_state.user_token = token
                        st.session_state.user_name = user.iloc[0]['Nama']
                        st.rerun()
                    else: st.error("Token Salah!")
    else:
        # TAMPILAN KANDIDAT YANG DIPERBAIKI (HTML IMG)
        st.markdown(f"**Halo, {st.session_state.user_name}** | Silakan pilih:")
        
        cands = DB['candidates']
        
        # BARIS 1 (1-3)
        cols1 = st.columns(3)
        for i in range(1, 4):
            cid = str(i)
            info = cands[cid]
            url = get_drive_image(info['foto_drive_url']) or PLACEHOLDER_IMG
            
            with cols1[i-1]:
                # RENDER HTML LANGSUNG (Agar ukuran fix)
                st.markdown(f"""
                <div class="card-html">
                    <img src="{url}" class="fixed-img">
                    <div class="cand-name">{info['nama']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"PILIH {cid}", key=f"v{cid}", type="primary"):
                    cur = load_data()
                    cur['votes'][cid] += 1
                    cur['used_tokens'].append(st.session_state.user_token)
                    save_data(cur, f"Voted {cid}")
                    st.session_state.db = cur
                    del st.session_state.user_token
                    st.toast("✅ Tersimpan!")
                    time.sleep(1)
                    st.rerun()
        
        st.write("") # Spasi tipis

        # BARIS 2 (4-6)
        cols2 = st.columns(3)
        for i in range(4, 7):
            cid = str(i)
            info = cands[cid]
            url = get_drive_image(info['foto_drive_url']) or PLACEHOLDER_IMG
            
            with cols2[i-4]:
                st.markdown(f"""
                <div class="card-html">
                    <img src="{url}" class="fixed-img">
                    <div class="cand-name">{info['nama']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"PILIH {cid}", key=f"v{cid}", type="primary"):
                    cur = load_data()
                    cur['votes'][cid] += 1
                    cur['used_tokens'].append(st.session_state.user_token)
                    save_data(cur, f"Voted {cid}")
                    st.session_state.db = cur
                    del st.session_state.user_token
                    st.toast("✅ Tersimpan!")
                    time.sleep(1)
                    st.rerun()

# --- ADMIN ---
elif menu == "Panel Admin":
    st.subheader("⚙️ Admin")
    if st.text_input("PIN", type="password") == st.secrets["admin"]["pin"]:
        col_t1, col_t2 = st.columns([3,1])
        with col_t2: 
            if st.toggle("Live"):
                st.session_state.db = load_data()
                time.sleep(5)
                st.rerun()
        
        t1, t2, t3 = st.tabs(["Data", "Suara", "Reset"])
        with t1:
            with st.form("set"):
                DB['config']['school_name'] = st.text_input("Sekolah", DB['config']['school_name'])
                DB['config']['logo_drive_url'] = st.text_input("Logo", DB['config']['logo_drive_url'])
                st.divider()
                for c,v in DB['candidates'].items():
                    c1,c2 = st.columns([1,3])
                    c1.image(get_drive_image(v['foto_drive_url']) or PLACEHOLDER_IMG, width=50)
                    c2.text_input(f"Nama {c}", v['nama'], key=f"n{c}")
                    DB['candidates'][c]['nama'] = st.session_state[f"n{c}"]
                    DB['candidates'][c]['foto_drive_url'] = c2.text_input(f"Foto {c}", v['foto_drive_url'], key=f"f{c}")
                if st.form_submit_button("Simpan"): save_data(DB); st.rerun()
        
        with t2:
            dpt = len(load_dpt())
            vt = sum(DB['votes'].values())
            pct = vt/dpt if dpt else 0
            st.progress(pct)
            st.caption(f"{vt}/{dpt} ({pct*100:.1f}%)")
            df = pd.DataFrame([{"No":k, "Nama":v['nama'], "Suara":DB['votes'][k]} for k,v in DB['candidates'].items()])
            st.dataframe(df, use_container_width=True)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: df.to_excel(w, index=False)
            st.download_button("Excel", buf.getvalue(), "Rekap.xlsx")
            
        with t3:
            if st.button("RESET"):
                DB['votes']={str(i):0 for i in range(1,7)}
                DB['used_tokens']=[]
                save_data(DB, "RESET")
                st.rerun()
