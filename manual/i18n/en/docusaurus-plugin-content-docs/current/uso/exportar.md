---
title: Export your data
sidebar_label: Export
---

There are two exports: **all your data**, to take it with you or keep it, and your **applications as CSV**, to work with them in a spreadsheet.

## Download all your data

In **Preferences**, in the **Your data** card, click **Download all my data**. While it is being prepared, the button says **Preparing the download…**; then `applications-tracker-export-<date>.zip` is downloaded.

The `.zip` holds everything you have in the application:

- `account.json`: your email, your preferences (language, time zone, notifications) and the sign-up date.
- One JSON file per kind of data: companies, applications, status history, interviews, reminders, documents, your profile (experience, education, projects, certifications, achievements, skills and languages), AI proposals and consents. Each file is named after its kind (`applications.json`, `interviews.json`…).
- `documents/`: all your PDFs, uploaded and generated.
- `README.txt`: what each file is, in Spanish and English.

The data comes with its codes and ids, as in the CSV: each interview says which application it belongs to with `application_id`, and dates are ISO 8601, in UTC. It is a format meant to be read by another program.

**It never includes your AI keys**, not even encrypted: only which provider and model you used.

You can download it **5 times an hour**. If the download is cut off, click the button again.

:::tip If you can no longer sign in
Ask whoever runs the installation for your data: they can generate the same `.zip` without your password.
:::

## Export your applications to CSV

In **Applications**, click **Export CSV**. A file is downloaded with **all** your applications, archived ones included, whatever filters you have applied.

Each row is an application, with these columns:

`position_title`, `company`, `status`, `applied_at`, `work_mode`, `source`, `origin`, `location`, `job_url`, `salary_min`, `salary_max`, `salary_currency`, `notes`, `job_description`, `cv_document`, `cover_letter_document`, `archived_at`, `created_at`, `updated_at`

`cv_document` and `cover_letter_document` hold the **name** of the CV and cover letter sent; the PDFs are not in the CSV.

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

The CSV does not include the status history, interviews or reminders: for that, [download all your data](#download-all-your-data).
