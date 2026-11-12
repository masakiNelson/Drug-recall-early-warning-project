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


## Streamlit app

An interactive web app built on the notebook's results, with eleven short pages in five groups:

| Group | Page | What it shows |
|---|---|---|
| Start | **Home** | What PharmaSignal AI is, who it is for, and a numbered route through all ten pages |
| Recall Insights | **Recall Snapshot** | Four headline facts and recall severity year by year |
| | **Failure Patterns** | Failure types and dosage forms behind recalls |
| | **Firm Directory** | The firms that recall most often, and a search across all records |
| Early Warning | **Signal Radar** | Recent surges in recalls, how big each jump was, and how strong the signal is |
| | **Trend Explorer** | Recalls per year by failure type, and sliders to test the signal rules |
| | **Crisis Back-test** | Whether the detectors would have recognised six real crises |
| Decision Tools | **Tender Screener** | Type or upload bidders; colour-coded results, evidence briefs and downloads |
| | **Ask PharmaSignal AI** | Plain-English questions with colour-coded answers, checked by code |
| About the Project | **Methods & Evidence** | Method, evaluation results, limitations and key terms |
| | **Team & Feedback** | The team, use of AI, a feedback form and the team's action points |

 
## Use of AI

We used Claude (Anthropic) in this project and declare it as follows:

- **Labelling:** the 1,000 recall reasons were labelled by LLM-assisted annotation 
- **Code and documentation:** Claude assisted annotation.
- **The assistant inside the app** uses Claude to write answers from SQL facts and retrieved recall records only; a code checker verifies every number and recall ID.
- **Our checks and decisions:** the team chose the problem and the evidence-not-verdicts rule, reviewed the results, and validated the work with the blind label check, a 20-question assistant test set and backtests on six known recall crises.
