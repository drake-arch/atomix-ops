# EOD / Atomix Ops Visual Redesign — Hacker Mind Model

## 1. Short Read

The screenshot shows the target direction: **Atomix Ops should feel like the Atomix admin app**, not a separate dark landing page.

Main move:

- Convert Atomix Ops and ShiftFlow EOD into a light operational control surface.
- Use a persistent left navigation rail.
- Use a simple top bar with page title, notification/user area, and clear actions.
- Use white cards, light gray background, compact filters, bordered stat cards, green primary buttons, and table/list surfaces.

The homepage card order was updated first. EOD Reporting now sits at the top, then the requested operating cluster.

## 2. Known Facts From Screenshot

Observed UI traits:

- Left sidebar with Atomix logo and vertical navigation.
- Current page is highlighted with a green pill/button.
- Main background is light gray/off-white.
- Top bar is white, lightly shadowed, with page title on the left and user controls on the right.
- KPI cards sit near the top, centered/clustered, with thin borders and small icons.
- Primary action is Atomix green with white text.
- Secondary action is a small bordered icon button.
- Filters are compact white controls with thin gray border.
- Main data area is a large white table card.
- Typography is compact, practical, and not decorative.
- Spacing is controlled: dense enough for ops, but still calm.
- Statuses use soft pills: green completed, blue in-progress, orange awaiting, cyan priority.
- Progress bars use green fill on pale track.

## 3. Hacker’s Mind Map

### Visible UI System

- **Shell:** left nav + topbar + content area.
- **Data density:** table-first, not marketing-card-first.
- **Hierarchy:** page title → KPI cards → action/filter row → work table.
- **Interaction language:** create, refresh, filter, expand row, paginate.
- **Brand language:** green = primary action / active state / success.

### Likely Backend / Data Model Behind Screenshot

Inferred entities:

- `users`
- `roles`
- `projects`
- `clients`
- `statuses`
- `priorities`
- `progress_events`
- `due_dates`
- `audit_events`

For EOD, equivalent entities should be:

- `reporting_date`
- `person`
- `role`
- `department/site`
- `submission_status`
- `answers`
- `missing_items`
- `manager_questions`
- `recap_email_status`
- `labor_inputs`
- `exceptions`
- `follow_ups`

### EOD Data Flow

Current ShiftFlow likely flow:

1. Person chooses name.
2. Person edits/questions or answers EOD.
3. Answers persist to Google Apps Script / Sheet when configured.
4. Manager view pulls status by date.
5. Manager reviews submitted/missing people.
6. Recap email preview/send happens from manager layer.

Redesigned Atomix-app flow should be:

1. Top page: `EOD Reporting` dashboard.
2. KPI cards: submitted, missing, total, recap readiness.
3. Left nav: Submit EOD / Manager Review / Recap Emails / Questions / Labor Inputs / Settings.
4. Main table: people rows with status, role, site, last answer timestamp, blocker/follow-up flag.
5. Right drawer/modal: selected person report detail.
6. Primary action: `Submit My EOD` or `Send Recap` depending on role.

### Failure Points

- People miss EOD because the page does not show who is missing clearly enough.
- Manager view can become buried behind picker screens.
- Questions can sprawl if every manager adds ad-hoc questions without review.
- Recap output can be sent before missing people/follow-ups are obvious.
- Current dark homepage visually conflicts with the Atomix admin app screenshot.

### Attack / Data Risks

- If Google Apps Script endpoint is public, submissions need basic passcode/token guardrails.
- Manager-only actions like recap send and question changes should not be exposed to everyone.
- EOD answers may include client-sensitive details; avoid dumping full answers in open dashboards unless role-gated.
- Tables should escape answer text to avoid HTML/script injection if stored answers are rendered back into the page.

## 4. Atomix Redesign Principles

### Homepage

- Replace the dark marketing hero with an Atomix admin shell.
- Left nav categories:
  - EOD Reporting
  - Role Architect
  - Labor Clock
  - Scheduling
  - Labor Analytics
  - Corrective Action
  - Labor Projection
  - Inventory / Quality / Audit / Tools
- Main content:
  - top stat cards for daily ops state
  - module grid/table underneath
  - green active selection

### EOD

- Treat EOD as a daily closeout control room, not a chat app.
- First screen should answer: `Who has submitted, who is missing, what needs action?`
- Employee submission should still be simple: pick name → answer → submit.
- Manager review should feel like the screenshot table: rows, statuses, filters, progress, due/date.
- Recap email should be a controlled final step with readiness checks.

### Visual Tokens From Screenshot

- Background: `#f5f5f5` / `#f7f7f7`
- Panel: `#ffffff`
- Text: near-black / navy ink
- Muted text: cool gray
- Primary green: Atomix green family
- Border: light gray `#e5e7eb`
- Radius: 7–10px for controls/cards
- Shadow: very soft, mostly for topbar/table card
- Buttons: green primary, bordered white secondary

## 5. Recommended EOD Page Structure

### Left Rail

- Atomix logo
- Dashboard
- EOD Reporting — active
- Labor Clock
- Labor Analytics
- Role Architect
- Scheduling
- Corrective Action
- Admin / Settings

### Top Bar

- Title: `EOD Reporting`
- Date selector
- Bell/notification icon
- User badge: Drake Meyer / Admin

### KPI Cards

- Submitted today
- Missing
- Total expected
- Recap readiness

### Action Row

- Search people
- Site filter
- Department filter
- Status filter
- `Submit My EOD` primary button
- `Refresh` secondary button

### Main Table

Columns:

- Expand
- Person
- Role
- Site / Team
- EOD Status
- Last Update
- Blocker?
- Manager Follow-up
- Recap Included

### Detail Drawer

When clicking a row:

- submitted answers
- labor numbers
- blockers/fires
- follow-up owed
- manager notes
- add ad-hoc question

## 6. Implementation Acceptance Criteria

- Homepage order matches Drake’s requested operating order.
- Homepage and EOD use screenshot-style Atomix app shell.
- EOD first view makes submitted/missing status obvious within 5 seconds.
- Employee submit flow remains simple and does not add extra clicks.
- Manager review, email preview, and ad-hoc question tools remain available.
- No data flow or Apps Script submission behavior is broken.
- Browser QA proves all primary buttons still navigate/work.
- Impeccable/design check is run and warnings are documented.

## 7. Next Build Path

1. Convert homepage from dark hero grid to Atomix app shell.
2. Convert ShiftFlow EOD from topbar-only layout to full left-nav admin shell.
3. Add EOD dashboard table as the default manager-style landing view.
4. Keep employee submission as a clear primary action.
5. QA with screenshot proof and one pass through EOD flow.
