# Demo video — storyboard and script

Target length: **~4 minutes** (the hackathon's stated limit). Must prove the backend actually runs on Google Cloud, not just that the UI looks good. Recorded against the live deployment (`https://project-f0b6b4ce-541f-43ff-9f7.web.app`), not localhost — a live URL is worth more on camera than a `localhost:5173` tab.

## Storyboard

| # | Time | Shot | What's on screen |
|---|---|---|---|
| 1 | 0:00–0:15 | Landing page | Hero, tagline, "how it works" steps, the live office-floor teaser, capabilities grid |
| 2 | 0:15–0:25 | Sign-in | Click "Sign in with Google," land on the Command Center |
| 3 | 0:25–0:50 | Office floor, idle | Full office floor, agents idle/animating, title bar's live service-status dot visible |
| 4 | 0:50–1:20 | Dispatch a goal | Open the CEO's Agent Detail → Terminal, type a real multi-department goal, hit send |
| 5 | 1:20–1:50 | Watch it happen | Cut between: office floor (agents light up thinking/working), Tasks board (a card appears, moves columns), Graph tab (message edges appear between CEO and departments) |
| 6 | 1:50–2:15 | A verified task | Open a completed task card, expand the aspect-vote list, point out the "independently verified" badge |
| 7 | 2:15–2:35 | Human-in-the-loop | Ask-me tab, a pending question from a department, answer it, watch the task unblock |
| 8 | 2:35–2:55 | Multimodal | Break-room music (Lyria) playing on the office floor, or a Marketing task's generated Veo promo video |
| 9 | 2:55–3:15 | Service health | Title bar status dot, kill the network briefly (dev tools offline) to show the connection-lost banner, restore it |
| 10 | 3:15–3:40 | Prove it's on GCP | Cut to the GCP Console: the two live Cloud Run services (corporate-backend, corporate-a2a-sales) with real traffic, the Firestore console showing real `orgs/demo/...` documents updating live |
| 11 | 3:40–4:00 | Close | Architecture diagram (docs/ARCHITECTURE.md), one line on the track and the department count, end card with the live URL |

## Script

**[0:00 Landing page]**
"This is Corporate — a virtual company of autonomous AI employees. Nine real departments, a CEO that delegates work between them, all running live on Google Cloud."

**[0:15 Sign-in]**
"Signing in with Google —"

**[0:25 Office floor]**
"— and here's the office floor. Every one of these sprites is a real ADK agent with its own persona, its own memory, and its own job. This status dot up top is polling our backend's health check live, right now."

**[0:50 Dispatch a goal]**
"Let's give the CEO something real to do." *(type a goal that clearly needs more than one department — e.g. "a customer is threatening to churn over a billing dispute, coordinate a response")* "The CEO doesn't have special-cased logic for this — it has the same reasoning as every agent, it just has the tool to create tasks and assign them."

**[1:20 Watch it happen]**
"Watch the floor — Finance is thinking, Support just picked up a task. Here's the Tasks board — a new card, moving from Todo to Doing. And the Graph tab shows the actual message passing between agents — this isn't simulated, it's the real Pub/Sub traffic."

**[1:50 A verified task]**
"Here's a finished task — and this badge isn't just an LLM saying 'trust me.' Every claim like this goes through independent verification: multiple checkers vote, and you can see exactly which one passed, which failed, and why."

**[2:15 Human-in-the-loop]**
"Sometimes an agent needs a human — here's a pending question in Ask-me. I'll answer it —" *(answer)* "— and the task unblocks and continues."

**[2:35 Multimodal]**
"Agents aren't limited to text — this is Lyria-generated break-room music playing right now, and Marketing can generate an actual promo video with Veo as part of a task."

**[2:55 Service health]**
*(open dev tools, go offline briefly)* "If the connection drops — like this — the UI tells you immediately instead of silently freezing. Reconnect —" *(go back online)* "— and it recovers."

**[3:15 Prove it's on GCP]**
"This isn't running on my laptop. Here's the actual Cloud Run console — two live services, real traffic. And here's Firestore — these documents are updating in real time as the agents work."

**[3:40 Close]**
"Corporate — built for the Fortified Enterprise Fleet track. Nine departments, one CEO, real governance and telemetry underneath. Live at the URL on screen now."

## Recording notes

- Use a goal in step 4 that's rehearsed once beforehand so the timing in steps 5–7 is predictable — live LLM output timing varies, don't gamble the whole take on a cold first attempt.
- Have the GCP Console tabs (Cloud Run, Firestore) already open and signed in before recording starts, so step 10 doesn't burn time on navigation.
- If a full take runs long, cut step 8 (multimodal) first — it's the most skippable without losing the "prove it's real and on GCP" narrative the rules explicitly grade on.
