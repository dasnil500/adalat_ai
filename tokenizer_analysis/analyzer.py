"""
Tokenizer efficiency analysis for English-Hindi legal text.

This package is intentionally separate from src/, which contains data loading,
training, and evaluation code.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Dict, List


def _encode(tokenizer, text: str) -> List[object]:
    if hasattr(tokenizer, "encode"):
        try:
            return list(tokenizer.encode(text, add_special_tokens=False))
        except TypeError:
            return list(tokenizer.encode(text))
    if hasattr(tokenizer, "tokenize"):
        return list(tokenizer.tokenize(text))
    raise TypeError("Tokenizer must provide encode() or tokenize()")


def analyze_tokenizer(tokenizer, text: str, tokenizer_name: str) -> Dict[str, object]:
    """Analyze a tokenizer on one text sample."""
    try:
        tokens = _encode(tokenizer, text)
        token_count = len(tokens)
        word_count = len(text.split())
        char_count = len(text)

        return {
            "tokenizer": tokenizer_name,
            "token_count": token_count,
            "word_count": word_count,
            "char_count": char_count,
            "tokens_per_word": round(token_count / word_count, 4) if word_count else 0,
            "chars_per_token": round(char_count / token_count, 4) if token_count else 0,
            "tokens_per_1k_chars": round(token_count / max(char_count, 1) * 1000, 2),
            "vocab_size": getattr(tokenizer, "vocab_size", "N/A"),
        }
    except Exception as exc:  # noqa: BLE001 - report tokenizer-specific failures
        return {"tokenizer": tokenizer_name, "error": str(exc)}


def _mean(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _median(values: List[float]) -> float:
    return round(statistics.median(values), 4) if values else 0.0


def compare_tokenizers(texts: List[str], tokenizers_dict: Dict[str, object]) -> Dict[str, object]:
    """Compare tokenizers across a corpus or sample."""
    results: Dict[str, object] = {"total_texts": len(texts), "tokenizers": {}}

    for tokenizer_name, tokenizer in tokenizers_dict.items():
        sample_stats = []
        errors = []

        for text in texts:
            stat = analyze_tokenizer(tokenizer, text, tokenizer_name)
            if "error" in stat:
                errors.append(stat["error"])
            else:
                sample_stats.append(stat)

        if not sample_stats:
            results["tokenizers"][tokenizer_name] = {
                "error": errors[0] if errors else "No samples processed"
            }
            continue

        tokens_per_word = [float(stat["tokens_per_word"]) for stat in sample_stats]
        chars_per_token = [float(stat["chars_per_token"]) for stat in sample_stats]
        tokens_per_1k_chars = [float(stat["tokens_per_1k_chars"]) for stat in sample_stats]

        results["tokenizers"][tokenizer_name] = {
            "samples_processed": len(sample_stats),
            "avg_tokens_per_word": _mean(tokens_per_word),
            "median_tokens_per_word": _median(tokens_per_word),
            "avg_chars_per_token": _mean(chars_per_token),
            "avg_tokens_per_1k_chars": _mean(tokens_per_1k_chars),
            "total_tokens": sum(int(stat["token_count"]) for stat in sample_stats),
            "total_words": sum(int(stat["word_count"]) for stat in sample_stats),
            "total_chars": sum(int(stat["char_count"]) for stat in sample_stats),
            "vocab_size": sample_stats[0].get("vocab_size", "N/A"),
        }

    return results


def compare_parallel_tokenizers(
    english_texts: List[str],
    hindi_texts: List[str],
    tokenizers_dict: Dict[str, object],
) -> Dict[str, object]:
    """Compare tokenizers on both sides of the parallel corpus."""
    english_analysis = compare_tokenizers(english_texts, tokenizers_dict)
    hindi_analysis = compare_tokenizers(hindi_texts, tokenizers_dict)
    overhead: Dict[str, object] = {}

    for tokenizer_name, hi_stats in hindi_analysis["tokenizers"].items():
        en_stats = english_analysis["tokenizers"].get(tokenizer_name, {})
        if "error" in hi_stats or "error" in en_stats:
            continue
        en_tpw = float(en_stats["avg_tokens_per_word"])
        hi_tpw = float(hi_stats["avg_tokens_per_word"])
        overhead[tokenizer_name] = {
            "english_avg_tokens_per_word": en_tpw,
            "hindi_avg_tokens_per_word": hi_tpw,
            "hindi_overhead_vs_english": round(hi_tpw / en_tpw, 4) if en_tpw else None,
            "hindi_total_tokens": hi_stats["total_tokens"],
            "english_total_tokens": en_stats["total_tokens"],
        }

    recommendation = None
    if overhead:
        recommendation = min(
            overhead.items(),
            key=lambda item: item[1]["hindi_avg_tokens_per_word"],
        )[0]

    return {
        "english_analysis": english_analysis,
        "hindi_analysis": hindi_analysis,
        "parallel_overhead": overhead,
        "recommended_tokenizer_by_hindi_tpw": recommendation,
    }


def export_analysis(analysis: Dict[str, object], output_path: str) -> None:
    """Export analysis results to JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(analysis, handle, indent=2, ensure_ascii=False)
    print(f"Analysis exported to {output_path}")


def print_analysis_report(analysis: Dict[str, object]) -> None:
    """Print a compact tokenizer analysis report."""
    print("\n" + "=" * 70)
    print("TOKENIZER ANALYSIS REPORT")
    print("=" * 70)

    if "parallel_overhead" in analysis:
        overhead = analysis.get("parallel_overhead", {})
        if not overhead:
            print("No tokenizer completed both English and Hindi analysis.")
        for name, stats in overhead.items():
            print(
                f"{name}: EN {stats['english_avg_tokens_per_word']} tokens/word, "
                f"HI {stats['hindi_avg_tokens_per_word']} tokens/word, "
                f"HI/EN overhead {stats['hindi_overhead_vs_english']}"
            )
        print(f"Recommended by Hindi tokens/word: {analysis.get('recommended_tokenizer_by_hindi_tpw')}")
        print("=" * 70 + "\n")
        return

    print(f"Total texts analyzed: {analysis.get('total_texts', 0)}")
    for tokenizer_name, stats in analysis.get("tokenizers", {}).items():
        if "error" in stats:
            print(f"{tokenizer_name}: ERROR - {stats['error']}")
            continue
        print(
            f"{tokenizer_name}: avg={stats['avg_tokens_per_word']} tokens/word, "
            f"median={stats['median_tokens_per_word']}, "
            f"tokens={stats['total_tokens']}"
        )
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("Tokenizer analysis module. Import from tokenizer_analysis.")
