Technology Stack

Royal Square Financial — Client & Advisor Platform

AfriHack 2026
Version: 1.0
Date: 19 September 2026



1. Stack Overview







Layer



Technology



Purpose





Frontend



React



Client App + Advisor Portal





Backend



Python + FastAPI



REST APIs, business logic, RAG, integrations





Database



Supabase (PostgreSQL)



All structured data





File Storage



Supabase Storage



Claim photos, documents, sketches





Authentication



Supabase Auth



Client & Advisor login + roles





Frontend Hosting



Vercel



React application





Backend Hosting



Render



FastAPI service





LLM / Chat



Groq (primary) or Google Gemini



RAG chatbot + email assistance





Vector Store



Supabase pgvector or Chroma



Document embeddings for RAG





Email Integration



Google Gmail API + OAuth 2.0



Advisor email assistance



2. Frontend — React





Used for both Client App and Advisor Portal



Preferred approach: single codebase with role-based routing



Recommended libraries:





React Router — navigation & protected routes



Tailwind CSS — fast, consistent styling



TanStack Query (React Query) — API data fetching & caching



React Hook Form — forms (claims, requests, goals)



Lucide React or Heroicons — icons



Deployment: Vercel



3. Backend — Python + FastAPI

FastAPI is the main backend. It provides:





High performance and automatic OpenAPI / Swagger docs



Clean REST endpoints for all features



File upload handling



RAG query endpoint



Google OAuth & Gmail-related endpoints



Background tasks (reminders, etc.)

Deployment: Render

Key Python packages:





fastapi, uvicorn



supabase or sqlalchemy + asyncpg



python-multipart (file uploads)



pydantic



langchain or llama-index



httpx



Google API client libraries for Gmail



4. Database & Storage — Supabase







Service



Usage





PostgreSQL



Clients, policies, goals, reminders, claims, claim updates, requests, users





Supabase Auth



Email/password or magic-link login with role claims (client / advisor)





Supabase Storage



Secure storage of photos, licences, sketches and documents





pgvector (optional)



Store document embeddings for the RAG system



5. RAG Document Assistant & LLM

The Advisor-side chatbot uses Retrieval-Augmented Generation.





Only approved documents are indexed (policy wordings, internal processes, company policies, regulations)



Every answer must include citations (document name + page number)

Recommended LLM Providers (Free / Low-cost)







Provider



Notes



Recommendation





Groq



Very fast inference, generous free tier, Llama & Mixtral models



Primary choice





Google Gemini



Strong free tier, good quality



Strong alternative





Together.ai



Good free credits, many open models



Backup





OpenRouter



Access to many models with free credits



Flexible backup



Grok API is not recommended as the primary free option for external hackathon apps at this time.

RAG libraries: LangChain or LlamaIndex



6. Google Workspace / Email Integration





Focus: Gmail



Capabilities: flag important emails, retrieve thread context, help draft replies, link emails to clients/claims



Implemented via Google OAuth 2.0 + Gmail API



Requires Google Cloud project, OAuth consent screen, and secure token storage

For AfriHack: a simulated or limited demo is acceptable if full live OAuth takes too long.



7. Deployment Summary







Component



Platform





React Frontend



Vercel





FastAPI Backend



Render





Database + Storage + Auth



Supabase (managed)

All secrets (API keys, OAuth credentials, Supabase keys) must be stored in environment variables. Never commit secrets to Git.



8. High-Level Architecture

React Client App          React Advisor Portal
(with role-based views)   (Dashboard + RAG Chat + Email assist)
         \                       /
          \                     /
               FastAPI Backend
                  (Render)
                     |
     ┌───────────────┼───────────────┐
     │               │               │
Supabase         LLM Provider     Google APIs
(PostgreSQL +    (Groq / Gemini)  (Gmail OAuth)
 Auth + Storage
 + pgvector)



9. Supporting Tools





Version control: Git + GitHub



API testing: FastAPI automatic Swagger UI



Environment management: .env files (never committed)



10. Important Notes for the Team





Keep the AfriHack demo focused on: dashboards, full claims flow, goals/reminders, and a working RAG example



Email integration can be shown as a prototype or as a clear next-step roadmap item



Use demo/seed data only — do not connect to Royal Square’s live production systems



Store all secrets in environment variables



End of Tech Stack Document
Royal Square Financial — AfriHack 2026