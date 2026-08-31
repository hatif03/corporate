# Demo video — final director's script

Target: **4 minutes**. Required beats per the hackathon guideline: problem overview → value proposition → app demo → proof the backend runs on Google Cloud. This version also covers Gemini/Veo/Lyria/voice explicitly, per request.

## Before you hit record — a 5-minute checklist

1. **Open 4 browser tabs, in this order**, all logged in / ready:
   - Tab 1: `https://project-f0b6b4ce-541f-43ff-9f7.web.app` (the live app), already signed in.
   - Tab 2: `https://console.cloud.google.com/run?project=project-f0b6b4ce-541f-43ff-9f7` (Cloud Run services list).
   - Tab 3: `https://console.cloud.google.com/run/detail/us-central1/corporate-backend/logs?project=project-f0b6b4ce-541f-43ff-9f7` (backend live logs).
   - Tab 4: `https://console.cloud.google.com/vertex-ai?project=project-f0b6b4ce-541f-43ff-9f7` (Vertex AI, where Gemini/Veo/Lyria run).
2. **In the app, open Tasks and check the Acme Corp marketing task** — if `videoGenerating` has resolved to a real video URL, great, use it live (Beat 7 below). If it hasn't yet, skip straight to the fallback line in Beat 7 — don't wait for it on camera.
3. **Click "Break room music" once, right now, before recording** — confirms it actually plays end-to-end on the live deployment (this was just fixed; verify it works before you're on camera, not during). If it errors, tell me immediately and skip that beat.
4. **Test the mic/voice feature once** before recording, so you know it responds and your mic input works.
5. Have a short, simple sentence ready to type into the CEO's dispatch box if you want to show a *live* dispatch — don't rely on it finishing during recording (department turns can take 30–90 seconds each); the pre-seeded Acme Corp work already on the Tasks board is your reliable primary material.

## Storyboard

| # | Time | Shot | Script (say this) |
|---|---|---|---|
| 1 | 0:00–0:20 | Landing page (signed out, or open an incognito tab) | "Most AI agent demos are one chatbot answering one question. Real companies aren't one person — they're departments: Finance, Engineering, Legal, Marketing, each with their own judgment, working together under real oversight. That's the gap Corporate closes: a virtual company of autonomous AI departments, coordinated by a CEO agent, that you can actually watch work." |
| 2 | 0:20–0:40 | Sign in, land on the office floor | "Every one of these sprites is a real Google ADK agent — nine departments plus a CEO — running live on Google Cloud right now, not a script. Sign in, and you're looking at the actual live state of the company." |
| 3 | 0:40–1:10 | Office floor + Tasks board (pre-seeded Acme Corp data) | "A few minutes ago I gave the CEO one real goal: we signed a new enterprise customer, Acme Corp. Watch what it did — it broke that into three real tasks and routed each to the department that actually owns that kind of work, over a real Pub/Sub message bus, not a function call." *(click into the Tasks board)* "Finance is processing the actual invoice. Engineering is investigating a reported API incident. Marketing already finished a welcome email — and a promo video." |
| 4 | 1:10–1:35 | Open the finished marketing task, expand verification votes | "Here's the part that matters for a company you'd actually trust: this task's copy isn't just accepted because a model wrote it. It went through independent verification — three separate checks, including a second, independent Gemini call reviewing the first one's work — and you can see exactly which check passed, which flagged an issue, and why." |
| 5 | 1:35–1:55 | Ask-me tab (the blocked engineering task) | "And when something genuinely needs a human, the system doesn't guess — it stops and asks. Here's Engineering flagging a real P2 incident for review, waiting on me, not silently making something up." *(optionally answer it on camera)* |
| 6 | 1:55–2:15 | Settings → Connected apps | "This isn't a toy integration layer either — GitHub and Slack are both really connected here, OAuth and all, with per-department access control behind them." |
| 7 | 2:15–2:40 | Tasks board, the video *(if ready)* — otherwise Break Room | **If the Veo video is ready:** "And Marketing didn't just write copy — it generated this promo video with Veo, Google's video model, as part of the same task." *(play a few seconds)* **If not ready:** "Marketing also kicked off a real Veo-generated promo video as part of this task — Veo generation takes a couple of minutes, so I'll spare you the wait, but it's the same pipeline." Then: *(walk to the Break Room, click music)* "And this — is Lyria, generating this break-room music live, on demand." |
| 8 | 2:40–3:00 | Mic / voice feature | "Agents aren't limited to text either — I can talk to the CEO directly." *(short real exchange — ask it something simple, like the company's current status)* |
| 9 | 3:00–3:15 | Title bar service-status dot + a quick connection-drop toggle (optional) | "And the whole thing reports its own health — this dot is a live poll of the backend, right now." |
| 10 | 3:15–3:45 | Cut to Tab 2 (Cloud Run list), then Tab 3 (logs) | "None of this is running on my laptop. This is Cloud Run — two real, live services, both currently serving traffic." *(click into corporate-backend → point at the URL, then the Logs tab)* "And here are its real request logs, live, from everything we just did." |
| 11 | 3:45–3:55 | Cut to Tab 4 (Vertex AI) | "Every one of those agents reasons using Gemini 3.5, through Vertex AI — same place Veo and Lyria ran from." |
| 12 | 3:55–4:00 | Close, back on the app | "Corporate — nine departments, one CEO, real governance underneath. Live right now at the URL on screen." |

## Exact GCP Console URLs

- **Cloud Run services (both live services)**: `https://console.cloud.google.com/run?project=project-f0b6b4ce-541f-43ff-9f7`
- **corporate-backend logs (proof of real live traffic)**: `https://console.cloud.google.com/run/detail/us-central1/corporate-backend/logs?project=project-f0b6b4ce-541f-43ff-9f7`
- **corporate-backend's own `.run.app` URL** (say it out loud / show the address bar): `https://corporate-backend-2wv6ilt7fa-uc.a.run.app`
- **Vertex AI overview**: `https://console.cloud.google.com/vertex-ai?project=project-f0b6b4ce-541f-43ff-9f7`
- **Live app**: `https://project-f0b6b4ce-541f-43ff-9f7.web.app`

## If you're running short on time, cut in this order

1. Beat 9 (service-status dot) — smallest, most skippable.
2. Beat 8 (voice) — real but not essential if the mic is being uncooperative.
3. Beat 7's video half — the Lyria music alone still covers "multimodal."
4. Never cut Beats 3–4 (multi-department + verification) or 10 (GCP proof) — those are the two things the rules explicitly grade on.
