# 🏥 Insurance Claim Extractor

Turns unstructured claim documents (discharge summaries, hospital bills) into **clean, validated JSON**
and flags claims that need a human to look at them.

> Built with synthetic sample documents only. No real patient data.

## What it does
1. **Reads** a PDF / TXT / pasted text
2. **Extracts** patient, policy number, hospital, dates, diagnosis, treatment, bill items and total using Gemini with a fixed JSON schema (structured output, temperature 0, "never guess" prompt)
3. **Validates** with plain Python rules (not AI):
   - required fields present
   - valid dates, discharge not before admission
   - amount > 0
   - bill line items add up to the total
   - high-value claims flagged for manual approval
4. **Decides**: `READY` or `NEEDS REVIEW` with the reasons listed
5. **Exports** the result as JSON

## Why LLM + rules?
LLMs are good at reading messy text but can be wrong. Deterministic rules catch errors the model can't be trusted with
(date order, arithmetic). A human reviews only the flagged claims.

## Tech stack
Python · Streamlit · Gemini API (structured JSON output) · Pydantic · pypdf

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Paste your Gemini API key in the sidebar, or set `GEMINI_API_KEY` in `.streamlit/secrets.toml`.
Try `samples/clean_claim.txt` (passes) and `samples/problem_claim.txt` (gets flagged).

## Limitations
- No OCR: scanned/image PDFs aren't supported
- Fixed schema and rules; not a substitute for real adjudication
- Not for real patient data without proper privacy/compliance controls

## Possible next steps
- Add a policy RAG step: check the claim against policy coverage clauses
- Wrap in a FastAPI endpoint + Docker
- OCR for scanned documents

## Live demo
(add your Streamlit Cloud link here)
