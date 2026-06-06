-- Outbound SMS log — every auto-sent lead follow-up text
-- Written by lead_followup.py outbound flow so the record survives beyond the local state file

CREATE TABLE IF NOT EXISTS outbound_sms_log (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id   text NOT NULL,
    contact_name text,
    pipeline     text,
    stage        text,
    message_body text NOT NULL,
    priority     text,          -- high | medium | low
    sent_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS outbound_sms_log_contact ON outbound_sms_log (contact_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS outbound_sms_log_sent_at ON outbound_sms_log (sent_at DESC);
