---
title: Export your applications
sidebar_label: Export to CSV
---

In **Applications**, click **Export CSV**. A file is downloaded with **all** your applications, archived ones included, whatever filters you have applied.

Each row is an application, with these columns:

`position_title`, `company`, `status`, `applied_at`, `work_mode`, `source`, `origin`, `location`, `job_url`, `salary_min`, `salary_max`, `salary_currency`, `notes`, `archived_at`, `created_at`, `updated_at`

Statuses, work modes and sources are written as **codes**, not as the labels on screen: `applied` rather than "Applied", `remote` rather than "Remote". That way the file is the same whatever the interface language, and any tool can process it.

| Code | Status |
|---|---|
| `saved` | Saved |
| `applied` | Applied |
| `screening` | Screening |
| `interviewing` | Interviewing |
| `offer` | Offer |
| `accepted` | Accepted |
| `rejected` | Rejected |
| `withdrawn` | Withdrawn |

The CSV does not include the status history, interviews or reminders.
