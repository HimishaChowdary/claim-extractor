"""
Insurance Claim Extractor
Upload a (synthetic) claim / discharge summary -> AI pulls out the key fields as
clean JSON -> business rules check it -> the claim is marked READY or NEEDS REVIEW.

HOW IT WORKS:
1. READ     : get text from a PDF, TXT file, or pasted text
2. EXTRACT  : Gemini fills a fixed form (the schema) with what it finds
3. VALIDATE : normal Python rules check dates, amounts, missing fields
4. DECIDE   : READY for processing, or NEEDS REVIEW with the reasons listed
"""
import json
from typing import List, Optional

import streamlit as st
from pydantic import BaseModel
from pypdf import PdfReader
from google import genai
from google.genai import types

from rules import validate

CHAT_MODEL = "gemini-3.6-flash"  # change to whatever model works in your other apps

st.set_page_config(page_title="Insurance Claim Extractor", page_icon="🏥", layout="wide")
st.title("🏥 Insurance Claim Extractor")
st.caption("Turns messy claim documents into clean, validated data. Use SYNTHETIC / sample data only - never real patient records.")


# ---------- THE FORM THE AI MUST FILL (the "schema") ----------
class BillItem(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None


class Claim(BaseModel):
    patient_name: Optional[str] = None
    policy_number: Optional[str] = None
    hospital_name: Optional[str] = None
    doctor_name: Optional[str] = None
    claim_type: Optional[str] = None          # e.g. hospitalization, outpatient
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    admission_date: Optional[str] = None      # YYYY-MM-DD
    discharge_date: Optional[str] = None      # YYYY-MM-DD
    total_billed_amount: Optional[float] = None
    currency: Optional[str] = None
    bill_items: List[BillItem] = []


# ---------- API KEY ----------
def get_client():
    key = None
    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    if not key:
        key = st.sidebar.text_input("Gemini API key", type="password")
    if not key:
        st.info("Add your Gemini API key in the sidebar to start.")
        st.stop()
    return genai.Client(api_key=key)


client = get_client()
threshold = st.sidebar.number_input("High-value review threshold", value=100000, step=10000)


# ---------- STEP 1: READ ----------
def get_text(uploaded):
    if uploaded.name.lower().endswith(".pdf"):
        reader = PdfReader(uploaded)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    return uploaded.read().decode("utf-8", errors="ignore")


# ---------- STEP 2: EXTRACT ----------
def extract(text):
    prompt = f"""Extract the claim details from the document below.
Rules:
- Use ONLY information in the document. If something is not stated, leave it null. Never guess.
- Dates must be formatted YYYY-MM-DD.
- Amounts must be plain numbers (no currency symbols or commas).
- List every itemised charge in bill_items if present.

DOCUMENT:
{text}"""
    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Claim,
            temperature=0,
        ),
    )
    return response.parsed.model_dump()


# ---------- THE APP ----------
left, right = st.columns(2)

with left:
    uploaded = st.file_uploader("Upload claim document (PDF or TXT)", type=["pdf", "txt"])
    pasted = st.text_area("...or paste the text here", height=200)

text = ""
if uploaded:
    text = get_text(uploaded)
elif pasted.strip():
    text = pasted

if text and st.button("Extract and validate", type="primary"):
    if len(text.strip()) < 30:
        st.error("Not enough readable text. Scanned image PDFs are not supported.")
        st.stop()
    with st.spinner("Reading the document..."):
        claim = extract(text)
    status, issues = validate(claim, threshold)

    with right:
        if status == "READY":
            st.success("✅ READY for processing - all checks passed")
        else:
            st.warning("⚠️ NEEDS REVIEW")
            for issue in issues:
                st.write(f"- {issue}")

    st.subheader("Extracted data")
    c1, c2 = st.columns(2)
    with c1:
        st.json(claim)
    with c2:
        if claim.get("bill_items"):
            st.write("**Bill items**")
            st.table(claim["bill_items"])
        st.download_button(
            "Download JSON",
            data=json.dumps(claim, indent=2),
            file_name="claim.json",
            mime="application/json",
        )
    with st.expander("Document text the AI read"):
        st.text(text)
