# models/llm/finetuner.py

import os
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Seq2SeqTrainer, Seq2SeqTrainingArguments, DataCollatorForSeq2Seq

def finetune_parser_model(
    model_name="t5-small",
    dataset_path="/mnt/linux-data/project/code/datasets/parser_examples.jsonl",
    output_dir="/mnt/linux-data/project/code/models/trained_models/parser-model",
    max_input_length=512,
    max_target_length=512,
    epochs=5,
    batch_size=8
):
    # Load base model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    # Load dataset
    raw_dataset = load_dataset("json", data_files=dataset_path, split="train")

    # Tokenization
    def preprocess(example):
        input_enc = tokenizer(example["input"], max_length=max_input_length, truncation=True)
        target_enc = tokenizer(example["output"], max_length=max_target_length, truncation=True)
        input_enc["labels"] = target_enc["input_ids"]
        return input_enc

    tokenized_dataset = raw_dataset.map(preprocess, remove_columns=["input", "output"])

    # Training arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        num_train_epochs=epochs,
        save_strategy="epoch",
        logging_strategy="epoch",
        evaluation_strategy="no",
        save_total_limit=1,
        fp16=False,
        learning_rate=5e-5,
        overwrite_output_dir=True,
    )

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"✅ Fine-tuned model saved to {output_dir}")
