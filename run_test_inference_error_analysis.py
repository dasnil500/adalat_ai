"""Run full-test inference and research-style error analysis.

This script is intended for the Indian court judgment English-to-Hindi
parallel corpus in this repository. It can:

1. Regenerate or load the test split.
2. Run model inference over every test instance.
3. Compute corpus and per-segment metrics.
4. Categorize errors with a legal-domain taxonomy.
5. Write JSONL, CSV, JSON, and Markdown artifacts suitable for a paper section.

Example:
    python run_test_inference_error_analysis.py ^
        --model-path checkpoints/final_model ^
        --output-dir results/test_error_analysis

For a LoRA adapter, pass the adapter directory as --model-path and keep
--model-name set to the original base model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


DEVANAGARI_DIGITS = str.maketrans("\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f", "0123456789")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")
TOKEN_RE = re.compile(r"[A-Za-z0-9\u0900-\u097F]+")
DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?(?![A-Za-z0-9])")
LEADING_MARKER_RE = re.compile(
    r"^\s*(?P<marker>(?:\d+(?:\.\d+)?|[ivxlcdm]+|[a-z])[\.)\u0964]?)\s+",
    re.IGNORECASE,
)
LIST_MARKER_RE = re.compile(
    r"(?i)(?:^|\s)(?:\d+(?:\.\d+)?|[ivxlcdm]+|[a-z])[\.)]\s+"
)
CLAUSE_SPLIT_RE = re.compile(r"[.;:!?।]+")


LEGAL_GROUPS: Dict[str, Dict[str, object]] = {
    "appeal": {
        "family": "legal_procedure",
        "en": ["appeal", "appellant", "appellate"],
        "hi": ["अपील", "अपीलकर्ता", "अपीलार्थी"],
    },
    "petition_writ": {
        "family": "legal_procedure",
        "en": ["petition", "petitioner", "writ", "application"],
        "hi": ["याचिका", "याचिकाकर्ता", "रिट", "आवेदन"],
    },
    "respondent_party": {
        "family": "party_role",
        "en": ["respondent"],
        "hi": ["प्रतिवादी", "उत्तरदाता"],
    },
    "accused_party": {
        "family": "party_role",
        "en": ["accused", "convict", "defendant"],
        "hi": ["अभियुक्त", "आरोपी", "दोषी", "प्रतिवादी"],
    },
    "plaintiff_complainant": {
        "family": "party_role",
        "en": ["plaintiff", "complainant"],
        "hi": ["वादी", "शिकायतकर्ता", "परिवादी"],
    },
    "court_forum": {
        "family": "court_institution",
        "en": ["court", "high court", "supreme court", "tribunal", "bench"],
        "hi": ["न्यायालय", "उच्च न्यायालय", "सर्वोच्च न्यायालय", "अदालत", "अधिकरण", "पीठ"],
    },
    "judge_bench": {
        "family": "court_institution",
        "en": ["judge", "justice", "bench"],
        "hi": ["न्यायाधीश", "न्यायमूर्ति", "पीठ"],
    },
    "judgment_order": {
        "family": "legal_procedure",
        "en": ["judgment", "judgement", "order", "decision"],
        "hi": ["निर्णय", "आदेश", "फैसला"],
    },
    "statutory_reference": {
        "family": "statutory_reference",
        "en": ["section", "article", "act", "rule", "constitution", "code", "ipc", "crpc", "cpc"],
        "hi": ["धारा", "अनुच्छेद", "अधिनियम", "नियम", "संविधान", "संहिता"],
    },
    "charge_fir": {
        "family": "criminal_procedure",
        "en": ["charge", "charge sheet", "chargesheet", "fir", "first information report"],
        "hi": ["आरोप", "आरोप-पत्र", "प्राथमिकी", "एफआईआर"],
    },
    "evidence_witness": {
        "family": "evidence",
        "en": ["evidence", "witness", "affidavit", "investigation", "record"],
        "hi": ["साक्ष्य", "गवाह", "हलफनामा", "जांच", "अभिलेख", "रिकॉर्ड"],
    },
    "dismissal_rejection": {
        "family": "legal_outcome",
        "en": ["dismissed", "rejected", "dismissal"],
        "hi": ["खारिज", "अस्वीकार", "निरस्त"],
    },
    "allowed_relief": {
        "family": "legal_outcome",
        "en": ["allowed", "relief", "granted"],
        "hi": ["स्वीकार", "अनुमति", "राहत", "प्रदान"],
    },
    "set_aside_quash": {
        "family": "legal_outcome",
        "en": ["set aside", "quashed", "quash", "remanded", "remand"],
        "hi": ["अपास्त", "रद्द", "खारिज", "वापस भेज", "प्रेषित"],
    },
    "conviction_sentence": {
        "family": "legal_outcome",
        "en": ["conviction", "convicted", "sentence", "acquitted", "acquittal", "bail"],
        "hi": ["दोषसिद्धि", "दोषी ठहराया", "सजा", "दंड", "बरी", "जमानत"],
    },
    "negation": {
        "family": "logic_modality",
        "en": ["not", "no", "never", "neither", "without"],
        "hi": ["नहीं", "न", "कभी नहीं", "बिना"],
    },
    "modality_direction": {
        "family": "logic_modality",
        "en": ["shall", "must", "may", "liable", "entitled", "directed", "ordered"],
        "hi": ["होगा", "चाहिए", "सकता", "उत्तरदायी", "हकदार", "निर्देशित", "आदेशित"],
    },
    "reasoning_connective": {
        "family": "legal_reasoning",
        "en": ["therefore", "hence", "however", "whereas", "because", "accordingly"],
        "hi": ["इसलिए", "अतः", "हालांकि", "जबकि", "क्योंकि", "तदनुसार"],
    },
}


CATEGORY_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "empty_or_degenerate_output": {
        "family": "fluency_script",
        "severity": "critical",
        "description": "The system produced an empty, near-empty, or otherwise unusable output.",
    },
    "wrong_script_or_source_copying": {
        "family": "fluency_script",
        "severity": "critical",
        "description": "The output remains substantially in English/Latin script or copies the source.",
    },
    "severe_semantic_drift": {
        "family": "adequacy",
        "severity": "critical",
        "description": "The output has very low character and token overlap with the reference.",
    },
    "under_translation_omission": {
        "family": "adequacy",
        "severity": "high",
        "description": "The output is materially shorter than the reference, suggesting omitted legal content.",
    },
    "over_translation_addition": {
        "family": "adequacy",
        "severity": "high",
        "description": "The output is materially longer than the reference or adds unsupported content.",
    },
    "legal_terminology_omission": {
        "family": "legal_domain_fidelity",
        "severity": "high",
        "description": "Expected legal concepts are missing from the hypothesis.",
    },
    "legal_terminology_addition": {
        "family": "legal_domain_fidelity",
        "severity": "medium",
        "description": "The hypothesis introduces legal concepts not observed in the source/reference.",
    },
    "party_role_error": {
        "family": "legal_domain_fidelity",
        "severity": "high",
        "description": "Party roles such as appellant, respondent, petitioner, or accused are dropped or altered.",
    },
    "statutory_reference_error": {
        "family": "legal_domain_fidelity",
        "severity": "high",
        "description": "Sections, articles, Acts, rules, or code references are not preserved.",
    },
    "outcome_error": {
        "family": "legal_domain_fidelity",
        "severity": "high",
        "description": "Disposition/outcome terms such as allowed, dismissed, quashed, conviction, or bail are mistranslated.",
    },
    "negation_modality_error": {
        "family": "legal_reasoning",
        "severity": "high",
        "description": "Negation, obligation, permission, entitlement, or judicial direction is missing or added.",
    },
    "date_number_error": {
        "family": "factual_preservation",
        "severity": "medium",
        "description": "Dates, amounts, paragraph numbers, years, or other numeric facts are not preserved.",
    },
    "named_entity_or_abbreviation_risk": {
        "family": "factual_preservation",
        "severity": "medium",
        "description": "Names, institutions, or legal abbreviations in the source are at risk of being lost or distorted.",
    },
    "repetition_or_fluency_error": {
        "family": "fluency_script",
        "severity": "medium",
        "description": "The output contains repeated words/phrases or visibly degraded fluency.",
    },
    "format_structure_error": {
        "family": "structure",
        "severity": "medium",
        "description": "Paragraph numbering, list markers, or enumerated legal structure are not preserved.",
    },
    "acceptable_or_minor_variation": {
        "family": "minor",
        "severity": "low",
        "description": "No major heuristic error was detected; remaining issues are likely lexical/style variation.",
    },
}


SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def normalize_space(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def normalize_digits(text: object) -> str:
    return str(text or "").translate(DEVANAGARI_DIGITS)


def tokenize(text: object) -> List[str]:
    return TOKEN_RE.findall(normalize_digits(text).lower())


def text_preview(text: object, limit: int = 280) -> str:
    compact = normalize_space(text)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def ratio(numerator: float, denominator: float, default: float = 0.0) -> float:
    return round(numerator / denominator, 4) if denominator else default


def char_script_ratios(text: str) -> Dict[str, float]:
    nonspace = [char for char in text if not char.isspace()]
    denominator = len(nonspace)
    return {
        "devanagari_ratio": ratio(sum(bool(DEVANAGARI_RE.match(char)) for char in nonspace), denominator),
        "latin_ratio": ratio(sum(bool(LATIN_RE.match(char)) for char in nonspace), denominator),
    }


def ngrams(tokens: Sequence[str], n: int) -> Counter[Tuple[str, ...]]:
    return Counter(tuple(tokens[index : index + n]) for index in range(max(0, len(tokens) - n + 1)))


def fallback_sentence_bleu(reference: str, hypothesis: str, max_n: int = 4) -> float:
    ref_tokens = tokenize(reference)
    hyp_tokens = tokenize(hypothesis)
    if not hyp_tokens:
        return 0.0

    precisions: List[float] = []
    for n in range(1, max_n + 1):
        ref_ngrams = ngrams(ref_tokens, n)
        hyp_ngrams = ngrams(hyp_tokens, n)
        matches = sum(min(count, ref_ngrams.get(ngram, 0)) for ngram, count in hyp_ngrams.items())
        total = sum(hyp_ngrams.values())
        precisions.append(matches / total if total else 0.0)

    if len(hyp_tokens) < len(ref_tokens):
        brevity_penalty = math.exp(1 - len(ref_tokens) / len(hyp_tokens))
    else:
        brevity_penalty = 1.0

    smoothed = [precision if precision > 0 else 1e-9 for precision in precisions]
    return round(100 * brevity_penalty * math.exp(sum(math.log(p) for p in smoothed) / max_n), 2)


def char_ngrams(text: str, n: int) -> Counter[str]:
    compact = normalize_space(text.lower())
    return Counter(compact[index : index + n] for index in range(max(0, len(compact) - n + 1)))


def fallback_sentence_chrf(reference: str, hypothesis: str, max_n: int = 6) -> float:
    scores: List[float] = []
    for n in range(1, max_n + 1):
        ref_ngrams = char_ngrams(reference, n)
        hyp_ngrams = char_ngrams(hypothesis, n)
        matches = sum(min(count, ref_ngrams.get(ngram, 0)) for ngram, count in hyp_ngrams.items())
        hyp_total = sum(hyp_ngrams.values())
        ref_total = sum(ref_ngrams.values())
        precision = matches / hyp_total if hyp_total else 0.0
        recall = matches / ref_total if ref_total else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return round(100 * sum(scores) / len(scores), 2) if scores else 0.0


def token_overlap_f1(reference: str, hypothesis: str) -> float:
    ref_counts = Counter(tokenize(reference))
    hyp_counts = Counter(tokenize(hypothesis))
    if not ref_counts or not hyp_counts:
        return 0.0
    overlap = sum((ref_counts & hyp_counts).values())
    precision = overlap / sum(hyp_counts.values())
    recall = overlap / sum(ref_counts.values())
    return round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0


def compute_metrics(references: Sequence[str], hypotheses: Sequence[str]) -> Dict[str, Any]:
    if len(references) != len(hypotheses):
        raise ValueError("Reference and hypothesis counts do not match.")
    if not references:
        return {
            "avg_bleu": 0.0,
            "avg_chrf": 0.0,
            "sentence_bleu_scores": [],
            "sentence_chrf_scores": [],
            "metric_impl": "none",
            "total_samples": 0,
        }

    sentence_bleu: List[float] = []
    sentence_chrf: List[float] = []
    try:
        import sacrebleu

        corpus_bleu = round(sacrebleu.corpus_bleu(list(hypotheses), [list(references)]).score, 2)
        corpus_chrf = round(sacrebleu.corpus_chrf(list(hypotheses), [list(references)]).score, 2)
        metric_impl = "sacrebleu"
        for reference, hypothesis in zip(references, hypotheses):
            sentence_bleu.append(round(sacrebleu.sentence_bleu(hypothesis, [reference]).score, 2))
            sentence_chrf.append(round(sacrebleu.sentence_chrf(hypothesis, [reference]).score, 2))
    except Exception:
        metric_impl = "internal_fallback"
        sentence_bleu = [fallback_sentence_bleu(ref, hyp) for ref, hyp in zip(references, hypotheses)]
        sentence_chrf = [fallback_sentence_chrf(ref, hyp) for ref, hyp in zip(references, hypotheses)]
        corpus_bleu = round(sum(sentence_bleu) / len(sentence_bleu), 2)
        corpus_chrf = round(sum(sentence_chrf) / len(sentence_chrf), 2)

    return {
        "avg_bleu": corpus_bleu,
        "avg_chrf": corpus_chrf,
        "sentence_bleu_scores": sentence_bleu,
        "sentence_chrf_scores": sentence_chrf,
        "metric_impl": metric_impl,
        "total_samples": len(references),
    }


def contains_term(text: str, term: str) -> bool:
    lowered = text.lower()
    term_lower = term.lower()
    if LATIN_RE.search(term_lower):
        return re.search(rf"(?<![A-Za-z]){re.escape(term_lower)}(?![A-Za-z])", lowered) is not None
    return term_lower in lowered


def extract_legal_groups(text: str) -> List[str]:
    groups: List[str] = []
    for group, spec in LEGAL_GROUPS.items():
        terms = list(spec.get("en", [])) + list(spec.get("hi", []))
        if any(contains_term(text, str(term)) for term in terms):
            groups.append(group)
    return sorted(groups)


def group_family(group: str) -> str:
    return str(LEGAL_GROUPS.get(group, {}).get("family", "other"))


def extract_dates(text: str) -> List[str]:
    normalized = normalize_digits(text)
    return sorted(set(DATE_RE.findall(normalized)))


def extract_numbers(text: str) -> List[str]:
    normalized = normalize_digits(text)
    return sorted(set(NUMBER_RE.findall(normalized)), key=lambda value: (len(value), value))


def extract_statutory_refs(text: str) -> List[str]:
    normalized = normalize_digits(text).lower()
    patterns = [
        r"\b(?:section|sec\.?|article|rule|order)\s+(\d+[a-z]?)\b",
        r"\b(\d+[a-z]?)\s+(?:ipc|crpc|cpc)\b",
        r"(?:धारा|अनुच्छेद|नियम|आदेश)\s*(\d+[a-z]?)",
    ]
    refs: List[str] = []
    for pattern in patterns:
        refs.extend(re.findall(pattern, normalized, flags=re.IGNORECASE))
    return sorted(set(refs))


def extract_markers(text: str) -> Dict[str, Any]:
    normalized = normalize_digits(text)
    leading = LEADING_MARKER_RE.search(normalized)
    markers = [match.group(0).strip() for match in LIST_MARKER_RE.finditer(normalized)]
    return {
        "leading_marker": leading.group("marker").rstrip(".):\u0964") if leading else "",
        "list_marker_count": len(markers),
        "list_markers": markers[:12],
    }


def extract_source_entities(text: str) -> List[str]:
    stopwords = {
        "The",
        "This",
        "That",
        "These",
        "Those",
        "On",
        "In",
        "At",
        "For",
        "And",
        "But",
        "Court",
        "High",
        "Supreme",
        "Section",
        "Article",
        "Act",
        "Rule",
    }
    candidates: List[str] = []
    for match in re.finditer(r"\b(?:[A-Z][A-Za-z&.'-]+(?:\s+|$)){2,}", text):
        candidate = normalize_space(match.group(0))
        pieces = candidate.split()
        if len(pieces) >= 2 and not all(piece in stopwords for piece in pieces):
            candidates.append(candidate)
    candidates.extend(re.findall(r"\b[A-Z]{2,}\b", text))
    unique: List[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique[:20]


def repeated_ngram_ratio(tokens: Sequence[str]) -> float:
    if len(tokens) < 4:
        return 0.0
    scores = []
    for n in (1, 2, 3):
        grams = ngrams(tokens, n)
        total = sum(grams.values())
        repeated = sum(count - 1 for count in grams.values() if count > 1)
        scores.append(repeated / total if total else 0.0)
    return round(max(scores), 4)


def max_token_run(tokens: Sequence[str]) -> int:
    longest = 0
    current = 0
    previous = None
    for token in tokens:
        current = current + 1 if token == previous else 1
        longest = max(longest, current)
        previous = token
    return longest


def count_clauses(text: str) -> int:
    pieces = [piece.strip() for piece in CLAUSE_SPLIT_RE.split(text) if piece.strip()]
    return max(1, len(pieces)) if text.strip() else 0


def analyze_segment(record: Mapping[str, Any], bleu: float, chrf: float) -> Dict[str, Any]:
    source = str(record["source_english"])
    reference = str(record["reference_hindi"])
    hypothesis = str(record["hypothesis_hindi"])
    source_tokens = tokenize(source)
    ref_tokens = tokenize(reference)
    hyp_tokens = tokenize(hypothesis)

    ref_groups = set(extract_legal_groups(reference))
    source_groups = set(extract_legal_groups(source))
    hyp_groups = set(extract_legal_groups(hypothesis))
    expected_groups = ref_groups | source_groups
    missing_groups = sorted(expected_groups - hyp_groups)
    added_groups = sorted(hyp_groups - expected_groups)

    ref_numbers = set(extract_numbers(reference))
    hyp_numbers = set(extract_numbers(hypothesis))
    ref_dates = set(extract_dates(reference))
    hyp_dates = set(extract_dates(hypothesis))
    source_stat_refs = set(extract_statutory_refs(source))
    ref_stat_refs = set(extract_statutory_refs(reference))
    hyp_stat_refs = set(extract_statutory_refs(hypothesis))
    expected_stat_refs = source_stat_refs | ref_stat_refs

    source_entities = extract_source_entities(source)
    source_abbreviations = [entity for entity in source_entities if entity.isupper() and len(entity) >= 2]
    missing_abbreviations = [
        abbreviation
        for abbreviation in source_abbreviations
        if abbreviation.lower() not in hypothesis.lower()
    ]

    source_latin_tokens = set(token.lower() for token in LATIN_WORD_RE.findall(source))
    hyp_latin_tokens = set(token.lower() for token in LATIN_WORD_RE.findall(hypothesis))
    copied_latin_tokens = sorted((source_latin_tokens & hyp_latin_tokens) - {"the", "and", "of", "to", "in", "for"})

    ref_markers = extract_markers(reference)
    hyp_markers = extract_markers(hypothesis)

    script_ratios = char_script_ratios(hypothesis)
    ref_script_ratios = char_script_ratios(reference)
    length_ratio = ratio(len(hyp_tokens), len(ref_tokens), default=0.0)
    char_length_ratio = ratio(len(hypothesis), len(reference), default=0.0)
    overlap_f1 = token_overlap_f1(reference, hypothesis)
    repetition_score = repeated_ngram_ratio(hyp_tokens)
    longest_run = max_token_run(hyp_tokens)

    features: Dict[str, Any] = {
        "source_token_count": len(source_tokens),
        "reference_token_count": len(ref_tokens),
        "hypothesis_token_count": len(hyp_tokens),
        "length_ratio": length_ratio,
        "char_length_ratio": char_length_ratio,
        "reference_clause_count": count_clauses(reference),
        "hypothesis_clause_count": count_clauses(hypothesis),
        "token_overlap_f1": overlap_f1,
        "hypothesis_devanagari_ratio": script_ratios["devanagari_ratio"],
        "hypothesis_latin_ratio": script_ratios["latin_ratio"],
        "reference_devanagari_ratio": ref_script_ratios["devanagari_ratio"],
        "source_copied_latin_terms": copied_latin_tokens[:20],
        "source_copied_latin_count": len(copied_latin_tokens),
        "reference_legal_groups": sorted(ref_groups),
        "source_legal_groups": sorted(source_groups),
        "hypothesis_legal_groups": sorted(hyp_groups),
        "missing_legal_groups": missing_groups,
        "added_legal_groups": added_groups,
        "missing_legal_families": sorted({group_family(group) for group in missing_groups}),
        "reference_numbers": sorted(ref_numbers),
        "hypothesis_numbers": sorted(hyp_numbers),
        "missing_reference_numbers": sorted(ref_numbers - hyp_numbers),
        "added_hypothesis_numbers": sorted(hyp_numbers - ref_numbers),
        "reference_dates": sorted(ref_dates),
        "hypothesis_dates": sorted(hyp_dates),
        "missing_reference_dates": sorted(ref_dates - hyp_dates),
        "expected_statutory_refs": sorted(expected_stat_refs),
        "hypothesis_statutory_refs": sorted(hyp_stat_refs),
        "missing_statutory_refs": sorted(expected_stat_refs - hyp_stat_refs),
        "source_entities": source_entities,
        "missing_source_abbreviations": missing_abbreviations,
        "reference_leading_marker": ref_markers["leading_marker"],
        "hypothesis_leading_marker": hyp_markers["leading_marker"],
        "reference_list_marker_count": ref_markers["list_marker_count"],
        "hypothesis_list_marker_count": hyp_markers["list_marker_count"],
        "repetition_score": repetition_score,
        "max_repeated_token_run": longest_run,
        "sentence_bleu": bleu,
        "sentence_chrf": chrf,
    }

    categories, evidence = categorize(features, record)
    return {
        "index": record["index"],
        "doc_id": record.get("doc_id"),
        "segment_id": record.get("segment_id"),
        "paragraph_no": record.get("paragraph_no"),
        "primary_category": choose_primary_category(categories),
        "categories": categories,
        "category_evidence": evidence,
        "features": features,
        "source_english": source,
        "reference_hindi": reference,
        "hypothesis_hindi": hypothesis,
    }


def add_category(
    categories: List[str],
    evidence: Dict[str, List[str]],
    category: str,
    reason: str,
) -> None:
    if category not in categories:
        categories.append(category)
    evidence[category].append(reason)


def categorize(features: Mapping[str, Any], record: Mapping[str, Any]) -> Tuple[List[str], Dict[str, List[str]]]:
    categories: List[str] = []
    evidence: Dict[str, List[str]] = defaultdict(list)

    hyp_tokens = int(features["hypothesis_token_count"])
    ref_tokens = int(features["reference_token_count"])
    length_ratio_value = float(features["length_ratio"])
    chrf = float(features["sentence_chrf"])
    overlap_f1 = float(features["token_overlap_f1"])

    if hyp_tokens == 0 or (hyp_tokens <= 2 and ref_tokens >= 8):
        add_category(
            categories,
            evidence,
            "empty_or_degenerate_output",
            f"Only {hyp_tokens} hypothesis tokens for {ref_tokens} reference tokens.",
        )

    if (
        float(features["reference_devanagari_ratio"]) >= 0.35
        and (
            float(features["hypothesis_latin_ratio"]) >= 0.22
            or float(features["hypothesis_devanagari_ratio"]) <= 0.35
            or int(features["source_copied_latin_count"]) >= 5
        )
    ):
        add_category(
            categories,
            evidence,
            "wrong_script_or_source_copying",
            (
                "Hypothesis script/copying signal: "
                f"Latin ratio={features['hypothesis_latin_ratio']}, "
                f"Devanagari ratio={features['hypothesis_devanagari_ratio']}, "
                f"copied Latin terms={features['source_copied_latin_count']}."
            ),
        )

    if chrf < 25.0 and overlap_f1 < 0.12 and hyp_tokens > 0:
        add_category(
            categories,
            evidence,
            "severe_semantic_drift",
            f"chrF={chrf} and token-overlap F1={overlap_f1}.",
        )

    if ref_tokens >= 8 and length_ratio_value < 0.70 and hyp_tokens > 0:
        add_category(
            categories,
            evidence,
            "under_translation_omission",
            f"Length ratio={length_ratio_value}; hypothesis is much shorter than reference.",
        )

    if ref_tokens >= 8 and length_ratio_value > 1.35:
        add_category(
            categories,
            evidence,
            "over_translation_addition",
            f"Length ratio={length_ratio_value}; hypothesis is much longer than reference.",
        )

    missing_groups = list(features["missing_legal_groups"])
    added_groups = list(features["added_legal_groups"])
    if missing_groups:
        add_category(
            categories,
            evidence,
            "legal_terminology_omission",
            "Missing expected legal groups: " + ", ".join(missing_groups[:10]),
        )
    if added_groups:
        add_category(
            categories,
            evidence,
            "legal_terminology_addition",
            "Added legal groups not seen in source/reference: " + ", ".join(added_groups[:10]),
        )

    if any(group_family(group) == "party_role" for group in missing_groups):
        add_category(
            categories,
            evidence,
            "party_role_error",
            "Missing party-role groups: "
            + ", ".join(group for group in missing_groups if group_family(group) == "party_role"),
        )

    if any(group_family(group) == "statutory_reference" for group in missing_groups) or features["missing_statutory_refs"]:
        add_category(
            categories,
            evidence,
            "statutory_reference_error",
            "Missing statutory groups/refs: "
            + ", ".join(list(features["missing_statutory_refs"]) + [g for g in missing_groups if group_family(g) == "statutory_reference"]),
        )

    if any(group_family(group) == "legal_outcome" for group in missing_groups):
        add_category(
            categories,
            evidence,
            "outcome_error",
            "Missing legal-outcome groups: "
            + ", ".join(group for group in missing_groups if group_family(group) == "legal_outcome"),
        )

    if any(group_family(group) == "logic_modality" for group in missing_groups + added_groups):
        add_category(
            categories,
            evidence,
            "negation_modality_error",
            "Negation/modality mismatch: "
            + ", ".join(group for group in missing_groups + added_groups if group_family(group) == "logic_modality"),
        )

    if features["missing_reference_dates"] or (
        len(features["missing_reference_numbers"]) >= 1 and chrf < 70.0
    ):
        add_category(
            categories,
            evidence,
            "date_number_error",
            "Missing dates/numbers from reference: "
            + ", ".join(list(features["missing_reference_dates"]) + list(features["missing_reference_numbers"])[:10]),
        )

    if features["missing_source_abbreviations"] or (
        len(features["source_entities"]) >= 2 and (chrf < 45.0 or length_ratio_value < 0.75)
    ):
        reason_parts = []
        if features["missing_source_abbreviations"]:
            reason_parts.append("missing abbreviations: " + ", ".join(features["missing_source_abbreviations"][:8]))
        if features["source_entities"]:
            reason_parts.append("source entity candidates: " + "; ".join(features["source_entities"][:5]))
        add_category(
            categories,
            evidence,
            "named_entity_or_abbreviation_risk",
            " | ".join(reason_parts),
        )

    if float(features["repetition_score"]) >= 0.18 or int(features["max_repeated_token_run"]) >= 3:
        add_category(
            categories,
            evidence,
            "repetition_or_fluency_error",
            f"Repetition score={features['repetition_score']}, max token run={features['max_repeated_token_run']}.",
        )

    expected_para = normalize_space(record.get("paragraph_no", ""))
    marker_mismatch = (
        features["reference_leading_marker"]
        and features["hypothesis_leading_marker"]
        and features["reference_leading_marker"] != features["hypothesis_leading_marker"]
    )
    missing_expected_para = (
        expected_para
        and expected_para != str(features["hypothesis_leading_marker"])
        and int(features["hypothesis_token_count"]) > 0
    )
    list_count_gap = abs(int(features["reference_list_marker_count"]) - int(features["hypothesis_list_marker_count"])) >= 2
    if marker_mismatch or missing_expected_para or list_count_gap:
        reasons = []
        if marker_mismatch:
            reasons.append(
                f"leading marker ref={features['reference_leading_marker']} hyp={features['hypothesis_leading_marker']}"
            )
        if missing_expected_para:
            reasons.append(f"paragraph_no={expected_para} not preserved in hypothesis leading marker")
        if list_count_gap:
            reasons.append(
                f"list marker count ref={features['reference_list_marker_count']} hyp={features['hypothesis_list_marker_count']}"
            )
        add_category(categories, evidence, "format_structure_error", "; ".join(reasons))

    if not categories:
        add_category(
            categories,
            evidence,
            "acceptable_or_minor_variation",
            "No major heuristic category triggered.",
        )

    categories.sort(
        key=lambda category: (
            -SEVERITY_RANK[CATEGORY_DEFINITIONS[category]["severity"]],
            category,
        )
    )
    return categories, dict(evidence)


def choose_primary_category(categories: Sequence[str]) -> str:
    if not categories:
        return "acceptable_or_minor_variation"
    return sorted(
        categories,
        key=lambda category: (
            -SEVERITY_RANK[CATEGORY_DEFINITIONS[category]["severity"]],
            category,
        ),
    )[0]


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def default_project_dir() -> Path:
    return Path(__file__).resolve().parent


def load_test_records(args: argparse.Namespace, project_dir: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    test_jsonl = Path(args.test_jsonl)
    if not test_jsonl.is_absolute():
        test_jsonl = project_dir / test_jsonl

    split_info: Dict[str, Any] = {"source": "test_jsonl", "path": str(test_jsonl)}
    if test_jsonl.exists():
        records = read_jsonl(test_jsonl)
    else:
        sys.path.insert(0, str(project_dir))
        try:
            from src.data_loader import create_data_split, load_parallel_texts, save_splits_to_jsonl
        except Exception as exc:
            raise RuntimeError(
                f"{test_jsonl} does not exist and src.data_loader could not be imported. "
                "Run main_pipeline.py first or keep this script inside the project root."
            ) from exc

        english_dir = Path(args.english_dir)
        hindi_dir = Path(args.hindi_dir)
        if not english_dir.is_absolute():
            english_dir = project_dir / english_dir
        if not hindi_dir.is_absolute():
            hindi_dir = project_dir / hindi_dir

        english_texts, hindi_texts = load_parallel_texts(str(english_dir), str(hindi_dir))
        split_data = create_data_split(
            english_texts,
            hindi_texts,
            train_ratio=args.train_ratio,
            dev_ratio=args.dev_ratio,
            test_ratio=args.test_ratio,
            random_seed=args.seed,
        )
        records = list(split_data["test"])
        split_info = dict(split_data["split_info"])
        split_info.update(
            {
                "source": "regenerated_from_clean_text",
                "english_dir": str(english_dir),
                "hindi_dir": str(hindi_dir),
            }
        )
        if args.save_generated_splits:
            save_splits_to_jsonl(split_data, str(project_dir / "data"))

    if args.limit:
        records = records[: args.limit]
        split_info["limit"] = args.limit

    normalized_records: List[Dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        normalized_records.append(
            {
                "index": index,
                "doc_id": record.get("doc_id", ""),
                "split": record.get("split", "test"),
                "segment_id": record.get("segment_id", index - 1),
                "paragraph_no": record.get("paragraph_no", ""),
                "alignment_method": record.get("alignment_method", ""),
                "source_english": record.get("english", record.get("source_english", "")),
                "reference_hindi": record.get("hindi", record.get("reference_hindi", "")),
            }
        )
    return normalized_records, split_info


def resolve_device(device_arg: str) -> str:
    if device_arg != "auto":
        return device_arg
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def set_tokenizer_languages(tokenizer: Any, source_lang: str, target_lang: str) -> None:
    if hasattr(tokenizer, "src_lang"):
        tokenizer.src_lang = source_lang
    if hasattr(tokenizer, "tgt_lang"):
        tokenizer.tgt_lang = target_lang


def forced_bos_token_id(tokenizer: Any, target_lang: str) -> Optional[int]:
    lang_code_to_id = getattr(tokenizer, "lang_code_to_id", None)
    if isinstance(lang_code_to_id, dict):
        return lang_code_to_id.get(target_lang)
    token_id = tokenizer.convert_tokens_to_ids(target_lang) if hasattr(tokenizer, "convert_tokens_to_ids") else None
    if isinstance(token_id, int) and token_id >= 0:
        return token_id
    return None


def load_model_and_tokenizer(args: argparse.Namespace) -> Tuple[Any, Any, str, Dict[str, Any]]:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = resolve_device(args.device)
    model_path = Path(args.model_path) if args.model_path else None
    if model_path and not model_path.is_absolute():
        model_path = default_project_dir() / model_path

    load_info: Dict[str, Any] = {
        "base_model": args.model_name,
        "model_path": str(model_path) if model_path else None,
        "device": device,
        "adapter_type": "base_model_only",
    }

    if model_path and (model_path / "adapter_config.json").exists():
        from peft import PeftModel

        tokenizer_source = model_path if (model_path / "tokenizer_config.json").exists() else args.model_name
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)
        base_model = AutoModelForSeq2SeqLM.from_pretrained(args.model_name)
        model = PeftModel.from_pretrained(base_model, str(model_path))
        load_info["adapter_type"] = "lora_adapter"
    elif model_path:
        tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        model = AutoModelForSeq2SeqLM.from_pretrained(str(model_path))
        load_info["adapter_type"] = "full_finetuned_model"
    else:
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(args.model_name)

    model.to(device)
    model.eval()
    set_tokenizer_languages(tokenizer, args.source_lang, args.target_lang)
    if device.startswith("cuda") and args.fp16:
        model.half()
        load_info["precision"] = "fp16"
    else:
        load_info["precision"] = "default"

    return model, tokenizer, device, load_info


def run_inference(records: Sequence[Mapping[str, Any]], args: argparse.Namespace) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    import torch

    model, tokenizer, device, load_info = load_model_and_tokenizer(args)
    predictions: List[Dict[str, Any]] = []
    start_time = time.time()
    forced_id = forced_bos_token_id(tokenizer, args.target_lang)

    generation_kwargs: Dict[str, Any] = {
        "max_length": args.generation_max_length,
        "num_beams": args.num_beams,
        "early_stopping": True,
    }
    if forced_id is not None:
        generation_kwargs["forced_bos_token_id"] = forced_id

    for batch_start in range(0, len(records), args.batch_size):
        batch = records[batch_start : batch_start + args.batch_size]
        sources = [str(record["source_english"]) for record in batch]
        set_tokenizer_languages(tokenizer, args.source_lang, args.target_lang)
        encoded = tokenizer(
            sources,
            max_length=args.max_input_length,
            truncation=True,
            padding=True,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}

        with torch.inference_mode():
            generated = model.generate(**encoded, **generation_kwargs)
        decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)

        for record, hypothesis in zip(batch, decoded):
            predictions.append(
                {
                    **dict(record),
                    "hypothesis_hindi": normalize_space(hypothesis),
                }
            )
        print(f"Generated {len(predictions)}/{len(records)} test translations")

    elapsed = round(time.time() - start_time, 2)
    load_info["elapsed_seconds"] = elapsed
    load_info["records_per_second"] = round(len(records) / elapsed, 4) if elapsed else None
    return predictions, load_info


def load_predictions(predictions_jsonl: Path, records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows = read_jsonl(predictions_jsonl)
    if not rows:
        raise ValueError(f"No rows found in {predictions_jsonl}")

    predictions: List[Dict[str, Any]] = []
    fallback_by_index = {int(record["index"]): record for record in records if str(record.get("index", "")).isdigit()}
    for position, row in enumerate(rows, start=1):
        index = int(row.get("index", position))
        fallback = fallback_by_index.get(index, {})
        source = row.get("source_english", row.get("english", fallback.get("source_english", "")))
        reference = row.get("reference_hindi", row.get("hindi", fallback.get("reference_hindi", "")))
        hypothesis = row.get("hypothesis_hindi", row.get("hypothesis", row.get("prediction", "")))
        predictions.append(
            {
                "index": index,
                "doc_id": row.get("doc_id", fallback.get("doc_id", "")),
                "split": row.get("split", fallback.get("split", "test")),
                "segment_id": row.get("segment_id", fallback.get("segment_id", index - 1)),
                "paragraph_no": row.get("paragraph_no", fallback.get("paragraph_no", "")),
                "alignment_method": row.get("alignment_method", fallback.get("alignment_method", "")),
                "source_english": source,
                "reference_hindi": reference,
                "hypothesis_hindi": hypothesis,
            }
        )
    return predictions


def summarize_analyses(
    analyses: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    split_info: Mapping[str, Any],
    model_info: Mapping[str, Any],
) -> Dict[str, Any]:
    total = len(analyses)
    primary_counts = Counter(str(item["primary_category"]) for item in analyses)
    multilabel_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    legal_group_missing_counts: Counter[str] = Counter()
    legal_family_missing_counts: Counter[str] = Counter()

    length_ratios = [float(item["features"]["length_ratio"]) for item in analyses]
    token_f1s = [float(item["features"]["token_overlap_f1"]) for item in analyses]
    legal_preservation_rates: List[float] = []

    for item in analyses:
        categories = list(item["categories"])
        for category in categories:
            multilabel_counts[category] += 1
            definition = CATEGORY_DEFINITIONS[category]
            family_counts[definition["family"]] += 1
            severity_counts[definition["severity"]] += 1

        features = item["features"]
        expected_groups = set(features["reference_legal_groups"]) | set(features["source_legal_groups"])
        missing_groups = set(features["missing_legal_groups"])
        for group in missing_groups:
            legal_group_missing_counts[group] += 1
            legal_family_missing_counts[group_family(group)] += 1
        if expected_groups:
            legal_preservation_rates.append((len(expected_groups) - len(missing_groups)) / len(expected_groups))

    category_rows = []
    for category, definition in CATEGORY_DEFINITIONS.items():
        count = multilabel_counts[category]
        category_rows.append(
            {
                "category": category,
                "family": definition["family"],
                "severity": definition["severity"],
                "count": count,
                "percent": round(100 * count / total, 2) if total else 0.0,
                "primary_count": primary_counts[category],
                "primary_percent": round(100 * primary_counts[category] / total, 2) if total else 0.0,
                "description": definition["description"],
            }
        )
    category_rows.sort(
        key=lambda row: (
            -int(row["count"]),
            -SEVERITY_RANK[str(row["severity"])],
            str(row["category"]),
        )
    )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": {
            "domain": "Indian court judgment parallel corpus",
            "language_pair": "English-to-Hindi",
            "test_records": total,
            "split_info": dict(split_info),
        },
        "model": dict(model_info),
        "automatic_metrics": dict(metrics),
        "aggregate_diagnostics": {
            "mean_length_ratio": round(statistics.mean(length_ratios), 4) if length_ratios else None,
            "median_length_ratio": round(statistics.median(length_ratios), 4) if length_ratios else None,
            "mean_token_overlap_f1": round(statistics.mean(token_f1s), 4) if token_f1s else None,
            "mean_legal_group_preservation": round(statistics.mean(legal_preservation_rates), 4)
            if legal_preservation_rates
            else None,
            "segments_with_legal_terms": len(legal_preservation_rates),
        },
        "category_summary": category_rows,
        "primary_category_counts": dict(primary_counts),
        "family_counts_multilabel": dict(family_counts),
        "severity_counts_multilabel": dict(severity_counts),
        "missing_legal_group_counts": dict(legal_group_missing_counts.most_common()),
        "missing_legal_family_counts": dict(legal_family_missing_counts.most_common()),
    }


def write_category_csv(path: Path, summary: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "category",
        "family",
        "severity",
        "count",
        "percent",
        "primary_count",
        "primary_percent",
        "description",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary["category_summary"]:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def top_examples_by_category(
    analyses: Sequence[Mapping[str, Any]], examples_per_category: int
) -> Dict[str, List[Mapping[str, Any]]]:
    examples: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    sorted_items = sorted(
        analyses,
        key=lambda item: (
            float(item["features"]["sentence_chrf"]),
            float(item["features"]["sentence_bleu"]),
        ),
    )
    for item in sorted_items:
        for category in item["categories"]:
            if len(examples[category]) < examples_per_category:
                examples[category].append(item)
    return dict(examples)


def markdown_table(rows: Sequence[Sequence[object]], headers: Sequence[str]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def build_report(
    summary: Mapping[str, Any],
    analyses: Sequence[Mapping[str, Any]],
    examples_per_category: int,
) -> str:
    metrics = summary["automatic_metrics"]
    diagnostics = summary["aggregate_diagnostics"]
    category_summary = summary["category_summary"]
    total = int(summary["dataset"]["test_records"])
    dominant_categories = [row for row in category_summary if row["count"] > 0][:5]
    dominant_families = Counter(summary["family_counts_multilabel"]).most_common(5)
    examples = top_examples_by_category(analyses, examples_per_category)

    lines: List[str] = []
    lines.append("# Full-Test Inference Error Analysis")
    lines.append("")
    lines.append(f"Generated: {summary['generated_at']}")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append(
        markdown_table(
            [
                ["Corpus", summary["dataset"]["domain"]],
                ["Language pair", summary["dataset"]["language_pair"]],
                ["Test segments", total],
                ["Metric implementation", metrics.get("metric_impl", "")],
                ["Model", summary["model"].get("model_path") or summary["model"].get("base_model")],
            ],
            ["Field", "Value"],
        )
    )
    lines.append("")
    lines.append("## Corpus-Level Metrics")
    lines.append("")
    lines.append(
        markdown_table(
            [
                ["BLEU", metrics.get("avg_bleu", 0.0)],
                ["chrF", metrics.get("avg_chrf", 0.0)],
                ["Mean length ratio", diagnostics.get("mean_length_ratio")],
                ["Median length ratio", diagnostics.get("median_length_ratio")],
                ["Mean token-overlap F1", diagnostics.get("mean_token_overlap_f1")],
                ["Mean legal-group preservation", diagnostics.get("mean_legal_group_preservation")],
            ],
            ["Metric", "Value"],
        )
    )
    lines.append("")
    lines.append("## Error Taxonomy Summary")
    lines.append("")
    rows = [
        [
            row["category"],
            row["family"],
            row["severity"],
            row["count"],
            f"{row['percent']}%",
            row["primary_count"],
        ]
        for row in category_summary
        if row["count"] > 0
    ]
    lines.append(markdown_table(rows, ["Category", "Family", "Severity", "Multi-label n", "%", "Primary n"]))
    lines.append("")
    lines.append("## Paper-Ready Interpretation")
    lines.append("")
    lines.append(
        "We evaluated the system on the full held-out test split of an Indian court judgment "
        f"English-Hindi parallel corpus, comprising {total} aligned legal text segments. "
        f"At corpus level, the system obtained BLEU={metrics.get('avg_bleu')} and "
        f"chrF={metrics.get('avg_chrf')}, with a mean hypothesis/reference length ratio of "
        f"{diagnostics.get('mean_length_ratio')}. These metrics were complemented with a "
        "multi-label legal error taxonomy, because general-purpose MT scores do not directly "
        "capture legally consequential failures such as party-role shifts, statutory-reference "
        "loss, or incorrect judicial outcomes."
    )
    lines.append("")
    if dominant_categories:
        top_category = dominant_categories[0]
        lines.append(
            f"The most frequent error category was `{top_category['category']}` "
            f"({top_category['count']}/{total}, {top_category['percent']}%). "
            "Across the taxonomy, the dominant error families were "
            + ", ".join(f"{family} ({count})" for family, count in dominant_families)
            + ". This indicates that the analysis should not be framed only as a fluency problem; "
            "a substantial part of the error profile concerns adequacy and domain fidelity."
        )
        lines.append("")
    lines.append(
        "For legal-domain fidelity, the script explicitly tracks whether concepts such as "
        "appeal, petition/writ, party roles, court/forum names, statutory references, charges, "
        "evidence, and judicial outcomes are preserved. Missing legal groups are especially "
        "important for Indian court judgments because mistranslating an appellant as a respondent, "
        "dropping a section/article reference, or changing whether a matter was dismissed or allowed "
        "can alter the legal proposition conveyed by the translation."
    )
    lines.append("")
    lines.append(
        "For factual preservation, the analysis separately flags dates, numbers, statutory-reference "
        "numbers, abbreviations, and named-entity risk. These errors are treated separately from "
        "generic semantic drift because court judgments are citation-heavy documents: years, sections, "
        "charge-sheet dates, FIR references, and case identifiers often carry central evidentiary or "
        "procedural meaning."
    )
    lines.append("")
    lines.append(
        "The taxonomy is heuristic and should be used as a structured first pass before manual "
        "adjudication. It is nevertheless useful for a research paper because it produces reproducible "
        "counts, keeps each segment's evidence, and separates legally material errors from ordinary "
        "lexical variation."
    )
    lines.append("")
    missing_legal = summary.get("missing_legal_group_counts", {})
    if missing_legal:
        lines.append("## Most Frequently Missing Legal Groups")
        lines.append("")
        lines.append(
            markdown_table(
                [[group, count] for group, count in list(missing_legal.items())[:12]],
                ["Legal group", "Missing count"],
            )
        )
        lines.append("")
    lines.append("## Category Definitions")
    lines.append("")
    definition_rows = [
        [
            category,
            definition["family"],
            definition["severity"],
            definition["description"],
        ]
        for category, definition in CATEGORY_DEFINITIONS.items()
    ]
    lines.append(markdown_table(definition_rows, ["Category", "Family", "Severity", "Definition"]))
    lines.append("")
    lines.append("## Representative Error Examples")
    lines.append("")
    for category, category_examples in examples.items():
        if category == "acceptable_or_minor_variation":
            continue
        definition = CATEGORY_DEFINITIONS[category]
        lines.append(f"### {category}")
        lines.append("")
        lines.append(f"Family: {definition['family']} | Severity: {definition['severity']}")
        lines.append("")
        for item in category_examples:
            features = item["features"]
            evidence = item["category_evidence"].get(category, [])
            lines.append(
                f"- Index {item['index']} | doc={item.get('doc_id')} | segment={item.get('segment_id')} | "
                f"BLEU={features['sentence_bleu']} | chrF={features['sentence_chrf']}"
            )
            if evidence:
                lines.append(f"  Evidence: {'; '.join(evidence[:3])}")
            lines.append(f"  EN: {text_preview(item['source_english'], 240)}")
            lines.append(f"  REF: {text_preview(item['reference_hindi'], 240)}")
            lines.append(f"  HYP: {text_preview(item['hypothesis_hindi'], 240)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_flat_analysis_csv(path: Path, analyses: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "index",
        "doc_id",
        "segment_id",
        "paragraph_no",
        "primary_category",
        "categories",
        "sentence_bleu",
        "sentence_chrf",
        "length_ratio",
        "token_overlap_f1",
        "missing_legal_groups",
        "missing_reference_numbers",
        "source_preview",
        "reference_preview",
        "hypothesis_preview",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in analyses:
            features = item["features"]
            writer.writerow(
                {
                    "index": item["index"],
                    "doc_id": item.get("doc_id", ""),
                    "segment_id": item.get("segment_id", ""),
                    "paragraph_no": item.get("paragraph_no", ""),
                    "primary_category": item["primary_category"],
                    "categories": ";".join(item["categories"]),
                    "sentence_bleu": features["sentence_bleu"],
                    "sentence_chrf": features["sentence_chrf"],
                    "length_ratio": features["length_ratio"],
                    "token_overlap_f1": features["token_overlap_f1"],
                    "missing_legal_groups": ";".join(features["missing_legal_groups"]),
                    "missing_reference_numbers": ";".join(features["missing_reference_numbers"]),
                    "source_preview": text_preview(item["source_english"], 180),
                    "reference_preview": text_preview(item["reference_hindi"], 180),
                    "hypothesis_preview": text_preview(item["hypothesis_hindi"], 180),
                }
            )


def parse_args() -> argparse.Namespace:
    project_dir = default_project_dir()
    parser = argparse.ArgumentParser(
        description=(
            "Run inference on every test segment and produce legal-domain error "
            "categorization for the Indian court case English-Hindi corpus."
        )
    )
    parser.add_argument("--test-jsonl", default=str(project_dir / "data" / "test.jsonl"))
    parser.add_argument("--english-dir", default=str(project_dir / "english" / "clean"))
    parser.add_argument("--hindi-dir", default=str(project_dir / "hindi" / "clean"))
    parser.add_argument("--output-dir", default=str(project_dir / "results" / "test_error_analysis"))
    parser.add_argument("--predictions-jsonl", default=None, help="Analyze existing predictions instead of running inference.")
    parser.add_argument("--model-name", default="facebook/mbart-large-50")
    parser.add_argument("--model-path", default=None, help="Saved full model or LoRA adapter path. Defaults to the base model.")
    parser.add_argument("--source-lang", default="en_XX")
    parser.add_argument("--target-lang", default="hi_IN")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, cuda:0, etc.")
    parser.add_argument("--fp16", action="store_true", help="Use fp16 on CUDA during generation.")
    parser.add_argument("--max-input-length", type=int, default=512)
    parser.add_argument("--generation-max-length", type=int, default=512)
    parser.add_argument("--num-beams", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--dev-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--limit", type=int, default=0, help="Optional debug limit; 0 means full test set.")
    parser.add_argument("--save-generated-splits", action="store_true", help="Persist regenerated train/dev/test JSONL files.")
    parser.add_argument("--examples-per-category", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_dir = default_project_dir()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_dir / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    records, split_info = load_test_records(args, project_dir)
    if not records:
        raise ValueError("No test records available for inference/error analysis.")

    if args.predictions_jsonl:
        predictions_path = Path(args.predictions_jsonl)
        if not predictions_path.is_absolute():
            predictions_path = project_dir / predictions_path
        predictions = load_predictions(predictions_path, records)
        model_info: Dict[str, Any] = {
            "mode": "analysis_existing_predictions",
            "predictions_jsonl": str(predictions_path),
            "base_model": args.model_name,
            "model_path": args.model_path,
        }
    else:
        predictions, model_info = run_inference(records, args)
        predictions_path = output_dir / "predictions.jsonl"
        write_jsonl(predictions_path, predictions)
        model_info["predictions_jsonl"] = str(predictions_path)

    references = [str(row["reference_hindi"]) for row in predictions]
    hypotheses = [str(row["hypothesis_hindi"]) for row in predictions]
    metrics = compute_metrics(references, hypotheses)

    analyses: List[Dict[str, Any]] = []
    for row, bleu, chrf in zip(predictions, metrics["sentence_bleu_scores"], metrics["sentence_chrf_scores"]):
        analyses.append(analyze_segment(row, float(bleu), float(chrf)))

    summary = summarize_analyses(analyses, metrics, split_info, model_info)

    write_jsonl(output_dir / "segment_error_analysis.jsonl", analyses)
    write_flat_analysis_csv(output_dir / "segment_error_analysis.csv", analyses)
    write_json(output_dir / "error_summary.json", summary)
    write_category_csv(output_dir / "error_summary.csv", summary)

    report = build_report(summary, analyses, args.examples_per_category)
    report_path = output_dir / "error_analysis_report.md"
    report_path.write_text(report, encoding="utf-8")

    print("\nFull-test inference and error analysis complete.")
    print(f"Predictions:      {model_info.get('predictions_jsonl')}")
    print(f"Segment analysis: {output_dir / 'segment_error_analysis.jsonl'}")
    print(f"Summary JSON:     {output_dir / 'error_summary.json'}")
    print(f"Summary CSV:      {output_dir / 'error_summary.csv'}")
    print(f"Paper report:     {report_path}")
    print(f"Corpus BLEU/chrF: {metrics['avg_bleu']} / {metrics['avg_chrf']}")


if __name__ == "__main__":
    main()
