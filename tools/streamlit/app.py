import streamlit as st
from notion_client import Client
from datetime import datetime
from pathlib import Path

# 1. Initial Configuration
# Use Path(__file__) to anchor the path to this exact script.
# This guarantees it works regardless of where the cloud container executes it from.
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_VIDEO_FOLDER = SCRIPT_DIR / "data" / "videos"

st.set_page_config(page_title="Manga Animation Evaluator", page_icon="🎓", layout="wide")
st.title("🎓 Qualitative Manga Animation Evaluation")
st.markdown("This app is designed for the **Human-in-the-Loop** evaluation of generated animations (Ablation Study & Proposed Pipeline).")

# 2. Structured Video Detection
with st.spinner("Scanning for videos in the repository..."):
    if not BASE_VIDEO_FOLDER.exists():
        st.error(f"❌ Folder not found: `{BASE_VIDEO_FOLDER}`. Please ensure your videos are pushed to GitHub under `data/videos`.")
        st.stop()

    # Find all .mp4 files recursively
    all_videos = sorted(list(BASE_VIDEO_FOLDER.rglob("*.mp4")))
    
    if not all_videos:
        st.warning(f"No .mp4 files found in `{BASE_VIDEO_FOLDER}`. Please check your GitHub repository.")
        st.stop()

    # Group by parent folder (e.g., 'baseline_outputs', 'Parallax_Smooth', 'TetsuSan')
    video_database = {}
    for v_path in all_videos:
        try:
            relative_parent = v_path.parent.relative_to(BASE_VIDEO_FOLDER)
            category = str(relative_parent) if str(relative_parent) != "." else "Root / General"
        except ValueError:
            category = "Root / General"
            
        if category not in video_database:
            video_database[category] = {}
            
        video_database[category][v_path.name] = str(v_path)

# 3. Notion Integration (Cloud Secrets Handling)
try:
    notion = Client(auth=st.secrets["NOTION_TOKEN"])
    DB_ID = st.secrets["DATABASE_ID"]
except KeyError:
    st.error("❌ Error: Notion secrets not found. Please add `NOTION_TOKEN` and `DATABASE_ID` to your Streamlit Community Cloud Secrets settings.")
    st.stop()
except Exception as e:
    st.error(f"❌ Notion Connection Error: {e}")
    st.stop()

# 4. Multi-Level UI Interface
st.sidebar.header("🎬 Video Selection")

# Dropdown 1: Select Category/Experiment
selected_category = st.sidebar.selectbox("1. Select Category / Experiment", list(video_database.keys()))

# Dropdown 2: Select specific video
selected_video_name = st.sidebar.selectbox("2. Select Video", list(video_database[selected_category].keys()))
selected_path = video_database[selected_category][selected_video_name]

st.subheader(f"📺 {selected_category} | {selected_video_name}")

# Video Playback (Read as bytes for reliable cloud streaming)
try:
    with open(selected_path, 'rb') as video_file:
        video_bytes = video_file.read()
    st.video(video_bytes)
except Exception as e:
    st.error(f"Error loading video: {e}")

# Evaluation Form
with st.form("evaluation_form"):
    st.markdown("### 📝 Evaluation Sheet (GAJMA2.0 Qualitative)")
    evaluator = st.text_input("Evaluator Name", value="")
    
    col1, col2 = st.columns(2)
    with col1:
        coherence = st.slider("Structural Coherence (Ink/Balloons) (1-5)", 1, 5, 3, help="Do ink lines and speech balloons remain stable without melting?")
        style = st.slider("Style Fidelity (B/W Manga) (1-5)", 1, 5, 3, help="Does it look like a 2D manga or a live-action/3D video?")
    with col2:
        fluidity = st.slider("Motion Fluidity (1-5)", 1, 5, 3, help="Is the motion natural, or are there morphing/artifacts?")
        quality = st.slider("Overall Quality (1-5)", 1, 5, 3)
        
    notes = st.text_area("Additional Notes (e.g., 'Text melting detected', 'Excellent parallax', 'Line boil present', etc.)")
    
    submit = st.form_submit_button("🚀 Submit Evaluation to Notion")

    if submit:
        if not evaluator:
            st.warning("⚠️ Please enter your name!")
        else:
            notion_name = f"{selected_category} - {selected_video_name}"
            try:
                notion.pages.create(
                    parent={"database_id": DB_ID},
                    properties={
                        "Video Name": {"title": [{"text": {"content": notion_name}}]},
                        "Evaluator": {"rich_text": [{"text": {"content": evaluator}}]},
                        "Coherence": {"number": coherence},
                        "Fluidity": {"number": fluidity},
                        "Style": {"number": style},
                        "Quality": {"number": quality},
                        "Notes": {"rich_text": [{"text": {"content": notes}}]},
                        "Date": {"date": {"start": datetime.now().isoformat()}}
                    }
                )
                st.success(f"✅ Evaluation for '{notion_name}' saved to Notion!")
            except Exception as e:
                st.error(f"Notion Error: {e}")

with st.expander("🛠️ Debug Info"):
    st.write(f"**Absolute Path:** `{selected_path}`")
    st.write(f"**Size:** {Path(selected_path).stat().st_size / (1024*1024):.2f} MB")