"""
train_coach.py

Trains the CoachLLM transformer on fitness/nutrition text data.

Usage:
    python -m training.train_coach --data_dir data/coach_text --epochs 30 --batch_size 8
"""

import argparse
import os
import random
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.coach_llm import CoachLLM, CoachConfig
from models.tokenizer import BPETokenizer


class TextDataset(Dataset):
    """Tokenized text dataset that creates fixed-length sequences."""

    def __init__(self, tokens: list[int], block_size: int):
        self.block_size = block_size
        self.tokens = tokens

    def __len__(self):
        return len(self.tokens) - self.block_size - 1

    def __getitem__(self, idx):
        chunk = self.tokens[idx : idx + self.block_size + 1]
        x = torch.tensor(chunk[:-1], dtype=torch.long)
        y = torch.tensor(chunk[1:], dtype=torch.long)
        return x, y


def load_training_data(data_dir: str) -> str:
    """Load all .txt files from data_dir and concatenate."""
    texts = []
    data_path = Path(data_dir)
    for txt_file in sorted(data_path.glob("*.txt")):
        print(f"  Loading {txt_file.name}")
        with open(txt_file, "r", encoding="utf-8") as f:
            texts.append(f.read())
    return "\n".join(texts)


def train():
    parser = argparse.ArgumentParser(description="Train CoachLLM")
    parser.add_argument("--data_dir", type=str, default="data/coach_text")
    parser.add_argument("--output_dir", type=str, default="data")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--vocab_size", type=int, default=8000)
    parser.add_argument("--block_size", type=int, default=256)
    parser.add_argument("--n_embed", type=int, default=256)
    parser.add_argument("--n_head", type=int, default=8)
    parser.add_argument("--n_layer", type=int, default=6)
    parser.add_argument("--dropout", type=float, default=0.1)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # 1. Load training data
    print("\nLoading training data...")
    raw_text = load_training_data(args.data_dir)
    print(f"Total text length: {len(raw_text):,} characters")

    # 2. Build tokenizer
    print("\nBuilding tokenizer...")
    tokenizer = BPETokenizer(vocab_size=args.vocab_size)
    # Split into lines for vocab building
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    tokenizer.build_vocab(lines)

    # 3. Tokenize all text
    print("\nTokenizing...")
    all_tokens = tokenizer.encode(raw_text)
    print(f"Total tokens: {len(all_tokens):,}")

    # 4. Create dataset
    dataset = TextDataset(all_tokens, args.block_size)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    print(f"Dataset size: {len(dataset):,} sequences")

    # 5. Create model
    config = CoachConfig(
        vocab_size=tokenizer.actual_vocab_size,
        block_size=args.block_size,
        n_embed=args.n_embed,
        n_head=args.n_head,
        n_layer=args.n_layer,
        dropout=args.dropout,
    )
    model = CoachLLM(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    # 6. Training loop
    print(f"\nTraining for {args.epochs} epochs...")
    os.makedirs(args.output_dir, exist_ok=True)

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0
        num_batches = 0

        for x, y in dataloader:
            x, y = x.to(device), y.to(device)
            logits, loss = model(x, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        avg_loss = total_loss / max(num_batches, 1)
        print(f"  Epoch {epoch+1}/{args.epochs}  loss={avg_loss:.4f}")

    # 7. Save model and tokenizer
    model_path = Path(args.output_dir) / "coach_model.pt"
    tokenizer_path = Path(args.output_dir) / "tokenizer.json"
    config_path = Path(args.output_dir) / "coach_config.json"

    torch.save(model.state_dict(), model_path)
    tokenizer.save(tokenizer_path)

    import json
    with open(config_path, "w") as f:
        json.dump({
            "vocab_size": config.vocab_size,
            "block_size": config.block_size,
            "n_embed": config.n_embed,
            "n_head": config.n_head,
            "n_layer": config.n_layer,
            "dropout": config.dropout,
        }, f, indent=2)

    print(f"\nDone! Saved:")
    print(f"  Model:     {model_path}")
    print(f"  Tokenizer: {tokenizer_path}")
    print(f"  Config:    {config_path}")


if __name__ == "__main__":
    train()
