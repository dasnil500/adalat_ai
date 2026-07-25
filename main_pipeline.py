from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, cast


reconfigure_stdout = getattr(sys.stdout, "reconfigure", None)
if callable(reconfigure_stdout):
    reconfigure_stdout(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.data_loader import (  # noqa: E402
    create_data_split,
    load_jsonl_split,
    load_parallel_texts,
    print_dataset_summary,
    record_to_pair,
    save_splits_to_jsonl,
)
from src.evaluation import (  # noqa: E402
    analyze_qualitative_examples,
    compare_before_after,
    evaluate_translations,
    export_evaluation,
    print_evaluation_report,
    print_qualitative_analysis,
)


def run_data_preparation(english_texts: List[str], hindi_texts: List[str], data_dir: str):
    print("\n" + "=" * 70)
    print("PHASE 1: DATA PREPARATION")
    print("=" * 70)

    split_data = create_data_split(english_texts, hindi_texts)
    print_dataset_summary(split_data)
    save_splits_to_jsonl(split_data, data_dir)
    return split_data


def _generate_batch(trainer, records: Sequence[object], max_length: int) -> List[str]:
    hypotheses = []
    for index, record in enumerate(records, start=1):
        english, _ = record_to_pair(record)
        hypotheses.append(trainer.generate_translation(english, max_length=max_length))
        if index % 5 == 0:
            print(f"Generated {index}/{len(records)} translations")
    return hypotheses


def run_model_training(
    args,
    data_dir: str,
    checkpoint_dir: str,
    test_records: Sequence[object],
):
    print("\n" + "=" * 70)
    print("PHASE 2: MODEL ADAPTATION")
    print("=" * 70)

    from src.model_trainer import TranslationTrainer

    train_data = load_jsonl_split(os.path.join(data_dir, "train.jsonl"))
    dev_data = load_jsonl_split(os.path.join(data_dir, "dev.jsonl"))

    trainer = TranslationTrainer(
        model_name=args.model_name,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
    )

    # ------------------------------------------------------------
    # Generate baseline translations BEFORE any adaptation
    # ------------------------------------------------------------
    baseline_records = list(test_records)
    baseline_hypotheses = None

    if baseline_records:
        print(
            f"Generating {len(baseline_records)} baseline translations "
            "before fine-tuning..."
        )
        baseline_hypotheses = _generate_batch(
            trainer,
            baseline_records,
            args.max_length,
        )

    # ------------------------------------------------------------
    # Select fine-tuning strategy
    # ------------------------------------------------------------
    if args.finetune_method == "lora":
        print("\nUsing LoRA fine-tuning...\n")

        trainer.setup_lora(
            lora_r=args.lora_rank,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
        )

    elif args.finetune_method == "full":
        print("\nUsing FULL model fine-tuning...\n")

    else:
        raise ValueError(
            f"Unknown fine-tuning method: {args.finetune_method}"
        )

    # ------------------------------------------------------------
    # Train
    # ------------------------------------------------------------
    trainer.train(
        train_data=train_data,
        dev_data=dev_data,
        output_dir=checkpoint_dir,
        num_epochs=args.num_epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_length=args.max_length,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
    )

    # ------------------------------------------------------------
    # Save
    # ------------------------------------------------------------
    trainer.save_model(checkpoint_dir)

    return trainer, checkpoint_dir, baseline_hypotheses


def _default_model_path(project_dir: Path) -> Path:
    candidates = [
        project_dir / "checkpoints" / "final_model",
        project_dir / "checkpoints" / "final_model_lora",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def run_evaluation(
    trainer,
    test_records: List[object],
    results_dir: str,
    max_length: int,
    baseline_hypotheses: Optional[List[str]] = None,
) -> Dict[str, object]:
    print("\n" + "=" * 70)
    print("PHASE 3: EVALUATION")
    print("=" * 70)

    eval_records = list(test_records)
    if not eval_records:
        raise ValueError("No test records available for evaluation")

    sources = [record_to_pair(record)[0] for record in eval_records]
    references = [record_to_pair(record)[1] for record in eval_records]
    hypotheses = _generate_batch(trainer, eval_records, max_length=max_length)

    eval_results = evaluate_translations(references, hypotheses)
    print_evaluation_report(eval_results)

    aligned_baseline = None
    before_after = None
    if baseline_hypotheses:
        aligned_count = min(len(baseline_hypotheses), len(references))
        aligned_baseline = baseline_hypotheses[:aligned_count]
        before_after = compare_before_after(
            references[:aligned_count],
            aligned_baseline,
            hypotheses[:aligned_count],
        )
        
        print("\n" + "="*70)
        print("BEFORE vs AFTER LoRA")
        print("="*70)

        print(f"Baseline BLEU : {before_after['baseline']['avg_bleu']:.2f}")
        print(f"Adapted  BLEU : {before_after['adapted']['avg_bleu']:.2f}")
        print(f"Δ BLEU        : {before_after['delta_bleu']:+.2f}")

        print()

        print(f"Baseline chrF : {before_after['baseline']['avg_chrf']:.2f}")
        print(f"Adapted  chrF : {before_after['adapted']['avg_chrf']:.2f}")
        print(f"Δ chrF        : {before_after['delta_chrf']:+.2f}")

    qualitative = analyze_qualitative_examples(
        references=references,
        hypotheses=hypotheses,
        sources=sources,
        baseline_hypotheses=aligned_baseline,
        num_examples=5,
    )
    print_qualitative_analysis(qualitative)

    output_path = os.path.join(results_dir, "evaluation_results.json")
    export_evaluation(eval_results, qualitative, output_path, before_after=before_after)

    return {
        "automatic_metrics": eval_results,
        "qualitative_examples": qualitative,
        "before_after": before_after,
    }


def summarize_tokenizer_analysis(project_dir: Path) -> Dict[str, object]:
    """Point to the standalone tokenizer-analysis artifact without running it here."""
    script_path = project_dir / "tokenizer_analysis" / "run_analysis.py"
    output_path = project_dir / "tokenizer_analysis" / "results" / "tokenizer_analysis.json"
    return {
        "status": "external_run_available" if output_path.exists() else "not_run",
        "run_from": str(script_path),
        "output_path": str(output_path),
    }


def generate_report(
    project_dir: Path,
    split_info: Dict[str, object],
    model_info: Dict[str, object],
    eval_results: Optional[Dict[str, object]],
    results_dir: str,
) -> Dict[str, object]:
    print("\n" + "=" * 70)
    print("PHASE 4: REPORT")
    print("=" * 70)

    report = {
        "title": "ML Assignment Report: English-to-Hindi Legal Text Translation",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "objective": {
            "summary": "Prototype a translation system for Indian court judgments with lightweight adaptation and separate tokenizer-efficiency analysis.",
            "language_pair": "English to Hindi",
            "domain": "Indian High Court judgments",
        },
        "dataset": {
            "source": "Local corpus of 30 English-Hindi judgment pairs",
            "split_info": split_info,
            "preprocessing": [
                "UTF-8 text loading",
                "Whitespace normalization",
                "Document-level train/dev/test split",
                "Wrapped-line cleanup, legal paragraph splitting, and sequence-aware alignment",
            ],
            "alignment_note": "English and Hindi records are aligned with sequence-aware paragraph-number matching after wrapped-line cleanup. Block-order fallback is used only when the cleaned paragraph blocks already line up safely.",
        },
        "tokenizer_analysis": summarize_tokenizer_analysis(project_dir),
        "model_adaptation": model_info,
        "evaluation": eval_results or {"status": "not_run"},
    }

    output_path = os.path.join(results_dir, "REPORT.json")
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(f"Report saved to {output_path}")
    return report


def parse_args():
    project_dir = Path(__file__).resolve().parent
    root_dir = project_dir.parent

    parser = argparse.ArgumentParser(description="Legal text training and evaluation pipeline")
    parser.add_argument("--english-dir", default=str(root_dir / "adalat_ai" / "english" / "clean"))
    parser.add_argument("--hindi-dir", default=str(root_dir / "adalat_ai" / "hindi" / "clean"))
    parser.add_argument("--skip-training", action="store_true")
    parser.add_argument("--model-name", default="facebook/mbart-large-50")
    parser.add_argument("--source-lang", default="en_XX")
    parser.add_argument("--target-lang", default="hi_IN")
    # parser.add_argument("--baseline-limit", type=int, default=0, help="0 disables baseline before/after")
    parser.add_argument(
        "--model-path",
        default=None,
        help="Path to a saved adapter/model directory to use when --skip-training is set",
    )
    parser.add_argument("--num-epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.1)
    parser.add_argument(
        "--finetune-method",
        choices=["lora", "full"],
        default="lora",
        help="Fine-tuning strategy: parameter-efficient LoRA or full model fine-tuning.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    checkpoint_dir = project_dir / "checkpoints"
    results_dir = project_dir / "results"

    data_dir.mkdir(exist_ok=True)
    checkpoint_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)

    print("\n" + "=" * 70)
    print("LEGAL TEXT TRAINING PIPELINE")
    print("=" * 70)
    print(f"English directory: {args.english_dir}")
    print(f"Hindi directory:   {args.hindi_dir}")
    print("Tokenizer analysis is separate: tokenizer_analysis/run_analysis.py")

    english_texts, hindi_texts = load_parallel_texts(args.english_dir, args.hindi_dir)

    split_data: Dict[str, object] = run_data_preparation(english_texts, hindi_texts, str(data_dir))
    test_records = cast(List[object], split_data["test"])

    trainer = None
    baseline_hypotheses = None
    model_info: Dict[str, object] = {
        "status": "not_run",
        "base_model": args.model_name,
        "adaptation_method": "LoRA",
    }

    if not args.skip_training:
        trainer, final_model_path, baseline_hypotheses = run_model_training(
            args,
            str(data_dir),
            str(checkpoint_dir / "final_model"),
            test_records,
        )
        model_info.update(
            {
                "status": "run",
                "base_model": args.model_name,
                "adapter_path": final_model_path,
                "lora": {
                    "rank": args.lora_rank,
                    "alpha": args.lora_alpha,
                    "dropout": args.lora_dropout,
                },
                "training_subset_records": "all",
                "epochs": args.num_epochs,
                "max_length": args.max_length,
            }
        )
    else:
        model_path = Path(args.model_path) if args.model_path else _default_model_path(project_dir)
        if not model_path.exists():
            raise FileNotFoundError(
                f"No saved model found for --skip-training. Checked: {model_path}"
            )

        print(f"Skipping model training; loading saved model from {model_path}")
        from src.model_trainer import TranslationTrainer

        trainer = TranslationTrainer(
            model_name=args.model_name,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
        )
        trainer.load_model(str(model_path), base_model_name=args.model_name)
        model_info.update(
            {
                "status": "loaded",
                "base_model": args.model_name,
                "adapter_path": str(model_path),
                "mode": "skip_training",
            }
        )

    eval_results = None
    if trainer is not None:
        eval_results = run_evaluation(
            trainer,
            test_records,
            str(results_dir),
            max_length=args.max_length,
            baseline_hypotheses=baseline_hypotheses,
        )
    else:
        print("Skipping evaluation because no adapted model is available")

    generate_report(
        project_dir=project_dir,
        split_info=cast(Dict[str, object], split_data["split_info"]),
        model_info=model_info,
        eval_results=eval_results,
        results_dir=str(results_dir),
    )

    print("\nPipeline finished.")
    print(f"Data:    {data_dir}")
    print(f"Results: {results_dir}")
    if model_info.get("status") == "run":
        print(f"Adapter: {model_info['adapter_path']}")


if __name__ == "__main__":
    main()
