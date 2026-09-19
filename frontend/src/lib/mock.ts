import {
  Profile, ClientDashboard, AdvisorDashboard, ClientDetail, Insurer, Policy,
  Goal, Reminder, ClaimSummary, Claim, RequestTypeDefinition, ClientRequest,
  DocumentRecord, AssistantAnswer, EmailThread, ClaimChecklistItem
} from './types';

// Synthetic Mock Data Handlers for Royal Square Frontend

export const mockHandlers: Record<string, any> = {
  '/me': {
    id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01',
    email: 'client1@demo.example',
    full_name: 'Thabo Mokoena',
    role: 'client',
    phone: '+27 82 123 4567',
    created_at: '2026-01-15T08:00:00Z',
    client: {
      id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01',
      adviser: { id: 'c1d2e3f4-0000-4000-8000-000000000001', full_name: 'Sarah van der Merwe', email: 'adviser@demo.example', phone: '+27 82 987 6543' },
      date_of_birth: '1985-06-22',
      drivers_licence_expiry: '2027-11-30',
      client_since: '2020-03-01',
      last_annual_review_date: '2025-10-15'
    },
    advisor: null
  },
  '/me-advisor': {
    id: 'c1d2e3f4-0000-4000-8000-000000000001',
    email: 'adviser@demo.example',
    full_name: 'Sarah van der Merwe',
    role: 'advisor',
    phone: '+27 82 987 6543',
    created_at: '2019-01-10T08:00:00Z',
    client: null,
    advisor: { id: 'c1d2e3f4-0000-4000-8000-000000000001' }
  },
  '/me/dashboard': {
    generated_at: '2026-09-19T14:30:00Z',
    client: { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena', email: 'client1@demo.example', phone: '+27 82 123 4567' },
    adviser: { id: 'c1d2e3f4-0000-4000-8000-000000000001', full_name: 'Sarah van der Merwe', email: 'adviser@demo.example', phone: '+27 82 987 6543' },
    net_worth: { currency: 'ZAR', total_assets_cents: 480000000, total_liabilities_cents: 165000000, net_worth_cents: 315000000, as_of: '2026-09-19', breakdown: [] },
    policies: { count: 4, items: [] },
    open_claims: { count: 1, items: [] },
    goals: { items: [] },
    reminders: { overdue_count: 0, upcoming: [] },
    pending_requests: { count: 1, items: [] }
  },
  '/advisor/dashboard': {
    generated_at: '2026-09-19T14:30:00Z',
    counts: { clients: 3, open_claims: 2, pending_requests: 3, reminders_due_7d: 4, overdue_reminders: 1 },
    claims_by_status: [
      { status: 'submitted', label: 'Submitted', count: 1 },
      { status: 'assessment', label: 'Assessment', count: 1 }
    ],
    needs_attention: [
      {
        kind: 'claim',
        id: 'a5f0e3f4-1000-4000-8000-000000000002',
        title: 'New claim submitted: CLM-2026-0042',
        subtitle: 'Thabo Mokoena · Santam · submitted 2 h ago',
        client: { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' },
        due_at: null,
        link: { resource: 'claim', id: 'a5f0e3f4-1000-4000-8000-000000000002' }
      }
    ],
    upcoming_reminders: []
  },
  '/clients': { 
    items: [
      { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena', email: 'client1@demo.example', phone: '+27 82 123 4567', date_of_birth: '1985-06-22', drivers_licence_expiry: '2027-11-30', client_since: '2020-03-01', last_annual_review_date: '2025-10-15', counts: { policies: 4, open_claims: 1, active_goals: 2, pending_requests: 1, pending_reminders: 3 }, created_at: '2026-01-15T08:00:00Z' },
      { id: '1c8f4b63-2d5f-5d4a-af55-3b5g7f2c9b02', full_name: 'Lerato Dlamini', email: 'client2@demo.example', phone: '+27 83 456 7890', date_of_birth: '1990-02-14', drivers_licence_expiry: '2025-08-10', client_since: '2022-07-20', last_annual_review_date: '2026-01-10', counts: { policies: 2, open_claims: 0, active_goals: 1, pending_requests: 0, pending_reminders: 1 }, created_at: '2026-02-10T10:00:00Z' },
      { id: '2d9g5c74-3e6g-6e5b-bg66-4c6h8g3d0c03', full_name: 'Johan Smit', email: 'client3@demo.example', phone: '+27 72 345 6789', date_of_birth: '1975-11-05', drivers_licence_expiry: '2028-05-25', client_since: '2015-11-01', last_annual_review_date: '2025-12-05', counts: { policies: 6, open_claims: 1, active_goals: 3, pending_requests: 2, pending_reminders: 0 }, created_at: '2026-03-05T09:00:00Z' }
    ], 
    total: 3, limit: 25, offset: 0 
  },
  '/insurers': { 
    items: [
      { id: 'ins-001', name: 'Sanlam' }, { id: 'ins-002', name: 'Old Mutual' }, { id: 'ins-003', name: 'Liberty' }, 
      { id: 'ins-004', name: 'Momentum' }, { id: 'ins-005', name: 'Discovery' }, { id: 'ins-006', name: 'Allan Gray' }, 
      { id: 'ins-007', name: 'Santam' }, { id: 'ins-008', name: 'Other' }
    ] 
  },
  '/policies': { 
    items: [
      { id: 'pol-001', client_id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', insurer: { id: 'ins-007', name: 'Santam' }, category: 'motor', product_name: 'Comprehensive Vehicle Cover', policy_number: 'MOT-789012', status: 'active', asset_description: '2022 Toyota Hilux 2.8 GD-6', cover_amount_cents: 65000000, current_value_cents: null, premium_cents: 145000, premium_frequency: 'monthly', start_date: '2022-04-01', renewal_date: '2027-04-01', valuation_certificate_date: '2026-03-15' },
      { id: 'pol-002', client_id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', insurer: { id: 'ins-005', name: 'Discovery' }, category: 'health', product_name: 'Executive Medical Aid', policy_number: 'MED-345678', status: 'active', asset_description: null, cover_amount_cents: null, current_value_cents: null, premium_cents: 420000, premium_frequency: 'monthly', start_date: '2020-01-01', renewal_date: '2027-01-01', valuation_certificate_date: null },
      { id: 'pol-003', client_id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', insurer: { id: 'ins-006', name: 'Allan Gray' }, category: 'retirement', product_name: 'Retirement Annuity Fund', policy_number: 'RET-901234', status: 'active', asset_description: null, cover_amount_cents: null, current_value_cents: 125000000, premium_cents: 500000, premium_frequency: 'monthly', start_date: '2015-06-01', renewal_date: '2045-06-01', valuation_certificate_date: null },
      { id: 'pol-004', client_id: '1c8f4b63-2d5f-5d4a-af55-3b5g7f2c9b02', insurer: { id: 'ins-002', name: 'Old Mutual' }, category: 'life', product_name: 'Life Cover Plus', policy_number: 'LIF-567890', status: 'active', asset_description: null, cover_amount_cents: 500000000, current_value_cents: null, premium_cents: 85000, premium_frequency: 'monthly', start_date: '2018-09-01', renewal_date: '2027-09-01', valuation_certificate_date: null }
    ], 
    total: 4, limit: 25, offset: 0 
  },
  '/goals': { 
    items: [
      { id: 'gol-001', title: "Children's University Fund", description: "Shared goal for the household", category: 'education', type: 'shared', status: 'active', target_amount_cents: 60000000, current_amount_cents: 15000000, progress_percent: 25.0, target_date: '2036-01-31', participants: [{ client_id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' }], created_by: 'c1d2e3f4-0000-4000-8000-000000000001', created_at: '2024-01-15T10:00:00Z', updated_at: '2026-08-20T14:30:00Z' },
      { id: 'gol-002', title: "Deposit for New House", description: "In Sandton", category: 'property', type: 'individual', status: 'active', target_amount_cents: 35000000, current_amount_cents: 30000000, progress_percent: 85.7, target_date: '2027-06-30', participants: [{ client_id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' }], created_by: 'c1d2e3f4-0000-4000-8000-000000000001', created_at: '2025-05-10T09:15:00Z', updated_at: '2026-09-01T11:45:00Z' },
      { id: 'gol-003', title: "Emergency Fund", description: "6 months expenses", category: 'emergency_fund', type: 'individual', status: 'active', target_amount_cents: 12000000, current_amount_cents: 12000000, progress_percent: 100.0, target_date: '2026-12-31', participants: [{ client_id: '1c8f4b63-2d5f-5d4a-af55-3b5g7f2c9b02', full_name: 'Lerato Dlamini' }], created_by: 'c1d2e3f4-0000-4000-8000-000000000001', created_at: '2025-11-20T16:20:00Z', updated_at: '2026-09-15T08:30:00Z' }
    ], 
    total: 3, limit: 25, offset: 0 
  },
  '/reminders': { 
    items: [
      { id: 'rem-001', type: 'licence_expiry', title: 'Your driving licence expires on 30 Nov 2027', description: 'Renew it before it expires to stay covered while driving.', due_date: '2027-11-30', audience: 'client', status: 'pending', urgency: 'upcoming', source: 'rule', client: { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' }, related: { resource: 'client', id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01' }, completed_at: null, created_at: '2026-09-19T14:30:00Z' },
      { id: 'rem-002', type: 'annual_review', title: 'Annual Review Due', description: 'Schedule the yearly portfolio review.', due_date: '2026-10-15', audience: 'advisor', status: 'pending', urgency: 'upcoming', source: 'rule', client: { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' }, related: { resource: 'client', id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01' }, completed_at: null, created_at: '2026-09-15T08:00:00Z' },
      { id: 'rem-003', type: 'custom', title: 'Call regarding fund switch', description: 'Client wanted to discuss moving to a lower risk fund.', due_date: '2026-09-18', audience: 'advisor', status: 'pending', urgency: 'overdue', source: 'manual', client: { id: '2d9g5c74-3e6g-6e5b-bg66-4c6h8g3d0c03', full_name: 'Johan Smit' }, related: null, completed_at: null, created_at: '2026-09-10T11:20:00Z' },
      { id: 'rem-004', type: 'claim_police_report', title: 'Report accident to police', description: 'You must report the accident within 48 hours to process your claim.', due_date: '2026-09-20', audience: 'client', status: 'pending', urgency: 'due_soon', source: 'rule', client: { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' }, related: { resource: 'claim', id: 'a5f0e3f4-1000-4000-8000-000000000002' }, completed_at: null, created_at: '2026-09-18T18:00:00Z' }
    ], 
    total: 4, limit: 25, offset: 0 
  },
  '/claims/checklist': { 
    items: [
      { id: 'road_surface', order: 1, title: 'Photograph the road', description: 'Photos of the road surface and the direction each vehicle was travelling.', upload_kind: 'road_photo' },
      { id: 'location', order: 2, title: 'Note where you are', description: 'The address, or the nearest cross streets.', upload_kind: null },
      { id: 'vehicles_people', order: 3, title: 'Photograph everything involved', description: 'All vehicles and all people involved.', upload_kind: 'vehicle_photo' },
      { id: 'plates_discs', order: 4, title: 'Licence plates and registration discs', description: 'A clear photo of each.', upload_kind: 'plate_or_disc_photo' },
      { id: 'id_documents', order: 5, title: 'ID documents', description: 'Of everyone involved.', upload_kind: 'id_document' },
      { id: 'witnesses', order: 6, title: 'Witnesses', description: 'Names and contact details. You can add a voice note if it is easier.', upload_kind: 'witness_voice_note' },
      { id: 'other_insurance', order: 7, title: "Other parties' insurance", description: 'Their insurer and policy number.', upload_kind: null },
      { id: 'police', order: 8, title: 'Report it to the police', description: 'Do this within 48 hours and keep the case number.', upload_kind: null }
    ] 
  },
  '/claims': { 
    items: [
      { id: 'a5f0e3f4-1000-4000-8000-000000000002', reference: 'CLM-2026-0042', client: { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' }, insurer: { id: 'ins-007', name: 'Santam' }, status: 'assessment', status_label: 'Assessment', claim_number: 'SC-778201', incident_occurred_at: '2026-09-18T17:45:00Z', incident_location_text: 'Corner of Buitenkant St and Roeland St, Cape Town', hire_car_status: 'not_required', days_in_status: 2, submitted_at: '2026-09-18T20:15:00Z', updated_at: '2026-09-19T08:00:00Z' },
      { id: 'b6g1f4g5-2111-5111-9111-111111111113', reference: 'CLM-2025-0198', client: { id: '2d9g5c74-3e6g-6e5b-bg66-4c6h8g3d0c03', full_name: 'Johan Smit' }, insurer: { id: 'ins-001', name: 'Sanlam' }, status: 'in_repair', status_label: 'In repair', claim_number: 'SL-993412', incident_occurred_at: '2025-11-10T14:30:00Z', incident_location_text: 'N1 Highway, Midrand', hire_car_status: 'delivered', days_in_status: 12, submitted_at: '2025-11-11T09:00:00Z', updated_at: '2025-11-25T16:45:00Z' }
    ], 
    total: 2, limit: 25, offset: 0 
  },
  '/claims/pipeline': { 
    columns: [
      { status: 'submitted', label: 'Submitted', count: 1, claims: [] },
      { status: 'registered', label: 'Registered (claim no. issued)', count: 0, claims: [] },
      { status: 'assessment', label: 'Assessment', count: 1, claims: [] },
      { status: 'quotes', label: 'Quotes with insurer', count: 0, claims: [] },
      { status: 'authorised', label: 'Authorised', count: 0, claims: [] },
      { status: 'in_repair', label: 'In repair', count: 0, claims: [] },
      { status: 'completed', label: 'Completed, awaiting client sign-off', count: 0, claims: [] }
    ] 
  },
  '/claims/detail': {
    // Return a full claim placeholder for specific IDs requested.
  },
  '/requests/types': { 
    items: [
      { type: 'address_change', label: 'Change of address', requires_verification: false, max_attachments: 3, fields: [{ name: 'address_line_1', label: 'Street address', type: 'string', required: true, max_length: 120 }, { name: 'suburb', label: 'Suburb', type: 'string', required: true, max_length: 80 }, { name: 'city', label: 'City', type: 'string', required: true, max_length: 80 }, { name: 'postal_code', label: 'Postal code', type: 'string', required: true, pattern: '^[0-9]{4}$' }] },
      { type: 'bank_details_change', label: 'Change of bank details', requires_verification: true, max_attachments: 3, fields: [{ name: 'account_holder', label: 'Account holder', type: 'string', required: true, max_length: 120 }, { name: 'bank_name', label: 'Bank', type: 'string', required: true, max_length: 80 }, { name: 'account_type', label: 'Account type', type: 'enum', required: true, options: ['cheque', 'savings', 'transmission', 'other'] }, { name: 'account_number', label: 'Account number', type: 'string', required: true, pattern: '^[0-9]{6,16}$' }, { name: 'branch_code', label: 'Branch code', type: 'string', required: true, pattern: '^[0-9]{6}$' }] },
      { type: 'policy_document', label: 'Request Policy Document', requires_verification: false, max_attachments: 0, fields: [{ name: 'policy_id', label: 'Policy', type: 'string', required: true }, { name: 'document_kind', label: 'Document Type', type: 'enum', required: true, options: ['policy_schedule', 'policy_wording', 'certificate', 'other'] }] },
      { type: 'border_letter', label: 'Request Border Letter', requires_verification: false, max_attachments: 0, fields: [{ name: 'policy_id', label: 'Policy', type: 'string', required: true }, { name: 'destination_countries', label: 'Destination Countries', type: 'string_list', required: true }, { name: 'travel_from', label: 'Travel From', type: 'date', required: true }, { name: 'travel_to', label: 'Travel To', type: 'date', required: true }] },
      { type: 'irp5', label: 'Request IRP5', requires_verification: false, max_attachments: 0, fields: [{ name: 'provider_name', label: 'Provider Name', type: 'string', required: true }, { name: 'tax_year', label: 'Tax Year', type: 'integer', required: true }] },
      { type: 'consultation', label: 'Book Consultation', requires_verification: false, max_attachments: 0, fields: [{ name: 'preferred_dates', label: 'Preferred Dates', type: 'string_list', required: true }, { name: 'mode', label: 'Mode', type: 'enum', required: true, options: ['in_person', 'phone', 'video'] }, { name: 'topic', label: 'Topic', type: 'string', required: true }] },
      { type: 'client_information', label: 'Update Client Information', requires_verification: false, max_attachments: 0, fields: [{ name: 'statement_type', label: 'Statement Type', type: 'enum', required: true, options: ['balance_sheet', 'income_statement'] }] }
    ] 
  },
  '/requests': { 
    items: [
      { id: 'req-001', type: 'address_change', type_label: 'Change of address', status: 'submitted', client: { id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', full_name: 'Thabo Mokoena' }, payload: { address_line_1: '12 Example Road', suburb: 'Gardens', city: 'Cape Town', postal_code: '8001' }, client_note: 'Moved last week.', adviser_response: null, requires_verification: false, attachments: [], submitted_at: '2026-09-18T10:00:00Z', updated_at: '2026-09-18T10:00:00Z', completed_at: null },
      { id: 'req-002', type: 'bank_details_change', type_label: 'Change of bank details', status: 'completed', client: { id: '1c8f4b63-2d5f-5d4a-af55-3b5g7f2c9b02', full_name: 'Lerato Dlamini' }, payload: { account_holder: 'L Dlamini', bank_name: 'FNB', account_type: 'cheque', account_number: '******1234', branch_code: '250655' }, client_note: null, adviser_response: 'Updated on all active policies.', requires_verification: true, attachments: [], submitted_at: '2026-08-01T09:15:00Z', updated_at: '2026-08-05T14:30:00Z', completed_at: '2026-08-05T14:30:00Z' }
    ], 
    total: 2, limit: 25, offset: 0 
  },
  '/documents': { 
    items: [
      { id: 'doc-001', title: 'Comprehensive Motor Policy Wording 2026', category: 'policy_wording', insurer: { id: 'ins-007', name: 'Santam' }, page_count: 45, version_label: 'v1.2', is_synthetic: true, source_note: 'Demo document', status: 'indexed', indexed_at: '2026-01-10T12:00:00Z' },
      { id: 'doc-002', title: 'Claims Handling Procedure', category: 'internal_process', insurer: null, page_count: 12, version_label: 'v3.0', is_synthetic: true, source_note: 'Internal wiki', status: 'indexed', indexed_at: '2026-02-15T09:30:00Z' },
      { id: 'doc-003', title: 'FAIS Code of Conduct', category: 'regulation', insurer: null, page_count: 38, version_label: '2025', is_synthetic: true, source_note: 'FSCA website', status: 'indexed', indexed_at: '2025-11-20T14:15:00Z' }
    ], 
    total: 3, limit: 25, offset: 0 
  },
  '/assistant/query': { 
    conversation_id: 'conv-1234', message_id: 'msg-5678', answer: 'The demo policy wording asks the insured to notify the insurer within 30 days of the event [1]. The internal claims process also requires the adviser to log the claim the same day [2].', grounded: true, citations: [{ index: 1, document_id: 'doc-001', document_title: 'Comprehensive Motor Policy Wording 2026', category: 'policy_wording', is_synthetic: true, page: 12, quote: 'The insured must notify the insurer of any event likely to give rise to a claim within 30 days…' }, { index: 2, document_id: 'doc-002', document_title: 'Claims Handling Procedure', category: 'internal_process', is_synthetic: true, page: 3, quote: 'Log every new claim in the register on the day it is received…' }], model: { provider: 'groq', name: 'llama3-70b-8192' }, latency_ms: 1840 
  },
  '/email/status': { provider: 'mock', is_simulated: true, connected: true, account: 'adviser@demo.example' },
  '/email/threads': { 
    items: [
      { id: 'thr-001', subject: 'Claim SC-778201: assessment appointment', snippet: 'Please book the vehicle in for assessment at…', participants: [{ name: 'Demo Handler', email: 'handler@insurer.example', role: 'insurer' }, { name: 'Sarah van der Merwe', email: 'adviser@demo.example', role: 'other' }], message_count: 2, last_message_at: '2026-09-19T09:12:00Z', unread: true, importance: 'high', flags: [{ code: 'insurer_sender', label: 'From an insurer' }, { code: 'claim_reference_match', label: 'Mentions claim SC-778201' }], link: { client_id: '0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01', claim_id: 'a5f0e3f4-1000-4000-8000-000000000002', linked_by: 'auto' }, is_simulated: true },
      { id: 'thr-002', subject: 'Re: Fund fact sheets', snippet: 'Thanks Sarah, I will review these over the weekend.', participants: [{ name: 'Lerato Dlamini', email: 'client2@demo.example', role: 'client' }, { name: 'Sarah van der Merwe', email: 'adviser@demo.example', role: 'other' }], message_count: 4, last_message_at: '2026-09-18T16:45:00Z', unread: false, importance: 'normal', flags: [{ code: 'client_sender', label: 'From a client' }], link: { client_id: '1c8f4b63-2d5f-5d4a-af55-3b5g7f2c9b02', claim_id: null, linked_by: 'auto' }, is_simulated: true },
      { id: 'thr-003', subject: 'URGENT: Renewal notices for October', snippet: 'Please note the following policies are due for renewal...', participants: [{ name: 'Underwriting Dept', email: 'underwriting@sanlam.example', role: 'insurer' }, { name: 'Sarah van der Merwe', email: 'adviser@demo.example', role: 'other' }], message_count: 1, last_message_at: '2026-09-17T11:20:00Z', unread: true, importance: 'high', flags: [{ code: 'insurer_sender', label: 'From an insurer' }, { code: 'deadline_keyword', label: 'Urgent deadline' }], link: { client_id: null, claim_id: null, linked_by: null }, is_simulated: true }
    ], 
    total: 3, limit: 25, offset: 0 
  },
  '/meta': { 
    api_version: 'v1', currency: 'ZAR', 
    claim_statuses: [{ value: 'draft', order: 0, client_label: 'Not sent yet', advisor_label: 'Draft' }, { value: 'submitted', order: 1, client_label: 'Sent to Royal Square', advisor_label: 'Submitted' }, { value: 'registered', order: 2, client_label: 'Registered with your insurer', advisor_label: 'Registered (claim no. issued)' }, { value: 'assessment', order: 3, client_label: 'Vehicle assessment', advisor_label: 'Assessment' }, { value: 'quotes', order: 4, client_label: 'Repair quotes', advisor_label: 'Quotes with insurer' }, { value: 'authorised', order: 5, client_label: 'Repairs approved', advisor_label: 'Authorised' }, { value: 'in_repair', order: 6, client_label: 'Being repaired', advisor_label: 'In repair' }, { value: 'completed', order: 7, client_label: 'Repairs finished', advisor_label: 'Completed, awaiting client sign-off' }, { value: 'closed', order: 8, client_label: 'Closed', advisor_label: 'Closed' }], 
    hire_car_statuses: ['not_required', 'requested', 'arranged', 'delivered', 'return_arranged', 'returned'], 
    reminder_types: [{ type: 'licence_expiry', label: 'Driving licence expiring', default_audience: 'client', lead_days: 60 }, { type: 'valuation_certificate', label: 'Valuation certificate due', default_audience: 'both', lead_days: 30 }, { type: 'annual_review', label: 'Annual financial review', default_audience: 'advisor', lead_days: 30 }, { type: 'custom', label: 'Custom reminder', default_audience: 'both', lead_days: 0 }], 
    request_types: [{ type: 'bank_details_change', label: 'Change of bank details', requires_verification: true }, { type: 'address_change', label: 'Change of address', requires_verification: false }], 
    policy_categories: ['motor', 'life', 'health', 'funeral', 'personal_other', 'commercial', 'investment', 'retirement'], 
    attachment_rules: { max_bytes: 10485760, max_per_claim: 40, max_per_request: 5, content_types: { image: ['image/jpeg', 'image/png', 'image/webp'], document: ['application/pdf'], audio: ['audio/webm', 'audio/mp4', 'audio/mpeg', 'audio/ogg', 'audio/wav'] }, kinds: [{ kind: 'drivers_licence', accepts: ['image', 'document'] }, { kind: 'witness_voice_note', accepts: ['audio'] }] } 
  }
};
