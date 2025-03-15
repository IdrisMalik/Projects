from transformers import MarianMTModel, MarianTokenizer
import torch

def translate_text(text, source_lang="en", target_lang="fr", model_name=None):
    try:
        if not model_name: # Determine correct model based on source and target langauge codes
            model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name).to(device)

        # Tokenize the text
        input_ids = tokenizer.encode(text, return_tensors="pt").to(device)


        # Perform translation and get output
        translated_ids = model.generate(input_ids)

        # Decode the translated IDs
        translated_text = tokenizer.decode(translated_ids[0], skip_special_tokens=True)

        return translated_text

    except Exception as e:
        return f"Translation error: {e}"