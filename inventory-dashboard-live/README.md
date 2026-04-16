# Atomix Inventory Dashboard (Live)

Real-time MKE warehouse inventory dashboard pulling live data from Metabase via Apps Script proxy.

## Sections
- Inventory Score — cycle count accuracy (30d)
- IMS Status — total SKUs, in-stock, zero-stock, units on hand
- Capacity Utilization — location fill rate by type (pick, backstock, pallet, shelf)
- Inventory Changes Today — adjustments, increases, decreases, net units
- Open Replenishments — open tasks by status and type
- Empty Fast-Pick Locations — pick locs with onHand = 0

## How to run

Requires Node.js installed.

```
node server.js
```

Then open: http://localhost:8080

## Config (server.js / index.html)
- `PROXY` — Google Apps Script web app URL (contains Metabase API key)
- `DB_ID` — Metabase database ID (2 = Atomix DB)
- `MKE` — MKE warehouse UUID
