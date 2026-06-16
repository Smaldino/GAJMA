import streamlit as st
from notion_client import Client
from datetime import datetime
from pathlib import Path
import os

# 1. Initial Configuration
# Get the directory where this script (app.py) is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Navigate up to the repository root (from tools/streamlit/ -> tools/ -> root)
REPO_ROOT = SCRIPT_DIR.parent.parent 
BASE_VIDEO_FOLDER = REPO_ROOT / "data" / "videos"

st.set_page_config(page_title="Manga Animation Evaluator", page_icon="🎓", layout="wide")
st.title("🎓 Qualitative Manga Animation Evaluation")

# Check if the folder exists
if not BASE_VIDEO_FOLDER.exists():
    st.error(f"Folder not found: `{BASE_VIDEO_FOLDER}`.\n\nPlease ensure your videos are pushed to GitHub under the `data/videos` folder at the **root** of your repository.")
    st.stop()

# Check if there are any videos inside
video_files = sorted(list(BASE_VIDEO_FOLDER.glob("*.mp4")))
if not video_files:
    st.warning(f"No `.mp4` files found in `{BASE_VIDEO_FOLDER}`. Please add some videos to evaluate.")
    st.stop()

# ... [Keep the rest of your existing app.py code exactly as it was] ...