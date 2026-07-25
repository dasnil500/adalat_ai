# Requirement Mapping

This file maps the assignment requirements to the current codebase. It avoids placeholder metrics; use generated JSON files for actual results after running the pipeline.

## 1. Evaluate and Optimize Tokenization

Implemented in `tokenizer_analysis/analyzer.py` and `tokenizer_analysis/run_analysis.py`.

Tokenizer analysis lives in its own top-level folder, disjoint from `main_pipeline.py`, `src/model_trainer.py`, and `src/evaluation.py`. Generated tokenizer-only artifacts are written to `tokenizer_analysis/results/`.

- Compares multiple available tokenizers: mBERT, mBART-50, XLM-R, IndicBERT, and optional Tiktoken.
- Reports token-per-word, characters-per-token, total tokens, and Hindi overhead versus English.
- Selects the tokenizer with the lowest measured Hindi tokens-per-word among successfully loaded candidates.
- Does not perform vocabulary merging by default. That is listed as a future extension in the generated report.

## 2. Prepare the Dataset

Implemented in `src/data_loader.py`.

- Loads 30 local English-Hindi judgment text pairs by filename stem.
- Applies light whitespace cleanup while preserving paragraph breaks.
- Splits at document level into 80/10/10 train/dev/test to reduce leakage.
- Splits documents into visible legal paragraphs.
- Aligns English/Hindi records with sequence-aware paragraph-number matching.
- Uses block-order fallback only when the cleaned English/Hindi paragraph blocks already line up safely.

## 3. Model Adaptation

Implemented in `src/model_trainer.py`.

- Default base model: `facebook/mbart-large-50`.
- Default language direction: English `en_XX` to Hindi `hi_IN`.
- LoRA is applied to `q_proj` and `v_proj` attention projections.
- Training limits are configurable for single-GPU experiments.
- mBART generation uses `forced_bos_token_id` for the Hindi target language when supported by the tokenizer.

## 4. Evaluation

Implemented in `src/evaluation.py`.

- Computes corpus BLEU and chrF through `sacrebleu` when available.
- Provides internal sentence-level fallback metrics for qualitative examples.
- Extracts coarse legal term groups in English/Hindi, such as appeal, court, judgment, section, and act.
- Supports baseline-before-LoRA versus adapted comparison when baseline hypotheses are generated.

## 5. Reflection

Implemented in `main_pipeline.py` report generation.

- `results/REPORT.json` records which training/evaluation phases were actually run.
- Includes limitations around small corpus size, extracted paragraph numbering, and missing tokenizer vocabulary extension.
- Includes next steps for scaling to more judgments and more Indic languages.

## Recommended Submission Flow

1. Run `python tokenizer_analysis/run_analysis.py` to generate tokenizer metrics from the separate tokenizer pipeline.
2. Run `python main_pipeline.py --skip-training` to verify data preparation and produce the training report shell.
3. Run `python main_pipeline.py` on a GPU machine for LoRA adaptation and evaluation.
4. Submit the code plus generated `results/REPORT.json`, `tokenizer_analysis/results/tokenizer_analysis.json`, and `results/evaluation_results.json` if training was run.
