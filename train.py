"""
LoRA Fine-tuning Script for Qwen2-1.8B
Train on generated Q&A pairs from patient data using 4-bit quantization
"""

import argparse
import json
import logging
from pathlib import Path
import sys

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType
from datasets import Dataset

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="LoRA fine-tuning for Qwen2-1.8B")
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        default="Qwen/Qwen2-1.8B",
        help="Model identifier from HuggingFace or local path",
    )
    parser.add_argument(
        "--use_lora",
        action="store_true",
        help="Use LoRA for parameter-efficient fine-tuning",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./models/lora_adapter",
        help="Output directory for trained model",
    )
    parser.add_argument(
        "--training_data",
        type=str,
        default="./data/training_data.json",
        help="Path to training data JSON file",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=4,
        help="Training batch size per device",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=2e-4,
        help="Learning rate",
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=512,
        help="Maximum sequence length",
    )
    return parser.parse_args()


def load_training_data(data_path: str) -> list:
    """Load training pairs from JSON file"""
    path = Path(data_path)
    if not path.exists():
        logger.error(f"Training data not found at {data_path}")
        logger.info("Run: python -m backend.export_data")
        sys.exit(1)

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} training pairs")
    return data


def format_training_sample(sample: dict, tokenizer) -> dict:
    """Format a training sample for Qwen2 chat format"""
    instruction = sample.get("instruction", "")
    response = sample.get("response", "")

    # Qwen2 chat template format
    messages = [
        {"role": "user", "content": instruction},
        {"role": "assistant", "content": response}
    ]

    # Apply chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )

    return {"text": text}


def prepare_dataset(data: list, tokenizer, max_length: int) -> Dataset:
    """Prepare dataset for training"""
    formatted_data = [format_training_sample(s, tokenizer) for s in data]

    dataset = Dataset.from_list(formatted_data)

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=max_length,
        )

    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"]
    )

    # Add labels for causal LM
    tokenized_dataset = tokenized_dataset.map(
        lambda x: {"labels": x["input_ids"]}
    )

    return tokenized_dataset


def setup_lora_model(model, use_lora: bool):
    """Setup LoRA configuration for parameter-efficient fine-tuning"""
    if not use_lora:
        logger.info("LoRA disabled - full fine-tuning")
        return model

    logger.info("Setting up LoRA for parameter-efficient fine-tuning")

    # LoRA configuration
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=16,  # LoRA rank
        lora_alpha=32,  # LoRA alpha
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # Qwen2 attention modules
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model


def main():
    args = parse_args()

    logger.info("=" * 50)
    logger.info("SPECTRA - LoRA Fine-tuning")
    logger.info("=" * 50)
    logger.info(f"Model: {args.model_name_or_path}")
    logger.info(f"LoRA: {args.use_lora}")
    logger.info(f"Output: {args.output_dir}")
    logger.info(f"Training data: {args.training_data}")
    logger.info(f"Epochs: {args.epochs}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Learning rate: {args.learning_rate}")
    logger.info("=" * 50)

    # Load training data
    training_data = load_training_data(args.training_data)

    # Configure 4-bit quantization for memory efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    logger.info(f"Loading model: {args.model_name_or_path}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name_or_path,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model with quantization
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name_or_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)

    # Setup LoRA
    model = setup_lora_model(model, args.use_lora)

    # Prepare dataset
    logger.info("Preparing dataset...")
    train_dataset = prepare_dataset(training_data, tokenizer, args.max_length)

    # Split into train/validation
    split_dataset = train_dataset.train_test_split(test_size=0.15, seed=42)
    train_dataset = split_dataset["train"]
    eval_dataset = split_dataset["test"]

    logger.info(f"Training samples: {len(train_dataset)}")
    logger.info(f"Validation samples: {len(eval_dataset)}")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        fp16=False,
        bf16=True,  # Use bfloat16 for stability
        logging_steps=10,
        save_steps=500,
        save_total_limit=2,
        eval_strategy="steps",
        eval_steps=500,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",  # Disable wandb/tensorboard
        push_to_hub=False,
    )

    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        padding=True,
        return_tensors="pt"
    )

    # Create Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    # Train
    logger.info("Starting training...")
    trainer.train()

    # Save the model
    logger.info(f"Saving model to {args.output_dir}")
    trainer.save_model(args.output_dir)

    # Save tokenizer
    tokenizer.save_pretrained(args.output_dir)

    logger.info("=" * 50)
    logger.info("Training complete!")
    logger.info(f"Model saved to: {args.output_dir}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
