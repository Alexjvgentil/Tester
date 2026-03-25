# web-tester

```bash
python -m web_tester https://google.com -i "Ache a caixa de texto, coloque a palavra Vorcaro, e clique em buscar" -n smoke_test --no-headless -v
```

AI-powered web testing agent built with [smolagents](https://github.com/huggingface/smolagents) `CodeAgent` + Playwright.

The agent receives a URL and natural-language instructions, drives a real browser, takes screenshots after every action, and asks a vision LLM (GPT-4o or Claude) what to do next. All screenshots, logs, and a final Markdown report are saved to a timestamped folder.

---

## How it works

```
URL + Instructions
       ↓
  BrowserController (Playwright sync)
       ↓
  Initial screenshot → smolagents CodeAgent
       ↓  ← screenshot injected after each step via step_callbacks
  CodeAgent generates Python code: click(x, y) / type_text(...) / ...
       ↓
  Tool executes the Playwright action
       ↓
  New screenshot → model sees it → next action
       ↓ (repeat until final_answer() is called)
  TestResult  +  test_runs/<timestamp>/
```

---

## Setup

```bash
# 1. Activate venv (from project root)
source ../venv/Scripts/activate   # Windows Git Bash
# or
..\venv\Scripts\activate          # Windows CMD

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Configure
cp .env.example .env
# Edit .env and add your API key
```

---

## Usage

```bash
# Basic run (OpenAI)
python -m web_tester https://example.com \
  -i "Find and click the 'More information' link, verify it loads a new page" \
  -n smoke_test -v

# Show browser window (non-headless)
python -m web_tester https://example.com \
  -i "Fill the search box with 'playwright' and press Enter" \
  --no-headless -v

# Use Anthropic Claude
python -m web_tester https://example.com \
  -i "Check the page title is 'Example Domain'" \
  --provider anthropic --model anthropic/claude-sonnet-4-6

# Programmatic usage
from web_tester import WebTestAgent, load_config

config = load_config()
agent = WebTestAgent(config=config)
result = agent.run(
    url="https://example.com",
    instructions="Click the More information link",
    verbose=True,
)
print(result.status, result.final_message)
print("Report:", result.report_md)
```

---

## Output

Each test run creates a folder:

```
test_runs/
└── 20260324_143022_click_the_more_information_link/
    ├── screenshots/
    │   ├── step_000_initial_143022.png
    │   ├── step_001_click_143024.png
    │   └── step_002_navigate_143026.png
    ├── execution.log      ← JSONL event stream
    ├── report.json        ← machine-readable full report
    └── report.md          ← human-readable with screenshots
```

---

## Environment variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `MODEL_PROVIDER` | `openai` | `openai` or `anthropic` |
| `MODEL_NAME` | `gpt-4o` | Model ID (e.g. `anthropic/claude-sonnet-4-6`) |
| `OPENAI_API_KEY` | — | Required when provider is `openai` |
| `ANTHROPIC_API_KEY` | — | Required when provider is `anthropic` |
| `BROWSER_HEADLESS` | `true` | Run browser without UI |
| `VIEWPORT_WIDTH` | `1280` | Browser viewport width |
| `VIEWPORT_HEIGHT` | `720` | Browser viewport height |
| `MAX_STEPS` | `50` | Max agent steps before stopping |
| `TEST_RUNS_DIR` | `test_runs` | Root folder for test output |

---

## Available browser tools

The agent can call these tools as Python code:

| Tool | Description |
|---|---|
| `navigate(url)` | Go to a URL |
| `click(x, y)` | Click at pixel coordinates |
| `type_text(text, selector?, clear_first?)` | Type text into an element |
| `press_key(key)` | Press a keyboard key (Enter, Tab, Escape…) |
| `scroll(x, y, delta_x, delta_y)` | Scroll the page |
| `hover(x, y)` | Move mouse to trigger hover effects |
| `select_option(selector, value)` | Choose a `<select>` dropdown option |
| `wait(milliseconds)` | Pause for animations/loading |
| `wait_for_selector(selector, timeout_ms?)` | Wait for an element to appear |
| `go_back()` | Browser back |
| `go_forward()` | Browser forward |
| `reload()` | Reload page |
| `final_answer(result)` | End the test (built-in smolagents tool) |
