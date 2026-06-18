import streamlit as st
from notion_client import Client
from datetime import datetime
from pathlib import Path

# 1. Initial Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent.parent  
BASE_VIDEO_FOLDER = REPO_ROOT / "data" / "videos"

st.set_page_config(page_title="Manga Animation Evaluator", page_icon="🎓", layout="wide")
st.title("🎓 Qualitative Manga Animation Evaluation")
st.markdown("This interactive tool showcases the curated results of the proposed pipeline versus the Naive Baseline for the GAJMA2.0 challenge defense.")

# 2. Define the Curated Whitelist (The 8 Hero Shots)
# Grouped logically to guide the commission through your thesis narrative
CATEGORIES = {
    "1. Stable Dialogue & Pans (Parallax Smooth)": [
        {"manga": "akuhamu", "style": "Parallax_Smooth", "file": "Parallax_Smooth_Final_32fps.mp4", "display": "Akuhamu (Rank #1 Overall)"},
        {"manga": "TetsuSan", "style": "Parallax_Smooth", "file": "Parallax_Smooth_Final_32fps.mp4", "display": "TetsuSan (Rank #6)"},
        {"manga": "OL_lunch", "style": "Parallax_Smooth", "file": "Parallax_Smooth_Final_32fps.mp4", "display": "OL_lunch (Rank #9)"},
    ],
    "2. Cinematic Depth-of-Field (Rack Focus / Bokeh)": [
        {"manga": "akuhamu", "style": "Rack_Focus", "file": "Rack_Focus_Final_32fps.mp4", "display": "Akuhamu Rack Focus (Rank #5)"},
        {"manga": "TetsuSan", "style": "Rack_Focus", "file": "Rack_Focus_Final_32fps.mp4", "display": "TetsuSan Rack Focus (Rank #7)"},
        {"manga": "OL_lunch", "style": "Dolly_Bokeh", "file": "Dolly_Bokeh_Final_32fps.mp4", "display": "OL_lunch Dolly Bokeh (Rank #8)"},
    ],
    "3. High Action Routing (Dynamic Controlled)": [
        {"manga": "akuhamu", "style": "Dynamic_Controlled", "file": "Dynamic_Controlled_Final_32fps.mp4", "display": "Akuhamu Action (Rank #11)"},
    ],
    "4. ⚠️ Naive Baseline (Control Group)": [
        {"manga": "z-naive", "style": "Akuhamu", "file": "Full_Manga_Animation_32fps.mp4", "display": "Naive Akuhamu (Text Melting)"},
        {"manga": "z-naive", "style": "Tetsusan", "file": "Full_Manga_Animation_32fps.mp4", "display": "Naive TetsuSan (Text Melting)"},
    ]
}

# 3. Scan and Map Videos
with st.spinner("Locating curated evaluation videos..."):
    video_database = {}
    missing_videos = []
    
    if not BASE_VIDEO_FOLDER.exists():
        st.error(f"❌ Folder not found: `{BASE_VIDEO_FOLDER}`. Please ensure the `data/videos` folder exists in your repository.")
        st.stop()

    for category, videos in CATEGORIES.items():
        video_database[category] = {}
        for v_info in videos:
            # Search recursively for the exact filename
            found_path = None
            for path in BASE_VIDEO_FOLDER.rglob(v_info["file"]):
                # Verify it belongs to the correct manga/style to avoid picking up wrong duplicates
                if v_info["manga"].lower() in str(path).lower() and v_info["style"].lower() in str(path).lower():
                    found_path = path
                    break
            
            if found_path:
                video_database[category][v_info["display"]] = str(found_path)
            else:
                missing_videos.append(f"{v_info['manga']} / {v_info['style']}")

    if missing_videos:
        st.warning(f"⚠️ Could not locate {len(missing_videos)} videos in `{BASE_VIDEO_FOLDER}`. They will be hidden. Missing: {', '.join(missing_videos)}")

    # Clean up empty categories
    video_database = {k: v for k, v in video_database.items() if v}

    if not video_database:
        st.error("No curated videos found. Please check your folder structure.")
        st.stop()

# 4. Notion Integration
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

# 5. Multi-Level UI Interface
st.sidebar.header("🎬 Video Selection")

# Dropdown 1: Select Category
available_categories = sorted(list(video_database.keys()))
selected_category = st.sidebar.selectbox("1. Select Evaluation Category", available_categories)

# Dropdown 2: Select Video
available_videos = sorted(list(video_database[selected_category].keys()))
selected_video = st.sidebar.selectbox("2. Select Manga Clip", available_videos)

selected_path = video_database[selected_category][selected_video]

st.subheader(f"📺 {selected_category} | {selected_video}")

# Reduce video dimension by placing it in the center column (50% width)
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
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
            notion_title = f"{selected_category} | {selected_video}"
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