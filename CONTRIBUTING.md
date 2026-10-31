# Contributing to OpportunityLens

Thank you for your interest in contributing to **OpportunityLens**! We are committed to building an open, accessible, and transparent AI-powered platform to help students navigate educational and funding opportunities.

Whether you are fixing a typo in documentation, reporting a bug, proposing a new feature, improving AI extraction prompts, or writing unit tests, your contributions are warmly welcomed.

---

## Code of Conduct

We are dedicated to providing a welcoming, inclusive, and harassment-free environment for everyone, regardless of background, identity, or experience level. Please treat fellow contributors with respect, empathy, and constructive feedback.

---

## Ways to Contribute

You do not need to be an expert in machine learning or full-stack engineering to contribute. Here are several ways to get involved:

1. **Bug Reports & Feedback:** Identify edge cases, document parsing failures, or UI rendering glitches.
2. **Opportunity Samples & Test Cases:** Add realistic (or sanitized) opportunity announcements to test extraction resilience.
3. **Prompt Engineering & Extraction Accuracy:** Enhance the Gemma 4 extraction prompt in `gemma_service.py` to capture nuance across diverse international scholarship formats.
4. **Eligibility Rules:** Expand rule-based checks in `eligibility_engine.py` (e.g., citizenship rules, discipline-specific constraints).
5. **UI & User Experience:** Refine Streamlit components, responsive styling, and accessibility.
6. **Documentation:** Improve installation guides, clarify code comments, or create tutorials.

---

## Getting Started

### Prerequisites

- **Python 3.11+** installed on your machine.
- **Git** installed and configured.
- A **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/apikey). *(Note: You can still run and develop using the Quick Demo mode without an API key).*

### 1. Fork and Clone the Repository

Fork the repository on GitHub, then clone your fork locally:

```bash
git clone https://github.com/[yourusername]/opportunity-lens.git
cd opportunity-lens
```

### 2. Set Up a Virtual Environment

Always use an isolated virtual environment:

#### On Windows (PowerShell / Command Prompt):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
# Or in Command Prompt: .\venv\Scripts\activate.bat
```

#### On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install the required packages in your active virtual environment:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a local `.env` file from the provided template:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` in your editor and provide your Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

> **Security Notice:** The `.env` file is listed in `.gitignore`. Never commit real API keys or sensitive credentials to version control.

### 5. Launch the Application Locally

```bash
streamlit run app.py
```

The application will start and open automatically in your browser at `http://localhost:8501`.

---

## Development Workflow & Git Conventions

### Branch Naming Conventions

Always branch from `main` using descriptive prefixes:

| Branch Prefix | Purpose | Example |
|---|---|---|
| `feature/` | New features or major capabilities | `feature/multi-currency-stipends` |
| `fix/` | Bug fixes and rendering corrections | `fix/pdf-page-boundary-truncation` |
| `docs/` | Documentation improvements | `docs/update-installation-instructions` |
| `test/` | Adding or refactoring unit tests | `test/add-age-boundary-tests` |
| `refactor/` | Code structure improvements without behavior change | `refactor/extract-css-constants` |

```bash
git checkout -b feature/your-feature-name
```

---

## Coding Standards

To maintain codebase readability and consistency:

1. **Python Style (PEP 8):** Follow standard Python formatting conventions (4 spaces indentation, descriptive variable names).
2. **Type Annotations:** Use Python type hints on functions and methods:
   ```python
   def evaluate_cgpa(student_cgpa: float, min_cgpa: float) -> RequirementStatus:
       ...
   ```
3. **Structured Data Validation:** When modifying data contracts, update or extend the Pydantic models in `schemas.py`. Always validate inputs and outputs through schemas.
4. **Frontend & HTML Hygiene:** Streamlit executes in a browser environment.
   - When outputting custom styled containers, ensure tags are properly closed.
   - Avoid leading 4-space indentations on HTML strings following blank lines in markdown, which triggers literal markdown code block rendering.
   - Use the centralized `render_html()` helper in `app.py` or `st.html()` where appropriate.
5. **No Direct Hardcoding:** Keep configuration values (such as model IDs) in designated modules (`gemma_service.py`), not scattered across components.

---

## Testing Guidelines

OpportunityLens maintains a comprehensive automated test suite. All pull requests must pass existing tests and include new test cases for added logic.

### Running the Test Suite

Run all tests with verbose output:

```bash
pytest tests/ -v
```

Run a specific test module:

```bash
pytest tests/test_eligibility_engine.py -v
```

### Test Suite Structure

The tests are located in `tests/`:

- `test_document_processor.py`: Verifies PDF parsing, edge-case rejection (empty, encrypted, oversized), and text length validation.
- `test_eligibility_engine.py`: Tests deterministic rule evaluation for country, academic level, CGPA, grading scale mismatches, and age constraints.
- `test_schemas.py`: Tests Pydantic data model instantiation, default values, and serialization.
- `test_demo_and_rendering.py`: Tests Quick Demo integrity, zero-API fallback execution, and HTML output safety (preventing raw tag leaks).

---

## Submitting a Pull Request (PR)

1. **Commit your changes:** Write clear, concise commit messages following conventional commit style:
   ```bash
   git commit -m "feat(engine): add discipline eligibility matching rule"
   ```
2. **Verify tests pass:** Run `pytest tests/ -v` to ensure zero regressions.
3. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```
4. **Open a Pull Request:** Navigate to the upstream repository and click **New Pull Request**.
5. **Fill in the PR template:**
   - **Summary:** What does this PR change and why?
   - **Related Issues:** Closes `#issue_number` (if applicable).
   - **Testing:** How was this tested locally?
   - **Screenshots:** Include screenshots or GIFs if you modified UI components.

---

## Issue Reporting Guidelines

### Reporting Bugs

Before creating an issue, please search existing issues to avoid duplicates. When opening a bug report, include:

- **A clear, descriptive title.**
- **Steps to reproduce:** Step-by-step instructions.
- **Expected vs. Actual behavior:** What should have happened vs. what actually occurred.
- **Environment details:** OS (Windows/macOS/Linux), Python version, Streamlit version, browser.
- **Error logs or tracebacks:** Console error output (omit any API keys or private data).

### Requesting Features

When suggesting a new feature, provide:
- A clear description of the problem this feature solves.
- Your proposed solution or workflow.
- Any alternative approaches you considered.

---

## Security and Privacy Guidelines

- **Never commit credentials:** Do not commit `.env`, `.streamlit/secrets.toml`, API tokens, or session credentials.
- **Protect student privacy:** Do not submit sample documents, screenshots, or test files that contain personally identifiable information (PII) of real individuals. Use fictionalized names and academic records.
- **Vulnerability Reporting:** If you discover a security vulnerability, please do NOT open a public GitHub issue. Send a private disclosure to `[security@example.com]` so we can address it responsibly.

---

Thank you for helping make OpportunityLens better for students everywhere!

