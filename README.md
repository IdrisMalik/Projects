## Gemini CLI Batch Processor

A command-line interface (CLI) tool to batch-process supported text files (.txt, .md, .html) through Google Gemini (GenAI) models. It reads input files asynchronously, generates content using specified Gemini models, and writes the outputs to a designated directory.

---

### Features

- **Asynchronous I/O**: Leverages `aiofiles` and `asyncio` for concurrent file reads and writes.
- **Rate Limiting**: Uses `aiolimiter` to respect API rate limits for different model tiers.
- **Caching**: In-memory TTL caches for file contents and API responses to reduce redundant work.
- **Retry Logic**: Automatic retries with exponential backoff and jitter for transient API errors (HTTP 429, 503).
- **Natural Sorting**: Orders files using human-friendly (natural) sort via `natsort`.
- **Interactive Prompts**: Step-by-step CLI prompts to select models, input paths, ranges, and parameters.
- **Configurable Logging**: Logs to both console and file with customizable log file path.

---

### Prerequisites

- **Python**: 3.8 or higher
- **Environment Variables**:
  - `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Your Google Gemini API key (required).
  - `GEMINI_LOG_FILE`: (Optional) Path to the log file (default: `gemini.log`).

---

### Installation

1. Clone this repository or download `gemini.py`.
2. Install required dependencies:

   ```bash
   pip install aiofiles cachetools aiolimiter natsort google-genai
   ```

---

### Supported File Types

- `.txt`
- `.md`
- `.html`

Files with other extensions are automatically ignored.

---

### Usage

Run the script from your terminal:

```bash
python gemini.py
```

You will be guided through a series of prompts:

1. **System Prompt File**: Path to a file containing your system instruction or prompt.
2. **Model Selection**: Choose from available models (e.g., `gemini-2.5-flash-preview-04-17`, `gemini-2.0-flash-001`, etc.).
3. **Input Paths**: Comma-separated files or directories containing supported files.
4. **File Range**: Specify indices or ranges (e.g., `1-5`, `-2` to exclude, combination `1,3-4,-2`).
5. **Output Directory**: Directory to save generated outputs (default: `outputs`).
6. **Sampling Temperature**: Float value (default `0.0`).
7. **Batch Size**: Number of concurrent tasks (default `1`).
8. **Repeat**: Optionally process another batch or exit.

Outputs are saved in the specified directory, preserving original filenames.

---

### Configuration

- **Cache TTLs**:
  - File cache: 3600 seconds
  - Response cache: 3600 seconds
- **Retry Settings**:
  - Max retries: 3
  - Base delay: 2.0 seconds
  - Jitter: up to 0.5 seconds
  - Request timeout: 60 seconds

Adjust constants in the script if different values are needed.

---

### Logging

- **Log Levels**: INFO and higher messages are recorded.
- **Log Output**: Streamed to console and written to `GEMINI_LOG_FILE` (default `gemini.log`).

---

### Example

1. Prepare `prompt.txt`:
   ```text
   Summarize the following document.
   ```
2. Place `.md` files in `inputs/`.
3. Run:
   ```bash
   python gemini.py
   ```
4. Follow prompts to select `prompt.txt`, model, input `inputs`, range `1-3`, output `outputs`, temperature `0.1`, batch size `2`.
5. Check `outputs/` for summarized files.
