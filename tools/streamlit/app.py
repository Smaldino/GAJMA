import streamlit as st
from notion_client import Client
from datetime import datetime
from pathlib import Path

# 1. Initial Configuration
BASE_VIDEO_FOLDER = Path(r"GAJMA\data\videos")
st.set_page_config(page_title="Manga Animation Evaluator", page_icon="🎓", layout="wide")
st.title("🎓 Qualitative Manga Animation Evaluation (Thesis)")
st.markdown("This app is designed for the **Human-in-the-Loop** evaluation of generated animations.")

# 2. Structured Video Detection & Smart Naming
with st.spinner("Scanning and categorizing videos..."):
    # Only grab final compiled videos, ignoring intermediate smoothed clips
    all_videos = sorted(list(BASE_VIDEO_FOLDER.rglob("final_compilation/*.mp4")))
    
    # Intermediate grouping: { "Style Name": [ ("Manga", path), ... ] }
    raw_db = {}
    for v_path in all_videos:
        parts = v_path.parts
        if 'video_input' in parts:
            idx = parts.index('video_input')
            manga = parts[idx+1]
            style_raw = parts[idx+2]
            # Format style nicely: "Dolly_Bokeh" -> "Dolly Bokeh"
            style = style_raw.replace('_', ' ').title() 
        else:
            manga = "Unknown Manga"
            style = "Unknown Style"
            
        if style not in raw_db:
            raw_db[style] = []
        raw_db[style].append((manga, v_path))

    # Build final UI dictionary: { "Style Name": { "Manga - Transition X": path } }
    video_database = {}
    for style, items in raw_db.items():
        video_database[style] = {}
        manga_counts = {}
        
        for manga, path in items:
            manga_counts[manga] = manga_counts.get(manga, 0) + 1
            count = manga_counts[manga]
            display_name = f"{manga} - Transition {count}"
            video_database[style][display_name] = str(path)
            
    if not all_videos:
        st.warning(f"No compiled .mp4 files found in {BASE_VIDEO_FOLDER}.")
        st.stop()

# 3. Notion Integration
try:
    notion = Client(auth=st.secrets["NOTION_TOKEN"])
    DB_ID = st.secrets["DATABASE_ID"]
except Exception as e:
    st.error("Error: Please configure `.streamlit/secrets.toml` with NOTION_TOKEN and DATABASE_ID.")
    st.stop()

# 4. Multi-Level UI Interface
st.sidebar.header("🎬 Video Selection")

# Dropdown 1: Select Style (Category)
selected_style = st.sidebar.selectbox("1. Select Cinematography Style", list(video_database.keys()))

# Dropdown 2: Select Manga Transition
selected_video_name = st.sidebar.selectbox("2. Select Manga Transition", list(video_database[selected_style].keys()))
selected_path = video_database[selected_style][selected_video_name]

st.subheader(f"📺 {selected_style} | {selected_video_name}")

# Video Playback
st.video(selected_path)

# Evaluation Form
with st.form("evaluation_form"):
    st.markdown("### 📝 Evaluation Sheet (GAJMA2.0 Qualitative)")
    evaluator = st.text_input("Evaluator Name", value="")
    
    col1, col2 = st.columns(2)
    with col1:
        coherence = st.slider("Structural Coherence (Ink/Balloons) (1-5)", 1, 5, 3, help="Do ink lines and speech balloons remain stable without melting?")
        style_fidelity = st.slider("Style Fidelity (B/W Manga) (1-5)", 1, 5, 3, help="Does it look like a 2D manga or a live-action/3D video?")
    with col2:
        fluidity = st.slider("Motion Fluidity (1-5)", 1, 5, 3, help="Is the motion natural, or are there morphing/artifacts?")
        quality = st.slider("Overall Quality (1-5)", 1, 5, 3)
        
    notes = st.text_area("Additional Notes (e.g., 'Text melting detected', 'Excellent parallax', 'Line boil present', etc.)")
    
    submit = st.form_submit_button("🚀 Submit Evaluation to Notion")

    if submit:
        if not evaluator:
            st.warning("⚠️ Please enter your name!")
        else:
            # Clean Notion Title: "Dolly Bokeh - Akuhamu - Transition 1"
            notion_name = f"{selected_style} - {selected_video_name}"
            try:
                notion.pages.create(
                    parent={"database_id": DB_ID},
                    properties={
                        "Video Name": {"title": [{"text": {"content": notion_name}}]},
                        "Evaluator": {"rich_text": [{"text": {"content": evaluator}}]},
                        "Coherence": {"number": coherence},
                        "Fluidity": {"number": fluidity},
                        "Style": {"number": style_fidelity},
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