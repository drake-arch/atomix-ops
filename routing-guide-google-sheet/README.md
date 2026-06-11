# Atomix Routing Guide Google Sheet Setup

This folder captures all 67 workshop questions and the Google Apps Script receiver.

## Files
- `Question_Bank.csv` — all workshop questions.
- `Raw_Answers_template.csv` — answer table headers.
- `Code.gs` — paste into Google Sheets → Extensions → Apps Script.

## Setup
1. Create a new Google Sheet named `Atomix Routing Guide Workshop Answers`.
2. Import `Question_Bank.csv` into a tab called `Question Bank`, or just run `setupWorkbook()` in Apps Script and it will create it.
3. Open Extensions → Apps Script.
4. Paste `Code.gs`.
5. Change `SHEET_PASSCODE`.
6. Run `setupWorkbook()` once and approve permissions.
7. Deploy → New deployment → Web app.
   - Execute as: Me
   - Who has access: Anyone with the link
8. Copy the Web App URL and send it to Cleo.
9. Cleo will wire the GitHub page to submit directly to that Sheet.

## Data flow
GitHub workshop page → Apps Script Web App → Google Sheet tabs:
- Raw Answers
- Compiled Summary
- Conflicts
- Consensus Ready
- Unanswered
