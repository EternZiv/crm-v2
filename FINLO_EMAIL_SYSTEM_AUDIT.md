# FINLO EMAIL SYSTEM AUDIT

Date: 2026-11-11
Scope: Read-only audit of mail sending, templates, attachments, background tasks, and related synchronization behavior.

## Executive summary

The mail subsystem is substantial and generally structured around custom models, rendering, and backend selection. There is explicit outbound email logic, SMTP and Outlook support, recipient validation, tracking pixel insertion, and Celery task automation. However, the mail system cannot be described as completely validated end-to-end without covering incoming mailbox processing, message synchronization, and object linking in live workflows.

## Outbound delivery: implemented and partially validated

Evidence: [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py), [finlo/contrib/mail/backends.py](./finlo/contrib/mail/backends.py), [finlo/contrib/mail/models.py](./finlo/contrib/mail/models.py)

Key behaviors:
- `FinloMailManager.send_mail()` renders subject/body, persists the rendered snapshot immediately, and validates recipients.
- `_find_undeliverable()` checks recipient domains using DNS MX/A resolution before sending.
- `FinloMailManager.send_mail()` obtains a mail backend via `get_connection("finlo.contrib.mail.backends.FinloDefaultMailBackend")`.
- `FinloDefaultMailBackend.send_messages()` switches behaviors based on the active configuration type: SMTP (`mail`) or Outlook Graph (`outlook`).
- Inline attachments and regular file attachments are added to the outgoing message.
- A tracking pixel is appended so open events can be detected.

Confirmed status:
- The outbound mail pipeline exists and is structured for real sending.
- It contains validation logic to avoid obvious non-deliverable domains.

## Background tasking and asynchronous processing

Evidence: [finlo/contrib/mail/tasks.py](./finlo/contrib/mail/tasks.py)

Key behaviors:
- `send_scheduled_mail_task()` handles scheduled sends and checks if the message is still valid to send.
- `refresh_outlook_auth_token()` refreshes Outlook OAuth tokens using a scheduled task.
- `process_scheduled_mails()` queues scheduled messages for asynchronous delivery.

Confirmed status:
- Email sending is explicitly designed to be asynchronous and scheduled.
- Token refresh and queue scheduling are represented as operational infrastructure.

## Incoming mail and message synchronization

Evidence: [finlo/contrib/mail/tasks.py](./finlo/contrib/mail/tasks.py), [finlo/contrib/mail/views/incoming_mail.py](./finlo/contrib/mail/views/incoming_mail.py), [finlo/contrib/mail/views/mail_history.py](./finlo/contrib/mail/views/mail_history.py)

Observations:
- The tasks file imports `imaplib` and references `fetch_hooks`, `IncomingMail`, and `DeletedIncomingMessageId`, which confirms the platform has a concept of inbound mailbox processing.
- There are dedicated incoming-mail and history views, which indicates that incoming mail is intended to be imported into the system.

Audit conclusion:
- The code supports inbound processing, but this audit did not validate a full end-to-end live mailbox ingestion flow.
- There is enough infrastructure to support message synchronization, but the evidence is incomplete for a full production trust assessment.

## Template and attachment handling

Evidence: [finlo/contrib/mail/models.py](./finlo/contrib/mail/models.py), [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py)

Key behaviors:
- `FinloMail` stores both `rendered_subject` and `rendered_body`, preserving the exact sent snapshot.
- `mail.attachments` supports inline and regular attachments.
- `FinloMailConfiguration` handles SMTP and Outlook-specific credentials, along with token storage.

Assessment:
- Template rendering and attachment handling are implemented as expected for a custom CRM mail system.
- The saved rendered snapshot is a good design choice for auditability.

## Severity findings

| # | Severity | Finding | Evidence | Status |
|---|---|---|---|---|
| 1 | 🟡 MEDIUM | The mail system is functional but end-to-end incoming message synchronization was not fully validated in this audit. | [finlo/contrib/mail/tasks.py](./finlo/contrib/mail/tasks.py), [finlo/contrib/mail/views/incoming_mail.py](./finlo/contrib/mail/views/incoming_mail.py) | Partial implementation |
| 2 | 🟡 MEDIUM | Outlook sender configuration depends on thread-local request context and fallback configuration selection; this can cause cross-company or wrong-sender behavior if misconfigured. | [finlo/contrib/mail/backends.py](./finlo/contrib/mail/backends.py) | Potential risk |
| 3 | 🟡 MEDIUM | The system allows a best-effort DNS validation fallback and then tries to send anyway if DNS lookup fails unexpectedly. | [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py) | Potential risk |
| 4 | ⚪ LOW | Tracking pixel and HTML attachment injection create a normal email-tracking surface. This is common but should be reviewed for privacy policy and consent expectations. | [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py) | Operational consideration |

## Conclusion

The custom email system is substantial and operationally rich. Outbound sending, scheduling, template rendering, Outlook OAuth handling, and attachment support are all present. The strongest caveat is that the full end-to-end mail synchronization path was not fully proven in this audit, and some configuration-driven behavior may create sender-selection or domain-validation edge cases in production if mail server configuration is not tightly managed.
