claude.md

Project Instructions for AI Assistants

Royal Square Financial — AfriHack 2026



You are helping a team build a prototype platform for Royal Square Financial, an independent financial services brokerage in South Africa.

What the product is

A dual-sided web platform:





Client App — simple interface for policyholders



Advisor Portal — powerful interface for financial advisers

Core value: reduce paperwork, make claims tracking clear, give advisers intelligent tools (document Q&A + email assistance).



Current Tech Stack (do not change unless asked)







Layer



Choice





Frontend



React





Backend



Python + FastAPI





Database / Auth / Storage



Supabase





Frontend Hosting



Vercel





Backend Hosting



Render





LLM for RAG



Groq (preferred) or Google Gemini





Email



Google Gmail API + OAuth



Key Features that must be respected

From original client brief:





Client dashboard (net worth, policies, claims, goals, reminders)



Automated reminders



Goal tracking with visual progress



Full motor claims flow:





Report Accident → checklist of what to collect at the scene



Register Claim → form + photo/document upload



Multi-stage tracking (Submitted → Assessment → Quotes → Authorised → Repair → Hire car → Closed)



Other simple requests (address change, policy document, IRP5, border letter, etc.)

Team additions:





RAG Document Assistant (Advisor only) — answers questions from internal documents with citations (document + page number)



Google Workspace / Email integration (Advisor only) — flag emails, draft replies, link to clients/claims



Important Constraints





Demo data only during AfriHack. Do not connect to Royal Square’s real production database.



Keep the MVP focused. A polished claims flow + dashboards + basic RAG is better than many half-finished features.



Email integration is valuable but complex. Prefer a clean prototype or clear roadmap over a broken live OAuth flow.



All secrets must live in environment variables.



Client-facing language should be simple and reassuring. Advisor-facing language should be efficient.



How you should help the team





Prefer simple, working solutions over complex architecture



When writing code, match the agreed stack (React + FastAPI + Supabase)



When designing flows, keep the claims journey clear and status-driven



For the RAG agent: always require citations



Suggest seed/demo data that makes the live demo impressive



If scope is growing too large, gently remind the team of the 24-hour constraint



File Map (important documents)





PRD.md — Full product requirements



TECHSTACK.md — Agreed technology choices



DESIGN.md — UI structure, flows and design principles



Agents.md — Human roles and AI agents in the system



claude.md — This file (instructions for AI assistants)



Tone when helping

Be direct, practical and calm.
Optimise for a working demo that clearly shows value to a financial adviser and their clients.



End of claude.md