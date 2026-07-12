# Project "Photon" — Private Email, Proton-style
## Execution Plan (CEO operating model)

**Working name**: Photon (placeholder — deliberately *not* Proton branding; we mimic
the architecture, never the identity).
**Prerequisite reading**: `docs/RESEARCH.md` — how Proton actually works.
**Mission**: an email system where the server provably cannot read your mail.

---

## 1. The Core Loop (what we build first)

One sentence: **two users of our system can exchange mail that the server stores but
can never read.**

```
SIGNUP                LOGIN                 SEND                    READ
──────                ─────                 ────                    ────
client generates      SRP handshake         fetch recipient's       list ciphertext
PGP keypair           (password never       public key              messages
     │                sent to server)            │                       │
encrypt private key        │                encrypt body client-    decrypt client-side
with password-             ▼                side (OpenPGP)          with private key
derived key           fetch encrypted            │                       │
     │                private key blob      POST ciphertext only    render plaintext
     ▼                     │                     │                  (never leaves
register SRP          decrypt locally           ▼                   the browser)
verifier + public          ▼                server stores blob
key with server       session established   it cannot open
```

**The Invariant** (non-negotiable, enforced by automated tests at every phase gate):
> No plaintext message body, no password, and no unencrypted private key ever
> appears in an API request, API response, server log, or database row.

## 2. Tech stack (decided; revisit only with cause)

| Layer | Choice | Why |
|---|---|---|
| Message crypto | **OpenPGP.js** (client-side) | The actual library Proton maintains and uses |
| Auth | **SRP-6a** (vetted lib, e.g. `tssrp6a` / port of `pm-srp`) | Proton's approach; password never transits |
| Key derivation | bcrypt (password → key-encryption-key), mirroring Proton | Documented, proven design |
| Backend | **Python / FastAPI** + SQLAlchemy | Fits this repo's ecosystem; the backend is deliberately "dumb" (stores blobs, routes messages) so language choice is low-risk |
| Database | SQLite (dev) → PostgreSQL (later) | Zero-friction start |
| Frontend | React + Vite | OpenPGP.js runs in browser; all crypto lives here |
| Phase 2 SMTP | aiosmtpd (inbound), standard relay (outbound) | Python-native |

Rule inherited from Proton: **we never write cryptographic primitives.** We compose
audited libraries.

## 3. Organization chart

**CEO — the orchestrating session (me).** Writes task briefs, sets acceptance
criteria, reviews every deliverable, runs the verification suite, gives written
feedback, decides merge/redo. Does not write feature code during build phases.

| Role | Subagent | Owns |
|---|---|---|
| **Architect** | Plan agent | System design docs, API contracts, DB schema, threat model |
| **Crypto Engineer** | general-purpose agent | Key generation/storage lifecycle, SRP flows, OpenPGP integration, the Invariant test suite |
| **Backend Engineer** | general-purpose agent | FastAPI services: auth endpoints, key directory, message store/routing |
| **Frontend Engineer** | general-purpose agent | Web client: signup/login, compose, inbox; all client-side crypto UX |
| **QA / Red Team** | general-purpose agent (separate from builders) | Adversarial review: tries to make the server see plaintext, breaks auth, fuzzes the API. Never reviews their own code |

Working agreements:
- Builders work in **isolated worktrees**; nothing lands on the branch without CEO review.
- The QA agent is always a *different* agent than the one that built the feature.
- Agents that repeatedly miss acceptance criteria get a narrower, more explicit brief
  (feedback loop below), not silent rework by the CEO.

## 4. The management loop (how work actually flows)

Every task follows this cycle:

1. **Brief** — CEO writes a task brief: goal, in-scope files, explicit acceptance
   criteria (runnable checks wherever possible), out-of-scope list.
2. **Build** — subagent implements in an isolated worktree and reports back.
3. **Verify** — CEO independently: runs the test suite, runs the Invariant checks
   (grep API traffic fixtures / DB fixtures for plaintext), reads the diff, exercises
   the feature end-to-end.
4. **Feedback or Accept** —
   - *Criteria met* → merge to the feature branch, log the milestone.
   - *Criteria missed* → written feedback with the exact failing check ("criterion 3
     failed: the signup request body contains the raw password — see capture X"),
     sent back to the **same agent** (context intact) for revision.
   - *Two failed revisions* → CEO rewrites the brief smaller, or reassigns.
5. **Record** — CEO updates `proton-clone/STATUS.md` so any session can pick up state.

## 5. Phases and gates

### Phase 0 — Foundations (CEO + Architect)
- Repo scaffolding under `proton-clone/` (backend, frontend, tests, CI script).
- Architecture doc: API contract for the core loop, DB schema, threat model.
- Skeleton Invariant test harness (fails until Phase 1 satisfies it).
- **Gate**: `make test` runs; API contract reviewed and frozen for Phase 1.

### Phase 1 — THE CORE LOOP (all hands)
| Task | Owner | Acceptance criteria (abridged) |
|---|---|---|
| 1.1 SRP signup/login endpoints | Crypto + Backend | SRP round-trip passes; server DB stores only verifier + salt; wrong password rejected |
| 1.2 Client keypair generation + encrypted storage | Crypto + Frontend | Curve25519 keypair generated in browser; private key blob on server is non-decryptable without password |
| 1.3 Key directory | Backend | GET public key by address; keys are signed/versioned |
| 1.4 Send: client-side encrypt → store | Frontend + Backend | Message encrypted to recipient AND sender keys; server row is PGP ciphertext |
| 1.5 Inbox: list + client-side decrypt | Frontend | Plaintext exists only in browser memory |
| 1.6 Invariant suite + E2E test | QA | Automated: two users, full loop, zero plaintext observed server-side; login with wrong password recovers nothing |
- **Gate (MVP)**: demo script — create alice & bob, alice mails bob "hello", bob reads
  it, and a DB/traffic dump shows ciphertext only. QA agent signs off in writing.

### Phase 2 — External mail (zero-access)
- Inbound SMTP (aiosmtpd): encrypt-on-arrival to recipient's key, discard plaintext.
- Outbound plain SMTP + **password-protected external messages** (symmetric encryption
  + secure web viewer link + expiry), mirroring Proton's design.
- **Gate**: mail from a real external address lands encrypted; password-protected
  message readable by an external recipient with the shared password only.

### Phase 3 — Hardening & trust
- Two-password mode, TOTP 2FA, key pinning/trusted keys, key rotation, recovery keys,
  rate limiting, subject-at-rest encryption, session management.
- **Gate**: red-team report from QA agent with all highs/criticals closed.

### Phase 4 — Ecosystem (the "other services", each its own plan)
- Bridge-style local IMAP proxy → Calendar (encrypted events) → Drive-lite (encrypted
  files) → Pass-lite. All reuse the Phase 1 key infrastructure — which is exactly why
  the core loop comes first.

## 6. Risks the CEO is tracking

1. **Crypto misuse** — mitigated by library-only rule + dedicated Crypto Engineer +
   independent QA + the Invariant suite.
2. **Scope creep** — every phase has a gate demo; nothing from a later phase starts
   until the current gate passes.
3. **Deliverability reality** — real-world sending reputation (SPF/DKIM/DMARC/IP
   warming) is operational, not code; Phase 2 targets *correctness*, not inbox
   placement at Gmail.
4. **Honest positioning** — this is an educational/portfolio build. It is not audited
   and must not be marketed as production-secure email, and it must not imitate
   Proton's name or branding.

## 7. Current status

- [x] Research complete (`docs/RESEARCH.md`)
- [x] Plan approved structure (this document)
- [ ] Phase 0 kickoff — awaiting green light
