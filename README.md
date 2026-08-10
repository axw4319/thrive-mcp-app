# Thrive AI Visibility — MCP server (ChatGPT app + Claude connector)

Remote MCP server that makes Thrive's AI visibility scanner and strategy-call booking usable **inside ChatGPT and Claude**. One codebase serves both surfaces: ChatGPT reads it via the Apps SDK / developer-mode connector, Claude via a custom connector.

- **Live endpoint:** `https://mcp.thriveagency.com/mcp` (Streamable HTTP, stateless, no auth)
- **Hosting:** Render `thrive-mcp` (`srv-d97bmmbtqb8s73fnvvkg`, Thrive workspace, starter plan, Oregon). Auto-deploys from `main`.
- **DNS:** Cloudflare CNAME `mcp` → `thrive-mcp.onrender.com`, **DNS-only/grey cloud** (Cloudflare's proxy can buffer the SSE streams MCP uses — don't orange-cloud it).

## What it does (user flow)

1. User asks ChatGPT/Claude to check their AI visibility → the model asks 2 quick context questions (business/niche/tier + location if local; prompted by the tool description).
2. `run_ai_visibility_scan` starts a **4-prompt scan** on the scanner backend, polls inline ~40s, otherwise hands back a `scan_id` for `get_scan_results`.
3. Results come back with score, per-platform breakdown, competitor leaderboard, and `how_to_improve` — a prioritized, scan-specific action list the model presents in chat.
4. Response includes the **branded PDF** (`pdf_download_url`, via the thrive-report-app URL-to-PDF gateway) and the **strategy-call Calendly link** (UTM-tagged).

## Architecture

```
ChatGPT / Claude
   └─ POST /mcp  (this server — thin wrapper, no scan logic, no database)
        ├─ run_ai_visibility_scan  → scanner POST /api/public/scan/start  (prompt_count=4, user_context)
        ├─ get_scan_results        → scanner GET /api/scan/:id/status + /public-report
        └─ book_ai_strategy_call   → returns Calendly link (no side effects)

scanner = thrive-ai-visibility.onrender.com  (repo: axw4319/thrive-ai-visibility)
   ├─ scan pipeline: scrape → profile+prompts (gpt-4o-mini) → 4 engines in parallel
   │    (gpt-4o-mini "ChatGPT", gemini-2.5-flash "Gemini" + "AI Mode", Perplexity sonar)
   ├─ lib/recommendations.js → data-driven action plan (also in web report + PDF)
   ├─ leads: every scan → Zoho nurture lead + notification (existing pipeline)
   └─ /report/:id → Thrive-branded HTML → thrive-report-app /api/url-to-pdf → PDF
```

## Attribution / lead tracking

- Scans: `utm_source=llm_app`, `utm_medium=mcp`, `utm_campaign=ai_visibility_app` — logged in the scanner's `scan_log` and on the Zoho nurture lead.
- Bookings: same UTMs + `utm_content=<domain>` appended to the Calendly URL → flows through the existing Calendly→Zoho→Google Ads offline-conversion pipeline untouched.
- PDF CTA uses `utm_source=report_pdf` so PDF-driven bookings are distinguishable.

## Env vars (all optional, sane defaults)

| Var | Default | Purpose |
|---|---|---|
| `SCANNER_BASE` | `https://thrive-ai-visibility.onrender.com` | Scanner backend |
| `CALENDLY_URL` | AI Search Strategy event | Booking link base |
| `PDF_GATEWAY` | thrive-report-app url-to-pdf | PDF rendering |
| `INLINE_WAIT_MS` | `40000` | How long a scan call polls before returning scan_id |
| `PORT` | `3002` | HTTP port |

## Run / test locally

```bash
npm install && npm start
# handshake
curl -s -H 'Content-Type: application/json' -H 'Accept: application/json,text/event-stream' \
  -X POST localhost:3002/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Connect for real testing: Claude → Settings → Connectors → Add custom connector → the /mcp URL. ChatGPT → Settings → Apps & Connectors → Developer mode → Create (No authentication).

## Operational notes

- **Rate limits live on the scanner**, per-IP: `PUBLIC_PER_IP_HOUR=30`, `PUBLIC_PER_IP_DAY=150` (env vars on the scanner service). All MCP traffic egresses from this server's IP, so those limits are effectively **global caps for the app** — raise them (or add a trusted-key bypass) if usage grows.
- Cost ≈ **$0.03–0.04 per fresh 4-prompt scan** (Perplexity's per-request fee dominates); repeat scans of the same URL are served from a 30-day cache for free unless the caller requests a deeper scan than the cached one.
- The scanner's LP/web funnel is untouched — no `prompt_count` in the body → same fast 1-prompt demo scan as before.
- Scan quality was validated against Peec (2026-07-08): 4 prompts + user context fixed the market-tier and geography failure modes of the 1-prompt scan.

## Launch checklist (directory submissions)

- [ ] OpenAI Platform: **business verification** for Thrive (blocker for ChatGPT App Directory; publishing under an unverified name = rejection)
- [ ] Privacy policy + terms URLs (required by both directories; missing privacy policy = auto-reject on Claude's)
- [ ] Icon 64×64 <5KB + screenshots + reviewer test cases (ChatGPT submission form)
- [ ] Claude Connectors Directory: submit from claude.ai org admin settings (org owner)
- [ ] Optional: Apps SDK UI widget (visual scorecard card) — strengthens the ChatGPT listing
- [x] Tool annotations (`readOnlyHint` etc.) + output schemas — done in v1.2
