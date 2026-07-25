"""Run tokenizer analysis from the standalone tokenizer_analysis folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from analyzer import compare_parallel_tokenizers, export_analysis, print_analysis_report  # noqa: E402


class TiktokenWrapper:
    """Small adapter so tiktoken can be compared with HF tokenizers."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        import tiktoken

        self.encoding = tiktoken.get_encoding(encoding_name)
        self.vocab_size = self.encoding.n_vocab

    def encode(self, text: str):
        return self.encoding.encode(text)


def clean_text(text: str) -> str:
    """Light whitespace cleanup for tokenizer comparison."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    blocks: List[str] = []
    buffer: List[str] = []

    for line in lines:
        if line:
            buffer.append(line)
        elif buffer:
            blocks.append(" ".join(buffer).strip())
            buffer = []

    if buffer:
        blocks.append(" ".join(buffer).strip())

    return "\n\n".join(blocks)


def _sort_key(path: Path):
    return int(path.stem) if path.stem.isdigit() else path.stem


def load_parallel_texts(english_dir: str, hindi_dir: str) -> Tuple[List[str], List[str]]:
    """Load matching English and Hindi .txt files for tokenizer analysis."""
    english_path = Path(english_dir)
    hindi_path = Path(hindi_dir)

    if not english_path.exists():
        raise FileNotFoundError(f"English directory not found: {english_path}")
    if not hindi_path.exists():
        raise FileNotFoundError(f"Hindi directory not found: {hindi_path}")

    english_texts: List[str] = []
    hindi_texts: List[str] = []

    for en_file in sorted(english_path.glob("*.txt"), key=_sort_key):
        hi_file = hindi_path / en_file.name
        if not hi_file.exists():
            print(f"Skipping {en_file.name}: Hindi file not found")
            continue

        english = clean_text(en_file.read_text(encoding="utf-8"))
        hindi = clean_text(hi_file.read_text(encoding="utf-8"))
        if english and hindi:
            english_texts.append(english)
            hindi_texts.append(hindi)

    print(f"Loaded {len(english_texts)} parallel document pairs")
    return english_texts, hindi_texts


def _load_hf_tokenizer(name: str, model_id: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    print(f"Loaded tokenizer: {name} ({model_id})")
    return tokenizer


def setup_tokenizers() -> Dict[str, object]:
    """Load tokenizer candidates. Failed candidates are skipped."""
    candidates = {
        "mBERT": ("hf", "bert-base-multilingual-cased"),
        "mBART-50": ("hf", "facebook/mbart-large-50"),
        "XLM-R": ("hf", "xlm-roberta-base"),
        "SUTRA": ("hf", "TwoAI/SUTRA-Tokenizer"),
        "IndicBERT": ("hf", "ai4bharat/indic-bert"),
        "Tiktoken-cl100k": ("tiktoken", "cl100k_base"),
    }
    tokenizers: Dict[str, object] = {}

    for display_name, (kind, model_id) in candidates.items():
        try:
            if kind == "hf":
                tokenizers[display_name] = _load_hf_tokenizer(display_name, model_id)
            else:
                tokenizers[display_name] = TiktokenWrapper(model_id)
                print(f"Loaded tokenizer: {display_name}")
        except Exception as exc:  # noqa: BLE001 - tokenizer availability varies by environment
            print(f"Skipping tokenizer {display_name}: {exc}")

    return tokenizers


def parse_args():
    project_dir = CURRENT_DIR.parent
    root_dir = project_dir.parent

    parser = argparse.ArgumentParser(description="Standalone tokenizer analysis")
    parser.add_argument("--english-dir", default=str(root_dir / "adalat_ai" / "english" / "clean"))
    parser.add_argument("--hindi-dir", default=str(root_dir / "adalat_ai" / "hindi" / "clean"))
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument(
        "--output",
        default=str(CURRENT_DIR / "results" / "tokenizer_analysis.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("\n" + "=" * 70)
    print("TOKENIZER ANALYSIS PIPELINE")
    print("=" * 70)
    print(f"English directory: {args.english_dir}")
    print(f"Hindi directory:   {args.hindi_dir}")

    english_texts, hindi_texts = load_parallel_texts(args.english_dir, args.hindi_dir)
    tokenizers = setup_tokenizers()
    if len(tokenizers) < 2:
        raise RuntimeError("Tokenizer analysis needs at least two available tokenizers")

    english_sample = english_texts[: args.sample_size]
    hindi_sample = hindi_texts[: args.sample_size]
    analysis = compare_parallel_tokenizers(english_sample, hindi_sample, tokenizers)
    print_analysis_report(analysis)
    export_analysis(analysis, args.output)

    print("\nTokenizer analysis finished.")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
