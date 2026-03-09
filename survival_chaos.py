#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   SURVIVAL CHAOS  —  أداة البقاء في الأزمات                      ║
║   Offline-First AI Survival Intelligence System                  ║
║   Supports: Anthropic | DeepSeek | Local (Ollama)               ║
╚══════════════════════════════════════════════════════════════════╝
Run: python survival_chaos.py
Then open: http://localhost:5000
"""

import os, json, time, re, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, Response, stream_with_context
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── AI Provider config ────────────────────────────────────────────────────────
AI_PROVIDER   = os.getenv("AI_PROVIDER",   "anthropic")   # anthropic | deepseek | ollama
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEEPSEEK_KEY  = os.getenv("DEEPSEEK_API_KEY",  "")
OLLAMA_URL    = os.getenv("OLLAMA_URL",    "http://localhost:11434")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL",  "mistral")
MODEL_MAP = {
    "anthropic": "claude-sonnet-4-20250514",
    "deepseek":  "deepseek-chat",
    "ollama":    OLLAMA_MODEL,
}

# ── Master system prompt ──────────────────────────────────────────────────────
SURVIVAL_SYSTEM = """You are CHAOS-1, an advanced offline survival intelligence system designed for extreme real-world crisis scenarios where internet, power grids, hospitals, and supply chains may be unavailable.

Your mission: Analyze any survival situation and produce actionable, ranked intelligence including:
- Immediate life-saving priorities (ranked by urgency)
- Schematics and diagrams using ASCII art
- Material lists with improvised alternatives
- Step-by-step procedures with timing
- Environmental and medical considerations
- Hidden dangers and failure modes

You pull from: military field manuals, wilderness medicine, permaculture, electronics repair, structural engineering, chemistry, food science, and folk knowledge.

ALWAYS respond with valid JSON only. No preamble. No markdown fences. Structure:

