"""Load the court corpus and align English-Hindi legal paragraphs."""

from __future__ import annotations

import json
import random
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple


Record = Dict[str, object]
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
INT_NO = r"[0-9०-९]{1,3}"
DECIMAL_NO = rf"{INT_NO}\.{INT_NO}"
START_NUMBER_RE = re.compile(
    rf"^\s*(?P<number>{DECIMAL_NO}|{INT_NO})(?:[\.)\u0964])?\s+"
)
INLINE_NUMBER_RE = re.compile(
    rf'(?P<prefix>(?:^|(?<=[\.\!\?\u0964])\s+|(?<=["\u201d\u2019\)])\s+))'
    rf"(?P<number>{DECIMAL_NO}|{INT_NO})[\.)\u0964]\s+"
    rf'(?=[A-Z"“\(\u0900-\u097F])'
)


def _sort_key(path: Path):
    return int(path.stem) if path.stem.isdigit() else path.stem


def clean_legal_text(text: str) -> str:
    """Normalize whitespace and join wrapped lines inside each paragraph block."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    blocks: List[str] = []
    buffer: List[str] = []

    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            buffer.append(line)
        elif buffer:
            blocks.append(" ".join(buffer).strip())
            buffer = []

    if buffer:
        blocks.append(" ".join(buffer).strip())

    return "\n\n".join(blocks)


def load_parallel_texts(english_dir: str, hindi_dir: str) -> Tuple[List[str], List[str]]:
    """Load matching English and Hindi .txt files."""
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

        english = clean_legal_text(en_file.read_text(encoding="utf-8"))
        hindi = clean_legal_text(hi_file.read_text(encoding="utf-8"))
        if english and hindi:
            english_texts.append(english)
            hindi_texts.append(hindi)

    print(f"Loaded {len(english_texts)} parallel document pairs")
    return english_texts, hindi_texts


def split_paragraph_blocks(text: str) -> List[str]:
    """Return cleaned paragraph blocks."""
    cleaned = clean_legal_text(text)
    return [block for block in cleaned.split("\n\n") if block.strip()]


def _marker_number(match: re.Match) -> str:
    return match.group("number").translate(DEVANAGARI_DIGITS)


def _leading_number(text: str) -> str:
    match = START_NUMBER_RE.match(text)
    return _marker_number(match) if match else ""


def _prefix_start(match: re.Match) -> int:
    return match.start("prefix") if "prefix" in match.re.groupindex else 0


def _add_segment(segments: List[Dict[str, str]], number: str, text: str) -> None:
    text = " ".join(text.split())
    if not text:
        return

    if number:
        segments.append({"number": number, "text": text})
        return

    if segments:
        segments[-1]["text"] = f"{segments[-1]['text']}\n\n{text}"
    else:
        segments.append({"number": "", "text": text})


def split_legal_paragraphs(text: str) -> List[Dict[str, str]]:
    """Split text into legal paragraph segments."""
    segments: List[Dict[str, str]] = []

    for block in split_paragraph_blocks(text):
        matches = list(INLINE_NUMBER_RE.finditer(block))
        start_match = START_NUMBER_RE.match(block)

        if start_match and (
            not matches or matches[0].start("number") != start_match.start("number")
        ):
            matches.insert(0, start_match)

        if not matches:
            _add_segment(segments, "", block)
            continue

        first_prefix = _prefix_start(matches[0])
        if first_prefix > 0:
            prefix_text = " ".join(block[:first_prefix].split())
            if prefix_text:
                _add_segment(segments, "", prefix_text)

        for index, match in enumerate(matches):
            start = match.start("number")
            if index + 1 < len(matches):
                next_match = matches[index + 1]
                end = _prefix_start(next_match) or next_match.start("number")
            else:
                end = len(block)

            piece = " ".join(block[start:end].split())
            if piece:
                _add_segment(segments, _marker_number(match), piece)

    return segments


def _should_use_order_alignment(english_blocks: List[str], hindi_blocks: List[str]) -> bool:
    if not english_blocks or not hindi_blocks:
        return False

    ratio = min(len(english_blocks), len(hindi_blocks)) / max(len(english_blocks), len(hindi_blocks))
    if ratio < 0.8:
        return False

    both_numbered = 0
    mismatches = 0
    for english_block, hindi_block in zip(english_blocks, hindi_blocks):
        english_no = _leading_number(english_block)
        hindi_no = _leading_number(hindi_block)
        if english_no and hindi_no:
            both_numbered += 1
            if english_no != hindi_no:
                mismatches += 1

    return both_numbered >= 3 and mismatches == 0


def _align_by_order(
    english_blocks: List[str],
    hindi_blocks: List[str],
    doc_id: str,
    split: str,
    method: str,
) -> List[Record]:
    records: List[Record] = []
    for index, (english_block, hindi_block) in enumerate(zip(english_blocks, hindi_blocks)):
        english_no = _leading_number(english_block)
        hindi_no = _leading_number(hindi_block)
        paragraph_no = english_no if english_no and english_no == hindi_no else ""
        records.append(
            {
                "doc_id": doc_id,
                "split": split,
                "segment_id": index,
                "paragraph_no": paragraph_no,
                "english": english_block,
                "hindi": hindi_block,
                "alignment_method": method,
            }
        )
    return records


def align_paragraphs(english: str, hindi: str, doc_id: str, split: str) -> List[Record]:
    """Align by ordered paragraph numbers, with safe block-order fallback."""
    english_blocks = split_paragraph_blocks(english)
    hindi_blocks = split_paragraph_blocks(hindi)

    if _should_use_order_alignment(english_blocks, hindi_blocks):
        return _align_by_order(
            english_blocks,
            hindi_blocks,
            doc_id,
            split,
            method="paragraph_order_blocks",
        )

    english_segments = split_legal_paragraphs(english)
    hindi_segments = split_legal_paragraphs(hindi)
    english_numbered = [
        (index, segment) for index, segment in enumerate(english_segments) if segment["number"]
    ]
    hindi_numbered = [
        (index, segment) for index, segment in enumerate(hindi_segments) if segment["number"]
    ]

    if english_numbered and hindi_numbered:
        english_numbers = [segment["number"] for _, segment in english_numbered]
        hindi_numbers = [segment["number"] for _, segment in hindi_numbered]
        matcher = SequenceMatcher(a=english_numbers, b=hindi_numbers, autojunk=False)

        records: List[Record] = []
        for match_block in matcher.get_matching_blocks():
            for offset in range(match_block.size):
                english_index, english_segment = english_numbered[match_block.a + offset]
                hindi_index, hindi_segment = hindi_numbered[match_block.b + offset]
                records.append(
                    {
                        "doc_id": doc_id,
                        "split": split,
                        "segment_id": len(records),
                        "paragraph_no": english_segment["number"],
                        "english": english_segments[english_index]["text"],
                        "hindi": hindi_segments[hindi_index]["text"],
                        "alignment_method": "paragraph_number_lcs",
                    }
                )
        if records:
            return records

    return _align_by_order(
        [segment["text"] for segment in english_segments],
        [segment["text"] for segment in hindi_segments],
        doc_id,
        split,
        method="paragraph_order_fallback",
    )


def create_data_split(
    english_texts: List[str],
    hindi_texts: List[str],
    train_ratio: float = 0.8,
    dev_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: int = 42,
) -> Dict[str, object]:
    """Split documents, then align paragraphs inside each split."""
    if len(english_texts) != len(hindi_texts):
        raise ValueError("English and Hindi text lists must have the same length")
    if not english_texts:
        raise ValueError("No text pairs were provided")
    if abs((train_ratio + dev_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError("Split ratios must add up to 1.0")

    documents = [
        {"doc_id": str(index + 1), "english": english, "hindi": hindi}
        for index, (english, hindi) in enumerate(zip(english_texts, hindi_texts))
    ]
    random.Random(random_seed).shuffle(documents)

    train_end = int(len(documents) * train_ratio)
    dev_end = train_end + int(len(documents) * dev_ratio)
    split_docs = {
        "train": documents[:train_end],
        "dev": documents[train_end:dev_end],
        "test": documents[dev_end:],
    }

    split_data: Dict[str, object] = {}
    for split, docs in split_docs.items():
        records: List[Record] = []
        for doc in docs:
            records.extend(align_paragraphs(doc["english"], doc["hindi"], doc["doc_id"], split))
        split_data[split] = records

    split_data["split_info"] = {
        "total_documents": len(documents),
        "train_docs": len(split_docs["train"]),
        "dev_docs": len(split_docs["dev"]),
        "test_docs": len(split_docs["test"]),
        "train_records": len(split_data["train"]),
        "dev_records": len(split_data["dev"]),
        "test_records": len(split_data["test"]),
        "random_seed": random_seed,
        "alignment_method": "paragraph_number_lcs_or_block_order",
    }
    return split_data


def save_splits_to_jsonl(split_data: Dict[str, object], output_dir: str) -> None:
    """Save train/dev/test records and split metadata."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for split in ("train", "dev", "test"):
        records = split_data[split]
        with (output_path / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Saved {len(records)} examples to {output_path / f'{split}.jsonl'}")

    with (output_path / "split_info.json").open("w", encoding="utf-8") as handle:
        json.dump(split_data["split_info"], handle, indent=2, ensure_ascii=False)


def load_jsonl_split(filepath: str) -> List[Record]:
    """Load a JSONL split as records."""
    records: List[Record] = []
    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def record_to_pair(record: object) -> Tuple[str, str]:
    """Return (english, hindi) from a split record or tuple."""
    if isinstance(record, dict):
        return str(record["english"]), str(record["hindi"])
    english, hindi = record  # type: ignore[misc]
    return str(english), str(hindi)


def print_dataset_summary(split_data: Dict[str, object]) -> None:
    """Print split counts."""
    info = split_data["split_info"]
    print("\n" + "=" * 70)
    print("DATASET SUMMARY")
    print("=" * 70)
    print(f"Documents: {info['total_documents']}")
    print(f"Train: {info['train_docs']} docs / {info['train_records']} records")
    print(f"Dev:   {info['dev_docs']} docs / {info['dev_records']} records")
    print(f"Test:  {info['test_docs']} docs / {info['test_records']} records")
    print(f"Alignment method: {info['alignment_method']}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("Data loader module. Import it from main_pipeline.py or quick_start.py.")
