import os
import cv2
import numpy as np
import torch
import lpips
from PIL import Image
from scipy.stats import wasserstein_distance
from skimage.metrics import structural_similarity as ssim
import csv
import glob

# -----------------------------------------------------------------------------
# 1. LPIPS (Learned Perceptual Image Patch Similarity)
# Measures perceptual similarity between consecutive frames.
# Lower is better.
# -----------------------------------------------------------------------------
def load_lpips_model():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # VGG-based LPIPS is standard for this type of evaluation
    loss_fn = lpips.LPIPS(net='vgg').to(device)
    return loss_fn, device

def calculate_lpips_for_video(video_path):
    """
    Calculates average LPIPS between all consecutive frame pairs in a video.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    loss_fn, device = load_lpips_model()
    lpips_scores = []
    
    prev_frame = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if prev_frame is not None:
            # Convert BGR (OpenCV) to RGB (PIL/LPIPS expects)
            prev_rgb = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2RGB)
            curr_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Images then to Tensors
            img1_pil = Image.fromarray(prev_rgb)
            img2_pil = Image.fromarray(curr_rgb)
            
            # LPIPS requires images normalized to [-1, 1]
            transform = lpips.im2tensor
            img1_t = transform(img1_pil).unsqueeze(0).to(device)
            img2_t = transform(img2_pil).unsqueeze(0).to(device)
            
            with torch.no_grad():
                score = loss_fn.forward(img1_t, img2_t).item()
            lpips_scores.append(score)
        
        prev_frame = frame
        
    cap.release()
    
    if not lpips_scores:
        return 0.0
    return np.mean(lpips_scores)

# -----------------------------------------------------------------------------
# 2. Warping Error
# Measures motion consistency. 
# Implementation: We use Optical Flow (Farneback) to warp Frame t-1 to Frame t,
# then compare the warped image with the actual Frame t using MSE/SSIM.
# Lower error means the motion predicted by flow matches the actual change well.
# -----------------------------------------------------------------------------
def calculate_warping_error_for_video(video_path):
    """
    Calculates average warping error using Farneback Optical Flow.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    errors = []
    prev_gray = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_gray is not None:
            # Calculate Optical Flow from prev_gray to gray
            # Farneback parameters can be tuned
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 
                                                pyr_scale=0.5, levels=3, winsize=15,
                                                iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
            
            # Warp previous frame using the flow field
            h, w = gray.shape
            flow_x = flow[:, :, 0]
            flow_y = flow[:, :, 1]
            
            # Create meshgrid for remapping
            x, y = np.meshgrid(np.arange(w), np.arange(h))
            dx = x + flow_x
            dy = y + flow_y
            
            # Remap previous frame to current frame's coordinate system
            warped_prev = cv2.remap(prev_gray, dx.astype(np.float32), dy.astype(np.float32), 
                                    interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
            
            # Calculate difference between warped previous frame and actual current frame
            # Using Mean Squared Error (MSE)
            mse = np.mean((gray - warped_prev) ** 2)
            errors.append(mse)
            
        prev_gray = gray
        
    cap.release()
    
    if not errors:
        return 0.0
    return np.mean(errors)

# -----------------------------------------------------------------------------
# 3. Style Distance
# Measures consistency of artistic style.
# Implementation: Compare Gram Matrices of feature maps from a pre-trained VGG network.
# Lower distance means style is more consistent.
# -----------------------------------------------------------------------------
def get_vgg_features(image_tensor):
    """
    Extracts features from VGG16 conv layers.
    image_tensor: [1, 3, H, W] normalized to [0, 1] or [-1, 1] depending on preprocessing
    """
    # Load pretrained VGG16 features only
    try:
        import torchvision.models as models
        vgg = models.vgg16(weights=models.VGG16_Weights.DEFAULT).features
    except Exception:
        # Fallback if weights loading fails due to internet/connection
        vgg = models.vgg16(pretrained=True).features
        
    vgg.eval()
    
    # Pass through first few convolutional blocks
    # Block 1: conv1_1 to conv1_2
    # Block 2: conv2_1 to conv2_2
    # ... we can take multiple blocks for better style representation
    
    features = []
    x = image_tensor
    
    # Define which layers to extract (indices in vgg.features)
    # 0: Conv2d, 1: ReLU, 2: Conv2d, 3: ReLU, 4: MaxPool2d
    # 5: Conv2d, 6: ReLU, 7: Conv2d, 8: ReLU, 9: MaxPool2d
    layer_indices = [4, 9, 18, 27, 36] 
    
    for i, module in enumerate(vgg):
        x = module(x)
        if i in layer_indices:
            features.append(x)
            
    return features

def gram_matrix(y):
    (b, ch, h, w) = y.size()
    features = y.view(b, ch, w * h)
    features_t = features.transpose(1, 2)
    gram = torch.bmm(features, features_t)
    return gram / (ch * h * w)

def calculate_style_distance_for_video(video_path):
    """
    Calculates average style distance between consecutive frames using VGG Gram matrices.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
        
    distances = []
    prev_features = None
    
    # Preprocessing mean/std for VGG
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Convert to tensor
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        
        # Normalize to [0, 1]
        tensor_img = torch.from_numpy(np.array(pil_img)).permute(2, 0, 1).float() / 255.0
        tensor_img = tensor_img.unsqueeze(0) # [1, 3, H, W]
        
        # Normalize with ImageNet stats
        tensor_norm = (tensor_img - mean) / std
        
        # Get features
        features = get_vgg_features(tensor_norm)
        
        if prev_features is not None:
            total_dist = 0.0
            for feat_prev, feat_curr in zip(prev_features, features):
                gram_prev = gram_matrix(feat_prev)
                gram_curr = gram_matrix(feat_curr)
                
                # Euclidean distance between Gram matrices
                dist = torch.norm(gram_prev - gram_curr)
                total_dist += dist.item()
            
            # Average over layers
            avg_dist = total_dist / len(features)
            distances.append(avg_dist)
            
        prev_features = features
        
    cap.release()
    
    if not distances:
        return 0.0
    return np.mean(distances)

# -----------------------------------------------------------------------------
# 4. Tone Consistency (EMD)
# Uses Earth Mover's Distance on tone histograms.
# Lower values indicate more stable lighting/tone.
# -----------------------------------------------------------------------------
def calculate_tone_consistency_emd_for_video(video_path):
    """
    Calculates average EMD on grayscale histograms between consecutive frames.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
        
    emd_scores = []
    prev_hist = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Flatten histogram
        hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 256), density=True)
        
        if prev_hist is not None:
            # Calculate Wasserstein Distance (EMD for 1D histograms)
            emd = wasserstein_distance(prev_hist, hist)
            emd_scores.append(emd)
            
        prev_hist = hist
        
    cap.release()
    
    if not emd_scores:
        return 0.0
    return np.mean(emd_scores)

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # CONFIGURATION
    VIDEO_PATH = "Manga109/final_videos/TetsuSan_Page1.mp4" # Update this path
    OUTPUT_CSV = "metrics_results.csv"
    
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: Video file not found at {VIDEO_PATH}")
        exit(1)

    print(f"Calculating metrics for: {VIDEO_PATH}")
    
    results = {}
    
    try:
        print("1. Calculating LPIPS...")
        results['LPIPS'] = calculate_lpips_for_video(VIDEO_PATH)
        print(f"   LPIPS: {results['LPIPS']:.6f}")
        
        print("2. Calculating Warping Error...")
        results['Warping_Error'] = calculate_warping_error_for_video(VIDEO_PATH)
        print(f"   Warping Error: {results['Warping_Error']:.6f}")
        
        print("3. Calculating Style Distance...")
        results['Style_Distance'] = calculate_style_distance_for_video(VIDEO_PATH)
        print(f"   Style Distance: {results['Style_Distance']:.6f}")
        
        print("4. Calculating Tone Consistency (EMD)...")
        results['Tone_Consistency_EMD'] = calculate_tone_consistency_emd_for_video(VIDEO_PATH)
        print(f"   Tone Consistency (EMD): {results['Tone_Consistency_EMD']:.6f}")
        
        # Save to CSV
        with open(OUTPUT_CSV, mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results.keys())
            writer.writeheader()
            writer.writerow(results)
            
        print(f"\nResults saved to {OUTPUT_CSV}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()