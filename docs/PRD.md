# Product Requirements Document (PRD)

**Royal Square Financial — Client & Advisor Platform**

| | |
|---|---|
| **Event** | AfriHack 2026 |
| **Client** | Royal Square Financial (Pty) Ltd, FSP 29370 |
| **Director** | Qimso Ntuli |
| **Version** | 1.0, Hackathon Edition |
| **Date** | 19 September 2026 |
| **Source of truth** | `Royal_Square_Financial_PRD.pdf` in this folder (marked "Confidential — For AfriHack 2026 Use"). This file is a Markdown copy of the PDF, plus clearly separated team notes in Sections 9 and 10. If the two ever differ, the PDF wins. |

Related documents: [`api.md`](api.md) (API contract), [`ARCHITECT.md`](ARCHITECT.md) (backend design), [`TECHSTACK.md`](TECHSTACK.md), [`Quickstart.md`](Quickstart.md), [`DESIGN.md`](DESIGN.md).

---

## 1. Problem Statement

Royal Square Financial is an independent full-service brokerage and Financial Services Provider focused on wealth creation and preservation. They offer life, health, funeral, personal and commercial insurance as well as goal-based investments from major South African providers (Sanlam, Old Mutual, Liberty, Momentum, Discovery, Allan Gray, Santam and others).

The core problem is **paperwork and compliance load**. Every adviser needs formal qualifications. Every client interaction generates admin: identity checks, record-keeping, data protection, policy documents, renewals and claims processes. The volume grows every year. Advisers now spend more time on forms and searching documents than advising clients. Software is the only scalable way out.

## 2. Solution Overview

A dual-sided digital platform that connects clients and advisers, reduces manual work, gives real-time visibility, and adds intelligent assistance for documents and email.

The platform has two interfaces sharing the same backend:

| Interface | Users | Purpose |
|---|---|---|
| **Client App** | Policyholders | Simple, mobile-friendly interface for their financial life, plus starting claims and requests |
| **Advisor Portal** | Advisers | Powerful dashboard to manage clients, claims, goals, reminders, documents and email |

## 3. Product Goals

- Reduce time spent on paperwork and admin
- Give both client and adviser a single source of truth for financial position, claims and goals
- Make claims handling (especially motor claims) faster and clearer from scene to settlement
- Automate reminders so nothing important is missed
- Help advisers quickly find answers inside policy documents, regulations and internal processes
- Surface and assist with important email communication

## 4. Core Features (from the original requirements)

### 4.1 Client Dashboard
A real-time view of each client's financial position and net worth in one place. It shows policies, open claims, goal progress and upcoming reminders.

### 4.2 Automated Reminders
System-generated reminders for tasks, documents, renewals and reviews. Examples:

| Reminder | Goes to |
|---|---|
| Insurance valuation certificate every 2 years | Adviser and client |
| Driving licence expiry | Client |
| Annual financial review meeting | Adviser |
| Retirement fee renewal | Adviser |
| Birthdays and anniversaries (automated) | Adviser |

The list of reminder types is expected to grow.

### 4.3 Goal Tracking
Advisers load individual or shared goals for a client. The dashboard shows visual progress (progress bars and percentages).

### 4.4 Motor Claims Journey

**A. Report an Accident / Loss.** The client taps "Report an Accident or Loss". The app immediately returns a checklist of what to gather at the scene:

- Photos of the road surface and direction of travel
- Address or nearest cross streets
- Photos of all vehicles and people involved
- Licence plates and registration discs
- ID documents of everyone involved
- Witness names, contact details and an optional voice note
- Insurance details of the other parties
- Reminder to report to the police within 48 hours

**B. Register a Motor Claim.** The client selects their insurer and the app collects:

- Date, time and description of the incident
- Police notification and case number
- Witness details
- Who was driving, and personal or business use
- Details of other vehicles or property
- Third-party licence, registration, insurer and policy number

Uploads: photos, the driver's licence, and a sketch of the accident.

**C. Post-submission tracking** (managed mainly by the adviser, visible to the client):

1. Insurer returns the claim number and claims handler
2. Client takes the vehicle for assessment
3. Assessment goes to the insurer and to Royal Square
4. Repair quotes go to the insurer
5. Insurer authorises repairs
6. Client picks a date for the vehicle to go in
7. Adviser arranges car hire and delivery to the repairer
8. Weekly repair updates are pushed to the adviser
9. Adviser arranges collection and return of the hire car
10. Client writes a short review and closes the transaction

