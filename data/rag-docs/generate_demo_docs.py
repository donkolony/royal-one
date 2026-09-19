"""Generate the synthetic demo documents and manifest.json for the document assistant.

Run (needs the dev dependencies, fpdf2):  python data/rag-docs/generate_demo_docs.py

EVERYTHING WRITTEN HERE IS FICTIONAL. These documents exist so the assistant can be demonstrated and tested with
page-level citations. They are not real policy wordings, internal Royal Square processes, or laws. Each document says so
on its first page and in the manifest (`is_synthetic: true`).
"""
from __future__ import annotations

import json
from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent
NOTE = "Synthetic demo document written for software demonstration. Not a real policy, process or regulation."
BANNER = "SYNTHETIC DEMO DOCUMENT. This is fictional text for software demonstration only."

DOCS = [
    {
        "file": "demo-motor-policy-wording.pdf",
        "title": "Demo Motor Policy Wording (Synthetic)",
        "category": "policy_wording",
        "version_label": "demo v1",
        "pages": [
            ("Section 1: Introduction and definitions",
             "This is a demonstration motor policy wording. It describes a fictional comprehensive vehicle cover so that the "
             "document assistant can be shown answering questions with page citations. The insured is the person named in the "
             "policy schedule. The insurer is the company that issues the policy. A claim is a request for payment or repair "
             "after an insured event. The excess is the amount the insured pays towards each claim."),
            ("Section 2: What is covered",
             "The policy covers accidental damage to the insured vehicle, theft and attempted theft, fire, and damage caused by "
             "storm or flood. The policy also covers the cost of towing the insured vehicle to the nearest approved repairer "
             "after an insured event. Cover applies within the borders of the country stated in the policy schedule."),
            ("Section 3: Notifying a claim",
             "The insured must notify the insurer of any event likely to give rise to a claim within 30 days of the event. "
             "Theft, hijacking and malicious damage must also be reported to the police within 48 hours, and the police case "
             "number must be given to the insurer. Late notification may reduce or void the claim. The insured must not admit "
             "liability or agree to pay any third party without the insurer's written permission."),
            ("Section 4: Exclusions",
             "The insurer will not pay for loss or damage caused while the driver is under the influence of alcohol or drugs. "
             "The insurer will not pay when the driver does not hold a valid licence for the vehicle. Racing, rallying and "
             "speed testing are excluded. Wear and tear, mechanical breakdown and tyre damage that is not caused by an insured "
             "event are excluded. Loss or damage outside the territorial limits in the policy schedule is excluded."),
            ("Section 5: Excess and repairs",
             "The insured pays the excess shown in the policy schedule for each claim. Repairs must be carried out by an "
             "approved repairer and must be authorised by the insurer before work starts. The insurer may choose to repair, "
             "replace or pay the market value of the insured vehicle."),
        ],
    },
    {
        "file": "demo-claims-handling-process.pdf",
        "title": "Demo Claims Handling Process (Synthetic)",
        "category": "internal_process",
        "version_label": "demo v1",
        "pages": [
            ("1. Purpose and scope",
             "This fictional internal process describes how an adviser handles a motor claim from first notice to closure. "
             "Every new claim must be logged in the claims register on the day it is received. The adviser is the client's "
             "single point of contact throughout the claim."),
            ("2. Registering the claim with the insurer",
             "After a client submits a claim, the adviser sends the claim to the insurer and records the insurer's claim number "
             "and the name of the claims handler on the claim record. The claim is only marked as registered once the insurer's "
             "claim number is recorded. The adviser confirms the registration to the client."),
            ("3. Arranging a hire car",
             "When the insurer authorises repairs, the adviser arranges a hire car with the approved hire supplier. The adviser "
             "arranges delivery of the hire car to the repairer on the day the client's vehicle goes in, and confirms the "
             "arrangement to the client by email. When repairs are complete the adviser arranges collection and return of the "
             "hire car and records the return date on the claim."),
            ("4. Weekly repair updates",
             "While the vehicle is in repair, the adviser asks the repairer for a progress update every week. The update is "
             "posted to the claim timeline so that the client can see it. If the repairer misses two weekly updates in a row, "
             "the adviser escalates to the claims handler at the insurer."),
            ("5. Closing the claim",
             "When the repairs are finished and the hire car is returned, the adviser marks the claim as completed and asks the "
             "client to write a short review. The claim is closed after the client's review."),
        ],
    },
    {
        "file": "demo-data-handling-policy.pdf",
        "title": "Demo Data Handling Policy (Synthetic)",
        "category": "company_policy",
        "version_label": "demo v1",
        "pages": [
            ("1. Principles",
             "This fictional company policy sets out how advisers handle client information. Collect only the information that "
             "is needed for the task. Store client documents only in the approved platform. Never send client identity "
             "documents over personal messaging applications."),
            ("2. Changing bank details",
             "A request to change a client's bank details is a high-risk request. The adviser must verify the request by "
             "telephoning the client on a number already held on file before the change is made. A bank details change must "
             "never be made only because of an email."),
            ("3. Record keeping",
             "Client records are kept for the period set by the firm's compliance officer. Advisers must not delete client "
             "records themselves. Requests to see or correct personal information are passed to the compliance officer."),
        ],
    },
    {
        "file": "demo-compliance-notes.pdf",
        "title": "Demo Compliance Notes (Synthetic)",
        "category": "regulation",
        "version_label": "demo v1",
        "pages": [
            ("Fictional compliance summary, page 1",
             "This fictional summary imitates the style of a regulatory note. It is NOT law and must not be relied on. "
             "Advisers must keep a record of each client meeting, including the date and the advice discussed. "
             "Records of client meetings must be stored in the approved platform."),
            ("Fictional compliance summary, page 2",
             "Advisers must disclose to the client, before giving advice, which product providers they work with. "
             "A client must be given a copy of any signed application. Complaints from clients must be recorded and "
             "passed to the compliance officer within five working days."),
        ],
    },
]


def build(doc: dict) -> None:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=15)
    for heading, body in doc["pages"]:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(0, 5, BANNER)
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, heading)
        pdf.ln(2)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, body)
    (OUT / doc["file"]).write_bytes(bytes(pdf.output()))


def main() -> None:
    for doc in DOCS:
        build(doc)
    manifest = {
        "documents": [
            {"file": d["file"], "title": d["title"], "category": d["category"], "insurer": None, "is_synthetic": True,
             "version_label": d["version_label"], "source_note": NOTE}
            for d in DOCS
        ]
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(DOCS)} documents and manifest.json to {OUT}")


if __name__ == "__main__":
    main()
