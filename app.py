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
PLACEHOLDER_IMG = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMDAiIGhlaWdodD0iMjAwIiB2aWV3Qm94PSIwIDAgMzAwIDIwMCI+PHJlY3QgZmlsbD0iI2RkZCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiLz48dGV4dCBmaWxsPSJyZ2JhKDAsMCwwLDAuNSkiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjMwIiBkeT0iMTAuNSIgZm9udC13ZWlnaHQ9ImJvbGQiIHg9IjUwJSIgeT0iNTAlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5ObyBJbWFnZTwvdGV4dD48L3N2Zz4="

# --- CSS ULTRA COMPACT (3 ATAS 3 BAWAH) ---
st.markdown("""
<style>
    /* 1. HAPUS PADDING ATAS HALAMAN (Biar naik pol) */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    /* 2. HEADER KECIL */
    h1, h2, h3 {
        margin-bottom: 0.5rem !important;
        padding-bottom: 0rem !important;
    }

    /* 3. FOTO KANDIDAT MIKRO */
    .candidate-img img {
        height: 80px !important; /* Sangat Kecil */
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 5px 5px 0 0;
        margin: 0 auto;
        display: block;
    }
    
    /* 4. CARD CONTAINER */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: #f5f5f5;
        border-radius: 5px;
        padding: 0px !important;
        border: 1px solid #ddd;
        gap: 0px !important;
    }
    
    /* 5. NAMA KANDIDAT */
    .compact-name {
        font-size: 13px;
        font-weight: bold;
        text-align: center;
        margin: 2px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding: 0 5px;
    }
    
    /* 6. TOMBOL */
    .stButton button {
        width: 100%;
        height: 25px !important;
        min-height: 25px !important;
        font-size: 11px !important;
        margin-top: 0px !important;
        padding: 0px !important;
        border-radius: 0 0 5px 5px;
    }
    
    /* 7. HILANGKAN JARAK ANTAR KOLOM */
    div[data-testid="column"] {
        padding: 0 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNGSI UTILS ---
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
    try:
        df = pd.read_csv(SHEET_URL)
        df['Token'] = df['Token'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

# --- APP START ---
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'page' not in st.session_state: st.session_state.page = 'home'
DB = st.session_state.db
LOGO_URL = get_drive_image(DB['config']['logo_drive_url'])

# --- SIDEBAR ---
with st.sidebar:
    if LOGO_URL: st.image(LOGO_URL, width=80)
    else: st.header("🗳️")
    st.markdown(f"**{DB['config']['school_name']}**")
    menu = st.radio("Menu", ["Bilik Suara", "Panel Admin"])
    st.markdown("---")
    st.metric("Total Suara", sum(DB['votes'].values()))

# --- BILIK SUARA ---
if menu == "Bilik Suara":
    if 'user_token' not in st.session_state:
        st.subheader("Login Pemilih")
        c1, c2 = st.columns([2,1])
        with c1:
            token = st.text_input("Token", placeholder="12345").strip()
            if st.button("Masuk"):
                latest = load_data()
                if latest: DB = latest
                if token in DB['used_tokens']: st.error("Token Terpakai!")
                else:
                    user = load_dpt()[load_dpt()['Token'] == token]
                    if not user.empty:
                        st.session_state.user_token = token
                        st.session_state.user_name = user.iloc[0]['Nama']
                        st.rerun()
                    else: st.error("Salah Token!")
    else:
        # HEADER SUPER TIPIS
        st.markdown(f"<div style='font-size:14px; margin-bottom:10px;'>Halo, <b>{st.session_state.user_name}</b>. Silakan pilih:</div>", unsafe_allow_html=True)
        
        # LOGIC GRID 3x2 MANUAL (Agar pasti 3 atas, 3 bawah)
        cands = DB['candidates']
        
        # ROW 1 (Kandidat 1, 2, 3)
        cols1 = st.columns(3)
        for i in range(1, 4):
            cid = str(i)
            with cols1[i-1]:
                info = cands[cid]
                img = get_drive_image(info['foto_drive_url'])
                with st.container():
                    st.markdown('<div class="candidate-img">', unsafe_allow_html=True)
                    if img: st.image(img, use_column_width=True)
                    else: st.image(PLACEHOLDER_IMG, use_column_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='compact-name'>{info['nama']}</div>", unsafe_allow_html=True)
                    
                    if st.button(f"PILIH NO {cid}", key=f"v{cid}", type="primary"):
                        current = load_data()
                        current['votes'][cid] += 1
                        current['used_tokens'].append(st.session_state.user_token)
                        save_data(current, f"Voted {cid}")
                        st.session_state.db = current
                        del st.session_state.user_token
                        st.toast("✅ Suara Masuk!")
                        time.sleep(1)
                        st.rerun()
        
        # ROW 2 (Kandidat 4, 5, 6)
        st.write("") # Spasi tipis antar row
        cols2 = st.columns(3)
        for i in range(4, 7):
            cid = str(i)
            with cols2[i-4]:
                info = cands[cid]
                img = get_drive_image(info['foto_drive_url'])
                with st.container():
                    st.markdown('<div class="candidate-img">', unsafe_allow_html=True)
                    if img: st.image(img, use_column_width=True)
                    else: st.image(PLACEHOLDER_IMG, use_column_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='compact-name'>{info['nama']}</div>", unsafe_allow_html=True)
                    
                    if st.button(f"PILIH NO {cid}", key=f"v{cid}", type="primary"):
                        current = load_data()
                        current['votes'][cid] += 1
                        current['used_tokens'].append(st.session_state.user_token)
                        save_data(current, f"Voted {cid}")
                        st.session_state.db = current
                        del st.session_state.user_token
                        st.toast("✅ Suara Masuk!")
                        time.sleep(1)
                        st.rerun()

# --- ADMIN ---
elif menu == "Panel Admin":
    st.subheader("⚙️ Admin")
    if st.text_input("PIN", type="password") == st.secrets["admin"]["pin"]:
        col1, col2 = st.columns([3,1])
        with col2: 
            if st.toggle("Live"):
                st.session_state.db = load_data()
                DB = st.session_state.db
                time.sleep(5)
                st.rerun()
        
        t1, t2, t3 = st.tabs(["Data", "Suara", "Reset"])
        with t1:
            with st.form("id"):
                DB['config']['school_name'] = st.text_input("Sekolah", DB['config']['school_name'])
                DB['config']['logo_drive_url'] = st.text_input("Logo", DB['config']['logo_drive_url'])
                if st.form_submit_button("Simpan ID"): save_data(DB); st.rerun()
            
            with st.form("cand"):
                for c, v in DB['candidates'].items():
                    c1, c2 = st.columns([1,3])
                    c1.image(get_drive_image(v['foto_drive_url']) or PLACEHOLDER_IMG, width=50)
                    c2.text_input(f"Nama {c}", v['nama'], key=f"n{c}")
                    DB['candidates'][c]['nama'] = st.session_state[f"n{c}"]
                    DB['candidates'][c]['foto_drive_url'] = c2.text_input(f"Foto {c}", v['foto_drive_url'], key=f"f{c}")
                if st.form_submit_button("Simpan Foto"): save_data(DB); st.rerun()
        
        with t2:
            dpt = len(load_dpt())
            voted = sum(DB['votes'].values())
            pct = (voted/dpt)*100 if dpt else 0
            st.progress(pct/100)
            st.caption(f"{voted}/{dpt} ({pct:.1f}%)")
            
            df = pd.DataFrame([{"No":k,"Nama":v['nama'],"Suara":DB['votes'][k]} for k,v in DB['candidates'].items()])
            st.dataframe(df, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w: df.to_excel(w, index=False)
            st.download_button("Excel", buf.getvalue(), "Rekap.xlsx")
            
        with t3:
            if st.button("RESET TOTAL"):
                DB['votes'] = {str(i):0 for i in range(1,7)}
                DB['used_tokens'] = []
                save_data(DB, "RESET")
                st.rerun()
