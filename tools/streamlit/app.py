import streamlit as st
from notion_client import Client
from datetime import datetime
from pathlib import Path

# 1. Initial Configuration
# Anchor to the script's location to avoid working directory issues on Streamlit Cloud
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent.parent  # tools/streamlit -> tools -> root
BASE_VIDEO_FOLDER = REPO_ROOT / "data" / "videos"

st.set_page_config(page_title="Manga Animation Evaluator", page_icon="🎓", layout="wide")
st.title("🎓 Qualitative Manga Animation Evaluation")
st.markdown("This app is designed for the **Human-in-the-Loop** evaluation of generated animations (Ablation Study & Proposed Pipeline).")

# 2. Structured Video Detection
with st.spinner("Scanning and organizing videos..."):
    video_database = {}
    manga_counters = {}
    
    if not BASE_VIDEO_FOLDER.exists():
        st.error(f"❌ Folder not found: `{BASE_VIDEO_FOLDER}`. Please ensure the `data/videos` folder exists in your GitHub repository.")
        st.stop()

    # Find all mp4s recursively (Removed the strict "final_compilation" requirement)
    all_mp4s = sorted(list(BASE_VIDEO_FOLDER.rglob("*.mp4")))
    
    for mp4_path in all_mp4s:
        parts = mp4_path.parts
        try:
            # Look for 'videos' in the path to anchor the manga and style
            v_idx = parts.index('videos')
            manga_name = parts[v_idx + 1]
            
            # Style could be a subfolder OR the filename itself
            if v_idx + 2 < len(parts):
                style_name = parts[v_idx + 2]
                # If the style name includes the extension, strip it
                if style_name.endswith('.mp4'):
                    style_name = style_name.replace('.mp4', '')
            else:
                style_name = "General"
                
        except (ValueError, IndexError):
            # Fallback if 'videos' is not in the path parts
            manga_name = mp4_path.parent.name
            style_name = mp4_path.stem
            
        # Format Style Name: "Dolly_Bokeh" -> "Dolly Bokeh"
        style_display = style_name.replace('_', ' ').title()
        
        if style_display not in video_database:
            video_database[style_display] = {}
            
        # Track manga counts to assign a sequential number per manga
        if manga_name not in manga_counters:
            manga_counters[manga_name] = 0
        manga_counters[manga_name] += 1
        
        # Format Video Name: "TetsuSan - 1"
        video_display = f"{manga_name} - {manga_counters[manga_name]}"
        
        video_database[style_display][video_display] = str(mp4_path)

    if not video_database:
        st.error(f"No `.mp4` videos found under `{BASE_VIDEO_FOLDER}`. Please check your GitHub repo structure.")
        st.stop()

# 3. Notion Integration
try:
    notion = Client(auth=st.secrets["NOTION_TOKEN"])
    DB_ID = st.secrets["DATABASE_ID"]
except KeyError:
    st.warning("⚠️ Notion secrets not found. Evaluations will not be saved to Notion. (Add NOTION_TOKEN and DATABASE_ID to Streamlit Cloud Secrets)")
    notion = None
    DB_ID = None
except Exception as e:
    st.error(f"Notion Connection Error: {e}")
    st.stop()

# 4. Multi-Level UI Interface
st.sidebar.header("🎬 Video Selection")

# Dropdown 1: Select Style
available_styles = sorted(list(video_database.keys()))
selected_style = st.sidebar.selectbox("1. Select Cinematography Style", available_styles)

# Dropdown 2: Select Video (Manga + Number)
available_videos = sorted(list(video_database[selected_style].keys()))
selected_video = st.sidebar.selectbox("2. Select Manga Clip", available_videos)

selected_path = video_database[selected_style][selected_video]

st.subheader(f"📺 {selected_style} | {selected_video}")

# Reduce video dimension by placing it in the center column (50% width)
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    # Read as bytes for more reliable streaming on cloud containers
    try:
        with open(selected_path, 'rb') as video_file:
            video_bytes = video_file.read()
        st.video(video_bytes)
    except Exception as e:
        st.error(f"Error loading video: {e}")

st.markdown("---")

# Evaluation Form
with st.form("evaluation_form"):
    st.markdown("### 📝 Evaluation Sheet (GAJMA2.0 Qualitative)")
    evaluator = st.text_input("Evaluator Name", value="")
    
    col1, col2 = st.columns(2)
    with col1:
        coherence = st.slider("Structural Coherence (Ink/Balloons) (1-5)", 1, 5, 3, help="Do ink lines and speech balloons remain stable without melting?")
        style_adherence = st.slider("Style Fidelity (B/W Manga) (1-5)", 1, 5, 3, help="Does it look like a 2D manga or a live-action/3D video?")
    with col2:
        fluidity = st.slider("Motion Fluidity (1-5)", 1, 5, 3, help="Is the motion natural, or are there morphing/artifacts?")
        quality = st.slider("Overall Quality (1-5)", 1, 5, 3)
        
    notes = st.text_area("Additional Notes (e.g., 'Text melting detected', 'Excellent parallax', 'Line boil present', etc.)")
    
    submitted = st.form_submit_button("🚀 Submit Evaluation to Notion")

    if submitted:
        if not evaluator:
            st.warning("⚠️ Please enter your name!")
        elif notion is None:
            st.error("Cannot save to Notion: Secrets not configured in Streamlit Cloud Settings.")
        else:
            notion_title = f"{selected_style} | {selected_video}"
            try:
                notion.pages.create(
                    parent={"database_id": DB_ID},
                    properties={
                        "Video Name": {"title": [{"text": {"content": notion_title}}]},
                        "Evaluator": {"rich_text": [{"text": {"content": evaluator}}]},
                        "Coherence": {"number": coherence},
                        "Fluidity": {"number": fluidity},
                        "Style": {"number": style_adherence},
                        "Quality": {"number": quality},
                        "Notes": {"rich_text": [{"text": {"content": notes}}]},
                        "Date": {"date": {"start": datetime.now().isoformat()}}
                    }
                )
                st.success(f"✅ Evaluation for '{notion_title}' successfully saved to Notion!")
            except Exception as e:
                st.error(f"Notion API Error: {e}")