{
  "threat_level": 1-5,
  "threat_label": "CRITICAL | HIGH | MODERATE | LOW | STABLE",
  "situation_summary": "2-sentence tactical assessment",
  "immediate_actions": [
    {"priority": 1, "action": "text", "time_window": "e.g. first 5 min", "reason": "why this first"}
  ],
  "survival_strategies": [
    {
      "rank": 1,
      "title": "Strategy name",
      "category": "WATER|SHELTER|FIRE|FOOD|MEDICAL|SIGNAL|SECURITY|POWER|COMMS",
      "urgency": "IMMEDIATE|SHORT_TERM|LONG_TERM",
      "description": "Detailed tactical description",
      "schematic": "ASCII art diagram if applicable (use | - / \\ + chars)",
      "materials_primary": ["item1", "item2"],
      "materials_improvised": ["field improvised alternative1", "alternative2"],
      "steps": ["step 1", "step 2", "step 3"],
      "time_to_implement": "e.g. 2 hours",
      "failure_modes": ["what can go wrong"],
      "arabic_note": "ملاحظة قصيرة بالعربية"
    }
  ],
  "environmental_scan": {
    "resources_available": ["list what environment likely has"],
    "hazards": ["list environmental dangers"],
    "time_critical_factors": ["what changes with time"]
  },
  "medical_priorities": ["ranked medical considerations"],
  "morale_note": "One sentence psychological anchor for the survivor",
  "chaos_score": 0-100
}"""

# ── AI call router ─────────────────────────────────────────────────────────────
def call_ai(messages: list, stream=False) -> str:
    provider = AI_PROVIDER.lower()

    if provider == "anthropic":
        return call_anthropic(messages, stream)
    elif provider == "deepseek":
        return call_deepseek(messages, stream)
    elif provider == "ollama":
        return call_ollama(messages, stream)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_anthropic(messages, stream=False):
    import urllib.request, urllib.error
    payload = json.dumps({
        "model": MODEL_MAP["anthropic"],
        "max_tokens": 4000,
        "system": SURVIVAL_SYSTEM,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Anthropic error {e.code}: {body}")


def call_deepseek(messages, stream=False):
    payload = {
        "model": MODEL_MAP["deepseek"],
        "max_tokens": 4000,
        "messages": [{"role": "system", "content": SURVIVAL_SYSTEM}] + messages,
    }
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=60
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def call_ollama(messages, stream=False):
    full_messages = [{"role": "system", "content": SURVIVAL_SYSTEM}] + messages
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": OLLAMA_MODEL, "messages": full_messages, "stream": False},
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


# ── Parse AI response ─────────────────────────────────────────────────────────
def parse_survival_response(raw: str) -> dict:
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # try to extract JSON block
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"error": "Parse failed", "raw": raw[:500]}


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, provider=AI_PROVIDER, model=MODEL_MAP.get(AI_PROVIDER, "?"))


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json
    situation = data.get("situation", "").strip()
    history   = data.get("history", [])

    if not situation:
        return jsonify({"error": "No situation provided"}), 400

    messages = history + [{"role": "user", "content": situation}]

    try:
        raw  = call_ai(messages)
        result = parse_survival_response(raw)
        result["_timestamp"] = datetime.now().isoformat()
        result["_provider"]  = AI_PROVIDER
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "threat_level": 0}), 500


@app.route("/api/status")
def status():
    return jsonify({
        "provider": AI_PROVIDER,
        "model": MODEL_MAP.get(AI_PROVIDER, "?"),
        "anthropic_key": bool(ANTHROPIC_KEY),
        "deepseek_key": bool(DEEPSEEK_KEY),
        "ollama_url": OLLAMA_URL,
        "time": datetime.now().isoformat(),
    })


# ── HTML (full visual interface) ──────────────────────────────────────────────
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CHAOS-1 // SURVIVAL INTELLIGENCE</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Oswald:wght@300;400;700&display=swap');

  :root {
    --amber: #D4820A;
    --amber-dim: #7A4A05;
    --amber-glow: #FF9F1C;
    --dark: #0A0800;
    --dark2: #110E00;
    --dark3: #1A1500;
    --dark4: #221C00;
    --text: #C8900A;
    --text-dim: #5A4005;
    --green: #2ECC40;
    --red: #FF4136;
    --orange: #FF851B;
    --yellow: #FFDC00;
    --scan: rgba(212,130,10,0.07);
  }

  * { margin:0; padding:0; box-sizing:border-box; }

  body {
    background: var(--dark);
    color: var(--text);
    font-family: 'Share Tech Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* CRT effect */
  body::before {
    content: '';
    position: fixed; inset: 0; pointer-events: none; z-index: 9999;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.12) 2px, rgba(0,0,0,0.12) 4px);
  }
  body::after {
    content: '';
    position: fixed; inset: 0; pointer-events: none; z-index: 9998;
    background: radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.6) 100%);
  }

  /* Scanline animation */
  @keyframes scan {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100vh); }
  }
  .scanline {
    position: fixed; left:0; right:0; height:3px;
    background: linear-gradient(transparent, rgba(212,130,10,0.15), transparent);
    animation: scan 6s linear infinite;
    pointer-events: none; z-index: 9997;
  }

  @keyframes flicker { 0%,100%{opacity:1} 50%{opacity:0.92} 75%{opacity:0.96} }
  @keyframes blink { 0%,49%{opacity:1} 50%,100%{opacity:0} }
  @keyframes pulse-red { 0%,100%{box-shadow:0 0 0 0 rgba(255,65,54,0.4)} 50%{box-shadow:0 0 20px 8px rgba(255,65,54,0.2)} }
  @keyframes slide-in { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
  @keyframes grid-move { 0%{background-position:0 0} 100%{background-position:40px 40px} }

  /* Layout */
  .app { display:grid; grid-template-rows:auto 1fr auto; min-height:100vh; }

  /* Header */
  .header {
    border-bottom: 1px solid var(--amber-dim);
    padding: 12px 24px;
    display: flex; align-items: center; justify-content: space-between;
    background: var(--dark2);
    animation: flicker 8s ease-in-out infinite;
  }
  .logo {
    font-family: 'Oswald', sans-serif;
    font-size: 22px; font-weight: 700; letter-spacing: 6px;
    color: var(--amber-glow);
    text-shadow: 0 0 20px var(--amber-dim);
  }
  .logo span { color: var(--red); }
  .tagline { font-size: 9px; letter-spacing: 3px; color: var(--text-dim); margin-top: 2px; }
  .status-bar { display:flex; gap:16px; align-items:center; font-size:10px; }
  .status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:4px; }
  .dot-online  { background:var(--green); box-shadow:0 0 8px var(--green); }
  .dot-offline { background:var(--red); animation:pulse-red 2s infinite; }
  .dot-warn    { background:var(--orange); }
  .provider-badge {
    padding: 3px 10px; border: 1px solid var(--amber-dim);
    font-size: 9px; letter-spacing: 2px; color: var(--amber);
    background: var(--dark3);
  }
  #clock { color: var(--amber-glow); font-size:12px; }

  /* Main grid */
  .main { display:grid; grid-template-columns:380px 1fr; height:calc(100vh - 90px); overflow:hidden; }

  /* Left panel — INPUT */
  .left-panel {
    border-right: 1px solid var(--amber-dim);
    background: var(--dark2);
    display:flex; flex-direction:column;
    overflow:hidden;
  }

  .panel-header {
    padding: 12px 16px; border-bottom: 1px solid var(--amber-dim);
    font-size: 9px; letter-spacing: 4px; color: var(--amber-dim);
    background: var(--dark3);
  }

  /* Threat meter */
  .threat-meter {
    padding: 16px;
    border-bottom: 1px solid var(--amber-dim);
  }
  .threat-label { font-size:9px; letter-spacing:3px; color:var(--text-dim); margin-bottom:8px; }
  .threat-bar { height:6px; background:var(--dark4); border:1px solid var(--amber-dim); position:relative; }
  .threat-fill {
    height:100%; width:0%; transition:width 1s ease, background 0.5s;
    background: linear-gradient(90deg, var(--green), var(--yellow), var(--orange), var(--red));
  }
  .threat-value { font-family:'Oswald',sans-serif; font-size:36px; font-weight:700; color:var(--amber-glow); margin-top:6px; }
  .threat-text { font-size:10px; letter-spacing:2px; color:var(--text-dim); }

  /* Input area */
  .input-area { padding:16px; flex:1; display:flex; flex-direction:column; gap:10px; overflow-y:auto; }
  .input-label { font-size:9px; letter-spacing:3px; color:var(--text-dim); }

  .situation-input {
    width:100%; background:var(--dark3);
    border: 1px solid var(--amber-dim); border-left: 3px solid var(--amber);
    color: var(--text); font-family:'Share Tech Mono',monospace; font-size:12px;
    padding: 12px; resize:none; height:140px; line-height:1.6;
    outline:none; transition:border-color 0.2s;
  }
  .situation-input:focus { border-color:var(--amber-glow); box-shadow:0 0 12px rgba(212,130,10,0.2); }
  .situation-input::placeholder { color:var(--text-dim); }

  .analyze-btn {
    width:100%; padding:14px;
    background: var(--dark3); border: 1px solid var(--amber);
    color: var(--amber-glow); font-family:'Oswald',sans-serif;
    font-size:14px; font-weight:700; letter-spacing:6px;
    cursor:pointer; transition:all 0.2s; text-transform:uppercase;
    position:relative; overflow:hidden;
  }
  .analyze-btn:hover { background:var(--amber-dim); box-shadow:0 0 20px rgba(212,130,10,0.3); }
  .analyze-btn:disabled { opacity:0.4; cursor:not-allowed; }
  .analyze-btn.loading::after {
    content:''; position:absolute; inset:0;
    background:linear-gradient(90deg,transparent,rgba(212,130,10,0.2),transparent);
    animation:shimmer 1s infinite;
  }
  @keyframes shimmer { 0%{transform:translateX(-100%)} 100%{transform:translateX(100%)} }

  /* Quick scenarios */
  .scenarios { display:flex; flex-direction:column; gap:6px; }
  .scenario-btn {
    padding:8px 10px; background:var(--dark3); border:1px solid var(--dark4);
    color:var(--text-dim); font-family:'Share Tech Mono',monospace; font-size:10px;
    letter-spacing:1px; cursor:pointer; text-align:left; transition:all 0.15s;
  }
  .scenario-btn:hover { border-color:var(--amber-dim); color:var(--amber); background:var(--dark4); }
  .scenario-icon { margin-right:8px; }

  /* Chat history mini */
  .chat-history {
    border-top: 1px solid var(--amber-dim);
    padding:10px 16px; max-height:120px; overflow-y:auto;
    font-size:9px; color:var(--text-dim);
  }
  .chat-history-item { padding:3px 0; border-bottom:1px solid var(--dark4); }
  .chi-user { color:var(--amber); }

  /* Right panel — OUTPUT */
  .right-panel { overflow-y:auto; background:var(--dark); }

  /* Empty state */
  .empty-state {
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    height:100%; gap:16px; opacity:0.4;
    background-image: repeating-linear-gradient(0deg,var(--scan),var(--scan) 1px,transparent 1px,transparent 40px),
                      repeating-linear-gradient(90deg,var(--scan),var(--scan) 1px,transparent 1px,transparent 40px);
    animation: grid-move 20s linear infinite;
  }
  .empty-icon { font-size:64px; opacity:0.3; }
  .empty-text { font-family:'Oswald',sans-serif; font-size:18px; letter-spacing:6px; color:var(--amber-dim); }
  .empty-sub  { font-size:10px; letter-spacing:3px; color:var(--text-dim); }

  /* Results */
  .results { padding:20px; display:flex; flex-direction:column; gap:16px; animation:slide-in 0.4s ease; }

  /* Situation summary card */
  .summary-card {
    border: 1px solid var(--amber-dim); border-left: 4px solid var(--amber-glow);
    padding:16px; background:var(--dark2);
  }
  .summary-card h3 { font-family:'Oswald',sans-serif; font-size:11px; letter-spacing:4px; color:var(--amber-dim); margin-bottom:8px; }
  .summary-card p  { font-size:13px; line-height:1.7; color:var(--text); }

  /* Immediate actions */
  .immediate-box {
    border: 1px solid var(--red); background:rgba(255,65,54,0.05);
    padding:14px;
  }
  .immediate-box h3 { font-family:'Oswald',sans-serif; font-size:11px; letter-spacing:4px; color:var(--red); margin-bottom:10px; }
  .imm-action {
    display:flex; gap:12px; align-items:flex-start;
    padding:8px 0; border-bottom:1px solid rgba(255,65,54,0.15);
    animation:slide-in 0.3s ease both;
  }
  .imm-action:last-child { border-bottom:none; }
  .imm-num {
    font-family:'Oswald',sans-serif; font-size:24px; font-weight:700;
    color:var(--red); min-width:32px; line-height:1;
  }
  .imm-body { flex:1; }
  .imm-action-text { font-size:12px; font-weight:bold; color:var(--amber-glow); }
  .imm-time { font-size:9px; letter-spacing:2px; color:var(--orange); margin-top:2px; }
  .imm-reason { font-size:10px; color:var(--text-dim); margin-top:3px; }

  /* Strategy cards */
  .strategies-grid { display:flex; flex-direction:column; gap:12px; }
  .strategy-card {
    border: 1px solid var(--amber-dim); background:var(--dark2);
    transition:border-color 0.2s; animation:slide-in 0.4s ease both;
  }
  .strategy-card:hover { border-color:var(--amber); }

  .card-header {
    display:flex; align-items:center; gap:10px;
    padding:10px 14px; background:var(--dark3);
    border-bottom:1px solid var(--dark4); cursor:pointer;
  }
  .card-rank {
    font-family:'Oswald',sans-serif; font-size:20px; font-weight:700;
    color:var(--amber-glow); min-width:28px;
  }
  .card-title { font-family:'Oswald',sans-serif; font-size:14px; color:var(--text); flex:1; }
  .card-cat {
    font-size:8px; letter-spacing:2px; padding:2px 8px;
    border:1px solid currentColor;
  }
  .cat-WATER    { color:#00b4d8; border-color:#00b4d8; }
  .cat-SHELTER  { color:#8B9467; border-color:#8B9467; }
  .cat-FIRE     { color:#FF6B35; border-color:#FF6B35; }
  .cat-FOOD     { color:#A8E063; border-color:#A8E063; }
  .cat-MEDICAL  { color:#FF4C6A; border-color:#FF4C6A; }
  .cat-SIGNAL   { color:#F7C59F; border-color:#F7C59F; }
  .cat-SECURITY { color:#B5838D; border-color:#B5838D; }
  .cat-POWER    { color:#FFE66D; border-color:#FFE66D; }
  .cat-COMMS    { color:#6BF178; border-color:#6BF178; }

  .urgency-tag {
    font-size:7px; letter-spacing:2px; padding:2px 6px;
  }
  .urgency-IMMEDIATE   { background:rgba(255,65,54,0.2); color:var(--red); }
  .urgency-SHORT_TERM  { background:rgba(255,133,27,0.2); color:var(--orange); }
  .urgency-LONG_TERM   { background:rgba(46,204,64,0.2); color:var(--green); }

  .card-body { padding:14px; display:none; flex-direction:column; gap:12px; }
  .card-body.open { display:flex; }

  .desc { font-size:12px; line-height:1.8; color:var(--text); }
  .arabic-note { font-size:12px; color:var(--amber-dim); border-right:3px solid var(--amber-dim); padding-right:10px; text-align:right; direction:rtl; margin-top:4px; }

  .schematic-box {
    background:var(--dark); border:1px solid var(--dark4);
    padding:12px; font-size:11px; line-height:1.5;
    color:var(--green); white-space:pre; overflow-x:auto;
    font-family:'Share Tech Mono',monospace;
  }

  .two-col { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .mat-section h4 { font-size:9px; letter-spacing:3px; color:var(--text-dim); margin-bottom:6px; }
  .mat-item {
    font-size:10px; padding:3px 0; color:var(--text);
    border-bottom:1px solid var(--dark4);
    display:flex; align-items:center; gap:6px;
  }
  .mat-item::before { content:'▸'; color:var(--amber-dim); }

  .steps-list { list-style:none; counter-reset:steps; }
  .steps-list li {
    counter-increment:steps; font-size:11px; padding:6px 0 6px 32px;
    border-bottom:1px solid var(--dark4); color:var(--text); position:relative;
    line-height:1.6;
  }
  .steps-list li::before {
    content:counter(steps);
    position:absolute; left:0; top:5px;
    font-family:'Oswald',sans-serif; font-size:13px; color:var(--amber-glow);
    width:22px; text-align:center;
  }

  .failure-box { background:rgba(255,65,54,0.05); border:1px solid rgba(255,65,54,0.2); padding:10px; }
  .failure-box h4 { font-size:9px; letter-spacing:3px; color:var(--red); margin-bottom:6px; }
  .failure-item { font-size:10px; padding:2px 0; color:rgba(255,65,54,0.7); }
  .failure-item::before { content:'⚠ '; }

  .time-badge {
    display:inline-block; padding:3px 12px;
    background:rgba(212,130,10,0.1); border:1px solid var(--amber-dim);
    font-size:9px; letter-spacing:2px; color:var(--amber);
  }

  /* Env scan */
  .env-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; }
  .env-box { border:1px solid var(--dark4); padding:12px; background:var(--dark2); }
  .env-box h4 { font-size:9px; letter-spacing:3px; color:var(--text-dim); margin-bottom:8px; }
  .env-item { font-size:10px; padding:3px 0; color:var(--text); border-bottom:1px solid var(--dark4); }

  /* Medical + morale */
  .bottom-row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .medical-box { border:1px solid rgba(255,76,106,0.3); padding:12px; background:rgba(255,76,106,0.03); }
  .medical-box h3 { font-family:'Oswald',sans-serif; font-size:11px; letter-spacing:4px; color:#FF4C6A; margin-bottom:8px; }
  .medical-item { font-size:10px; padding:3px 0; color:var(--text); border-bottom:1px solid var(--dark4); }
  .medical-item::before { content:'+ '; color:#FF4C6A; }

  .morale-box {
    border:1px solid rgba(107,241,120,0.3); padding:16px;
    background:rgba(46,204,64,0.03);
    display:flex; align-items:center; gap:12px;
  }
  .morale-icon { font-size:32px; opacity:0.7; }
  .morale-text { font-family:'Oswald',sans-serif; font-size:15px; color:var(--green); line-height:1.5; }

  /* Chaos score */
  .chaos-score-bar {
    display:flex; align-items:center; gap:12px;
    padding:12px 16px; border:1px solid var(--amber-dim); background:var(--dark2);
  }
  .chaos-label { font-size:9px; letter-spacing:4px; color:var(--text-dim); white-space:nowrap; }
  .chaos-bar-wrap { flex:1; height:8px; background:var(--dark4); border:1px solid var(--dark4); }
  .chaos-bar-fill { height:100%; transition:width 1.2s cubic-bezier(0.4,0,0.2,1); }
  .chaos-num { font-family:'Oswald',sans-serif; font-size:22px; font-weight:700; color:var(--amber-glow); min-width:40px; text-align:right; }

  /* Loading overlay */
  .loading-overlay {
    position:fixed; inset:0; background:rgba(10,8,0,0.9);
    display:none; flex-direction:column; align-items:center; justify-content:center;
    gap:20px; z-index:9000;
  }
  .loading-overlay.show { display:flex; }
  .loading-text { font-family:'Oswald',sans-serif; font-size:18px; letter-spacing:6px; color:var(--amber-glow); }
  .loading-sub  { font-size:10px; letter-spacing:4px; color:var(--text-dim); }
  .loading-bar  { width:300px; height:3px; background:var(--dark4); position:relative; overflow:hidden; }
  .loading-bar::after {
    content:''; position:absolute; top:0; left:-50%; width:50%; height:100%;
    background:linear-gradient(90deg, transparent, var(--amber-glow), transparent);
    animation:loadmove 1.2s linear infinite;
  }
  @keyframes loadmove { 0%{left:-50%} 100%{left:150%} }

  /* Footer */
  .footer {
    border-top:1px solid var(--amber-dim); padding:8px 24px;
    display:flex; justify-content:space-between; align-items:center;
    background:var(--dark2); font-size:8px; letter-spacing:2px; color:var(--text-dim);
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width:4px; height:4px; }
  ::-webkit-scrollbar-track { background:var(--dark); }
  ::-webkit-scrollbar-thumb { background:var(--amber-dim); }

  /* Error */
  .error-card { border:1px solid var(--red); background:rgba(255,65,54,0.05); padding:16px; }
  .error-card h3 { color:var(--red); font-size:12px; letter-spacing:3px; margin-bottom:8px; }
  .error-card p  { font-size:11px; color:rgba(255,65,54,0.7); }
</style>
</head>
<body>
<div class="scanline"></div>

<!-- Loading overlay -->
<div class="loading-overlay" id="loadingOverlay">
  <div style="font-size:48px;">⚡</div>
  <div class="loading-text">CHAOS-1 ANALYZING</div>
  <div class="loading-bar"></div>
  <div class="loading-sub" id="loadingMsg">SCANNING SURVIVAL PARAMETERS...</div>
</div>

<div class="app">
  <!-- Header -->
  <header class="header">
    <div>
      <div class="logo">CHAOS<span>-1</span> // SURVIVAL INTEL</div>
      <div class="tagline">OFFLINE-READY AI CRISIS RESPONSE SYSTEM // نظام الذكاء الاصطناعي للبقاء في الأزمات</div>
    </div>
    <div class="status-bar">
      <span id="clock">--:--:--</span>
      <span><span class="status-dot" id="aiDot"></span><span id="aiStatus">CHECKING...</span></span>
      <span class="provider-badge">{{ provider|upper }} // {{ model }}</span>
    </div>
  </header>

  <!-- Main -->
  <div class="main">
    <!-- Left: Input -->
    <div class="left-panel">
      <div class="panel-header">▸ SITUATION INPUT // إدخال الموقف</div>

      <!-- Threat meter -->
      <div class="threat-meter">
        <div class="threat-label">THREAT LEVEL // مستوى التهديد</div>
        <div class="threat-bar"><div class="threat-fill" id="threatFill"></div></div>
        <div class="threat-value" id="threatValue">—</div>
        <div class="threat-text" id="threatText">AWAITING ANALYSIS</div>
      </div>

      <div class="input-area">
        <div class="input-label">▸ DESCRIBE YOUR SITUATION</div>
        <textarea class="situation-input" id="situationInput"
          placeholder="Describe your situation in detail...&#10;&#10;Examples:&#10;• Grid down, urban area, no water, 3 people&#10;• Lost in forest, night approaching, injured ankle&#10;• Chemical plant fire 2km away, shelter needed&#10;&#10;أو اكتب بالعربية..."></textarea>

        <button class="analyze-btn" id="analyzeBtn" onclick="analyze()">
          ⚡ ANALYZE SITUATION
        </button>

        <div class="input-label" style="margin-top:4px;">▸ QUICK SCENARIOS</div>
        <div class="scenarios">
          <button class="scenario-btn" onclick="setScenario(this.dataset.s)" data-s="Complete power grid failure in urban area. No electricity, no running water, stores closed. Winter approaching. 4 people including 1 elderly and 1 child.">
            <span class="scenario-icon">🏙️</span>URBAN GRID DOWN
          </button>
          <button class="scenario-btn" onclick="setScenario(this.dataset.s)" data-s="Lost in dense forest. Night approaching in 2 hours. Injured ankle, limited mobility. Have: empty backpack, lighter, pocket knife, phone (no signal, 20% battery).">
            <span class="scenario-icon">🌲</span>WILDERNESS SURVIVAL
          </button>
          <button class="scenario-btn" onclick="setScenario(this.dataset.s)" data-s="Flood warning. 6 hours to evacuate. House on 2nd floor. No vehicle. River rising 30cm per hour. Family of 5.">
            <span class="scenario-icon">🌊</span>FLOOD EVACUATION
          </button>
          <button class="scenario-btn" onclick="setScenario(this.dataset.s)" data-s="Chemical factory explosion nearby. Unknown fumes. No hazmat info available. 200 civilians. Need shelter-in-place protocol and improvised filtration.">
            <span class="scenario-icon">☢️</span>CHEMICAL HAZARD
          </button>
          <button class="scenario-btn" onclick="setScenario(this.dataset.s)" data-s="Post-earthquake. Building partially collapsed. 8 people trapped in basement. No electricity, limited air, water pipe broken. Rescue ETA unknown.">
            <span class="scenario-icon">🏚️</span>EARTHQUAKE TRAPPED
          </button>
          <button class="scenario-btn" onclick="setScenario(this.dataset.s)" data-s="انقطاع الكهرباء والإنترنت في منطقة ريفية. لا ماء ولا اتصالات. حرارة شديدة. عائلة من 6 أشخاص. موارد محدودة جداً.">
            <span class="scenario-icon">🌵</span>أزمة ريفية (عربي)
          </button>
        </div>
      </div>

      <!-- Chat history -->
      <div class="chat-history" id="chatHistory">
        <div style="font-size:9px;letter-spacing:3px;color:var(--text-dim);margin-bottom:6px;">▸ SESSION LOG</div>
        <div id="chatItems"></div>
      </div>
    </div>

    <!-- Right: Output -->
    <div class="right-panel" id="outputPanel">
      <div class="empty-state" id="emptyState">
        <div class="empty-icon">☢</div>
        <div class="empty-text">CHAOS-1 STANDBY</div>
        <div class="empty-sub">INPUT SITUATION TO GENERATE SURVIVAL INTELLIGENCE</div>
        <div class="empty-sub" style="margin-top:4px;">أدخل وصف الأزمة للحصول على بروتوكول البقاء</div>
      </div>
      <div class="results" id="resultsArea" style="display:none;"></div>
    </div>
  </div>

  <!-- Footer -->
  <footer class="footer">
    <span>CHAOS-1 // SURVIVAL INTELLIGENCE SYSTEM // OFFLINE-CAPABLE</span>
    <span>نظام البقاء بالذكاء الاصطناعي // يعمل بدون إنترنت</span>
    <span id="analysisCount">ANALYSES: 0</span>
  </footer>
</div>

<script>
let history = [];
let analysisCount = 0;
const loadingMsgs = [
  "SCANNING SURVIVAL PARAMETERS...",
  "CROSS-REFERENCING FIELD MANUALS...",
  "COMPUTING THREAT VECTORS...",
  "GENERATING SCHEMATICS...",
  "RANKING SURVIVAL PROTOCOLS...",
  "يحلل البيانات البيئية...",
];

// Clock
setInterval(() => {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toTimeString().split(' ')[0];
}, 1000);

// Loading message rotator
let msgInterval;
function startLoadingMsgs() {
  let i = 0;
  document.getElementById('loadingMsg').textContent = loadingMsgs[0];
  msgInterval = setInterval(() => {
    i = (i + 1) % loadingMsgs.length;
    document.getElementById('loadingMsg').textContent = loadingMsgs[i];
  }, 900);
}
function stopLoadingMsgs() { clearInterval(msgInterval); }

// Status check
async function checkStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('aiDot').className = 'status-dot dot-online';
    document.getElementById('aiStatus').textContent = d.provider.toUpperCase() + ' READY';
  } catch {
    document.getElementById('aiDot').className = 'status-dot dot-offline';
    document.getElementById('aiStatus').textContent = 'OFFLINE MODE';
  }
}
checkStatus(); setInterval(checkStatus, 15000);

function setScenario(text) {
  document.getElementById('situationInput').value = text;
  document.getElementById('situationInput').focus();
}

function toggleCard(header) {
  const body = header.nextElementSibling;
  body.classList.toggle('open');
  header.querySelector('.toggle-arrow').textContent = body.classList.contains('open') ? '▲' : '▼';
}

function catClass(cat) { return 'cat-' + (cat || 'SHELTER'); }
function urgClass(u)   { return 'urgency-' + (u || 'SHORT_TERM'); }

function threatColor(score) {
  if (score >= 80) return '#FF4136';
  if (score >= 60) return '#FF851B';
  if (score >= 40) return '#FFDC00';
  if (score >= 20) return '#2ECC40';
  return '#7FDBFF';
}

function levelColor(level) {
  const c = ['#7FDBFF','#2ECC40','#FFDC00','#FF851B','#FF4136','#FF4136'];
  return c[level] || '#FF4136';
}

function renderResults(d) {
  const res = document.getElementById('resultsArea');
  const chaos = d.chaos_score || 0;
  const threatLvl = d.threat_level || 0;
  const strategies = d.survival_strategies || [];

  let html = '';

  // Chaos score bar
  const cc = threatColor(chaos);
  html += `<div class="chaos-score-bar">
    <div class="chaos-label">CHAOS SCORE</div>
    <div class="chaos-bar-wrap">
      <div class="chaos-bar-fill" id="chaosBarFill" style="width:0%;background:${cc}"></div>
    </div>
    <div class="chaos-num" style="color:${cc}">${chaos}</div>
  </div>`;

  // Summary
  if (d.situation_summary) {
    html += `<div class="summary-card">
      <h3>▸ TACTICAL ASSESSMENT // التقييم التكتيكي</h3>
      <p>${d.situation_summary}</p>
    </div>`;
  }

  // Immediate actions
  if ((d.immediate_actions||[]).length) {
    html += `<div class="immediate-box"><h3>⚡ IMMEDIATE ACTIONS — ACT NOW</h3>`;
    d.immediate_actions.forEach((a,i) => {
      html += `<div class="imm-action" style="animation-delay:${i*0.1}s">
        <div class="imm-num">${a.priority||i+1}</div>
        <div class="imm-body">
          <div class="imm-action-text">${a.action||''}</div>
          <div class="imm-time">⏱ ${a.time_window||''}</div>
          <div class="imm-reason">${a.reason||''}</div>
        </div>
      </div>`;
    });
    html += `</div>`;
  }

  // Strategies
  if (strategies.length) {
    html += `<div class="panel-header" style="padding:8px 0;margin-top:4px;">▸ SURVIVAL STRATEGIES // بروتوكولات البقاء — RANKED BY PRIORITY</div>`;
    html += `<div class="strategies-grid">`;
    strategies.forEach((s, i) => {
      const schematic = s.schematic ? `<div class="schematic-box">
        <div style="font-size:9px;letter-spacing:3px;color:var(--text-dim);margin-bottom:6px;">▸ SCHEMATIC DIAGRAM</div>
${s.schematic}
      </div>` : '';

      const matPrimary = (s.materials_primary||[]).map(m => `<div class="mat-item">${m}</div>`).join('');
      const matImprov  = (s.materials_improvised||[]).map(m => `<div class="mat-item">${m}</div>`).join('');
      const steps      = (s.steps||[]).map(st => `<li>${st}</li>`).join('');
      const failures   = (s.failure_modes||[]).map(f => `<div class="failure-item">${f}</div>`).join('');
      const arabic     = s.arabic_note ? `<div class="arabic-note">${s.arabic_note}</div>` : '';

      html += `<div class="strategy-card" style="animation-delay:${i*0.08}s">
        <div class="card-header" onclick="toggleCard(this)">
          <div class="card-rank">#${s.rank||i+1}</div>
          <div class="card-title">${s.title||'Strategy'}</div>
          <span class="card-cat ${catClass(s.category)}">${s.category||'GENERAL'}</span>
          <span class="urgency-tag ${urgClass(s.urgency)}">${(s.urgency||'').replace('_',' ')}</span>
          <span class="toggle-arrow" style="color:var(--amber-dim);margin-left:8px;">▼</span>
        </div>
        <div class="card-body">
          <div class="desc">${s.description||''}</div>
          ${arabic}
          ${schematic}
          <div class="two-col">
            <div class="mat-section"><h4>▸ PRIMARY MATERIALS</h4>${matPrimary}</div>
            <div class="mat-section"><h4>▸ FIELD IMPROVISED</h4>${matImprov}</div>
          </div>
          <div>
            <h4 style="font-size:9px;letter-spacing:3px;color:var(--text-dim);margin-bottom:8px;">▸ IMPLEMENTATION STEPS</h4>
            <ol class="steps-list">${steps}</ol>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <span class="time-badge">⏱ IMPL. TIME: ${s.time_to_implement||'?'}</span>
          </div>
          ${failures ? `<div class="failure-box"><h4>▸ FAILURE MODES & RISKS</h4>${failures}</div>` : ''}
        </div>
      </div>`;
    });
    html += `</div>`;
  }

  // Env scan
  const env = d.environmental_scan || {};
  if (env.resources_available || env.hazards || env.time_critical_factors) {
    html += `<div class="panel-header" style="padding:8px 0;">▸ ENVIRONMENTAL SCAN</div>
    <div class="env-grid">
      <div class="env-box">
        <h4>▸ AVAILABLE RESOURCES</h4>
        ${(env.resources_available||[]).map(r=>`<div class="env-item">✓ ${r}</div>`).join('')}
      </div>
      <div class="env-box">
        <h4>▸ HAZARDS DETECTED</h4>
        ${(env.hazards||[]).map(h=>`<div class="env-item" style="color:var(--red)">⚠ ${h}</div>`).join('')}
      </div>
      <div class="env-box">
        <h4>▸ TIME-CRITICAL</h4>
        ${(env.time_critical_factors||[]).map(t=>`<div class="env-item" style="color:var(--orange)">⏱ ${t}</div>`).join('')}
      </div>
    </div>`;
  }

  // Medical + Morale
  const medical = d.medical_priorities || [];
  const morale  = d.morale_note || '';
  if (medical.length || morale) {
    html += `<div class="bottom-row">`;
    if (medical.length) {
      html += `<div class="medical-box"><h3>▸ MEDICAL PRIORITIES</h3>
        ${medical.map(m=>`<div class="medical-item">${m}</div>`).join('')}
      </div>`;
    }
    if (morale) {
      html += `<div class="morale-box">
        <div class="morale-icon">🧠</div>
        <div class="morale-text">"${morale}"</div>
      </div>`;
    }
    html += `</div>`;
  }

  res.innerHTML = html;

  // Animate chaos bar
  setTimeout(() => {
    const fill = document.getElementById('chaosBarFill');
    if (fill) fill.style.width = chaos + '%';
  }, 200);
}

async function analyze() {
  const input = document.getElementById('situationInput').value.trim();
  if (!input) return;

  // Update threat meter
  document.getElementById('threatValue').textContent = '...';
  document.getElementById('threatText').textContent  = 'ANALYZING';
  document.getElementById('threatFill').style.width  = '100%';
  document.getElementById('threatFill').style.background = 'var(--amber-dim)';

  // Show loading
  document.getElementById('loadingOverlay').classList.add('show');
  document.getElementById('analyzeBtn').disabled = true;
  document.getElementById('analyzeBtn').classList.add('loading');
  startLoadingMsgs();

  // Hide empty state
  document.getElementById('emptyState').style.display  = 'none';
  document.getElementById('resultsArea').style.display = 'none';

  // Add to history
  history.push({ role: 'user', content: input });
  const chatItems = document.getElementById('chatItems');
  const item = document.createElement('div');
  item.className = 'chat-history-item';
  item.innerHTML = `<span class="chi-user">▸ YOU:</span> ${input.substring(0, 60)}${input.length>60?'...':''}`;
  chatItems.appendChild(item);

  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ situation: input, history: history.slice(-6) }),
    });

    const data = await resp.json();

    if (data.error) {
      document.getElementById('resultsArea').innerHTML =
        `<div class="error-card"><h3>⚠ ANALYSIS FAILED</h3><p>${data.error}</p></div>`;
      document.getElementById('resultsArea').style.display = 'flex';
      return;
    }

    // Update threat meter
    const lvl = data.threat_level || 0;
    const lbl = data.threat_label || 'UNKNOWN';
    const col = levelColor(lvl);
    document.getElementById('threatValue').textContent = `${lvl}/5`;
    document.getElementById('threatValue').style.color = col;
    document.getElementById('threatText').textContent  = lbl;
    document.getElementById('threatFill').style.width  = (lvl/5*100) + '%';
    document.getElementById('threatFill').style.background = col;

    // Add AI to history
    history.push({ role: 'assistant', content: JSON.stringify(data).substring(0, 200) });

    // Render
    renderResults(data);
    document.getElementById('resultsArea').style.display = 'flex';

    // Count
    analysisCount++;
    document.getElementById('analysisCount').textContent = `ANALYSES: ${analysisCount}`;

    // Scroll to top of results
    document.getElementById('outputPanel').scrollTop = 0;

  } catch (err) {
    document.getElementById('resultsArea').innerHTML =
      `<div class="error-card"><h3>⚠ CONNECTION ERROR</h3><p>${err.message}</p></div>`;
    document.getElementById('resultsArea').style.display = 'flex';
  } finally {
    document.getElementById('loadingOverlay').classList.remove('show');
    document.getElementById('analyzeBtn').disabled = false;
    document.getElementById('analyzeBtn').classList.remove('loading');
    stopLoadingMsgs();
  }
}

// Enter to submit
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'Enter') analyze();
});
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("\n" + "═"*60)
    print("  CHAOS-1 // SURVIVAL INTELLIGENCE SYSTEM")
    print("  نظام الذكاء الاصطناعي للبقاء في الأزمات")
    print("═"*60)
    print(f"  AI Provider : {AI_PROVIDER.upper()}")
    print(f"  Model       : {MODEL_MAP.get(AI_PROVIDER, '?')}")
    if AI_PROVIDER == "ollama":
        print(f"  Ollama URL  : {OLLAMA_URL}")
    print(f"  Interface   : http://localhost:5000")
    print("═"*60 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
