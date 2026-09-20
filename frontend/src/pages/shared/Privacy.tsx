import React from "react";
import { AlertTriangle } from "lucide-react";
import { Card, PageHeader } from "@/components/ui";
import { useMeta } from "@/lib/meta";

const Row = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div className="py-2 sm:grid sm:grid-cols-[12rem_1fr] gap-4 border-b border-charcoal-100 dark:border-charcoal-700 last:border-0"><dt className="font-medium text-charcoal-900 dark:text-white">{k}</dt><dd className="text-charcoal-700 dark:text-charcoal-300">{children}</dd></div>
);

/**
 * Privacy and data handling, in plain language, describing what THIS SYSTEM actually does. It is a draft for legal review: it makes no
 * claim that the firm complies with any law. POPIA is named as the regime counsel should validate this against.
 */
export default function Privacy() {
  const { data: meta } = useMeta();
  const years = (meta as { retention_years?: number } | undefined)?.retention_years ?? 5;
  return (
    <div className="p-4 md:p-8 max-w-3xl space-y-6">
      <PageHeader title="Privacy and data handling" subtitle="What this system collects, who can see it, and how long it is kept." />
      <p role="note" className="flex gap-3 rounded-md border border-amber-300 bg-amber-50 dark:bg-amber-900/30 p-4 text-sm text-amber-900 dark:text-amber-100">
        <AlertTriangle className="w-5 h-5 shrink-0" aria-hidden="true" />
        <span><strong>Draft for legal review.</strong> This page describes what the prototype does. It is not legal advice and does not claim that the firm complies with any law. The relevant South African regime is the Protection of Personal Information Act (POPIA); counsel needs to validate this text and the retention period before real use. All data in this prototype is synthetic.</span>
      </p>
      <Card><h2 className="font-semibold text-lg mb-2 text-charcoal-900 dark:text-white">What is collected</h2>
        <dl className="text-sm">
          <Row k="Who you are">Name, email address, phone number, date of birth, the date you became a client, and (if you drive) your driver's licence expiry date. There is no field for your ID number.</Row>
          <Row k="Your finances">Your policies, balance sheet lines and goals. Your adviser may also record two optional fields: annual income and number of dependants, used only to check whether your life cover keeps up with your commitments. Without them that check does not run.</Row>
          <Row k="Claims and requests">What happened, where, police case number, other drivers, witnesses, photos, and the requests you make (for example an address change).</Row>
          <Row k="Identity documents">Your ID, licence and proof of address, added once and reused instead of asking again while they are valid. Verification here is a demo: no identity provider is contacted.</Row>
          <Row k="Records of our dealings">Advice records (what was discussed and recommended, approved by your adviser), the consents you give or withdraw, and a log of who opened or changed your information, with the time and network address.</Row>
        </dl></Card>
      <Card><h2 className="font-semibold text-lg mb-2 text-charcoal-900 dark:text-white">Who can see it</h2>
        <dl className="text-sm">
          <Row k="You">Everything about you, but not your adviser's internal sales notes.</Row>
          <Row k="Your adviser">Only the clients assigned to them. Opening a client's file is recorded.</Row>
          <Row k="The firm's owner">Every client's file, for oversight. Opening a file is recorded.</Row>
          <Row k="Anyone else">No one. Access is enforced twice: by the application and by the database's own row-level rules. Files are stored privately and are only ever opened through short-lived links.</Row>
        </dl></Card>
      <Card><h2 className="font-semibold text-lg mb-2 text-charcoal-900 dark:text-white">Where AI is used, and what it sees</h2>
        <ul className="text-sm list-disc pl-5 space-y-1 text-charcoal-700 dark:text-charcoal-300">
          <li>The document assistant (advisers only) answers from the firm's approved documents and cites them. Your data is not in that document set.</li>
          <li>Drafting helpers (an email to an insurer, outreach wording, an advice summary) receive only the facts needed for that draft. A person reviews and sends or approves everything; the system never sends anything by itself.</li>
          <li>Documents, identity files and bank details are never sent to an AI model.</li>
        </ul></Card>
      <Card><h2 className="font-semibold text-lg mb-2 text-charcoal-900 dark:text-white">How long it is kept</h2>
        <p className="text-sm text-charcoal-700 dark:text-charcoal-300">The retention period is set to <strong>{years} years</strong> in this prototype. That number is a <strong>placeholder</strong>, not a statement of the legal requirement: counsel or the firm's compliance officer must set it. Records past the period are listed for a person to review. <strong>Nothing is deleted automatically.</strong></p></Card>
      <Card><h2 className="font-semibold text-lg mb-2 text-charcoal-900 dark:text-white">Your choices</h2>
        <p className="text-sm text-charcoal-700 dark:text-charcoal-300">You can give or withdraw your consents at any time (in "My record" if you are a client). Withdrawing tells your adviser. Each consent records which version of this notice you saw.</p></Card>
      <Card><h2 className="font-semibold text-lg mb-2 text-charcoal-900 dark:text-white">What is simulated</h2>
        <ul className="text-sm list-disc pl-5 space-y-1 text-charcoal-700 dark:text-charcoal-300"><li>The insurer and product providers (a demo simulator moves claims and requests).</li><li>Identity verification (a demo adapter).</li><li>The mailbox (seeded, synthetic threads).</li><li>Every rand figure on the owner's and advisers' screens is a demo estimate.</li></ul></Card>
    </div>
  );
}
