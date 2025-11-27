import streamlit as st
import pandas as pd
import json
import io
import time
from github import Github

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pilketos Online", page_icon="🗳️", layout="wide")

# --- DATABASE ---
FILE_DATA_JSON = "database_pilketos.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSz67ms_9qkcSB_O-Td290-S55KiIL0kV-63lB2upMzOpn6dr2-qk_IHcRDttuk1fIIGDTPhoRTC8_8/pub?output=csv"

# --- PLACEHOLDER IMAGE ---
PLACEHOLDER_IMG = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMDAiIGhlaWdodD0iMjAwIiB2aWV3Qm94PSIwIDAgMzAwIDIwMCI+PHJlY3QgZmlsbD0iI2RkZCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiLz48dGV4dCBmaWxsPSJyZ2JhKDAsMCwwLDAuNSkiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjMwIiBkeT0iMTAuNSIgZm9udC13ZWlnaHQ9ImJvbGQiIHg9IjUwJSIgeT0iNTAlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5ObyBJbWFnZTwvdGV4dD48L3N2Zz4="

# --- CSS REVISI (KANDIDAT KECIL) ---
st.markdown("""
<style>

    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    .candidate-card {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 15px;
    }

    .candidate-img img {
        height: 85px !important;
        width: auto !important;
        object-fit: cover !important;
        border-radius: 5px;
        margin-bottom: 6px;
    }

    .cand-name {
        font-size: 12px;
        font-weight: bold;
        text-align: center;
        color: #333;
        margin-bottom: 6px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .stButton button {
        width: 100%;
        background-color: #007bff !important;
        color: white !important;
        border-radius: 5px;
        font-size: 12px;
        padding: 4px 0;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNGSI UTILS ---
def get_drive_image(url_or_id):
    if not url_or_id:
        return None
    file_id = url_or_id
    if "drive.google.com" in url_or_id:
        if "/d/" in url_or_id:
            file_id = url_or_id.split("/d/")[1].split("/")[0]
        elif "id=" in url_or_id:
            file_id = url_or_id.split("id=")[1].split("&")[0]
    return f"https://lh3.googleusercontent.com/d/{file_id}"

def init_github():
    try:
        return Github(st.secrets["github"]["token"]).get_repo(st.secrets["github"]["repo_name"])
    except Exception as e:
        st.error(f"GitHub Error: {e}")
        return None

def load_data():
    repo = init_github()
    if not repo:
        return None
    try:
        content = repo.get_contents(FILE_DATA_JSON).decoded_content.decode()
        return json.loads(content)
    except:
        return {
            "config": {"school_name": "SMPN 4 Mendoyo", "logo_drive_url": ""},
            "candidates": {str(i): {"nama": f"Calon {i}", "foto_drive_url": ""} for i in range(1, 7)},
            "votes": {str(i): 0 for i in range(1, 7)},
            "used_tokens": []
        }

def save_data(data, msg="Update"):
    repo = init_github()
    if not repo:
        return
    content = json.dumps(data, indent=2)
    try:
        file = repo.get_contents(FILE_DATA_JSON)
        repo.update_file(file.path, msg, content, file.sha)
    except:
        repo.create_file(FILE_DATA_JSON, "Init", content)

@st.cache_data(ttl=60)
def load_dpt():
    try:
        df = pd.read_csv(SHEET_URL)
        df['Token'] = df['Token'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

# --- APP START ---
if "db" not in st.session_state:
    with st.spinner("Memuat Database..."):
        st.session_state.db = load_data()

if "page" not in st.session_state:
    st.session_state.page = "home"

DB = st.session_state.db
SCHOOL_NAME = DB["config"]["school_name"]
LOGO_URL = get_drive_image(DB["config"]["logo_drive_url"])

# --- SIDEBAR ---
with st.sidebar:
    if LOGO_URL:
        st.image(LOGO_URL, width=100)
    st.markdown(f"**{SCHOOL_NAME}**")
    st.caption("E-Voting System")
    st.markdown("---")
    menu = st.radio("Menu", ["Bilik Suara", "Panel Admin"])
    st.markdown("---")
    st.metric("Total Suara", sum(DB["votes"].values()))

# ================= HALAMAN BILIK SUARA =================
if menu == "Bilik Suara":

    # LOGIN TOKEN
    if "user_token" not in st.session_state:
        st.title("🔐 Login Pemilih")
        st.info("Masukkan Token Anda.")

        token = st.text_input("Token", placeholder="12345").strip()
        if st.button("Verifikasi & Masuk", type="primary"):

            latest = load_data()
            if latest:
                DB = latest

            if token in DB["used_tokens"]:
                st.error("❌ Token sudah digunakan!")

            else:
                dpt = load_dpt()
                user = dpt[dpt["Token"] == token]

                if not user.empty:
                    st.session_state.user_token = token
                    st.session_state.user_name = user.iloc[0]["Nama"]
                    st.rerun()
                else:
                    st.error("❌ Token tidak terdaftar.")

    else:
        st.markdown(f"#### 👋 Halo, {st.session_state.user_name}")
        st.write("Silakan pilih kandidat:")

        cands = DB["candidates"]

        # --- BARIS 1 (1–3) ---
        cols1 = st.columns(3)
        for i in range(1, 4):
            cid = str(i)
            with cols1[i-1]:

                info = cands[cid]
                img = get_drive_image(info["foto_drive_url"])

                st.markdown('<div class="candidate-card">', unsafe_allow_html=True)

                st.markdown('<div class="candidate-img">', unsafe_allow_html=True)
                if img:
                    st.image(img, use_column_width=True)
                else:
                    st.image(PLACEHOLDER_IMG, use_column_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown(f"<div class='cand-name'>{info['nama']}</div>", unsafe_allow_html=True)

                if st.button(f"PILIH NO {cid}", key=f"v{cid}"):
                    current = load_data()
                    current["votes"][cid] += 1
                    current["used_tokens"].append(st.session_state.user_token)
                    save_data(current, f"Vote {cid}")
                    st.session_state.db = current
                    del st.session_state.user_token
                    st.success("Suara Masuk!")
                    st.balloons()
                    time.sleep(1.2)
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        # --- BARIS 2 (4–6) ---
        cols2 = st.columns(3)
        for i in range(4, 7):
            cid = str(i)
            with cols2[i-4]:

                info = cands[cid]
                img = get_drive_image(info["foto_drive_url"])

                st.markdown('<div class="candidate-card">', unsafe_allow_html=True)

                st.markdown('<div class="candidate-img">', unsafe_allow_html=True)
                if img:
                    st.image(img, use_column_width=True)
                else:
                    st.image(PLACEHOLDER_IMG, use_column_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown(f"<div class='cand-name'>{info['nama']}</div>", unsafe_allow_html=True)

                if st.button(f"PILIH NO {cid}", key=f"v{cid}"):
                    current = load_data()
                    current["votes"][cid] += 1
                    current["used_tokens"].append(st.session_state.user_token)
                    save_data(current, f"Vote {cid}")
                    st.session_state.db = current
                    del st.session_state.user_token
                    st.success("Suara Masuk!")
                    st.balloons()
                    time.sleep(1.2)
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

# ================= HALAMAN ADMIN =================
elif menu == "Panel Admin":
    st.header("⚙️ Admin Panel")

    pin = st.text_input("PIN Admin", type="password")
    if pin == st.secrets["admin"]["pin"]:

        col1, col2 = st.columns([4, 1])
        with col2:
            auto_refresh = st.toggle("🔴 Live Update")

        if auto_refresh:
            fresh = load_data()
            if fresh:
                st.session_state.db = fresh
                DB = fresh

        tab1, tab2, tab3 = st.tabs(["Sekolah & Kandidat", "Data & Export", "Reset"])

        with tab1:
            st.subheader("Identitas Sekolah")
            with st.form("form_identitas"):
                new_name = st.text_input("Nama Sekolah", DB["config"]["school_name"])
                new_logo = st.text_input("Link Logo (Drive)", DB["config"]["logo_drive_url"])
                if st.form_submit_button("Simpan"):
                    DB["config"]["school_name"] = new_name
                    DB["config"]["logo_drive_url"] = new_logo
                    save_data(DB, "Update Config")
                    st.rerun()

            st.subheader("Kandidat")
            with st.form("form_kandidat"):
                for cid, info in DB["candidates"].items():
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        prev = get_drive_image(info["foto_drive_url"])
                        if prev:
                            st.image(prev, width=60)
                        else:
                            st.image(PLACEHOLDER_IMG, width=60)
                    with c2:
                        DB["candidates"][cid]["nama"] = st.text_input(f"Nama {cid}", info["nama"], key=f"n{cid}")
                        DB["candidates"][cid]["foto_drive_url"] = st.text_input(f"Foto {cid}", info["foto_drive_url"], key=f"f{cid}")
                    st.markdown("---")
                if st.form_submit_button("Simpan Semua"):
                    save_data(DB, "Update Candidates")
                    st.rerun()

        with tab2:
            st.subheader("Statistik")
            dpt_total = len(load_dpt())
            masuk = sum(DB["votes"].values())
            pct = masuk / dpt_total if dpt_total else 0

            st.progress(pct)
            st.caption(f"Partisipasi: {masuk} dari {dpt_total} ({pct*100:.1f}%)")

            data = [{"No": k, "Nama": v["nama"], "Suara": DB["votes"][k]} for k, v in DB["candidates"].items()]
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as writer:
                df.to_excel(writer, sheet_name="Rekap", index=False)
                pd.DataFrame({"Token": DB["used_tokens"]}).to_excel(writer, sheet_name="Log", index=False)

            st.download_button("📥 Download Excel", buf.getvalue(), "Rekap_Pilketos.xlsx")

        with tab3:
            st.warning("Hati-hati, tindakan ini menghapus semua data!")
            if st.button("RESET SEMUA DATA ❌"):
                DB["votes"] = {str(i): 0 for i in range(1, 7)}
                DB["used_tokens"] = []
                save_data(DB, "RESET ALL")
                st.success("Reset Berhasil!")
                st.rerun()

        if auto_refresh:
            time.sleep(5)
            st.rerun()

    elif pin:
        st.error("PIN salah!")
