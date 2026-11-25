"""Client-ready *static* FAQ demo source from approved business facts.

No model improvisation, network calls, credential handling or lead collection.
The output is a reviewed Falcon website proposal; saving still follows Falcon's
normal source review and consent. Hosting/deployment is separate.
"""
from __future__ import annotations

from html import escape
import json
import re

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class FAQError(ValueError):
    pass


def _clean(value, label, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise FAQError(label + " must be non-empty and limited to " + str(maximum) + " characters")
    if "\x00" in value or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise FAQError(label + " contains unsupported characters")
    return value.strip()


def make_faq_website(name, business, faqs, contact_email):
    """Build an editable 3-file responsive FAQ site from user-approved facts."""
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise FAQError("Invalid Falcon project name")
    business = _clean(business, "Business name", 90)
    if not isinstance(contact_email, str) or not EMAIL.fullmatch(contact_email):
        raise FAQError("Valid business handoff email required")
    if not isinstance(faqs, (list, tuple)) or not 2 <= len(faqs) <= 30:
        raise FAQError("Provide 2 to 30 approved business FAQ entries")
    clean = []
    seen = set()
    for index, item in enumerate(faqs, 1):
        if not isinstance(item, dict) or set(item) != {"question", "answer"}:
            raise FAQError("FAQ #" + str(index) + " needs exactly question and answer")
        question = _clean(item["question"], "FAQ question", 180)
        answer = _clean(item["answer"], "FAQ answer", 800)
        key = " ".join(question.casefold().split())
        if key in seen:
            raise FAQError("Duplicate FAQ question")
        seen.add(key)
        clean.append({"question": question, "answer": answer})
    title = escape(business)
    # The DOM uses textContent for all chat responses (never innerHTML).
    # Encode < > and & to prevent any untrusted FAQ text ending script tags.
    faq_json = json.dumps(clean, ensure_ascii=True).replace("<", r"\u003c").replace(
        ">", r"\u003e").replace("&", r"\u0026")
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Frequently asked questions and help">
  <title>""" + title + """ | Help Center</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="bar">
  <a class="brand" href="#home">""" + title + """</a>
  <nav aria-label="Main navigation">
    <a href="#faqs">Questions</a><a href="#assistant">Ask</a><a href="#contact">Contact</a>
  </nav>
</header>
<main id="home">
  <section class="hero" aria-labelledby="headline">
    <p class="eyebrow">CUSTOMER HELP CENTER</p>
    <h1 id="headline">The answers you need.<br><span>Without the wait.</span></h1>
    <p class="lede">Explore answers supplied and approved by """ + title + """.
      If something isn't covered, reach our team directly.</p>
    <a class="cta" href="#assistant">Ask a question</a>
  </section>
  <section id="faqs" class="section">
    <p class="eyebrow">KNOW BEFORE YOU GO</p><h2>Frequently asked questions</h2>
    <div class="faq-list">
""" + "\n".join("      <details><summary>" + escape(item["question"]) +
                  "</summary><p>" + escape(item["answer"]) + "</p></details>"
                  for item in clean) + """
    </div>
  </section>
  <section id="assistant" class="section assistant">
    <p class="eyebrow">QUICK ANSWERS</p><h2>Ask our FAQ assistant</h2>
    <p>This simple tool matches your question to published answers. It does not
       access your accounts, remember conversations, or make appointments.</p>
    <div class="chat" aria-label="FAQ assistant">
      <div id="transcript" role="log" aria-live="polite"></div>
      <form id="ask-form">
        <label for="question">Your question</label>
        <div class="input-row">
          <input id="question" type="text" required maxlength="240"
                 placeholder="What would you like to know?">
          <button type="submit">Ask</button>
        </div>
      </form>
    </div>
  </section>
  <section id="contact" class="section contact">
    <p class="eyebrow">HUMAN SUPPORT</p><h2>Still have questions?</h2>
    <p>Our team can help with anything this FAQ doesn't cover.</p>
    <a class="cta" href="mailto:""" + escape(contact_email, quote=True) + """">Contact our team</a>
  </section>
</main>
<footer><span>""" + title + """</span><span>Answers are informational; please confirm important details with our team.</span></footer>
<script src="app.js" defer></script>
</body></html>
"""
    css = """*{box-sizing:border-box}html{scroll-behavior:smooth}
:root{color-scheme:dark;font-family:Inter,"Segoe UI",Arial,sans-serif}
body{margin:0;color:#f5f2ff;background:#0d0b18;line-height:1.65}
.bar{display:flex;justify-content:space-between;align-items:center;gap:2rem;padding:1rem max(5vw,24px);
background:#151126;border-bottom:1px solid #30284d;position:sticky;top:0;z-index:2}
.brand{color:#f6eeff;font-weight:800;font-size:1.2rem;text-decoration:none}
nav{display:flex;gap:1.5rem}nav a{color:#c7bee6;text-decoration:none}
a:hover,a:focus-visible{color:#dab3ff}
.hero{padding:clamp(5rem,13vw,10rem) max(5vw,24px);min-height:65vh;
background:radial-gradient(circle at 70% 30%,#4c2a77 0%,transparent 40%),#0d0b18}
.eyebrow{font-size:.75rem;letter-spacing:.18em;font-weight:800;color:#c79afe}
h1{font-size:clamp(2.9rem,7vw,5.8rem);line-height:1.07;letter-spacing:-.045em;margin:1.3rem 0;max-width:950px}
h1 span{color:#b48cff}h2{font-size:clamp(2rem,4vw,3rem);line-height:1.15}
.lede{max-width:660px;color:#c5bed7;font-size:1.12rem}
.cta,button{display:inline-block;background:#ac70f7;color:#170725;border:0;border-radius:.65rem;
font-weight:800;padding:.85rem 1.3rem;text-decoration:none;cursor:pointer}
button:hover,.cta:hover{background:#d3a7ff;color:#170725}
.section{padding:5.5rem max(5vw,24px);max-width:1200px;margin:auto}
.faq-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}
details,.chat{background:#1b1530;border:1px solid #43335e;border-radius:1rem;padding:1.3rem}
details summary{font-weight:700;cursor:pointer}details p,.assistant>p,.contact p{color:#c3bad6}
.assistant{border-top:1px solid #2c2244}.chat{max-width:810px}
#transcript{min-height:6rem;max-height:16rem;overflow-y:auto;margin-bottom:1rem;white-space:pre-wrap}
.message{margin:.6rem 0;padding:.75rem 1rem;border-radius:.7rem;background:#2f2349}
.message.user{background:#3e2d62}label{display:block;margin-bottom:.45rem}
.input-row{display:flex;gap:.75rem}input{min-width:0;flex:1;background:#100d1c;color:white;
border:1px solid #68518b;border-radius:.6rem;padding:.8rem;font:inherit}
footer{display:flex;justify-content:space-between;flex-wrap:wrap;gap:1rem;color:#a79cbe;
border-top:1px solid #30284d;padding:2rem max(5vw,24px);font-size:.85rem}
@media(max-width:660px){.bar{flex-direction:column;align-items:flex-start;gap:.4rem}
nav{gap:.8rem;flex-wrap:wrap}.faq-list{grid-template-columns:1fr}
.input-row{flex-direction:column}.hero{min-height:auto;padding-top:5rem}}
"""
    js = """'use strict';
const FAQS = """ + faq_json + """;
const HANDOFF = """ + json.dumps(contact_email) + """;
const stopwords = new Set(['a','an','and','are','can','do','does','for','how','i','is','my',
  'of','on','the','to','what','when','where','who','why','with','you','your']);
function tokens(s) {
  return new Set(s.toLowerCase().match(/[a-z0-9]+/g)?.filter(w =>
    w.length > 2 && !stopwords.has(w)) || []);
}
function answer(text) {
  const input = text.toLowerCase().trim();
  const words = tokens(input);
  let chosen = null, best = 0;
  for (const row of FAQS) {
    const question = row.question.toLowerCase().trim();
    if (input === question) return row.answer;
    const expected = tokens(question);
    const common = [...words].filter(w => expected.has(w)).length;
    const score = common / Math.max(1, expected.size);
    if (common >= 2 && score >= 0.68 && score > best) {
      best = score; chosen = row.answer;
    }
  }
  return chosen || 'I don\\'t have a verified answer to that question. Please contact our team: ' + HANDOFF;
}
function addMessage(text, role) {
  const line = document.createElement('p');
  line.className = 'message ' + role;
  line.textContent = text;
  const box = document.getElementById('transcript');
  box.appendChild(line); box.scrollTop = box.scrollHeight;
}
document.getElementById('ask-form').addEventListener('submit', event => {
  event.preventDefault();
  const input = document.getElementById('question');
  const question = input.value.trim();
  if (!question) return;
  addMessage(question, 'user'); addMessage(answer(question), 'assistant');
  input.value = ''; input.focus();
});
"""
    readme = ("# " + business + " — Local FAQ assistant demo\n\n"
              "Source generated exclusively from approved FAQs. No external AI API,"
              " data storage, analytics, account login or message sending. "
              "Unknown or weakly matched questions get a contact handoff. "
              "Search matching is simple and may fail to understand paraphrases.\n\n"
              "Open index.html in a browser to preview. Test desktop, mobile, "
              "all FAQs, unknown questions, accessibility and the contact mailto link "
              "before offering this to customers. No hosting or automated client "
              "account operations are included. The public contact email supplied "
              "in this project is visible in source. Confirm its use with the client.\n")
    return {"name": name, "kind": "website",
            "files": {"index.html": html, "styles.css": css,
                      "app.js": js, "README.md": readme}}
