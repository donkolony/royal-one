Product Requirements Document (PRD)

Royal Square Financial — Client & Advisor Platform

AfriHack 2026
Version: 1.0
Date: 19 September 2026



1. Problem Statement

Royal Square Financial (Pty) Ltd is an independent full-service brokerage and Financial Services Provider (FSP 29370). They help clients with wealth creation and preservation by offering insurance and investment products from major South African providers such as Sanlam, Old Mutual, Liberty, Momentum, Discovery, Allan Gray, Santam and others.

The core problem is paperwork.

Every adviser needs formal qualifications. Every client interaction creates compliance work: identity checks, record-keeping, data protection, policy documents, renewals and claims. This load grows every year. Advisers now spend more time on forms and searching documents than actually advising people.

Software is the only scalable solution.



2. Solution Overview

A dual-sided digital platform that connects clients and advisers, reduces manual work, gives real-time visibility, and adds intelligent assistance for documents and email.

Two Interfaces (same backend)







Interface



Who uses it



Purpose





Client App



Policyholders



Simple mobile-friendly view of their financial life + ability to start claims and requests





Advisor Portal



Advisers



Full control over clients, claims, goals, reminders, document Q&A and email assistance



3. Product Goals





Reduce time spent on paperwork and admin



Give both client and adviser a single source of truth



Make the motor claims process clear and trackable from scene to settlement



Automate reminders so nothing important is missed



Help advisers quickly find answers inside policy documents and regulations



Assist with important email communication



4. Core Features (Original Requirements)

4.1 Client Dashboard

Real-time view of the client’s financial position and net worth in one place. Shows:





Policies



Estimated net worth



Open claims and status



Goal progress



Upcoming reminders

4.2 Automated Reminders

System-generated reminders sent to the client, the adviser, or both.

Examples:





Insurance valuation certificate every 2 years → adviser + client



Driving licence expiry → client



Annual financial review meeting → adviser



Retirement fee renewal → adviser



Birthdays and anniversaries → adviser (automated)

The list of reminder types will keep growing.

4.3 Goal Tracking

Advisers can load individual or shared goals for a client. The dashboard shows visual progress (progress bars + percentages).

4.4 Motor Claims Journey (Detailed Flow)

A. Report an Accident / Loss
Client taps “Report an Accident or Loss”. The app immediately shows a checklist of what to gather at the scene:





Photos of the road surface and direction of travel



Address or nearest cross streets



Photos of all vehicles and people involved



Licence plates and registration discs



ID documents of everyone involved



Witness names, contact details + optional voice note



Insurance details of the other parties



Reminder to report to the police within 48 hours

B. Register a Motor Claim
Client selects their insurer and provides:





Date, time and description of the incident



Police notification and case number



Witness details



Who was driving + personal or business use



Details of other vehicles or property



Third-party licence, registration, insurer and policy number

Uploads: photos, driver’s licence, and a sketch of the accident.

C. Post-submission Tracking (mainly managed by adviser, visible to client)





Insurer returns claim number and claims handler



Client takes vehicle for assessment



Assessment goes to insurer and to Royal Square



Repair quotes go to insurer



Insurer authorises repairs



Client picks a date for the vehicle to go in



Adviser arranges car hire and delivery to the repairer



Weekly repair updates



Adviser arranges collection and return of hire car



Client writes a short review and closes the transaction

4.5 Other Client Requests





Change of address



Change of bank details



Request a policy document



Request a border letter



Request an IRP5 from an investment company



Request a consultation



Client information collection (balance sheet / income statement)

4.6 Core Principle

The more that can pass straight through to the product provider automatically (API, direct integration or file transfer), the more useful the system becomes.



5. Additional Features (Team Additions)

5.1 RAG Document Assistant (Advisor only)

A Retrieval-Augmented Generation chatbot that answers questions using only the firm’s approved documents (policy wordings, internal processes, company policies, regulations and laws).

Every answer includes clear citations: document name + page number.

Example questions:





“What is the notification period for a motor claim under a typical Santam policy?”



“What does our internal process say about arranging a hire car?”

5.2 Google Workspace / Email Integration (Advisor only)

Integration with the adviser’s Google Workspace (primarily Gmail) so the system can:





Surface and flag important client or insurer emails



Retrieve context from email threads related to a client or claim



Help draft replies



Link relevant emails to a client or claim record



Note: Full production Gmail integration requires careful OAuth handling. For AfriHack a controlled demo or clear roadmap presentation is acceptable.



6. User Roles







Role



Permissions





Client



View own dashboard, goals, claims, reminders. Start accident report & register claim. Submit requests. Upload documents.





Advisor



View assigned clients. Manage claims pipeline. Set & update goals. Manage reminders. Action client requests. Use RAG assistant. Use email integration.





Admin (future)



User management, document library for RAG, system configuration.



7. Feature Matrix







Feature



Client



Advisor





Dashboard / Net worth view



Yes



Yes





Goal tracking (view)



Yes



Yes





Goal creation & updates



No



Yes





Receive reminders



Yes



Yes





Manage reminders



No



Yes





Report Accident + Checklist



Yes



View





Register Motor Claim + Uploads



Yes



View full record





Claims status tracking



Yes



Yes + update





Arrange hire car / repair logistics



Informed



Action





Other requests (docs, address, IRP5…)



Submit



Action





RAG Document Assistant



No



Yes





Google Workspace / Email assist



No



Yes



8. Success Metrics (Post-Hackathon)





Reduction in time spent searching policy or process documents



Faster claim registration with fewer missing documents



Higher percentage of reminders actioned on time



More adviser time spent in actual client conversations



Positive feedback on the RAG assistant and overall usability



9. Out of Scope for AfriHack MVP





Live connection to Royal Square’s production database



Real insurer API integrations



Full production-grade Gmail OAuth with all edge cases



Native mobile apps (PWA / responsive web is sufficient)



Complex multi-policy live net-worth calculations from external feeds



End of PRD
Royal Square Financial — AfriHack 2026