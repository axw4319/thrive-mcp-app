# Reviewer test cases — Thrive AI Visibility

For the ChatGPT App Directory submission form ("detailed test cases demonstrating functionality on web and mobile").

## TC1 — Basic scan, auto-generated prompts
1. Prompt: "How visible is thriveagency.com in AI search?"
2. Expect: assistant may ask 1–2 context questions (what the business does, local vs national) and offer auto vs custom prompts. Answer: "full-service digital marketing agency, national, you pick the prompts."
3. Expect: `run_ai_visibility_scan` runs (1–3 min; may require a `get_scan_results` follow-up). Result renders the scorecard widget: 0–100 score, 4 platform bars (ChatGPT, Gemini, Perplexity, Google AI Mode), competitor leaderboard with the scanned brand highlighted, top fixes, and three buttons (Download PDF report / Full report / Book free strategy call).
4. Verify the PDF button downloads a branded PDF and the full-report link opens the hosted report.

## TC2 — Custom prompts
1. Prompt: "Scan acme-example.com and test these exact questions: 'best HVAC marketing agencies', 'top marketing agencies for home services'."
2. Expect: scan runs with those prompts verbatim (visible in the full report's prompt table, category "custom").

## TC3 — Local business geography
1. Prompt: "Scan [any local roofing company domain] — they serve San Antonio homeowners."
2. Expect: generated prompts include San Antonio phrasing; recommendations include the local trust-sources item (Google Business Profile, reviews, local directories).

## TC4 — In-progress handling
1. Start a scan of a domain never scanned before; if the tool returns `in_progress` with a scan_id, the assistant should wait and call `get_scan_results`.
2. Expect: no hallucinated results while pending; widget shows results only when status=complete.

## TC5 — Booking link
1. Prompt: "I want help fixing this — can I talk to someone at Thrive?"
2. Expect: `book_ai_strategy_call` returns a Calendly link (calendly.com/d/cvrh-9hr-43p/…) presented as a clickable link; describes a free 30-minute strategy call; no payment requested anywhere.

## TC6 — Invalid input
1. Prompt: "Scan 'best marketing agency'" (not a domain).
2. Expect: graceful error asking for a valid domain; no crash.

## Notes for reviewers
- The scan queries public AI APIs about generic industry questions; it fetches only public pages of the submitted domain.
- Rate limits: repeated scans of one domain are served from a 30-day cache; per-service limits prevent abuse.
- Free tool; the only "transaction" is an optional free consultation booking via Calendly.
