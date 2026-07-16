INSERT INTO identity.users (id, email, display_name, role)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'buyer@example.test', 'Demo Buyer', 'BUYER'),
    ('00000000-0000-0000-0000-000000000002', 'organizer@example.test', 'Demo Organizer', 'ORGANIZER')
ON CONFLICT DO NOTHING;

INSERT INTO catalog.events (id, organizer_id, title, category, location, starts_at, status)
VALUES (
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    'TicketPlus Demo Concert',
    'MUSIC',
    'Demo Hall',
    now() + interval '30 days',
    'ON_SALE'
)
ON CONFLICT DO NOTHING;

