import cv2
import torch
import lpips
import pandas as pd
import numpy as np
from torchvision.models import vgg19, VGG19_Weights
import torch.nn.functional as F_torch
from scipy.stats import wasserstein_distance
import torchvision.transforms as T
from pathlib import Path
from tqdm import tqdm

# === PATH RESOLUTION ===
# Assumes this script is inside src/evaluation/ or scripts/evaluation/
# parents[0] = evaluation/, parents[1] = src/ or scripts/, parents[2] = GAJMA_ROOT
GAJMA_ROOT = Path(__file__).resolve().parents[2]
BASE_VIDEO_DIR = GAJMA_ROOT / "data" / "videos"
OUTPUT_DIR = GAJMA_ROOT / "data" / "evaluation_results"
OUTPUT_DIR.mkdir(exist_ok=True)
CSV_OUT = OUTPUT_DIR / "submission_metrics.csv"

if not BASE_VIDEO_DIR.exists():
    raise FileNotFoundError(f"Folder not found: {BASE_VIDEO_DIR}\nCheck BASE_VIDEO_DIR in the script.")

print("🧠 Loading Evaluation Models (LPIPS & VGG19)...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
lpips_loss = lpips.LPIPS(net='alex').to(device).eval()
vgg = vgg19(weights=VGG19_Weights.DEFAULT).features[:16].to(device).eval()
to_tensor = T.ToTensor()


def get_gram_matrix(frame_tensor):
    with torch.no_grad():
        features = vgg(frame_tensor)
    b, c, h, w = features.shape
    features = features.view(b, c, h * w)
    gram = torch.bmm(features, features.transpose(1, 2))
    return gram / (c * h * w)


def compute_lpips(f1, f2):
    t1 = torch.from_numpy(cv2.cvtColor(f1, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 127.5 - 1.0
    t2 = torch.from_numpy(cv2.cvtColor(f2, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 127.5 - 1.0
    with torch.no_grad():
        return lpips_loss(t1.unsqueeze(0).to(device), t2.unsqueeze(0).to(device)).item()


def compute_warping_error(f1, f2):
    gray1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0)

    h, w = flow.shape[:2]
    y_coords, x_coords = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    pixel_map = np.stack((x_coords, y_coords), axis=-1).astype(np.float32)
    flow_map = pixel_map + flow

    warped = cv2.remap(f1, flow_map, None, cv2.INTER_LINEAR)
    diff = np.abs(f2.astype(np.float32) - warped.astype(np.float32))
    mask = diff.mean(axis=2) < 50
    if mask.sum() == 0:
        return diff.mean()
    return diff[mask].mean()


def compute_style_distance(f1, f2):
    t1 = to_tensor(cv2.cvtColor(f1, cv2.COLOR_BGR2RGB)).unsqueeze(0).to(device)
    t2 = to_tensor(cv2.cvtColor(f2, cv2.COLOR_BGR2RGB)).unsqueeze(0).to(device)
    with torch.no_grad():
        g1 = get_gram_matrix(t1)
        g2 = get_gram_matrix(t2)
        return F_torch.mse_loss(g1, g2).item()


def compute_tone_consistency(f1, f2):
    gray1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
    hist1, _ = np.histogram(gray1, bins=256, range=(0, 256), density=True)
    hist2, _ = np.histogram(gray2, bins=256, range=(0, 256), density=True)
    values = np.arange(256)
    return wasserstein_distance(values, values, hist1, hist2)

print(f"\n📊 Scanning only 'final_compilation' folders in: {BASE_VIDEO_DIR}")
video_files = [str(p) for p in BASE_VIDEO_DIR.rglob("final_compilation/*.mp4")]

if not video_files:
    print("⛔ No videos found inside 'final_compilation' folders. Check your directory structure.")
    exit()

print(f"🎬 Found {len(video_files)} final videos. Starting evaluation (this may take a while)...\n")

results = []
for video_path in tqdm(video_files, desc="Evaluating Videos"):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    if len(frames) < 2:
        continue

    lpips_s, warp_s, style_s, tone_s = [], [], [], []
    for i in range(len(frames) - 1):
        f1, f2 = frames[i], frames[i + 1]
        lpips_s.append(compute_lpips(f1, f2))
        warp_s.append(compute_warping_error(f1, f2))
        style_s.append(compute_style_distance(f1, f2))
        tone_s.append(compute_tone_consistency(f1, f2))

    p = Path(video_path)
    try:
        parts = p.parts
        if 'videos' in parts:
            idx = parts.index('videos')
            manga_name = parts[idx + 1] if idx + 1 < len(parts) else "Unknown"
            style_name = parts[idx + 2] if idx + 2 < len(parts) else "Unknown"
        else:
            manga_name = p.parent.parent.parent.name
            style_name = p.parent.parent.name
    except Exception:
        manga_name = "Unknown"
        style_name = "Unknown"

    results.append({
        "Manga": manga_name,
        "Style": style_name,
        "Video": p.name,
        "LPIPS (↓)": np.mean(lpips_s),
        "Warping Error (↓)": np.mean(warp_s),
        "Style Distance (↓)": np.mean(style_s),
        "Tone EMD (↓)": np.mean(tone_s)
    })


df = pd.DataFrame(results)

if df.empty:
    print("\n⚠️ No valid videos were evaluated. Exiting.")
    exit()

for col in ["LPIPS (↓)", "Warping Error (↓)", "Style Distance (↓)", "Tone EMD (↓)"]:
    min_val, max_val = df[col].min(), df[col].max()
    df[f"{col}_norm"] = (df[col] - min_val) / (max_val - min_val) if max_val > min_val else 0

df["Overall Score (↓)"] = df[[c for c in df.columns if c.endswith("_norm")]].sum(axis=1)
df = df.sort_values(by="Overall Score (↓)").reset_index(drop=True)
df.index += 1
df.index.name = "Rank"

print("\n🏆 GAJMA2.0 EVALUATION RESULTS 🏆")
print(df[["Manga", "Style", "Video", "LPIPS (↓)", "Warping Error (↓)", "Style Distance (↓)", "Tone EMD (↓)", "Overall Score (↓)"]].to_string())
df.to_csv(CSV_OUT, index=True)
print(f"\n💾 Full CSV saved to: {CSV_OUT}")

print("\n" + "=" * 60)
print("📈 AVERAGES BY MANGA (Copy to Overleaf Table)")
print("=" * 60)
# ✅ FIXED: Added the missing closing bracket ']' before .mean()
print(df.groupby("Manga")[["LPIPS (↓)", "Warping Error (↓)", "Style Distance (↓)", "Tone EMD (↓)"]].mean().round(4).to_string())

print("\n" + "=" * 60)
print("📈 AVERAGES BY STYLE (Copy to Overleaf Table)")
print("=" * 60)
print(df.groupby("Style")[["LPIPS (↓)", "Warping Error (↓)", "Style Distance (↓)", "Tone EMD (↓)"]].mean().round(4).to_string())