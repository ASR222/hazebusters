"""PyTorch Dataset + transforms over the load_traqid() table."""

import pandas as pd
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision.transforms import v2

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# Stored in every checkpoint so the backend can reproduce it exactly:
# RGB PIL image -> resize short side to 256 (bilinear, antialiased) ->
# centre crop 224 -> float in [0, 1] -> normalise with mean/std -> CHW.
EVAL_PREPROCESS = {
    "color": "RGB",
    "resize_short_side": 256,
    "interpolation": "bilinear",
    "antialias": True,
    "center_crop": 224,
    "scale": "divide by 255",
    "mean": list(IMAGENET_MEAN),
    "std": list(IMAGENET_STD),
    "layout": "NCHW",
}


def eval_transform(pre: dict = EVAL_PREPROCESS) -> v2.Compose:
    return v2.Compose([
        v2.ToImage(),
        v2.Resize(pre["resize_short_side"], interpolation=v2.InterpolationMode.BILINEAR, antialias=pre["antialias"]),
        v2.CenterCrop(pre["center_crop"]),
        v2.ToDtype(torch.float32, scale=True),
        v2.Normalize(pre["mean"], pre["std"]),
    ])


def train_transform(size: int = 224) -> v2.Compose:
    """Whole-scene crops + strong lighting jitter (time-of-day confound, CLAUDE.md §4).

    Brightness/hue are jittered hard; contrast/saturation only moderately
    because they are haze cues themselves.
    """
    return v2.Compose([
        v2.ToImage(),
        v2.RandomResizedCrop(size, scale=(0.6, 1.0), ratio=(3 / 4, 4 / 3), antialias=True),
        v2.RandomHorizontalFlip(),
        v2.RandomApply([v2.ColorJitter(brightness=0.5, contrast=0.3, saturation=0.3, hue=0.05)], p=0.8),
        v2.RandomApply([v2.GaussianBlur(5, sigma=(0.1, 1.0))], p=0.2),
        v2.RandomAdjustSharpness(2.0, p=0.2),
        v2.ToDtype(torch.float32, scale=True),
        v2.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


class TraqidImages(Dataset):
    """Rows of a load_traqid() frame -> (image tensor, band)."""

    def __init__(self, df: pd.DataFrame, transform):
        self.paths = df["path"].tolist()
        self.bands = df["band"].astype(int).tolist()
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, i: int):
        # TRAQID files are JPEGs named .png; PIL detects the format from content.
        with Image.open(self.paths[i]) as im:
            image = im.convert("RGB")
        return self.transform(image), self.bands[i]