### 4.5 Other Client Requests
Change of address · Change of bank details · Request a policy document · Request a border letter · Request an IRP5 · Request a consultation · Client information collection (balance sheet / income statement).

### 4.6 Principle
The more that can pass straight through to the product provider automatically (API, direct integration or file transfer), the more useful the system becomes.

## 5. Additional Features (team additions)

### 5.1 RAG Document Assistant (adviser side)
A Retrieval-Augmented Generation chatbot available only to advisers. It answers questions using **only** the firm's approved document set (policy wordings, internal process documents, company policies, relevant regulations and laws). Every answer includes clear citations: **document name and page number**, so the adviser can go straight to the source.

Example use cases:

- "What is the notification period for a motor claim under a typical Santam policy?"
- "What does our internal process say about arranging a hire car?"
- "Summarise the key exclusions in this product wording."

This directly reduces time spent scrolling through long PDFs and lowers compliance risk.

### 5.2 Google Workspace / Email Integration (adviser side)
Integration with the adviser's Google Workspace (primarily Gmail) so the platform can:

- Surface and flag important client or insurer emails
- Retrieve context from email threads related to a client or claim
- Help draft replies
- Link relevant emails to a client or claim record inside the platform

Note: full production-grade Gmail integration requires OAuth consent, careful permission handling and reliability work. For the AfriHack demonstration a controlled/simulated version or a clear roadmap presentation is acceptable. Full live integration is intended as a near-term production enhancement.

## 6. User Roles and Permissions

| Role | Can do |
|---|---|
| **Client** | View own dashboard, goals, claims and reminders; start an accident report and register a claim; submit requests; upload documents |
| **Advisor** | View all assigned clients; manage the claims pipeline; set and update goals; manage reminders; action client requests; use the RAG assistant; interact with the email integration |
| **Admin** (future) | User management, document library management for RAG, system configuration |

## 7. Feature Summary Matrix

| Feature | Client | Advisor |
|---|---|---|
| Personal / client dashboard | Yes | Yes |
| Net worth / financial position view | Yes | Yes |
| Goal tracking (view) | Yes | Yes |
| Goal creation and updates | No | Yes |
| Automated reminders (receive) | Yes | Yes |
| Reminder management | No | Yes |
| Report accident + checklist | Yes | View |
| Register motor claim + uploads | Yes | View full record |
| Claims status tracking | Yes | Yes + update |
| Arrange hire car / repair logistics | Informed | Action |
| Other requests (documents, address, IRP5 …) | Submit | Action |
| RAG document assistant | No | Yes |
| Google Workspace / email assist | No | Yes |

## 8. Success Metrics (post-hackathon)

- Reduction in time spent searching for policy or process information
- Faster claim registration and fewer missing documents at first submission
- Higher percentage of reminders actioned on time
- Adviser time freed for actual client conversations
- Positive feedback from pilot advisers on the RAG assistant and overall usability

---

# Team notes (not part of the client PDF)

## 9. Out of scope for the AfriHack MVP

These come from the team's earlier scope notes, not from the client PDF, apart from the Gmail point which the PDF states in Section 5.2.

- Live connection to Royal Square's production database (demo data only)
- Real insurer API integrations
- Full production-grade Gmail OAuth with all edge cases
- Native mobile apps (a responsive web app is sufficient)
- Complex multi-policy live net-worth calculations from external feeds

## 10. Interpretation decisions made by the team

Where the PDF is silent, the API contract makes the following choices. They are proposals and need confirmation from Royal Square. The full list is in [`api.md`](api.md) §8.

- **Net worth** is the adviser-maintained balance sheet plus the current value of investment and retirement policies, not a live external feed.
- **"Anniversary"** is read as the client relationship anniversary. The PDF does not define it.
- **Reminders** are in-app only. The PDF says reminders are "sent" but does not name a channel (email, SMS or push).
- **Draft claims** are private to the client until they are submitted.
- The **48-hour police reporting** reminder is taken from the PDF checklist as written. Its legal basis has not been verified.
- **Claim statuses** map the ten tracking steps in Section 4.4 C onto nine ordered states; see [`api.md`](api.md) §3.1.
- Advisers **cannot edit** client-entered claim fields after submission in v1 (they can add updates, insurer details, repair and hire-car information).

## 11. Changes made to this file

The previous version of this file had broken table formatting and omitted the client PDF's document metadata, the list of insurance lines, the third RAG use case, and the "Confidential" marking. Those are now restored from the PDF. Its "Out of Scope" section is kept as Section 9 with its source made clear.
