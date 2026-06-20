# HackerRank Orchestrate: Damage Verification Pipeline

Build a system that verifies visual evidence for damage claims across three object types: **cars**, **laptops**, and **packages**.

Your system will receive claim conversations, one or more submitted images, user claim history, and minimum evidence requirements. It must decide whether the submitted images support the claim, contradict it, or do not provide enough information.

---

## 🚀 Architecture & Approach

This solution utilizes a highly optimized **Hybrid API Architecture** designed for speed, cost-efficiency, and resilience:
1. **Text Parsing (Groq `llama-3.3-70b-versatile`)**: All chat transcripts are parsed using Groq. This ensures ultra-low latency text understanding while saving 100% of the vision-model API quota.
2. **Vision Analysis (Gemini `gemini-2.5-flash-lite`)**: Gemini is used strictly for multimodal image inspection. Flash-lite was selected for its high free-tier limits (15 RPM) and excellent JSON schema adherence.
3. **Deterministic Logic**: Final decisions are calculated using a pure Python `DecisionEngine` and `RiskEngine` to ensure predictable, rule-based outputs that perfectly align with HackerRank's required schemas.
4. **Strict Enforcement**: The pipeline strictly enforces live API access. There are no hardcoded mocks or fallbacks. If the API fails, the pipeline correctly halts. 

---

## ⚙️ Setup Instructions

### 1. Environment Setup
We recommend using a Python virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. API Keys Configuration
Create a `.env` file in the root directory and add your Groq and Google Gemini API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Run the Pipeline
To evaluate the claims dataset and generate `outputs/output.csv`, run:
```bash
python src/main.py --input data/claims.csv --output outputs/output.csv
```

---

Read `problem_statement.md` for the full task spec, input/output schema, and allowed values.
