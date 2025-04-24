import os
import sys
import asyncio
import logging
import random
import re
from pathlib import Path
from typing import List, Tuple

import aiofiles
from cachetools import TTLCache
from aiolimiter import AsyncLimiter
from natsort import natsorted
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from google.genai.errors import APIError


# Configuration


# Load API key from environment variables
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logging.critical("Environment variable $GOOGLE_API_KEY or $GEMINI_API_KEY not set")
    sys.exit(1)

# Configure logging to console and file
LOG_FILE = os.getenv("GEMINI_LOG_FILE", "gemini.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger("GeminiCLI")

# Supported file extensions for processing
SUPPORTED_EXTS = {".txt", ".md", ".html"}

# Cache TTLs (in seconds)
FILE_CACHE_TTL = 3600       # Cache raw file contents
RESPONSE_CACHE_TTL = 3600   # Cache API responses

# Retry logic settings
MAX_RETRIES = 3             # Maximum retry attempts for transient API errors
BASE_RETRY_DELAY = 2.0      # Initial backoff delay in seconds
JITTER_MAX = 0.5            # Maximum random jitter added to delays
REQUEST_TIMEOUT = 60.0      # per-request timeout in seconds

# Token limits by Gemini model
default_models = {
    "gemini-2.5-flash-preview-04-17": 65536,
    "gemini-2.0-flash-001": 8192,
    "gemini-1.5-flash": 8192,
    "gemini-1.5-flash-8b": 8192,
    "gemini-1.5-pro": 8192,
}

# Rate limits for model classes (requests per minute)
RATE_LIMITS = {
    "pro": AsyncLimiter(2, 60),     # 2 requests/minute
    "flash": AsyncLimiter(10, 60),  # 10 requests/minute
}

# Initialize caches: file contents and responses
file_cache = TTLCache(maxsize=128, ttl=FILE_CACHE_TTL)
resp_cache = TTLCache(maxsize=256, ttl=RESPONSE_CACHE_TTL)

# Initialize the Gemini client
client = genai.Client(
    api_key=API_KEY,
    http_options=HttpOptions(api_version="v1alpha", timeout=int(REQUEST_TIMEOUT * 1000)),
)


# Utility functions


def sanitize(raw: str) -> str:
    """
    Trim whitespace and enclosing quotes from the input string.

    Args:
        raw: Original string to sanitize.
    Returns:
        A clean string without leading/trailing spaces or quotes.
    """
    return raw.strip().strip('"\'')

async def read_file(path: Path) -> str:
    """
    Asynchronously read and cache the content of a file.

    Args:
        path: Path object pointing to a text file.
    Returns:
        The full text content of the file.

    Raises:
        FileNotFoundError: If the path is not a file.
        ValueError: If the file is empty or whitespace only.
    """
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
    """
    Collect all supported files from given paths or directories.

    Args:
        paths: List of file or directory paths.
    Returns:
        A flat list of file paths with supported extensions.
    """
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
    """
    Sort files naturally by name (e.g., file1, file2, file10).

    Args:
        files: List of Path objects.
    Returns:
        A sorted list of Path objects.
    """
    return [Path(p) for p in natsorted([str(p) for p in files])]


def parse_range(spec: str, total: int) -> List[int]:
    """
    Parse a comma-separated range specification (e.g., "1-5,-3").

    Args:
        spec: Range specifier string.
        total: Total number of items available.
    Returns:
        Sorted list of indices (1-based) to include.
    """
    include, exclude = set(), set()
    for part in spec.split(','):
        tok = sanitize(part)
        if not tok:
            continue
        neg = tok.startswith('-')
        if neg:
            tok = tok[1:]
        if '-' in tok:
            start_str, end_str = tok.split('-', 1)
            start = int(start_str) if start_str else 1
            end = int(end_str) if end_str else total
            rng = set(range(max(1, start), min(total, end) + 1))
        else:
            rng = {int(tok)}
        (exclude if neg else include).update(rng)
    # Compute final selection as include minus exclude
    return sorted(include - exclude)


# API interaction


async def generate_with_retry(
    model_id: str,
    parts: List[types.Part],
    config: types.GenerateContentConfig
) -> str:
    """
    Call the Gemini GenerateContent API with retries, rate limiting, and caching.

    Args:
        model_id: Identifier of the Gemini model to use.
        parts: List of content parts to send.
        config: Generation configuration (instructions, temperature, tokens).
    Returns:
        The generated text response from the API.

    Raises:
        RuntimeError: If maximum retries are exceeded.
        APIError: For non-transient errors.
    """
    # Use tuple of params as cache key
    key: Tuple = (model_id, tuple(p.text for p in parts), config.system_instruction, config.temperature)
    if key in resp_cache:
        return resp_cache[key]

    # Select appropriate rate limiter
    limiter = RATE_LIMITS["flash"] if "flash" in model_id else RATE_LIMITS["pro"]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with limiter:
                resp = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model_id,
                        contents=parts,
                        config=config
                    ),
                    timeout=REQUEST_TIMEOUT
                )
            # Extract text from response or parts
            text = resp.text or "".join(chunk.text or "" for chunk in getattr(resp, "parts", []))
            resp_cache[key] = text
            return text

        except APIError as e:
            # Retry on rate limit or service unavailable
            if e.code in (429, 503):
                delay = BASE_RETRY_DELAY * attempt + random.random() * JITTER_MAX
                logger.warning(f"Transient error {e.code}, retry {attempt}/{MAX_RETRIES} after {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"API error {e.code}: {e.message}")
                raise

    # All retries exhausted
    raise RuntimeError("Exceeded maximum retry attempts")

async def process_file(
    model_id: str,
    system_instruction: str,
    temperature: float,
    inp: Path,
    out_dir: Path,
    task_id: str,
    semaphore: asyncio.Semaphore
) -> None:
    """
    Process a single input file: read, call API, and write output.

    Args:
        model_id: Gemini model identifier.
        system_instruction: Prompt instruction text.
        temperature: Sampling temperature.
        inp: Input file path.
        out_dir: Directory to write output file.
        task_id: Unique task ID for logging.
        semaphore: Concurrency semaphore.
    """
    async with semaphore:
        logger.info(f"[{task_id}] Processing '{inp.name}'")
        try:
            # Read file content
            text = await read_file(inp)
            part = types.Part.from_text(text=text)
            # Build generation config
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
            # Generate response with retry logic
            result = await generate_with_retry(model_id, [part], config)
            # Strip markdown code fences if present
            cleaned = re.sub(r"^```.*?\n|```$", "", result, flags=re.DOTALL)

            # Write to output file
            out_path = out_dir / inp.name
            async with aiofiles.open(out_path, "w", encoding="utf-8") as f:
                await f.write(cleaned)

            logger.info(f"[{task_id}] Wrote '{out_path}'")

        except Exception as e:
            logger.error(f"[{task_id}] Error '{inp.name}': {e}")

async def run_batch(
    system_instruction: str,
    temperature: float,
    model_id: str,
    input_files: List[Path],
    out_dir: Path,
    batch_size: int
) -> None:
    """
    Execute concurrent processing of multiple files in batches.

    Args:
        system_instruction: Prompt instruction text.
        temperature: Sampling temperature.
        model_id: Gemini model identifier.
        input_files: List of input file paths.
        out_dir: Directory to write outputs.
        batch_size: Number of concurrent tasks.
    """
    sem = asyncio.Semaphore(batch_size)
    tasks = [
        process_file(model_id, system_instruction, temperature, inp, out_dir, f"T{i+1}", sem)
        for i, inp in enumerate(input_files)
    ]
    await asyncio.gather(*tasks)


# User prompts for CLI


def prompt_path(message: str) -> Path:
    """
    Prompt user for a file path until a valid file is provided.

    Args:
        message: Prompt message to display.
    Returns:
        A Path object pointing to an existing file.
    """
    while True:
        user_input = sanitize(input(f"{message}: "))
        p = Path(user_input).expanduser()
        if p.is_file():
            return p
        print(f"Invalid path: {p}")


def prompt_choice(message: str, options: List[str]) -> str:
    """
    Display a numbered list and prompt user to select one option.

    Args:
        message: Header message for choices.
        options: List of option strings.
    Returns:
        The selected option string.
    """
    print(message)
    for idx, opt in enumerate(options, start=1):
        print(f"  {idx}. {opt}")
    while True:
        sel = sanitize(input("Enter choice number: "))
        if sel.isdigit() and 1 <= int(sel) <= len(options):
            return options[int(sel) - 1]
        print("Invalid choice")


def prompt_list(message: str) -> List[Path]:
    """
    Prompt user for a comma-separated list of file or directory paths.

    Args:
        message: Prompt message to display.
    Returns:
        List of Path objects for each valid entry.
    """
    raw = sanitize(input(f"{message}: "))
    return [Path(p).expanduser() for p in raw.split(",") if p.strip()]


# Main entry point

def main() -> None:
    """
    Main interactive loop: prompt for inputs and run processing batches.

    Exits when user opts not to process another batch.
    """
    while True:
        # Load system prompt
        base = prompt_path("Enter system prompt file")
        system_instruction = asyncio.run(read_file(base))

        # Select model and inputs
        model_id = prompt_choice("Select model:", list(default_models.keys()))
        paths = prompt_list("Enter input file(s) or folder(s)")

        # Gather and display files
        inputs = sort_files(gather_inputs(paths))
        print("Files to process:")
        for i, fp in enumerate(inputs, 1):
            print(f" {i}. {fp.name} ({fp.stat().st_size} bytes)")

        # Choose subset of files
        spec = sanitize(input("Select range (e.g. 1-5,-2): "))
        selected = [inputs[i - 1] for i in parse_range(spec, len(inputs))]

        # Configure output directory and processing params
        out_dir = Path(sanitize(input("Output directory [outputs]: ")) or "outputs").expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        temperature = float(sanitize(input("Sampling temperature [0.0]: ")) or 0.0)
        batch_size = int(sanitize(input("Batch size [1]: ")) or 1)

        # Run batch and optionally repeat
        asyncio.run(run_batch(system_instruction, temperature, model_id, selected, out_dir, batch_size))
        if sanitize(input("\nProcess another batch? [y/N]: ").lower()) != "y":
            print("Exiting.")
            break

if __name__ == "__main__":
    main()
