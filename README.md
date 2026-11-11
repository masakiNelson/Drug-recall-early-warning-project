# PharmaSignal AI: Drug-Quality Recall Intelligence

**Team:** Cindy Murogo, Daniel Kimasar, Mananda Kirungu Salim, Nelson Masaki, Varlerly Maina

Capstone group project: an AI-powered prototype that turns openFDA drug-recall records into evidence for pharmaceutical procurement teams. Everything is in `Drug_Recall_Intelligence_Final.ipynb`.

## Files

| File | What it is |
|---|---|
| `Drug_Recall_Intelligence_Final.ipynb` | The full analysis notebook |
| `drug_recalls.csv` | openFDA drug enforcement snapshot |
| `labelled_recall_reasons.csv` | 1,000 recall reasons labelled by AI-assisted annotation (see *Use of AI*) |
| `blind_check_150.csv` | Blind human check of 150 labels, used to measure agreement (Cohen's kappa) |
| `app.py`, `pharmasignal_core.py`, `ui.py` | Streamlit app: pages, logic taken from the notebook, and shared styling |
| `.streamlit/config.toml`, `assets/` | App theme (colours, fonts) and logo |
| `USER_TEST.md` | Five-minute script for testing the app with someone outside the team |
| `outputs/` | Results written by the notebook; the app reads them |

Keep all files in the same folder as the notebook. Results are written to `outputs/`.

## Setup

Install Python 3.10 or newer, then from the project folder:

```bash
pip install -r requirements.txt
```

## Connecting Claude (optional)

Without an API key the notebook still runs fully; the assistant section answers in **evidence-only mode**. To get AI-written answers, give the notebook an Anthropic API key (create one at https://console.anthropic.com → API Keys).

**Easiest (Mac and Windows):** create a file called `.env` next to the notebook containing one line:

```
ANTHROPIC_API_KEY=sk-ant-...
```

You can copy `.env.example` to `.env` and edit it. The notebook loads it automatically, and `.gitignore` keeps it out of GitHub. **Never commit or share your key.**

> **Windows / Notepad tip:** in *Save As*, set *Save as type* to **All Files (\*.\*)** and type the name as `".env"` (with the quotes). Otherwise Notepad saves it as `.env.txt` and it will not be found.

**Alternative: environment variable** (restart Jupyter afterwards):

- Mac/Linux: `export ANTHROPIC_API_KEY="sk-ant-..."` then start `jupyter notebook` from the same terminal
- Windows: `setx ANTHROPIC_API_KEY "sk-ant-..."` then close and reopen all terminals and Jupyter

## Running

Open the notebook and choose **Kernel → Restart & Run All** (about 2 minutes; a little longer with Claude connected). Section 8 should print `LLM: Claude (claude-sonnet-5-5) connected` when the key is found.

To check whether the key is visible to the notebook, run in a cell:

```python
import os; print(bool(os.environ.get("ANTHROPIC_API_KEY")))
```

## Deploying to Streamlit Community Cloud

1. Run the notebook once so `outputs/` is up to date, then push the whole folder (including `outputs/`) to GitHub. Never push `.env`.
2. At share.streamlit.io choose the repository, branch and `app.py`; under *Advanced settings* pick Python 3.12 or 3.13.
3. In the app's **Settings -> Secrets** add:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   # Optional:
   LLM_MODEL = "claude-sonnet-5-5"     # or "claude-haiku-5-5" for about 20 times lower cost
   DAILY_QUESTION_LIMIT = 150          # written answers per day for the whole app
   SESSION_QUESTION_LIMIT = 25         # written answers per visitor
   ```
   When a limit is reached the assistant keeps working in evidence-only mode, so the app never breaks.
4. Set a monthly spend limit in the Anthropic Console, because anyone with the link can ask questions.

Live app: *add the URL here after deploying*

## Streamlit app

An interactive web app built on the notebook's results, with eleven short pages in five groups:

| Group | Page | What it shows |
|---|---|---|
| Start | **Home** | What PharmaSignal AI is, who it is for, and where to start |
| Explore the data | **Key findings** | Four headline facts and recall severity year by year |
| | **What goes wrong** | Failure types and dosage forms behind recalls |
| | **Firms and records** | Firms with the most recalls, and a search across all records |
| Recall signals | **Latest signals** | Recent surges in recalls, explained in plain words |
| | **Trends and sensitivity** | Any series month by month, with sliders to test the signal rules |
| | **Back-test** | Whether the detectors would have recognised six real crises |
| Decide | **Tender screening** | Type or upload bidders; evidence cards, briefs and downloads |
| | **AI assistant** | Plain-English questions answered from the data, checked by code |
| About | **How it works** | Method, evaluation results, limitations and key terms |
| | **Team and feedback** | The team and roles, use of AI, and a feedback form |

1. **Run the notebook once** (Restart & Run All). It creates the `outputs/` folder the app reads; the app does not retrain anything.
2. From the project folder, start the app:

   ```bash
   streamlit run app.py
   ```

   On Windows, if `streamlit` is not recognised, use `python -m streamlit run app.py`.
3. Your browser opens at http://localhost:8501. Stop the app with **Ctrl+C** in the terminal.

The assistant uses the same `.env` API key as the notebook. Without a key the app still works, and the assistant shows the evidence only. Re-run the notebook whenever the data changes, then restart the app.

The app code is in `app.py` (pages) and `pharmasignal_core.py` (data loading, tender screening and assistant logic, taken from the notebook).

## Use of AI

We used Claude (Anthropic) in this project and declare it as follows:

- **Labelling:** the 1,000 recall reasons were labelled by LLM-assisted annotation (Claude) following a written 10-category codebook. The `annotator` column records this. Team members checked label quality with a blind human review of 150 records (`blind_check_150.csv`, agreement reported as Cohen's kappa); human corrections in `human_verified_label` override the AI label.
- **Code and documentation:** Claude assisted in writing and debugging the notebook, the Streamlit app and the documentation.
- **The assistant inside the app** uses Claude to write answers from SQL facts and retrieved recall records only; a code checker verifies every number and recall ID.
- **Our checks and decisions:** the team chose the problem and the evidence-not-verdicts rule, reviewed the results, and validated the work with the blind label check, a 20-question assistant test set and backtests on six known recall crises.
