from pathlib import Path
from torch.utils.data import Dataset
from PIL import Image


class LoRADataset(Dataset):
    def __init__(self, manifest_path, image_root=None, transform=None):
        self.manifest_path = Path(manifest_path)
        self.image_root = Path(image_root) if image_root else None
        self.transform = transform
        self.samples = self._load_manifest()

    def _load_manifest(self):
        if not self.manifest_path.exists():
            return []
        with self.manifest_path.open("r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path = Path(self.samples[idx])
        if self.image_root and not path.is_absolute():
            path = self.image_root / path
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image
