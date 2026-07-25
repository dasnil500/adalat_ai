"""
LoRA-based adaptation for English-to-Hindi legal translation.
"""

from __future__ import annotations

import os
from typing import List, Sequence, Tuple
import numpy as np
import evaluate
import torch
from datasets import Dataset
from peft import LoraConfig, PeftModel, TaskType, get_peft_model
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)

bleu_metric = evaluate.load("sacrebleu")
chrf_metric = evaluate.load("chrf")

def _pair_from_record(record: object) -> Tuple[str, str]:
    if isinstance(record, dict):
        return str(record["english"]), str(record["hindi"])
    english, hindi = record  # type: ignore[misc]
    return str(english), str(hindi)


class TranslationTrainer:
    """Small-scale seq2seq trainer with optional LoRA adapters."""

    def __init__(
        self,
        model_name: str = "facebook/mbart-large-50",
        source_lang: str = "en_XX",
        target_lang: str = "hi_IN",
        device: str | None = None,
    ):
        self.model_name = model_name
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.using_lora = False

        print(f"Loading model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.model.to(self.device)
        self._set_source_language()

        print(f"Model loaded on {self.device}")
        print(f"Model parameters: {self.model.num_parameters():,}")

    def _set_source_language(self) -> None:
        if hasattr(self.tokenizer, "src_lang"):
            self.tokenizer.src_lang = self.source_lang
        if hasattr(self.tokenizer, "tgt_lang"):
            self.tokenizer.tgt_lang = self.target_lang

    def _forced_bos_token_id(self):
        lang_code_to_id = getattr(self.tokenizer, "lang_code_to_id", None)
        if isinstance(lang_code_to_id, dict):
            return lang_code_to_id.get(self.target_lang)
        return None

    def setup_lora(self, lora_r: int = 8, lora_alpha: int = 16, lora_dropout: float = 0.1):
        """Apply LoRA to attention projections for parameter-efficient tuning."""
        lora_config = LoraConfig(
            r=lora_r,
            lora_alpha=lora_alpha,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=lora_dropout,
            bias="none",
            task_type=TaskType.SEQ_2_SEQ_LM,
        )
        self.model = get_peft_model(self.model, lora_config)
        self.using_lora = True
        self.model.print_trainable_parameters()
        return self.model

    def prepare_dataset(self, data_records: Sequence[object], max_length: int = 512) -> Dataset:
        """Convert split records to a Hugging Face Dataset."""
        pairs = [_pair_from_record(record) for record in data_records]
        dataset = Dataset.from_dict(
            {
                "english": [pair[0] for pair in pairs],
                "hindi": [pair[1] for pair in pairs],
            }
        )

        def preprocess_function(examples):
            self._set_source_language()
            model_inputs = self.tokenizer(
                examples["english"],
                max_length=max_length,
                truncation=True,
            )
            try:
                labels = self.tokenizer(
                    text_target=examples["hindi"],
                    max_length=max_length,
                    truncation=True,
                )
            except TypeError:
                with self.tokenizer.as_target_tokenizer():
                    labels = self.tokenizer(
                        examples["hindi"],
                        max_length=max_length,
                        truncation=True,
                    )
            model_inputs["labels"] = labels["input_ids"]
            return model_inputs

        return dataset.map(preprocess_function, batched=True, remove_columns=["english", "hindi"])

    def compute_metrics(self, eval_preds):
        """
        Compute BLEU and chrF on the validation set.
        """

        predictions, labels = eval_preds

        if isinstance(predictions, tuple):
            predictions = predictions[0]

        # Decode predictions
        decoded_preds = self.tokenizer.batch_decode(
            predictions,
            skip_special_tokens=True,
        )

        # Replace ignored tokens (-100)
        labels = np.where(labels != -100, labels, self.tokenizer.pad_token_id)

        decoded_labels = self.tokenizer.batch_decode(
            labels,
            skip_special_tokens=True,
        )

        # SacreBLEU expects list of references
        references = [[label] for label in decoded_labels]

        bleu = bleu_metric.compute(
            predictions=decoded_preds,
            references=references,
        )["score"]

        chrf = chrf_metric.compute(
            predictions=decoded_preds,
            references=references,
        )["score"]

        return {
            "bleu": bleu,
            "chrf": chrf,
        }

    def train(
        self,
        train_data,
        dev_data,
        output_dir="./checkpoints",
        num_epochs=2,
        batch_size=4,
        learning_rate=5e-4,
        max_length=512,
        gradient_accumulation_steps=1,
    ):
        """Fine-tune the model using either full fine-tuning or LoRA."""

        if not train_data:
            raise ValueError("train_data is empty")
        if not dev_data:
            raise ValueError("dev_data is empty")

        train_dataset = self.prepare_dataset(train_data, max_length)
        eval_dataset = self.prepare_dataset(dev_data, max_length)

        training_args = Seq2SeqTrainingArguments(
            output_dir=output_dir,
            eval_strategy="epoch",
            save_strategy="epoch",
            learning_rate=learning_rate,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            num_train_epochs=num_epochs,
            save_total_limit=1,
            load_best_model_at_end=True,
            metric_for_best_model="bleu",
            greater_is_better=True,
            warmup_steps=20,
            logging_steps=10,
            predict_with_generate=True,
            report_to=[],
            fp16=self.device == "cuda",
        )

        data_collator = DataCollatorForSeq2Seq(
            self.tokenizer,
            model=self.model,
            pad_to_multiple_of=8 if self.device == "cuda" else None,
        )

        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
            compute_metrics=self.compute_metrics,
        )

        print("=" * 70)
        if self.using_lora:
            print("Training mode : LoRA Fine-tuning")
            self.model.print_trainable_parameters()
        else:
            print("Training mode : Full Fine-tuning")
            total = sum(p.numel() for p in self.model.parameters())
            trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            print(f"Trainable parameters : {trainable:,}")
            print(f"Total parameters     : {total:,}")
            print(f"Trainable percentage : {100 * trainable / total:.2f}%")
        print("=" * 70)

        print("Starting training...")
        return trainer.train()


    # Replace save_model() with:

    def save_model(self, path: str):
        if self.using_lora:
            print("Saving LoRA adapter...")
        else:
            print("Saving fully fine-tuned model...")

        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        print(f"Model saved to {path}")


    # Replace load_model() with:

    def load_model(self, path: str, base_model_name: str | None = None):
        adapter_config = os.path.join(path, "adapter_config.json")

        if os.path.exists(adapter_config):
            base_name = base_model_name or self.model_name
            base_model = AutoModelForSeq2SeqLM.from_pretrained(base_name)
            self.model = PeftModel.from_pretrained(base_model, path)
            self.tokenizer = AutoTokenizer.from_pretrained(path)
            self.using_lora = True
            print("Loaded LoRA adapter.")
        else:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(path)
            self.tokenizer = AutoTokenizer.from_pretrained(path)
            self.using_lora = False
            print("Loaded fully fine-tuned model.")

        self.model.to(self.device)
        self._set_source_language()
        print(f"Model loaded from {path}")


    def generate_translation(self, text: str, max_length: int = 512, num_beams: int = 4) -> str:
        """Generate a Hindi translation for one English text."""
        self._set_source_language()
        inputs = self.tokenizer(
            text,
            max_length=max_length,
            truncation=True,
            return_tensors="pt",
        ).to(self.device)

        generate_kwargs = {
            "max_length": max_length,
            "num_beams": num_beams,
            "early_stopping": True,
        }
        forced_bos_token_id = self._forced_bos_token_id()
        if forced_bos_token_id is not None:
            generate_kwargs["forced_bos_token_id"] = forced_bos_token_id

        with torch.no_grad():
            outputs = self.model.generate(**inputs, **generate_kwargs)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    # def save_model(self, path: str) -> None:
    #     """Save model or LoRA adapter and tokenizer."""
    #     self.model.save_pretrained(path)
    #     self.tokenizer.save_pretrained(path)
    #     print(f"Model saved to {path}")

    # def load_model(self, path: str, base_model_name: str | None = None) -> None:
    #     """
    #     Load either a full seq2seq model or a PEFT adapter.

    #     For LoRA adapter folders, pass base_model_name or rely on self.model_name.
    #     """
    #     adapter_config = os.path.join(path, "adapter_config.json")
    #     if os.path.exists(adapter_config):
    #         base_name = base_model_name or self.model_name
    #         base_model = AutoModelForSeq2SeqLM.from_pretrained(base_name)
    #         self.model = PeftModel.from_pretrained(base_model, path)
    #         self.tokenizer = AutoTokenizer.from_pretrained(path)
    #     else:
    #         self.model = AutoModelForSeq2SeqLM.from_pretrained(path)
    #         self.tokenizer = AutoTokenizer.from_pretrained(path)
    #     self.model.to(self.device)
    #     self._set_source_language()
    #     print(f"Model loaded from {path}")


if __name__ == "__main__":
    print("Model trainer module. Import it from main_pipeline.py.")
