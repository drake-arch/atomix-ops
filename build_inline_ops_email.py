#!/usr/bin/env python3
"""Build an inline Atomix ops email with slide-like cards in the email body.

No attachment parts. The slides are HTML sections/cards that render directly in the email.
"""
from __future__ import annotations

import argparse, json, re, html, datetime as dt, subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/home/fabric041/work/atomix-ops')


def esc(x): return html.escape(str(x or ''))

def money(x): return f"${float(x or 0):,.2f}"

def one_dec(x): return f"{float(x or 0):,.1f}"

def load_pulse():
    p = Path('/tmp/atomix_pulse_now.json')
    if not p.exists():
        subprocess.run(['python3', 'atomix_ops_pulse.py', '--json'], cwd=ROOT, check=True, stdout=p.open('w'))
    return json.loads(p.read_text())

def load_latest_deck():
    candidates = sorted((ROOT/'standup_archive').glob('*/CLICK_TO_OPEN_Atomix_Standup_*CORRECTED_SMALL.html'), reverse=True)
    candidates += sorted((ROOT/'standup_archive').glob('*/CLICK_TO_OPEN_Atomix_Standup_*LOCAL_ONLY.html'), reverse=True)
    if not candidates:
        return None, None
    path = candidates[0]
    text = path.read_text(errors='ignore')
    m = re.search(r"<script id=['\"]deck-data['\"] type=['\"]application/json['\"]>(.*?)</script>", text, re.S)
    if not m:
        return path, None
    return path, json.loads(m.group(1))

def summarize_deck(data):
    if not data:
        return {'date':'unknown','submitted':0,'people':0,'fires':[], 'wins':[]}
    submitted=people=0; fires=[]; wins=[]
    for s in data.get('slides',[]):
        if s.get('type')!='person': continue
        people += 1
        submitted += 1 if s.get('submitted') else 0
        for a in s.get('answers',[]):
            rec=(s.get('title'), a.get('q'), a.get('a'))
            if a.get('kind')=='fire': fires.append(rec)
            elif len(wins)<5: wins.append(rec)
    return {'date':data.get('date','unknown'), 'submitted':submitted, 'people':people, 'fires':fires, 'wins':wins}

