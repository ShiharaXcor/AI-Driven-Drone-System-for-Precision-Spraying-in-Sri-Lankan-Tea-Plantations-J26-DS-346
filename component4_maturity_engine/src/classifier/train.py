"""
Component 4 - Function 1: train and evaluate the tea maturity classifier.

Transfer learning with EfficientNet-B0 (or MobileNetV3) from timm:
  - split by source photo (no leakage), saved to splits.csv
  - class-weighted loss, because "young" has fewer examples
  - augmentation: flips, rotation, colour jitter (lighting variation)
  - early stopping on validation macro-F1
  - test-set report: accuracy, precision, recall, F1, confusion matrix, latency

Usage (from component4_maturity_engine/):
    python -m src.classifier.train --labels data/labels.csv --tiles data/processed/tiles \
        --model efficientnet_b0 --epochs 25 --out runs/effnet_b0
    python -m src.classifier.train ... --model mobilenetv3_large_100 --out runs/mobilenetv3
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import timm
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_recall_fscore_support)
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from src.classifier.dataset import (CLASSES, describe, group_split, load_labelled,
                                    save_split)

IMG_SIZE = 224
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)  # ImageNet statistics


def build_transforms(train: bool):
    if train:
        return transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),       # top-down view: no "up"
            transforms.RandomRotation(20),
            transforms.ColorJitter(0.3, 0.3, 0.2, 0.02),  # sun / shadow / overcast
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ])
    return transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


class TileDataset(Dataset):
    def __init__(self, items, train: bool):
        self.items, self.tf = items, build_transforms(train)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, label, _ = self.items[i]
        return self.tf(Image.open(path).convert("RGB")), label


def build_model(name: str, pretrained: bool = True):
    return timm.create_model(name, pretrained=pretrained, num_classes=len(CLASSES))


def class_weights(items) -> torch.Tensor:
    counts = np.bincount([lbl for _, lbl, _ in items], minlength=len(CLASSES)).astype(float)
    counts[counts == 0] = 1
    w = counts.sum() / (len(CLASSES) * counts)   # inverse frequency
    return torch.tensor(w, dtype=torch.float32)


@torch.no_grad()
def predict_loader(model, loader, device):
    model.eval()
    ys, ps, probs = [], [], []
    for x, y in loader:
        out = torch.softmax(model(x.to(device)), dim=1).cpu()
        probs.append(out)
        ps.extend(out.argmax(1).tolist())
        ys.extend(y.tolist())
    return np.array(ys), np.array(ps), torch.cat(probs).numpy()


@torch.no_grad()
def measure_latency(model, device, n: int = 50) -> float:
    """Average ms to classify one 224x224 tile."""
    model.eval()
    x = torch.randn(1, 3, IMG_SIZE, IMG_SIZE, device=device)
    for _ in range(5):
        model(x)
    if device.type == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(n):
        model(x)
    if device.type == "cuda":
        torch.cuda.synchronize()
    return (time.perf_counter() - t0) / n * 1000


def save_confusion_matrix(cm, out_png: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.imshow(cm, cmap="Greens")
    ax.set_xticks(range(len(CLASSES)), CLASSES)
    ax.set_yticks(range(len(CLASSES)), CLASSES)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def save_training_curves(history, out_png: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ep = [h["epoch"] for h in history]
    fig, ax1 = plt.subplots(figsize=(6, 4))
    ax1.plot(ep, [h["train_loss"] for h in history], "o-", color="tab:red", label="train loss")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Train loss")
    ax2 = ax1.twinx()
    ax2.plot(ep, [h["val_acc"] for h in history], "s-", color="tab:blue", label="val accuracy")
    ax2.plot(ep, [h["val_macro_f1"] for h in history], "^-", color="tab:green", label="val macro-F1")
    ax2.set_ylabel("Validation score")
    ax2.set_ylim(0, 1)
    fig.legend(loc="lower right", bbox_to_anchor=(0.88, 0.15), fontsize=8)
    ax1.set_title(title)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


def train(args):
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    items = load_labelled(Path(args.labels), Path(args.tiles))
    split = group_split(items, seed=args.seed)
    save_split(split, out / "splits.csv")
    print(f"Device: {device}\nData split (by source photo):\n{describe(split)}")

    loaders = {
        "train": DataLoader(TileDataset(split["train"], True), args.batch, shuffle=True,
                            num_workers=args.workers),
        "val": DataLoader(TileDataset(split["val"], False), args.batch, num_workers=args.workers),
        "test": DataLoader(TileDataset(split["test"], False), args.batch, num_workers=args.workers),
    }

    model = build_model(args.model, pretrained=not args.no_pretrained).to(device)
    weights = class_weights(split["train"])
    criterion = nn.CrossEntropyLoss(weight=weights.to(device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    print(f"Class weights: {dict(zip(CLASSES, weights.round(decimals=2).tolist()))}")

    history, best_f1, bad_epochs = [], -1.0, 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        for x, y in loaders["train"]:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
            running += loss.item() * x.size(0)
        scheduler.step()

        yv, pv, _ = predict_loader(model, loaders["val"], device)
        val_f1 = f1_score(yv, pv, average="macro", zero_division=0)
        val_acc = accuracy_score(yv, pv)
        train_loss = running / len(split["train"])
        history.append({"epoch": epoch, "train_loss": round(train_loss, 4),
                        "val_acc": round(val_acc, 4), "val_macro_f1": round(val_f1, 4)})
        print(f"epoch {epoch:>2}  loss {train_loss:.4f}  val_acc {val_acc:.3f}  val_F1 {val_f1:.3f}")

        if val_f1 > best_f1:
            best_f1, bad_epochs = val_f1, 0
            torch.save({"model": args.model, "classes": CLASSES,
                        "state_dict": model.state_dict()}, out / "best.pt")
        else:
            bad_epochs += 1
            if bad_epochs >= args.patience:
                print(f"Early stopping (no val improvement for {args.patience} epochs)")
                break

    # ---------------------------------------------------------- test evaluation
    ckpt = torch.load(out / "best.pt", map_location=device)
    model.load_state_dict(ckpt["state_dict"])
    yt, pt, _ = predict_loader(model, loaders["test"], device)
    prec, rec, f1, support = precision_recall_fscore_support(
        yt, pt, labels=range(len(CLASSES)), zero_division=0)
    cm = confusion_matrix(yt, pt, labels=range(len(CLASSES)))
    latency = measure_latency(model, device)

    results = {
        "model": args.model,
        "device": str(device),
        "test_tiles": int(len(yt)),
        "accuracy": round(float(accuracy_score(yt, pt)), 4),
        "macro_precision": round(float(prec.mean()), 4),
        "macro_recall": round(float(rec.mean()), 4),
        "macro_f1": round(float(f1.mean()), 4),
        "per_class": {c: {"precision": round(float(prec[i]), 4), "recall": round(float(rec[i]), 4),
                          "f1": round(float(f1[i]), 4), "support": int(support[i])}
                      for i, c in enumerate(CLASSES)},
        "confusion_matrix": cm.tolist(),
        "latency_ms_per_tile": round(latency, 2),
        "best_val_macro_f1": round(best_f1, 4),
        "history": history,
    }
    (out / "results.json").write_text(json.dumps(results, indent=2))
    report = classification_report(yt, pt, labels=range(len(CLASSES)), target_names=CLASSES,
                                   zero_division=0)
    (out / "classification_report.txt").write_text(report)
    save_confusion_matrix(cm, out / "confusion_matrix.png", f"{args.model} - test set")
    save_training_curves(history, out / "training_curves.png", f"{args.model} - training")

    print("\nTEST RESULTS\n" + report)
    print(f"Confusion matrix (rows=actual, cols=predicted, order {CLASSES}):\n{cm}")
    print(f"Latency: {latency:.1f} ms per tile on {device}")
    print(f"Saved model and results to {out}/")
    return results


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Train C4 tea maturity classifier")
    p.add_argument("--labels", required=True)
    p.add_argument("--tiles", required=True)
    p.add_argument("--model", default="efficientnet_b0",
                   help="timm name, e.g. efficientnet_b0 or mobilenetv3_large_100")
    p.add_argument("--out", default="runs/effnet_b0")
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--patience", type=int, default=6)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-pretrained", action="store_true",
                   help="train from scratch (only for offline testing)")
    return p.parse_args(argv)


if __name__ == "__main__":
    train(parse_args())
