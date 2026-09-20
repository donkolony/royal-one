export type Claim = {
  id: string;
  client: string;
  insurer: string;
  vehicle: string;
  description: string;
  date: string;
  status: number;
  files: string[];
  details: Record<string, string>;
  updates: { date: string; text: string }[];
  review?: string;
};
export type Goal = {
  id: string;
  client: string;
  name: string;
  current: number;
  target: number;
  date: string;
  shared: boolean;
};
export type Reminder = {
  id: string;
  client: string;
  title: string;
  date: string;
  recipient: string;
  done: boolean;
};
export type Request = {
  id: string;
  client: string;
  type: string;
  details: string;
  date: string;
  status: string;
};
export type Store = {
  claims: Claim[];
  goals: Goal[];
  reminders: Reminder[];
  requests: Request[];
  drafts: Record<string, string>;
};
export const clients = [
  {
    name: "Thando Mokoena",
    initials: "TM",
    email: "thando@example.com",
    assets: 1845000,
    liabilities: 420000,
  },
  {
    name: "Lerato Dlamini",
    initials: "LD",
    email: "lerato@example.com",
    assets: 2320000,
    liabilities: 640000,
  },
  {
    name: "James Williams",
    initials: "JW",
    email: "james@example.com",
    assets: 970000,
    liabilities: 180000,
  },
];
export const stages = [
  "Submitted",
  "Assessment",
  "Quotes received",
  "Repairs authorised",
  "In repair",
  "Ready for collection",
  "Closed",
];
export const policies = [
  {
    id: "SAN-2048-091",
    name: "Comprehensive motor",
    provider: "Santam",
    category: "Motor",
    premium: 1250,
    cover: 325000,
    renewal: "2026-11-01",
    detail: "2022 Volkswagen Polo · JH 42 NP GP",
  },
  {
    id: "DIS-8821-032",
    name: "Life & disability cover",
    provider: "Discovery",
    category: "Life",
    premium: 890,
    cover: 2500000,
    renewal: "2027-03-01",
    detail: "Life, disability and severe illness",
  },
  {
    id: "AG-7732-104",
    name: "Retirement annuity",
    provider: "Allan Gray",
    category: "Investment",
    premium: 2500,
    cover: 485000,
    renewal: "2027-01-15",
    detail: "Balanced fund · Monthly contribution",
  },
  {
    id: "SAN-1102-087",
    name: "Home & contents",
    provider: "Santam",
    category: "Home",
    premium: 680,
    cover: 1200000,
    renewal: "2026-12-01",
    detail: "Rosebank, Johannesburg",
  },
];
export const seed: Store = {
  claims: [
    {
      id: "CLM-2026-014",
      client: "Thando Mokoena",
      insurer: "Santam",
      vehicle: "2022 Volkswagen Polo",
      description: "Rear bumper damaged in a collision on Jan Smuts Avenue.",
      date: "2026-09-14",
      status: 3,
      files: ["accident-scene.jpg", "drivers-licence.pdf"],
      details: {
        caseNumber: "CAS 142/09/2026",
        handler: "Sarah Jacobs",
        insurerReference: "SAN-CL-90842",
        repairer: "Auto Magic Rosebank",
        hireCar: "Compact vehicle reserved",
        repairDate: "2026-09-23",
      },
      updates: [
        {
          date: "2026-09-18",
          text: "Repairs authorised. Your repair booking is confirmed for 23 September.",
        },
        {
          date: "2026-09-16",
          text: "Assessment completed and repair quote received.",
        },
        { date: "2026-09-14", text: "Claim registered and sent to Santam." },
      ],
    },
    {
      id: "CLM-2026-012",
      client: "Lerato Dlamini",
      insurer: "Discovery",
      vehicle: "2021 Toyota Corolla",
      description: "Windscreen damage.",
      date: "2026-09-12",
      status: 1,
      files: [],
      details: {},
      updates: [
        { date: "2026-09-12", text: "Claim submitted. Assessment pending." },
      ],
    },
  ],
  goals: [
    {
      id: "g1",
      client: "Thando Mokoena",
      name: "A place to call home",
      current: 120000,
      target: 200000,
      date: "2027-12-01",
      shared: true,
    },
    {
      id: "g2",
      client: "Thando Mokoena",
      name: "Emergency fund",
      current: 45000,
      target: 60000,
      date: "2027-03-01",
      shared: false,
    },
    {
      id: "g3",
      client: "Thando Mokoena",
      name: "Retirement freedom",
      current: 485000,
      target: 2000000,
      date: "2045-01-01",
      shared: false,
    },
  ],
  reminders: [
    {
      id: "r1",
      client: "Thando Mokoena",
      title: "Annual financial review",
      date: "2026-09-24",
      recipient: "Both",
      done: false,
    },
    {
      id: "r2",
      client: "Thando Mokoena",
      title: "Driving licence renewal",
      date: "2026-10-08",
      recipient: "Client",
      done: false,
    },
    {
      id: "r3",
      client: "Thando Mokoena",
      title: "Home valuation certificate",
      date: "2026-10-15",
      recipient: "Both",
      done: false,
    },
    {
      id: "r4",
      client: "Lerato Dlamini",
      title: "Retirement fee renewal",
      date: "2026-09-22",
      recipient: "Adviser",
      done: false,
    },
  ],
  requests: [
    {
      id: "REQ-1024",
      client: "Thando Mokoena",
      type: "Policy document",
      details: "Please send my latest motor policy schedule.",
      date: "2026-09-18",
      status: "In progress",
    },
  ],
  drafts: {},
};
const key = "royal-square-demo-v1";
export const repository = {
  load(): Store {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "null");
      if (
        value &&
        Array.isArray(value.claims) &&
        Array.isArray(value.goals) &&
        Array.isArray(value.reminders) &&
        Array.isArray(value.requests) &&
        value.drafts
      )
        return value;
    } catch {}
    return structuredClone(seed);
  },
  save(data: Store) {
    localStorage.setItem(key, JSON.stringify(data));
  },
};
export const money = (n: number) =>
  new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    maximumFractionDigits: 0,
  }).format(n);
export const dateLabel = (date: string) =>
  new Date(date + "T12:00:00").toLocaleDateString("en-ZA", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
export const today = () => new Date().toLocaleDateString("en-CA");
export const uid = (prefix: string) =>
  `${prefix}-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