def build_html(kind='morning'):
    now=dt.datetime.now(ZoneInfo('America/New_York'))
    pulse=load_pulse(); deck_path, deck=load_latest_deck(); eod=summarize_deck(deck)
    title = 'Good Morning — Floor Read' if kind=='morning' else 'Good Evening — Closeout Read'
    subject = f"{'Good Morning' if kind=='morning' else 'Good Evening'} — Inline Floor Read — {now.date().isoformat()}"
    orders=pulse.get('orders_total') or 0
    cpo = pulse.get('live_cpo') if orders else None
    depts = sorted((pulse.get('dept_hours') or {}).items(), key=lambda x:x[1], reverse=True)[:5]
    facilities = pulse.get('by_facility') or {}
    mke=facilities.get('MKE',{}); slc=facilities.get('SLC',{}); bal=facilities.get('BAL',{})
    fires=eod['fires']
    top_fire_1 = fires[0] if len(fires)>0 else ('', '', 'No major blocker pulled from latest deck.')
    top_fire_2 = fires[1] if len(fires)>1 else ('', '', '')
    top_fire_3 = fires[2] if len(fires)>2 else ('', '', '')
    cpo_text = f"${cpo:,.2f}" if cpo is not None else 'N/A'
    html_body=f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f7f4;color:#141414;font-family:Arial,Helvetica,sans-serif;">
  <div style="max-width:820px;margin:0 auto;padding:24px;">
    <div style="background:#002f35;border-radius:24px;padding:28px;color:#ffffff;margin-bottom:16px;">
      <div style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#a3f5c4;font-weight:800;">Atomix operating read</div>
      <h1 style="margin:8px 0 8px;font-size:34px;line-height:1.05;letter-spacing:-.5px;">{esc(title)}</h1>
      <p style="margin:0;color:#ffffff;font-size:15px;line-height:1.45;">Hey Drake and team — cleaner inline version, no deck attachment. Slides are built directly into the email.</p>
    </div>

    <div style="background:#ffffff;border:1px solid #dde5e0;border-radius:22px;padding:22px;margin-bottom:16px;">
      <div style="font-size:11px;letter-spacing:1.8px;text-transform:uppercase;color:#007a63;font-weight:900;margin-bottom:10px;">Slide 1 / live labor pulse</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>
        <td style="width:25%;padding:10px;background:#f4f7f4;border-radius:14px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#002f35;">{pulse.get('active_total',0)}</div><div style="font-size:12px;color:#66736e;">active bodies</div></td>
        <td style="width:25%;padding:10px;background:#f4f7f4;border-radius:14px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#002f35;">{one_dec(pulse.get('ops_hours'))}</div><div style="font-size:12px;color:#66736e;">ops hours</div></td>
        <td style="width:25%;padding:10px;background:#f4f7f4;border-radius:14px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#002f35;">{orders:,}</div><div style="font-size:12px;color:#66736e;">orders synced</div></td>
        <td style="width:25%;padding:10px;background:#e7fbef;border-radius:14px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#007a63;">{cpo_text}</div><div style="font-size:12px;color:#66736e;">live CPO</div></td>
      </tr></table>
      <p style="margin:14px 0 0;font-size:13px;color:#66736e;line-height:1.45;">Source: LaborClock pulse generated {esc(pulse.get('generated_at'))}. Same-day CPO is shown only when order sync has non-zero same-day orders.</p>
    </div>

    <div style="background:#ffffff;border:1px solid #dde5e0;border-radius:22px;padding:22px;margin-bottom:16px;">
      <div style="font-size:11px;letter-spacing:1.8px;text-transform:uppercase;color:#007a63;font-weight:900;margin-bottom:10px;">Slide 2 / facility read</div>
      <ul style="margin:0;padding-left:18px;line-height:1.55;font-size:15px;">
        <li><strong>MKE:</strong> {mke.get('active',0)} active, {one_dec(mke.get('ops_hours'))} ops hours, {money(mke.get('ops_cost'))} ops labor.</li>
        <li><strong>SLC:</strong> {slc.get('active',0)} active, {one_dec(slc.get('ops_hours'))} ops hours, {money(slc.get('ops_cost'))} ops labor.</li>
        <li><strong>BAL:</strong> {bal.get('active',0)} active, {one_dec(bal.get('ops_hours'))} ops hours, {money(bal.get('ops_cost'))} ops labor.</li>
      </ul>
    </div>

    <div style="background:#ffffff;border:1px solid #dde5e0;border-radius:22px;padding:22px;margin-bottom:16px;">
      <div style="font-size:11px;letter-spacing:1.8px;text-transform:uppercase;color:#007a63;font-weight:900;margin-bottom:10px;">Slide 3 / labor placement</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
        {''.join(f'<tr><td style="padding:8px 0;border-bottom:1px solid #edf2ef;font-weight:700;color:#002f35;">{esc(k)}</td><td style="padding:8px 0;border-bottom:1px solid #edf2ef;text-align:right;">{one_dec(v)}h</td></tr>' for k,v in depts)}
      </table>
      <p style="margin:12px 0 0;font-size:13px;color:#66736e;">Excluded/non-CPO buckets: {one_dec(pulse.get('excluded_hours'))}h / {money(pulse.get('excluded_cost'))}.</p>
    </div>

    <div style="background:#ffffff;border:1px solid #dde5e0;border-radius:22px;padding:22px;margin-bottom:16px;">
      <div style="font-size:11px;letter-spacing:1.8px;text-transform:uppercase;color:#007a63;font-weight:900;margin-bottom:10px;">Slide 4 / prior EOD signal</div>
      <p style="margin:0 0 12px;font-size:16px;line-height:1.45;"><strong>{eod['submitted']}/{eod['people']} submitted</strong> from source EOD date {esc(eod['date'])}. Pulled {len(fires)} fire/blocker items from the latest standup deck.</p>
      <ul style="margin:0;padding-left:18px;line-height:1.55;font-size:15px;">
        <li><strong>{esc(top_fire_1[0])}:</strong> {esc(top_fire_1[2])}</li>
        {f'<li><strong>{esc(top_fire_2[0])}:</strong> {esc(top_fire_2[2])}</li>' if top_fire_2[2] else ''}
        {f'<li><strong>{esc(top_fire_3[0])}:</strong> {esc(top_fire_3[2])}</li>' if top_fire_3[2] else ''}
      </ul>
    </div>

    <div style="background:#071a1d;border-radius:22px;padding:22px;color:#ffffff;margin-bottom:16px;">
      <div style="font-size:11px;letter-spacing:1.8px;text-transform:uppercase;color:#a3f5c4;font-weight:900;margin-bottom:10px;">Slide 5 / Cleo read</div>
      <ol style="margin:0;padding-left:20px;line-height:1.6;font-size:15px;">
        <li>Keep labor tied to synced order output; watch CPO as the day moves.</li>
        <li>Back-room cleanup / warehouse moves need named owners and closeout notes.</li>
        <li>Inventory risk is still Lights offboarding, FEFO dashboard friction, and open discrepancies.</li>
      </ol>
    </div>

    <div style="padding:10px 2px;color:#66736e;font-size:13px;line-height:1.45;">
      From Cleo<br>Atomix operating nervous system<br>ai.ops@atomixlogistics.com
    </div>
  </div>
</body></html>"""
    text_body=f"""Hey Drake and team,\n\nInline floor read — no attachment.\n\nLive pulse: {pulse.get('active_total',0)} active, {one_dec(pulse.get('ops_hours'))} ops hours, {orders:,} orders synced, CPO {cpo_text}.\nPrior EOD: {eod['submitted']}/{eod['people']} submitted, {len(fires)} fire/blocker items.\nMain read: keep labor tied to output; back-room/warehouse moves need owner closeout; inventory risk remains Lights/FEFO/discrepancies.\n\nFrom Cleo\nAtomix operating nervous system\nai.ops@atomixlogistics.com\n"""
    return subject, text_body, html_body

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--kind', choices=['morning','evening'], default='morning')
    ap.add_argument('--outdir', default=str(ROOT/'good_morning_reports'/'inline_current'))
    args=ap.parse_args()
    subject,text,html_body=build_html(args.kind)
    out=Path(args.outdir); out.mkdir(parents=True, exist_ok=True)
    (out/'inline_email.html').write_text(html_body)
    (out/'inline_email.txt').write_text(text)
    mml=f"""From: Cleo <ai.ops@atomixlogistics.com>\nTo: Drake <Drake@atomixlogistics.com>\nSubject: {subject}\n\n<#multipart type=alternative>\n<#part type=text/plain>\n{text}<#part type=text/html>\n{html_body}\n<#/multipart>\n"""
    (out/'send_inline_email.mml').write_text(mml)
    print(json.dumps({'subject':subject,'mml':str(out/'send_inline_email.mml'),'html':str(out/'inline_email.html'),'text':str(out/'inline_email.txt')}, indent=2))

if __name__=='__main__': main()
