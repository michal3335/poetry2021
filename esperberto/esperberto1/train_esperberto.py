#!/usr/bin/env python
# coding: utf-8
# import os
import torch
from pathlib import Path
from tokenizers import ByteLevelBPETokenizer
# from tokenizers.processors import BertProcessing
from transformers import RobertaConfig
from transformers import RobertaTokenizerFast
from transformers import RobertaForMaskedLM
from transformers import LineByLineTextDataset
from transformers import DataCollatorForLanguageModeling
from transformers import Trainer, TrainingArguments
# from transformers import pipeline
from typing import Dict, List, Optional
from torch.utils.data.dataset import Dataset

data_path = Path('data/esperberto')
dataset_path = data_path / 'dataset'
tokenizer_path = data_path / 'tokenizer'
run_path = Path('runs/esperberto') / 'run_8'

# ## 1. Find a dataset
# os.system('wget -c https://cdn-datasets.huggingface.co/EsperBERTo/data/oscar.eo.txt')

# ## 2. Train a tokenizer
# paths = [str(x) for x in dataset_path.glob("**/*.txt")]
# paths = [str(dataset_path / 'oscar.eo.1000.txt')]

# tokenizer = ByteLevelBPETokenizer()
# # 52_000
# tokenizer.train(files=paths, vocab_size=10_000, min_frequency=2, special_tokens=[
#     "<s>",
#     "<pad>",
#     "</s>",
#     "<unk>",
#     "<mask>",
# ])
# tokenizer_path.mkdir(parents=True, exist_ok=True)
# tokenizer.save_model(str(tokenizer_path))

# tokenizer = ByteLevelBPETokenizer(
#     str(tokenizer_path / "vocab.json"),
#     str(tokenizer_path / "merges.txt"),
# )

# tokenizer._tokenizer.post_processor = BertProcessing(
#     ("</s>", tokenizer.token_to_id("</s>")),
#     ("<s>", tokenizer.token_to_id("<s>")),
# )
# tokenizer.enable_truncation(max_length=128)

# print(tokenizer.encode("Mi estas Julien."))
# print(tokenizer.encode("Mi estas Julien.").tokens)

# Now let's re-create our tokenizer in transformers
tokenizer = RobertaTokenizerFast.from_pretrained(tokenizer_path, max_len=128)

# ## 3. Train a language model from scratch
print(f'cuda: {torch.cuda.is_available()}')

# config = RobertaConfig(
#     vocab_size=52_000,
#     max_position_embeddings=514,
#     num_attention_heads=12,
#     num_hidden_layers=6,
#     type_vocab_size=1,
# )

# config = RobertaConfig(
#     vocab_size=tokenizer._tokenizer.get_vocab_size(),
#     hidden_size=240,
#     intermediate_size=2048,
#     max_position_embeddings=514,
#     num_attention_heads=12,
#     num_hidden_layers=6,
#     type_vocab_size=1,
#     bos_token_id=tokenizer._tokenizer.token_to_id("<s>"),
#     eos_token_id=tokenizer._tokenizer.token_to_id("</s>"),
#     pad_token_id=tokenizer._tokenizer.token_to_id("<pad>"),
#     attention_probs_dropout_prob=0.0,
#     hidden_dropout_prob=0.0,
# )

# SmallBERTa
config = RobertaConfig(
    vocab_size=tokenizer._tokenizer.get_vocab_size(),
    hidden_size=128,
    intermediate_size=256,
    max_position_embeddings=256,
    num_attention_heads=1,
    num_hidden_layers=1,
    type_vocab_size=1,
    bos_token_id=tokenizer._tokenizer.token_to_id("<s>"),
    eos_token_id=tokenizer._tokenizer.token_to_id("</s>"),
    pad_token_id=tokenizer._tokenizer.token_to_id("<pad>"),
    attention_probs_dropout_prob=0.1,
    hidden_dropout_prob=0.3,
)

print(config)

# model = RobertaForMaskedLM(config=config)
model = RobertaForMaskedLM.from_pretrained('runs/esperberto/run_7/model')
print(f'model.num_parameters(): {model.num_parameters()}')

dataset = LineByLineTextDataset(
    tokenizer=tokenizer,
    file_path=dataset_path / "oscar.eo.1000x10.txt",
    block_size=128,
)

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer, mlm=True, mlm_probability=0.15
)

training_args = TrainingArguments(
    output_dir=str(run_path),
    logging_dir=str(run_path),
    overwrite_output_dir=True,
    num_train_epochs=5000,
    per_device_train_batch_size=1400,
    logging_steps=100,
    eval_steps=1000,
    save_steps=2500,
    save_total_limit=2,
    learning_rate=1e-4,
    fp16=True,
    evaluation_strategy='steps',
    disable_tqdm=True,
)
print(training_args)

max_length = 100


class MyTrainer(Trainer):

    def evaluate(
        self,
        eval_dataset: Optional[Dataset] = None,
        ignore_keys: Optional[List[str]] = None,
        metric_key_prefix: str = "eval",
    ) -> Dict[str, float]:
        print("\nevaluate()")
        prime_str = 'Eichkorn en tri kajeroj,'
        ids = tokenizer.encode(prime_str, return_tensors="pt")[:, :-1]
        preds = model.generate(ids.to(model.device), max_length=max_length)
        print(tokenizer.decode(preds[0]))
        return []


trainer = MyTrainer(
    model=model,
    args=training_args,
    data_collator=data_collator,
    train_dataset=dataset
)

# ### Start training
trainer.train()

# #### 🎉 Save final model (+ tokenizer + config) to disk
trainer.save_model(run_path / "model")

# ## 4. Check that the LM actually trained
# fill_mask = pipeline(
#     "fill-mask",
#     model=str(run_path / "model"),
#     tokenizer=str(tokenizer_path)
# )

# # The sun <mask>.
# print(fill_mask("La suno <mask>."))

# # Ok, simple syntax/grammar works. Let’s try a slightly more interesting prompt:
# print(fill_mask("Jen la komenco de bela <mask>."))

# This is the beginning of a beautiful <mask>.

# ## 5. Generate

prime_str = 'Eichkorn en tri kajeroj,'

ids = tokenizer.encode(prime_str, return_tensors="pt")[:, :-1]
preds = model.generate(ids.to(model.device), max_length=max_length)

print(f'preds[0]: {preds[0]}')
print(tokenizer.decode(preds[0]))
