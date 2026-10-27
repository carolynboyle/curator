# Qt Customer App — Design Notes
## Refurb Customer Portal Companion

---

## Concept

A Qt desktop application shipped as part of the refurb package to every
customer. Cross-platform: develop on Linux, build Windows .exe, Mac if
patience holds.

Primary purpose: **one-click remote support access**, customer-initiated,
time-bounded, cryptographically secure.

---

## Remote Support Flow

```
Customer clicks "Request Support"
    → Qt app requests time-limited authkey from headscale server
    → authkey encrypted + signed with GPG, sent to Carolyn over mesh
    → Carolyn receives authkey, customer machine joins mesh temporarily
    → Remote session proceeds (NX/SPICE/RDP depending on platform)
    → Authkey expires, machine leaves mesh automatically
```

**Why this is elegant:**
- No VPN setup for the customer
- No port forwarding, no "tell me your IP address"
- No permanent mesh membership — time-bounded only
- Customer-initiated — they clicked the button, they stay in control
- Authkey expiry means access ends automatically even if Carolyn forgets
  to disconnect

---

## GPG Role

GPG handles security transparently — customer never touches it directly.

**At onboarding (provisioned by curator_init.py or equivalent):**
- Customer GPG keypair generated and stored in Qt app config
- Carolyn's public GPG key pre-installed in the app
- App is pre-configured — customer never runs gpg commands

**During support request:**
- Authkey request encrypted with Carolyn's public key (only she can read it)
- Request signed with customer's private key (proves it's really them)
- Carolyn's tooling decrypts and verifies automatically

**Proven pattern:**
GPG used successfully in Proxmox API app — passphrase entered once at
app start, then completely transparent. Same pattern applies here.
Customer experience: click button, support session starts. GPG invisible.

---

## Qt App UI (sketch)

**Main window — minimal:**
```
┌─────────────────────────────────┐
│  [Logo]  WCYJ Tech Support      │
│                                 │
│  Your devices: 2                │
│  Open tickets: 1                │
│                                 │
│  ┌─────────────────────────┐   │
│  │   Request Support       │   │
│  └─────────────────────────┘   │
│                                 │
│  Status: No active session      │
└─────────────────────────────────┘
```

**Status indicators:**
- `No active session` — idle
- `Requesting session...` — authkey being requested
- `Support session active` — mesh connected, Carolyn is in
- `Session ended` — authkey expired or closed

**Optional: portal link**
- Button to open Curator customer portal in browser
- Shows their devices, tickets, work history

---

## Observatory Integration

Active support sessions visible on the star map:

```
● Gray   — customer machine, no active session
● Amber  — support session requested, not yet connected
● Green  — support session active
● Gray   — session expired/closed
```

Clicking the star in Observatory → opens session details or connects
directly.

---

## Headscale Integration

- App holds pre-provisioned headscale node identity (set up at onboarding)
- On support request: calls headscale API for time-limited authkey
- Authkey duration: configurable (default 1 hour)
- On expiry: node automatically deregisters from mesh
- Customer machine is never a permanent mesh node

**Authkey transmission:**
- Encrypted to Carolyn's GPG key → only she can decrypt
- Signed by customer's GPG key → she can verify the source
- Sent via mesh or fallback to encrypted email if mesh not yet active

---

## Curator Integration

Customer portal (scoped Curator view):
- Customer logs in → sees only their own records
- Their devices (from `infrastructure` schema)
- Their tickets/projects (from `projects` schema, filtered by contact)
- Work history and notes
- Maybe: discussion thread per ticket

**Database scope:**
- `identity.contacts` — customer record
- `identity.app_user` — portal login (customer role)
- `projects.projects` filtered by customer contact
- `infrastructure` filtered by customer's devices

**Felipe's scoped access** (already in roadmap):
- Herald mesh node
- `refurb` PostgreSQL role limiting to refurb records only
- Same pattern extends to all refurb customers

---

## Onboarding Package

When customer picks up their refurbed machine:

1. Qt app pre-installed and pre-configured
2. GPG keypair already generated (by onboarding script)
3. Carolyn's public key pre-installed
4. Headscale node identity provisioned
5. Portal login credentials in a GPG-signed welcome email
6. One-page printed instructions: "Click this button if you need help"

Customer effort: zero cryptography, zero configuration.

---

## Build Plan

**Phase 1 — Linux (develop here first):**
- Qt6 + Python (PyQt6) or C++ Qt
- GPG via python-gnupg or subprocess
- Headscale API calls via requests/httpx
- Single window, minimal UI

**Phase 2 — Windows .exe:**
- PyInstaller or cx_Freeze if Python
- Qt installer framework if C++
- GPG bundled (Gpg4win or similar)
- Code signing certificate eventually

**Phase 3 — Mac (if patience holds):**
- Same codebase, different build target
- GPG via GPG Suite or bundled
- App notarization required for distribution

---

## Related Projects

- **Curator** — customer portal backend and UI
- **Headscale** — mesh coordination server at jump.whycantyoujust.tech
- **Observatory** — star map showing active support sessions
- **curator_init.py** — customer onboarding script (provisions keys,
  mesh identity, portal account, sends welcome email)
- **Bosun** (future) — git operations, may overlap with some tooling

---

## Key Design Principles

1. **Customer-initiated** — support access only when customer clicks
   the button. No persistent access, no background agents phoning home.

2. **Time-bounded** — authkey expires automatically. No cleanup required.

3. **GPG invisible** — cryptography happens in the background.
   Customer experience is: click button, get help.

4. **Zero configuration** — everything pre-provisioned at onboarding.
   Customer receives a working app, not a setup wizard.

5. **Cross-platform** — Qt chosen specifically for write-once,
   build-for-each-platform capability.
