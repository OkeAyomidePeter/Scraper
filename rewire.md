Below is a **clean, implementation-ready Markdown document** you can hand directly to Codex or any engineering agent. It is written as a **system design + execution spec**, not marketing fluff.

---

```md
# Semi-Automated Outbound Outreach Pipeline (Nigeria-Focused)

## Purpose

This document defines a **human-in-the-loop outbound pipeline** for contacting local Nigerian businesses safely and consistently, without triggering WhatsApp bans or creating high manual overhead.

The system automates:
- Lead discovery
- Data enrichment
- Channel decision
- Message drafting
- State tracking
- Analytics

The human handles:
- First WhatsApp sends
- Real conversations
- Judgment calls

---

## Design Principles

1. **WhatsApp is never fully automated**
2. **Automation prepares; humans execute**
3. **State-driven, not action-driven**
4. **Minimal cognitive load**
5. **Nigeria-specific communication realities**
6. **Safety > speed**

---

## High-Level Architecture

```

Google Maps Scraper
↓
Lead Enrichment Engine
↓
Channel Decision Engine
↓
AI Message Generator
↓
Telegram Delivery Queue
↓
Manual WhatsApp / Email Sending
↓
Passive State Tracking
↓
Database
↓
Analytics Dashboard

```

---

## Core Entities

### Lead (Business)
Represents a single business discovered via Google Maps.

### Message Draft
AI-generated outreach content tied to a lead and channel.

### State
The lifecycle stage of a lead.

---

## Lead Lifecycle States

```

SCRAPED
ENRICHED
DRAFTED
QUEUED
SENT
WAITING
NO_REPLY
FOLLOW_UP_ELIGIBLE
REPLIED
CONVERSATION_ACTIVE
CLOSED
DROPPED

```

State transitions are automatic except where explicitly noted.

---

## Stage 1: Google Maps Scraping

### Inputs
- Search query (category + city)
- Radius / bounds

### Data Collected
Required:
- lead_id (UUID)
- business_name
- category
- address
- city
- phone_number (raw)
- google_maps_url
- website_url (nullable)

Derived:
- has_website (boolean)
- whatsapp_likely (boolean, inferred from Nigerian mobile formats)

### Notes
- Email is NOT expected from Google Maps
- Phone number is the primary asset in Nigeria

---

## Stage 2: Website & Email Enrichment

### Trigger
```

IF has_website == true

```

### Actions
- Crawl homepage, contact page, footer
- Extract emails via regex
- Deduplicate results

### Output Fields
- email (nullable)
- email_source (homepage | contact | footer)
- email_confidence (high | medium | low)

If no email found, the system falls back to phone-based outreach.

---

## Stage 3: Channel Decision Engine

### Decision Logic

```

IF email exists:
primary_channel = EMAIL
ELSE IF whatsapp_likely:
primary_channel = WHATSAPP_MANUAL
ELSE:
primary_channel = NONE (skip or call)

````

### Rules
- SMS is never used as first contact
- WhatsApp is always manual
- Email can be automated

---

## Stage 4: AI Message Generation

The AI never sends messages directly.  
It only drafts content.

### Message Types

#### 1. Email
- Length: 120–180 words
- Formal but local
- Focus on business outcome, not “website building”

#### 2. WhatsApp
- Max 200 characters
- Permission-based
- No links in first message
- No aggressive selling

#### 3. SMS (Follow-up only)
- Max 140 characters
- Reminder or nudge tone
- Used only after WhatsApp interaction

---

### AI Input Schema

```json
{
  "business_name": "",
  "category": "",
  "city": "",
  "channel": "EMAIL | WHATSAPP | SMS",
  "primary_pain": "",
  "service_angle": "",
  "tone": "neutral | polite | direct",
  "character_limit": 200
}
````

### AI Output

* message_text
* subject_line (email only)

---

## Stage 5: Telegram Delivery Queue

Telegram acts as the **human control layer**.

Each queued item contains:

* Business name
* Channel
* Drafted message
* Action buttons

### Example Actions

* OPEN WHATSAPP
* MARK AS SENT
* SKIP
* REMIND LATER

No typing required. One-tap actions only.

---

## Stage 6: Manual Sending

### WhatsApp

* Opened via:

  ```
  wa.me/234XXXXXXXXX?text=ENCODED_MESSAGE
  ```
* Sent manually
* Timing is irregular and human-like

### Email

* Can be sent automatically or reviewed before sending

---

## Stage 7: Passive State Tracking (“Healthy Bot”)

The system **does not require constant manual updates**.

### Automatic Transitions

```
SENT → WAITING (48h)
WAITING → NO_REPLY (72h)
NO_REPLY → FOLLOW_UP_ELIGIBLE (7 days)
```

### Human Input (Minimal)

Only required when:

* A meaningful reply is received

Telegram prompt example:

> Any reply from {Business Name}?
> [Yes] [No] [Later]

One tap updates state.

---

## Stage 8: Follow-Up Logic

### Trigger

```
state == FOLLOW_UP_ELIGIBLE
```

### Action

* AI drafts follow-up message
* Queued to Telegram
* Human decides to send or skip

Rules:

* Max 1–2 follow-ups
* Follow-ups only if respectful

---

## Stage 9: SMS Usage Rules

SMS is **secondary only**.

### Allowed Use Cases

* Reminder after WhatsApp contact
* Follow-up when WhatsApp is silent but number is valid

### Constraints

* No links
* No pitch
* Reminder tone only

---

## Stage 10: Database Schema (Conceptual)

### Lead

* lead_id
* business_name
* category
* city
* phone_number
* email
* state
* primary_channel
* timestamps

### Message

* message_id
* lead_id
* channel
* content
* sent_at

### Event Log

* event_id
* lead_id
* event_type
* actor (system | human)
* timestamp

---

## Stage 11: Analytics & Dashboard

### Key Metrics

* Leads scraped
* Emails sent
* WhatsApp sent (manual)
* Replies by channel
* Conversion to meeting

### Charts

* Funnel drop-off
* Reply rate by niche
* Channel performance by city

---

## Daily Operating Rhythm

* Drafts generated: 15/day
* Manual sends:

  * Morning: 5
  * Afternoon: 5
  * Evening: 5

Monthly capacity:

* ~390 leads
* Low ban risk
* High personalization

---

## Non-Goals

* No WhatsApp automation via unofficial APIs
* No read/seen tracking
* No spam or bulk blasting
* No dependency on human memory

---

## Summary

This pipeline balances:

* Automation efficiency
* Platform safety
* Human judgment
* Scalability

WhatsApp is treated as a **conversion layer**, not an automation layer.

---



```

---


