# Linnet

> AI for the tasks the system made hard on purpose.

**Real-time voice transcription with tone annotation — tonal subtext labels for calls, appointments, and difficult conversations.**

[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)](https://git.opensourcesolarpunk.com/Circuit-Forge/linnet)
[![License: BSL 1.1 / MIT](https://img.shields.io/badge/license-BSL%201.1%20%2F%20MIT-blue)](LICENSE)
[![Privacy: Local-first](https://img.shields.io/badge/privacy-local--first-green)](https://circuitforge.tech)

---

## The problem Linnet solves

Reading tone is a skill most communication tools assume you have. For autistic and neurodivergent (ND) users, the emotional and social subtext of speech — "is this person being passive-aggressive or genuinely agreeable?" — can be cognitively expensive to parse in real time, especially during high-stakes conversations like medical appointments, workplace meetings, or difficult phone calls. Linnet labels what is being said *and how it is being said*, so you can stay focused on the content instead of spending bandwidth decoding the register.

---

## What it does

- **Real-time transcription** — local Whisper inference, no cloud required, no audio leaves your machine
- **Tone annotation** — labels each speech segment with its emotional and social register (e.g. "Apologetic", "Stressed", "Enthusiastically agreeing", "Passive-aggressively complying")
- **Elcor mode** — bracketed tone-prefix format inspired by Mass Effect's Elcor species, for users who want tone made explicit in-line with the transcript text
- **Speaker diarization** — distinguishes who is speaking across multi-participant calls
- **Session history** — browse, search, and export past sessions; nothing is sent to a server
- **Translation** — tone labels can be translated via DeepL (BYOK: bring your own key with your DeepL Free account, or use the CF-managed key on Paid tier)
- **Corrections** — inline correction widget to fix transcript errors and retrain your local model over time
- **Embeddable widget** — overlay architecture designed to sit on top of video call windows
- **Meeting notes export** — structured export of transcript + tone timeline for debriefing after a call

---

## Status

**Alpha — core pipeline functional, not production-hardened.**

The transcription pipeline (Whisper + local wav2vec2 SER (speech emotion recognition) inference via `cf-voice`), tone annotation engine, session store, and Vue frontend are all wired up and running. The elcor annotation mode, corrections flow, history strip, and DeepL translation (CF-managed + BYOK) are implemented. The embeddable widget overlay and fine-tuned model support are on the roadmap.

Do not rely on this for high-stakes documentation yet. Use it to orient yourself in conversations, then verify anything important.

---

## Quick start

> Requires Docker + Docker Compose.

```bash
git clone https://git.opensourcesolarpunk.com/Circuit-Forge/linnet
cd linnet
cp .env.example .env          # fill in your settings
./manage.sh start             # API on :8522, frontend on :8521
```

Open `http://localhost:8521` in your browser.

### manage.sh commands

```
./manage.sh start             # start API + frontend
./manage.sh stop              # stop all services
./manage.sh restart           # stop then start
./manage.sh status            # check running services
./manage.sh logs              # tail logs
./manage.sh open              # open UI in browser
```

### Ports

| Service | Default port |
|---------|-------------|
| Frontend (Vue) | 8521 |
| API (FastAPI) | 8522 |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Transcription | [Whisper](https://github.com/openai/whisper) (local, runs on-device) |
| Tone inference | `cf-voice` (wav2vec2 SER, local) |
| Backend | Python 3.11 + FastAPI + WebSockets |
| Frontend | Vue 3 + Vite + UnoCSS |
| Audio capture | Web Audio API |
| Translation | DeepL API (optional, BYOK or CF-managed) |
| Storage | SQLite (local session store) |
| Deployment | Docker Compose |

All transcription and tone annotation runs on your hardware. No audio is transmitted to any server. The only optional network call is the DeepL translation request for tone labels (disabled by default).

---

## Who it's for

**Primary audience: autistic and neurodivergent users.**

If you find reading tonal subtext in real time cognitively expensive — tracking whether someone's agreement is genuine, whether a neutral voice is actually frustrated, whether a doctor is being dismissive or reassuring — Linnet does that work alongside you. The tone labels are not a replacement for your own judgment; they are a second opinion, in real time, that you can weight however you want.

**Also useful for:**
- Deaf and hard-of-hearing users who want real-time captions with social context
- Users with auditory processing differences who hear speech clearly but struggle to parse prosody
- Anyone who wants a transcript of a difficult conversation with tone metadata for review afterward
- Interpreter and accessibility support workflows

**What Linnet will not do:**
- Tell you what someone *means* — only what register their speech is in
- Make decisions on your behalf
- Send your audio anywhere without explicit consent

---

## Tiers

| Tier | What you get |
|------|-------------|
| **Free** | Local transcription + tone annotation, unlimited sessions, local LLM only |
| **Paid** | DeepL translation (CF-managed key), session pinning, cloud STT (speech-to-text) option |
| **Premium** | Fine-tuned models, multi-session dashboard, advanced export |

BYOK: users on any tier can supply their own DeepL Free API key to unlock translation without a Paid subscription.

---

## Privacy · Safety · Accessibility

These are design constraints, not marketing claims.

**Privacy by architecture:** Audio never leaves your machine unless you explicitly configure a cloud STT option. No behavioral profiles, no PII (personally identifiable information) logging, no telemetry by default.

**Safety:** Tone labels are probabilities, not verdicts. Linnet surfaces a confidence threshold and will not emit a label below the reliability floor. You are always in control of what to do with the annotation.

**Accessibility:** Linnet is built for users whose needs are routinely ignored by mainstream tooling. The ND use case is the primary design target, not an afterthought. If the interface creates cognitive load rather than reducing it, that is a bug.

---

## Forgejo-primary

Linnet is developed and maintained on Forgejo at [git.opensourcesolarpunk.com/Circuit-Forge/linnet](https://git.opensourcesolarpunk.com/Circuit-Forge/linnet). GitHub and Codeberg are read-only mirrors. File issues and submit pull requests on Forgejo.

---

## License

- **Transcription pipeline** (audio capture, Whisper integration, session store, export): **MIT**
- **Tone annotation engine** (`app/services/annotator.py`, `cf-voice` integration, elcor mode, translation): **BSL 1.1** — free for personal non-commercial self-hosting; commercial use or SaaS re-hosting requires a paid license. Converts to MIT after 4 years.
- **Fine-tuned model weights** (when released): proprietary, per-user, non-redistributable

---

*Linnet is a product of [CircuitForge LLC](https://circuitforge.tech) — privacy-first, safety-first, accessible AI tools for the tasks the system made hard on purpose.*

---

Humans own design, architecture, code review, testing, and verification. LLMs are part of our development workflow. [Our positions on LLM use →](https://circuitforge.tech/positions)
