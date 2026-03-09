# CHAOS-1 // Survival Intelligence System
## نظام الذكاء الاصطناعي للبقاء في الأزمات

An offline-capable AI survival assistant that analyzes any crisis situation
and generates ranked survival strategies, ASCII schematics, material lists,
and step-by-step procedures — even without internet (using local AI).

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env        # Fill your API key or Ollama config
python survival_chaos.py
# Open: http://localhost:5000
```

---

## AI Provider Options

### Option 1 — Anthropic (Claude) — Requires internet + credits
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Option 2 — DeepSeek — Cheap API, requires internet
```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
```

### Option 3 — Ollama LOCAL — Fully offline, no internet needed ✅
```bash
# Install Ollama: https://ollama.com
ollama pull mistral        # or: llama3, phi3, gemma2, qwen2
```
```env
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

---

## Features

- **Threat Level Meter** — Visual 1-5 threat assessment
- **Immediate Actions** — Time-ranked urgent steps
- **Survival Strategies** — Priority-ranked protocols by category:
  WATER | SHELTER | FIRE | FOOD | MEDICAL | SIGNAL | SECURITY | POWER | COMMS
- **ASCII Schematics** — Visual diagrams for construction/improvisation
- **Improvised Materials** — Field alternatives when supplies unavailable
- **Environmental Scan** — Resources, hazards, time-critical factors
- **Medical Priorities** — Triage and medical considerations
- **Chaos Score** — 0-100 situational severity index
- **Bilingual** — English + Arabic notes per strategy
- **Session History** — Contextual follow-up questions
- **Offline-Ready** — Works fully with Ollama (no internet)

---

## Usage Tips

- Ctrl+Enter to submit
- Use Quick Scenarios for testing
- Ask follow-up questions — the system remembers context
- More detail = better analysis (location, people, resources, time)

---

## المميزات الرئيسية

- يعمل بدون إنترنت مع Ollama
- تحليل فوري لأي سيناريو أزمة
- بروتوكولات مرتبة حسب الأولوية
- مخططات ASCII للبناء والتصنيع
- بدائل مبتكرة للمواد المتاحة في الميدان
- يدعم العربية في المدخلات والمخرجات
