import os
import sys
import asyncio
import logging
import random
import re
from pathlib import Path
from typing import List

import aiofiles
from cachetools import TTLCache
from aiolimiter import AsyncLimiter
from natsort import natsorted
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from google.genai.errors import APIError

# Load API key
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logging.critical("Environment variable $GOOGLE_API_KEY or $GEMINI_API_KEY not set")
    sys.exit(1)

# Configure logging
LOG_FILE = os.getenv("GEMINI_LOG_FILE", "gemini.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger("GeminiCLI")

SUPPORTED_EXTS = {".txt", ".md", ".html"}
FILE_CACHE_TTL = 3600
RESPONSE_CACHE_TTL = 3600
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2.0
JITTER_MAX = 0.5
REQUEST_TIMEOUT = 60.0

# Token limits by model
default_models = {
    "gemini-2.5-flash-preview-04-17": 65536,
    "gemini-2.0-flash-001": 8192,
    "gemini-1.5-flash": 8192,
    "gemini-1.5-flash-8b": 8192,
    "gemini-1.5-pro": 8192,
}

# Rate limits by model type
RATE_LIMITS = {
    "pro": AsyncLimiter(2, 60),
    "flash": AsyncLimiter(10, 60),
}

# Caches
file_cache = TTLCache(maxsize=128, ttl=FILE_CACHE_TTL)
resp_cache = TTLCache(maxsize=256, ttl=RESPONSE_CACHE_TTL)

# Initialize client
client = genai.Client(
    api_key=API_KEY,
    http_options=HttpOptions(api_version="v1alpha", timeout=int(REQUEST_TIMEOUT * 1000)),
)

def sanitize(raw: str) -> str:
    return raw.strip().strip('"\'')  # Trim whitespace and quotes

async def read_file(path: Path) -> str:
    if path in file_cache:
        return file_cache[path]
    if not path.is_file():
        raise FileNotFoundError(f"{path} is not a valid file")
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
    if not content.strip():
        raise ValueError(f"File {path} is empty or whitespace")
    file_cache[path] = content
    return content

def gather_inputs(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_dir():
            for entry in p.iterdir():
                if entry.suffix.lower() in SUPPORTED_EXTS:
                    files.append(entry)
        elif p.exists() and p.suffix.lower() in SUPPORTED_EXTS:
            files.append(p)
    return files

def sort_files(files: List[Path]) -> List[Path]:
    return [Path(p) for p in natsorted([str(p) for p in files])]

def parse_range(spec: str, total: int) -> List[int]:
    include, exclude = set(), set()
    for part in spec.split(","):
        tok = sanitize(part)
        if not tok:
            continue
        neg = tok.startswith("-")
        if neg:
            tok = tok[1:]
        if "-" in tok:
            start_str, end_str = tok.split("-", 1)
            start = int(start_str) if start_str else 1
            end = int(end_str) if end_str else total
            rng = set(range(max(1, start), min(total, end) + 1))
        else:
            rng = {int(tok)}
        (exclude if neg else include).update(rng)
    return sorted(include - exclude)

async def generate_with_retry(model_id: str, parts: List[types.Part], config: types.GenerateContentConfig) -> str:
    key = (model_id, tuple(p.text for p in parts), config.system_instruction, config.temperature)
    if key in resp_cache:
        return resp_cache[key]
    limiter = RATE_LIMITS["flash"] if "flash" in model_id else RATE_LIMITS["pro"]
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with limiter:
                resp = await asyncio.wait_for(
                    client.aio.models.generate_content(model=model_id, contents=parts, config=config),
                    timeout=REQUEST_TIMEOUT,
                )
            text = resp.text or "".join(chunk.text or "" for chunk in getattr(resp, "parts", []))
            resp_cache[key] = text
            return text
        except APIError as e:
            if e.code in (429, 503):
                delay = BASE_RETRY_DELAY * attempt + random.random() * JITTER_MAX
                logger.warning(f"Transient error {e.code}, retry {attempt}/{MAX_RETRIES} after {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"API error {e.code}: {e.message}")
                raise
    raise RuntimeError("Exceeded maximum retry attempts")

async def process_file(model_id: str, system_instruction: str, temperature: float, inp: Path, out_dir: Path, task_id: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        logger.info(f"[{task_id}] Processing '{inp.name}'")
        try:
            text = await read_file(inp)
            part = types.Part.from_text(text=text)
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=default_models[model_id],
                safety_settings=[
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.OFF),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.OFF),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.OFF),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.OFF),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.OFF),
                ],
            )
            result = await generate_with_retry(model_id, [part], config)
            cleaned = re.sub(r"^```.*?\n|```$", "", result, flags=re.DOTALL)
            out_path = out_dir / inp.name
            async with aiofiles.open(out_path, "w", encoding="utf-8") as f:
                await f.write(cleaned)
            logger.info(f"[{task_id}] Wrote '{out_path}'")
        except Exception as e:
            logger.error(f"[{task_id}] Error '{inp.name}': {e}")

async def run_batch(system_instruction: str, temperature: float, model_id: str, input_files: List[Path], out_dir: Path, batch_size: int):
    sem = asyncio.Semaphore(batch_size)
    tasks = [
        process_file(model_id, system_instruction, temperature, inp, out_dir, f"T{i+1}", sem)
        for i, inp in enumerate(input_files)
    ]
    await asyncio.gather(*tasks)

def prompt_path(message: str) -> Path:
    while True:
        user_input = sanitize(input(f"{message}: "))
        p = Path(user_input).expanduser()
        if p.is_file():
            return p
        print(f"Invalid path: {p}")

def prompt_choice(message: str, options: List[str]) -> str:
    print(message)
    for idx, opt in enumerate(options, start=1):
        print(f"  {idx}. {opt}")
    while True:
        sel = sanitize(input("Enter choice number: "))
        if sel.isdigit() and 1 <= int(sel) <= len(options):
            return options[int(sel) - 1]
        print("Invalid choice")

def prompt_list(message: str) -> List[Path]:
    raw = sanitize(input(f"{message}: "))
    return [Path(p).expanduser() for p in raw.split(",") if p.strip()]

def main():
    while True:
        base = prompt_path("Enter system prompt file")
        system_instruction = asyncio.run(read_file(base))

        model_id = prompt_choice("Select model:", list(default_models.keys()))
        paths = prompt_list("Enter input file(s) or folder(s)")
        inputs = gather_inputs(paths)
        inputs = sort_files(inputs)

        print("Files to process:")
        for i, fp in enumerate(inputs, 1):
            print(f" {i}. {fp.name} ({fp.stat().st_size} bytes)")
        spec = sanitize(input("Select range (e.g. 1-5,-2): "))
        selected = [inputs[i - 1] for i in parse_range(spec, len(inputs))]

        out_dir = Path(sanitize(input("Output directory [outputs]: ")) or "outputs").expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)

        temperature = float(sanitize(input("Sampling temperature [0.0]: ")) or 0.0)
        batch_size = int(sanitize(input("Batch size [1]: ")) or 1)

        asyncio.run(run_batch(system_instruction, temperature, model_id, selected, out_dir, batch_size))
        if sanitize(input("\nProcess another batch? [y/N]: ").lower()) != "y":
            print("Exiting.")
            break

if __name__ == "__main__":
    main()