"""
tokenizer.py

Simple character/word-level tokenizer for the CoachLLM.
Falls back to a word-level approach if BPE is not available.
Supports save/load to JSON.
"""

import json
import re
from pathlib import Path
from typing import List


class BPETokenizer:
    """Word-level tokenizer with special tokens for the TrackFit Coach."""

    SPECIAL_TOKENS = ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<SEP>"]

    def __init__(self, vocab_size: int = 8000):
        self.vocab_size = vocab_size
        self.token_to_id: dict[str, int] = {}
        self.id_to_token: dict[int, str] = {}
        self._initialized = False

    def _tokenize_text(self, text: str) -> List[str]:
        """Split text into tokens (words + punctuation)."""
        # Lowercase and split on whitespace/punctuation, keeping punctuation
        text = text.lower().strip()
        tokens = re.findall(r"\w+|[^\w\s]", text)
        return tokens

    def build_vocab(self, texts: List[str]):
        """Build vocabulary from a list of text strings."""
        # Add special tokens first
        for i, tok in enumerate(self.SPECIAL_TOKENS):
            self.token_to_id[tok] = i
            self.id_to_token[i] = tok

        # Count word frequencies
        freq: dict[str, int] = {}
        for text in texts:
            for tok in self._tokenize_text(text):
                freq[tok] = freq.get(tok, 0) + 1

        # Take top vocab_size - len(special) tokens
        sorted_tokens = sorted(freq.items(), key=lambda x: -x[1])
        max_tokens = self.vocab_size - len(self.SPECIAL_TOKENS)

        for i, (tok, _) in enumerate(sorted_tokens[:max_tokens]):
            token_id = len(self.SPECIAL_TOKENS) + i
            self.token_to_id[tok] = token_id
            self.id_to_token[token_id] = tok

        self._initialized = True
        print(f"Tokenizer: {len(self.token_to_id)} tokens built")

    def encode(self, text: str) -> List[int]:
        """Encode text to token IDs."""
        tokens = self._tokenize_text(text)
        unk_id = self.token_to_id.get("<UNK>", 1)
        return [self.token_to_id.get(tok, unk_id) for tok in tokens]

    def decode(self, ids: List[int]) -> str:
        """Decode token IDs back to text."""
        tokens = []
        for id in ids:
            tok = self.id_to_token.get(id, "<UNK>")
            if tok == "<EOS>":
                break
            if tok not in self.SPECIAL_TOKENS:
                tokens.append(tok)
        return " ".join(tokens)

    def save(self, path: str | Path):
        """Save tokenizer to JSON."""
        data = {
            "vocab_size": self.vocab_size,
            "token_to_id": self.token_to_id,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Tokenizer saved to {path}")

    def load(self, path: str | Path):
        """Load tokenizer from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vocab_size = data["vocab_size"]
        self.token_to_id = data["token_to_id"]
        self.id_to_token = {v: k for k, v in self.token_to_id.items()}
        self._initialized = True
        print(f"Tokenizer loaded from {path} ({len(self.token_to_id)} tokens)")

    @property
    def actual_vocab_size(self) -> int:
        return len(self.token_to_id)
