# How Proton Mail Works — Research Notes

Research compiled 2026-07-12 from Proton's public documentation, their open-source
repositories, and the published academic analysis of their cryptographic architecture
(Kobeissi, 2018). This is the foundation for our clone's architecture.

## 1. The core idea: zero-access encryption

Proton's defining property is that **the server can never read your mail**, even though
it stores it. This is achieved by doing all encryption and decryption **client-side**:

- Every message body and attachment stored on Proton's servers is encrypted with the
  user's **public key**. Only the user's **private key** — which never leaves the
  client unencrypted — can decrypt it.
- The private key itself is stored server-side, but encrypted with AES-256 using a
  key derived from the user's password (hashed with bcrypt). The server holds an
  encrypted blob it cannot open.
- Consequence: Proton cannot reset your mailbox password and recover your mail. Losing
  the password means losing the data (unless a recovery key was set up). A faithful
  clone must reproduce this trade-off.

### What is and isn't end-to-end encrypted

| Data | Protection |
|---|---|
| Message body | E2E encrypted (Proton→Proton), zero-access at rest (external inbound) |
| Attachments | Same as body |
| Subject line | Encrypted at rest, but NOT end-to-end (server sees it on external mail transit) |
| Sender/recipient addresses, timestamps | Visible to server (required for routing/SMTP) |

Metadata visibility is an inherent limit of email as a protocol — our clone will have
the same limits and should document them honestly.

## 2. Cryptographic building blocks

- **OpenPGP** is the message format. Proton maintains **OpenPGP.js** (browser) and
  **GopenPGP** (Go wrapper) — both open source and reusable by us.
- **Keys**: by default ECC Curve25519 (X25519) keypairs; historically 4096-bit RSA.
  One keypair generated per email address, plus account-level ("user") keys.
- **Symmetric layer**: AES-256. PGP hybrid encryption = random session key encrypts
  the message, session key encrypted to each recipient's public key.

### Key hierarchy

```
User (account) keys          — encrypt account-level secrets (contacts, settings)
 └── Address keys (per email address, up to 20, one primary)
      └── Session keys (per message, random, wrapped by address public keys)
```

- Users can import external PGP keys, rotate primaries, and mark old keys obsolete.
- **Trusted keys / key pinning**: a contact's key can be pinned so the server cannot
  silently swap it (defense against a malicious server MITM).

## 3. Authentication: SRP (Secure Remote Password)

The login password can derive the mailbox decryption key, so it must **never reach the
server**. Proton uses the SRP protocol (a PAKE — password-authenticated key exchange):

1. At signup, the client computes a **verifier** from the password + salt and sends
   only the verifier. The server never sees the password.
2. At login, client and server run the SRP exchange, mutually authenticating without
   transmitting anything password-equivalent. Resistant to MITM even over broken TLS.
3. After auth, the client fetches the encrypted private key blob and decrypts it
   locally with a key derived from the password (bcrypt + server-provided salt).
4. **One-password mode**: mailbox key derived from login password via a one-way hash
   (with a salt the client doesn't store). **Two-password mode**: separate login and
   mailbox passwords for extra protection against offline oracle attacks.

Proton's SRP implementation is open source: `ProtonMail/pm-srp`.

## 4. Mail flows

### Proton → Proton (internal)
1. Sender's client asks the server for the recipient's public key.
2. Client encrypts body + attachments to recipient's key (and sender's own key, so
   the sent copy is readable) using OpenPGP.
3. Server stores and relays ciphertext only. True E2E.

### External → Proton (inbound from Gmail etc.)
- Arrives as plaintext over SMTP (TLS in transit at best). The server **immediately
  encrypts it to the recipient's public key** and discards the plaintext. This is
  "zero-access" (protects data at rest) but not E2E — the server briefly saw it.

### Proton → External, password-protected
- Sender sets a message password. The message is symmetrically encrypted with it and
  stored on Proton's servers. The external recipient gets a **link** to a secure web
  viewer, enters the shared password, reads and can "Reply securely" (reply goes back
  E2E). Password is shared out-of-band. Messages can auto-expire.

### Proton → External, plain
- Sent as normal SMTP email (TLS in transit); sent copy stored zero-access encrypted.

## 5. Other pieces of the Proton system (later phases)

- **Proton Bridge**: local IMAP/SMTP proxy that decrypts/encrypts so desktop clients
  (Thunderbird, Outlook) work with the encrypted mailbox.
- **Address verification**: signed, pinned contact keys.
- **2FA (TOTP/hardware keys)** layered on top of SRP.
- **Ecosystem**: Calendar (encrypted events), Drive (encrypted file storage), VPN,
  Pass (password manager) — all reuse the same account key infrastructure.
- **Deliverability infrastructure** (the unglamorous hard part of real email):
  SPF, DKIM, DMARC, MX records, IP reputation, spam filtering that must work on
  encrypted content (Proton filters at SMTP ingress, before encryption).

## 6. Implications for our clone

1. **Never invent crypto.** Use OpenPGP.js for message crypto and a vetted SRP
   implementation. The innovation is in the *system design*, not new primitives.
2. **The invariant that defines the product**: no plaintext message body, and no
   password or unencrypted private key, ever crosses the API boundary for internal
   mail. This is testable and every phase gate checks it.
3. **Start internal-only.** The core loop (signup → keys → send/receive between two
   users of our system) exercises the entire cryptographic architecture without
   needing SMTP, DNS, or deliverability. External mail is a later, separable phase.
4. **Honest scope**: this is an educational/portfolio-grade build. Running a *real*
   private email service additionally requires security audits, abuse handling, and
   years of IP reputation work.

## Sources

- [How Proton Mail messages are encrypted](https://proton.me/support/proton-mail-encryption-explained)
- [What is encrypted within Proton Mail](https://proton.me/support/what-is-encrypted-within-protonmail)
- [Proton Mail security overview](https://proton.me/mail/security)
- [Improved authentication (SRP)](https://proton.me/blog/encrypted-email-authentication)
- [pm-srp — Proton's SRP library](https://github.com/ProtonMail/pm-srp)
- [An Analysis of the ProtonMail Cryptographic Architecture (Kobeissi, 2018)](https://eprint.iacr.org/2018/1121.pdf)
- [Proton's response to the analysis](https://proton.me/blog/cryptographic-architecture-response)
- [Encryption and keys](https://proton.me/support/account/security-privacy/encryption-keys)
- [Key management](https://proton.me/support/pgp-key-management)
- [Address verification / trusted keys](https://proton.me/support/address-verification)
- [Password-protected emails](https://proton.me/support/password-protected-emails)
- [How encrypted email works](https://proton.me/blog/encrypted-email)
