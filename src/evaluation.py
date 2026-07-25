"""
Automatic and qualitative evaluation for Hindi legal translation.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence


LEGAL_TERM_GROUPS = {
    "appeal": {
        "en": ["appeal", "appellant"],
        "hi": ["अपील", "अपीलार्थी"],
    },
    "respondent": {
        "en": ["respondent"],
        "hi": ["प्रतिवादी", "उत्तरदाता"],
    },
    "petitioner": {
        "en": ["petitioner", "petition"],
        "hi": ["याचिकाकर्ता", "याचिका"],
    },
    "court": {
        "en": ["court", "high court"],
        "hi": ["न्यायालय", "उच्च न्यायालय", "अदालत"],
    },
    "judgment": {
        "en": ["judgment", "order", "decision"],
        "hi": ["निर्णय", "आदेश", "फैसला"],
    },
    "section": {
        "en": ["section"],
        "hi": ["धारा"],
    },
    "act": {
        "en": ["act"],
        "hi": ["अधिनियम"],
    },
    "dismissed": {
        "en": ["dismissed", "rejected"],
        "hi": ["खारिज", "अस्वीकार"],
    },
}


def get_ngrams(tokens: Sequence[str], n: int) -> Dict[tuple, int]:
    """Extract n-grams from tokenized text."""
    ngrams: Dict[tuple, int] = defaultdict(int)
    for index in range(len(tokens) - n + 1):
        ngrams[tuple(tokens[index : index + n])] += 1
    return ngrams


def compute_bleu(reference: str, hypothesis: str, max_n: int = 4) -> Dict[str, object]:
    """
    Compute a sentence-level BLEU fallback.

    The pipeline uses sacrebleu for corpus metrics when available. This helper
    is retained for per-example inspection and dependency-light operation.
    """
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()

    if not hyp_tokens:
        return {
            "bleu": 0.0,
            "precisions": [0.0] * max_n,
            "brevity_penalty": 0.0,
            "hyp_length": 0,
            "ref_length": len(ref_tokens),
        }

    precisions = []
    for n in range(1, max_n + 1):
        ref_ngrams = get_ngrams(ref_tokens, n)
        hyp_ngrams = get_ngrams(hyp_tokens, n)
        matches = sum(min(count, ref_ngrams.get(ngram, 0)) for ngram, count in hyp_ngrams.items())
        total = sum(hyp_ngrams.values())
        precisions.append(matches / total if total else 0.0)

    if len(hyp_tokens) < len(ref_tokens) and hyp_tokens:
        brevity_penalty = math.exp(1 - len(ref_tokens) / len(hyp_tokens))
    else:
        brevity_penalty = 1.0

    smoothed = [precision if precision > 0 else 1e-9 for precision in precisions]
    bleu = brevity_penalty * math.exp(sum(math.log(p) for p in smoothed) / max_n)

    return {
        "bleu": round(bleu * 100, 2),
        "precisions": [round(p * 100, 2) for p in precisions],
        "brevity_penalty": round(brevity_penalty, 4),
        "hyp_length": len(hyp_tokens),
        "ref_length": len(ref_tokens),
    }


def compute_chrf(reference: str, hypothesis: str, max_n: int = 6) -> Dict[str, object]:
    """Compute a dependency-light sentence-level chrF fallback."""
    def char_ngrams(text: str, n: int) -> Dict[str, int]:
        text = text.lower()
        ngrams: Dict[str, int] = defaultdict(int)
        for index in range(len(text) - n + 1):
            ngrams[text[index : index + n]] += 1
        return ngrams

    scores = []
    for n in range(1, max_n + 1):
        ref_ngrams = char_ngrams(reference, n)
        hyp_ngrams = char_ngrams(hypothesis, n)
        matches = sum(min(count, ref_ngrams.get(ngram, 0)) for ngram, count in hyp_ngrams.items())
        hyp_count = sum(hyp_ngrams.values())
        ref_count = sum(ref_ngrams.values())

        precision = matches / hyp_count if hyp_count else 0.0
        recall = matches / ref_count if ref_count else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)

    return {
        "chrf": round(sum(scores) / len(scores) * 100, 2) if scores else 0.0,
        "char_f_scores": [round(score * 100, 2) for score in scores],
    }


def evaluate_translations(references: List[str], hypotheses: List[str]) -> Dict[str, object]:
    """Evaluate translations with corpus BLEU/chrF and per-sample fallback scores."""
    if len(references) != len(hypotheses):
        raise ValueError("References and hypotheses must have same length")
    if not references:
        return {"avg_bleu": 0.0, "avg_chrf": 0.0, "total_samples": 0}

    try:
        import sacrebleu

        corpus_bleu = sacrebleu.corpus_bleu(hypotheses, [references]).score
        corpus_chrf = sacrebleu.corpus_chrf(hypotheses, [references]).score
        metric_impl = "sacrebleu"
    except Exception:  # noqa: BLE001 - fallback keeps evaluation usable
        sentence_bleu = [compute_bleu(ref, hyp)["bleu"] for ref, hyp in zip(references, hypotheses)]
        sentence_chrf = [compute_chrf(ref, hyp)["chrf"] for ref, hyp in zip(references, hypotheses)]
        corpus_bleu = sum(sentence_bleu) / len(sentence_bleu)
        corpus_chrf = sum(sentence_chrf) / len(sentence_chrf)
        metric_impl = "internal_fallback"

    bleu_scores = [compute_bleu(ref, hyp)["bleu"] for ref, hyp in zip(references, hypotheses)]
    chrf_scores = [compute_chrf(ref, hyp)["chrf"] for ref, hyp in zip(references, hypotheses)]

    return {
        "avg_bleu": round(corpus_bleu, 2),
        "avg_chrf": round(corpus_chrf, 2),
        "sentence_bleu_scores": bleu_scores,
        "sentence_chrf_scores": chrf_scores,
        "metric_impl": metric_impl,
        "total_samples": len(references),
    }


def _contains_any(text: str, terms: Sequence[str]) -> bool:
    lowered = text.lower()
    for term in terms:
        if re.search(rf"\b{re.escape(term.lower())}\b", lowered) or term in text:
            return True
    return False


def extract_legal_terms(text: str) -> List[str]:
    """Extract coarse legal term groups from English or Hindi text."""
    found = []
    for group, terms in LEGAL_TERM_GROUPS.items():
        if _contains_any(text, terms["en"]) or _contains_any(text, terms["hi"]):
            found.append(group)
    return found


def legal_term_preservation(reference: str, hypothesis: str) -> Dict[str, object]:
    """Compare legal term groups present in reference and hypothesis."""
    ref_terms = set(extract_legal_terms(reference))
    hyp_terms = set(extract_legal_terms(hypothesis))
    preserved = sorted(ref_terms & hyp_terms)
    return {
        "reference_terms": sorted(ref_terms),
        "hypothesis_terms": sorted(hyp_terms),
        "preserved_terms": preserved,
        "preserved_count": len(preserved),
        "reference_term_count": len(ref_terms),
        "preservation_rate": round(len(preserved) / len(ref_terms), 4) if ref_terms else None,
    }


def analyze_qualitative_examples(
    references: List[str],
    hypotheses: List[str],
    sources: Optional[List[str]] = None,
    baseline_hypotheses: Optional[List[str]] = None,
    num_examples: int = 5,
) -> List[Dict[str, object]]:
    """Create compact qualitative examples for the report."""
    examples = []
    limit = min(num_examples, len(references), len(hypotheses))

    for index in range(limit):
        ref = references[index]
        hyp = hypotheses[index]
        example = {
            "index": index + 1,
            "source_english": sources[index] if sources else None,
            "reference_hindi": ref,
            "adapted_hypothesis": hyp,
            "adapted_bleu": compute_bleu(ref, hyp)["bleu"],
            "adapted_chrf": compute_chrf(ref, hyp)["chrf"],
            "adapted_legal_terms": legal_term_preservation(ref, hyp),
            "length_ratio": round(len(hyp.split()) / len(ref.split()), 4) if ref.split() else None,
        }
        if baseline_hypotheses and index < len(baseline_hypotheses):
            baseline = baseline_hypotheses[index]
            example["baseline_hypothesis"] = baseline
            example["baseline_bleu"] = compute_bleu(ref, baseline)["bleu"]
            example["baseline_chrf"] = compute_chrf(ref, baseline)["chrf"]
            example["baseline_legal_terms"] = legal_term_preservation(ref, baseline)
        examples.append(example)

    return examples


def compare_before_after(
    references: List[str],
    baseline_hypotheses: List[str],
    adapted_hypotheses: List[str],
) -> Dict[str, object]:
    """Evaluate baseline and adapted outputs on the same references."""
    baseline = evaluate_translations(references, baseline_hypotheses)
    adapted = evaluate_translations(references, adapted_hypotheses)
    return {
        "baseline": baseline,
        "adapted": adapted,
        "delta_bleu": round(float(adapted["avg_bleu"]) - float(baseline["avg_bleu"]), 2),
        "delta_chrf": round(float(adapted["avg_chrf"]) - float(baseline["avg_chrf"]), 2),
    }


def print_evaluation_report(eval_results: Dict[str, object]) -> None:
    """Print formatted evaluation results."""
    print("\n" + "=" * 70)
    print("AUTOMATIC EVALUATION RESULTS")
    print("=" * 70)
    print(f"Samples: {eval_results.get('total_samples', 0)}")
    print(f"BLEU: {eval_results.get('avg_bleu', 'N/A')}")
    print(f"chrF: {eval_results.get('avg_chrf', 'N/A')}")
    print(f"Metric implementation: {eval_results.get('metric_impl', 'N/A')}")
    print("=" * 70 + "\n")


def print_qualitative_analysis(examples: List[Dict[str, object]]) -> None:
    """Print qualitative examples without flooding the terminal."""
    print("\n" + "=" * 70)
    print("QUALITATIVE EXAMPLES")
    print("=" * 70)
    for example in examples:
        print(f"Example {example['index']}: BLEU={example['adapted_bleu']}, chrF={example['adapted_chrf']}")
        if example.get("source_english"):
            print(f"EN: {str(example['source_english'])[:160]}...")
        print(f"REF: {str(example['reference_hindi'])[:160]}...")
        print(f"HYP: {str(example['adapted_hypothesis'])[:160]}...")
        print("-" * 70)
    print()


def export_evaluation(
    eval_results: Dict[str, object],
    qualitative_examples: List[Dict[str, object]],
    output_path: str,
    before_after: Optional[Dict[str, object]] = None,
) -> None:
    """Export evaluation results to JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    output = {
        "automatic_metrics": eval_results,
        "qualitative_examples": qualitative_examples,
        "before_after": before_after,
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)
    print(f"Evaluation results exported to {output_path}")


if __name__ == "__main__":
    print("Evaluation module. Import it from main_pipeline.py.")
