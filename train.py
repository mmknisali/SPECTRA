"""
LoRA Fine-tuning Script for Qwen2-1.8B
Train on generated Q&A pairs from patient data
"""

import argparse
import json
from pathlib import Path
import sys

def parse_args():
    parser = argparse.ArgumentParser(description="LoRA fine-tuning for Qwen2-1.8B")
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        default="Qwen/Qwen2-1.8B",
        help="Model identifier from HuggingFace or local path"
    )
    parser.add_argument(
        "--use_lora",
        action="store_true",
        help="Use LoRA for parameter-efficient fine-tuning"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./models/lora_adapter",
        help="Output directory for trained model"
    )
    parser.add_argument(
        "--training_data",
        type=str,
        default="./data/training_data.json",
        help="Path to training data JSON file"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=4,
        help="Training batch size per device"
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=2e-4,
        help="Learning rate"
    )
    return parser.parse_args()


def load_training_data(data_path: str) -> list:
    """Load training pairs from JSON file"""
    path = Path(data_path)
    if not path.exists():
        print(f"Training data not found at {data_path}")
        print("Run: python -m backend.export_data")
        sys.exit(1)

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} training pairs")
    return data


def format_instruction_sample(sample: dict) -> dict:
    """Format a training sample for instruction tuning"""
    return {
        "instruction": sample["instruction"],
        "input": "",
        "output": sample["response"]
    }


def main():
    args = parse_args()

    print("=" * 50)
    print("SPECTRA - LoRA Fine-tuning")
    print("=" * 50)
    print(f"Model: {args.model_name_or_path}")
    print(f"LoRA: {args.use_lora}")
    print(f"Output: {args.output_dir}")
    print(f"Training data: {args.training_data}")
    print("=" * 50)

    # Load training data
    training_data = load_training_data(args.training_data)
    formatted_data = [format_instruction_sample(s) for s in training_data]

    # Note: Actual training requires GPU and transformers/peft/accelerate
    # This is a structure placeholder matching the documented CLI
    print(f"\nPrepared {len(formatted_data)} samples for training")
    print("\nTo start training with accelerate, run:")
    print(f"  accelerate launch train.py \\")
    print(f"    --model_name_or_path {args.model_name_or_path} \\")
    print(f"    --use_lora \\")
    print(f"    --output_dir {args.output_dir}")
    print("\nNote: Full training implementation requires:")
    print("  - transformers, peft, accelerate, bitsandbytes")
    print("  - GPU with 6GB+ VRAM (vast.ai recommended)")

    # Save formatted data for reference
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    formatted_path = output_path / "formatted_training_data.json"
    with open(formatted_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_data, f, ensure_ascii=False, indent=2)

    print(f"\nFormatted training data saved to: {formatted_path}")


if __name__ == "__main__":
    main()
