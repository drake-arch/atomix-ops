import argparse, csv, io, json, urllib.request, html, pathlib, collections, datetime, re, base64, mimetypes
from zoneinfo import ZoneInfo

SID='130wcBqy6QUzPM9KID9fXAHUP47a8NGVPSxVOaPt3qo0'
GIDS={'Reports':'146026037','Answers':'489860443','People':'1868587579'}
ROOT=pathlib.Path('/home/fabric041/work/atomix-ops')
STANDARD_QUESTIONS=[
    'What was the first thing you attacked today?',
    'What fires did you put out today?',
    'What fires are still active?',
    'What do you need to put these fires out?',
    'What projects are still pending?',
    'What is your top priority for the day?',
    'What is your top priority to complete by the end of the week?',
    'What was the last thing you attacked today?',
]
MEETING_PEOPLE=[
    ('kody','Kody','AM Outbound'),
    ('luis','Luis','Inventory'),
    ('emyly','Emyly','Inbound'),
    ('hugh','Hugh','PM Lead'),
    ('adam','Adam','Special Projects'),
    ('norman','Norman','SLC'),
    ('burke','Burke','BAL'),
]
NOISE={'','n/a','na','no','none','.', 'nothing'}
def prior_business_day(today=None):
    """Return the operating day to review.

    Monday morning reviews Friday EOD. Weekends do not generate a new EOD source
    date. Tuesday-Friday review the previous calendar day.
    """
    today = today or datetime.datetime.now(ZoneInfo('America/Chicago')).date()
    if today.weekday() == 0:  # Monday -> prior Friday
        return today - datetime.timedelta(days=3)
    if today.weekday() == 6:  # Sunday -> prior Friday if manually run
        return today - datetime.timedelta(days=2)
    if today.weekday() == 5:  # Saturday -> prior Friday if manually run
        return today - datetime.timedelta(days=1)
    return today - datetime.timedelta(days=1)

parser=argparse.ArgumentParser(description='Build Nucleus-style Atomix standup meeting site.')
parser.add_argument('--date', help='Report date YYYY-MM-DD. Defaults to prior Atomix business day in America/Chicago; Monday reviews Friday.')
args=parser.parse_args()
DATE=args.date or prior_business_day().isoformat()
OUT=ROOT/f'cleo-standup-meeting-{DATE}.html'
LEGACY=ROOT/f'cleo-standup-deck-{DATE}.html'

def fetch(gid):
    url=f'https://docs.google.com/spreadsheets/d/{SID}/export?format=csv&gid={gid}'
    data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8-sig','replace')
    return list(csv.DictReader(io.StringIO(data)))

def clean(s): return re.sub(r'\s+', ' ', str(s or '')).strip()
def is_noise(s): return clean(s).lower() in NOISE

def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i+size]

def complexity_label(answer_count):
    if answer_count >= 7: return 'full story'
    if answer_count >= 4: return 'expanded story'
    if answer_count >= 1: return 'short story'
    return 'no story yet'

def classify(q,a):
    t=(q+' '+a).lower()
    if any(x in t for x in ['fire','risk','issue','blocker','missing','not able','did not','could not','violation','broken process','low','running out','needs','left from today','batches left','lock-location','lock location','fefo','fifo','t force']): return 'fire'
    if any(x in t for x in ['good','ready','completed','all orders out','caught up','no call']): return 'good'
    return 'note'

def data_uri(path):
    p=ROOT/path
    if not p.exists(): return ''
    mime=mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
    return f'data:{mime};base64,'+base64.b64encode(p.read_bytes()).decode('ascii')

def svg_uri(svg):
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode('utf-8')).decode('ascii')

def svg_lines(s, n=50, max_lines=4):
    words=clean(s).split()
    lines=[]; line=''
    for w in words:
        if len(line)+len(w)+1>n:
            if line: lines.append(line)
            line=w
        else:
            line=(line+' '+w).strip()
    if line: lines.append(line)
    return lines[:max_lines] or ['No detail captured.']

def build_answer_comic(display, role, raw):
    panels=(raw[:4] if raw else [{'q':'No EOD submitted','a':'Couch, TV, and Cheez-Its.','kind':'fire'}])
    while len(panels)<4:
        panels.append({'q':'Meeting prompt','a':'Ask live for owner, blocker, and next action.','kind':'note'})
    colors={'good':'#ddf8e7','fire':'#ffe5dc','note':'#eaf4ff'}
    labels={'good':'WIN','fire':'FIRE','note':'NEXT'}
    blocks=[]
    positions=[(55,170),(520,170),(55,560),(520,560)]
    for i,p in enumerate(panels[:4]):
        x,y=positions[i]
        fill=colors.get(p.get('kind'),'#f6f7f4')
        badge=labels.get(p.get('kind'),'NOTE')
        q_lines=svg_lines(p.get('q','Question'),30,2)
        q_svg=''.join(f"<text x='{x+110}' y='{y+56+j*24}' class='question'>{html.escape(line)}</text>" for j,line in enumerate(q_lines))
        a_svg=''.join(f"<text x='{x+34}' y='{y+226+j*27}' class='bubble'>{html.escape(line)}</text>" for j,line in enumerate(svg_lines(p.get('a',''),38,4)))
        # simple illustrated warehouse scene, deterministic and readable; no emoji placeholders
        scene=f"""
          <rect x='{x+28}' y='{y+92}' width='120' height='68' rx='10' fill='#f8faf7' stroke='#102b2f' stroke-width='3'/>
          <rect x='{x+42}' y='{y+112}' width='32' height='35' fill='#caa46a' stroke='#102b2f' stroke-width='2'/>
          <rect x='{x+80}' y='{y+104}' width='32' height='43' fill='#d8b978' stroke='#102b2f' stroke-width='2'/>
          <circle cx='{x+132}' cy='{y+132}' r='16' fill='#a3f5c4' stroke='#102b2f' stroke-width='3'/>
          <line x1='{x+132}' y1='{y+148}' x2='{x+132}' y2='{y+166}' stroke='#102b2f' stroke-width='4'/>
          <line x1='{x+122}' y1='{y+157}' x2='{x+142}' y2='{y+157}' stroke='#102b2f' stroke-width='4'/>
        """
        blocks.append(f"""
        <g>
          <rect x='{x}' y='{y}' width='425' height='350' rx='26' fill='{fill}' stroke='#102b2f' stroke-width='5'/>
          <rect x='{x+22}' y='{y+22}' width='72' height='44' rx='16' fill='#002f35'/>
          <text x='{x+58}' y='{y+51}' text-anchor='middle' class='badge'>{badge}</text>
          <text x='{x+110}' y='{y+35}' class='panelTitle'>Panel {i+1}</text>
          {q_svg}
          {scene}
          <rect x='{x+24}' y='{y+198}' width='377' height='124' rx='18' fill='#fff' stroke='#102b2f' stroke-width='3'/>
          {a_svg}
        </g>""")
    svg=f"""<svg xmlns='http://www.w3.org/2000/svg' width='1000' height='1040' viewBox='0 0 1000 1040'>
    <style>.title{{font:900 50px Arial,sans-serif;fill:#07353a}}.sub{{font:700 22px Arial,sans-serif;fill:#0b5f56}}.panelTitle{{font:900 24px Arial,sans-serif;fill:#07353a}}.question{{font:700 18px Arial,sans-serif;fill:#41504b}}.bubble{{font:700 19px Arial,sans-serif;fill:#141414}}.badge{{font:900 18px Arial,sans-serif;fill:#a3f5c4}}</style>
    <rect width='1000' height='1040' fill='#f4f7f4'/><rect x='20' y='20' width='960' height='1000' rx='34' fill='#ffffff' stroke='#002f35' stroke-width='8'/>
    <text x='48' y='80' class='title'>{html.escape(display)} EOD Comic</text>
    <text x='52' y='118' class='sub'>Atomix standup recap • {html.escape(role)} • generated from ShiftFlow answers</text>
    {''.join(blocks)}
    <text x='52' y='985' class='sub'>Rule: real details create the comic. No answers = couch + TV + Cheez-Its.</text>
    </svg>"""
    return svg_uri(svg)

MISSING_EOD_COMIC=data_uri(pathlib.Path('comic_art')/'shared'/'no_submission_cheezits_comic.webp') or build_answer_comic('No EOD','Missing submission',[])

reports=fetch(GIDS['Reports']); answers=fetch(GIDS['Answers'])
day_reports=[r for r in reports if r.get('date')==DATE]
day_answers=[a for a in answers if a.get('date')==DATE]
latest={}
for r in day_reports:
    pid=(r.get('person_id') or '').lower()
    if pid not in latest or r.get('submitted_at','')>latest[pid].get('submitted_at',''):
        latest[pid]=r
by_person=collections.defaultdict(list)
for a in day_answers:
    by_person[(a.get('person_id') or '').lower()].append(a)

def load_labor(date):
    p=ROOT/'labor_intelligence'/date/f'labor_intelligence_{date}.json'
    if not p.exists():
        return {'ok':False,'source':str(p),'reason':'Labor intelligence JSON not found.'}
    data=json.loads(p.read_text())
    snap=dict(data.get('snapshot',{}))
    dept=data.get('deptTotals',{})
    total_hours=round(sum(float(v or 0) for v in dept.values()),2)
    assumed_rate=20.0
    if not snap.get('totalHoursToday') and total_hours:
        snap['totalHoursToday']=total_hours
    if not snap.get('estLaborCost') and total_hours:
        snap['estLaborCost']=round(total_hours*assumed_rate,2)
        snap['estLaborCostAssumedRate']=assumed_rate
        snap['estLaborCostNote']='Estimated management view only; source did not include true loaded labor rate.'
    top_depts=sorted(dept.items(), key=lambda x:x[1], reverse=True)[:8]
    html_path=ROOT/'labor_intelligence'/date/f'labor_intelligence_{date}.html'
    md_path=ROOT/'labor_intelligence'/date/f'labor_intelligence_{date}.md'
    return {'ok':True,'source':str(p),'html':str(html_path) if html_path.exists() else '', 'md':str(md_path) if md_path.exists() else '', 'snapshot':snap,'topDepts':top_depts,'packRate':data.get('packRateSnapshot',{}).get('summary',{}),'true_cost_present':False}

def load_excused(date):
    qfile=ROOT/'standup_archive'/date/f'eod_questions_{date}.md'
    excused={}
    if not qfile.exists():
        return excused
    text=qfile.read_text()
    sections=re.split(r'(?m)^##\s+', text)
    name_to_pid={display.lower():pid for pid,display,_role in MEETING_PEOPLE}
    # Accept spoken/common spelling too.
    name_to_pid.update({'emily':'emyly','louise':'luis','cody':'kody'})
    for sec in sections:
        if not sec.strip():
            continue
        first,*rest=sec.splitlines()
        pid=name_to_pid.get(clean(first).lower())
        body='\n'.join(rest)
        if pid and re.search(r'\b(excused|sick|give her a break|give him a break)\b', body, re.I):
            reason=clean(body) or 'Excused today.'
            excused[pid]=reason
    return excused

def build_excused_comic(display, reason):
    reason=clean(reason) or 'Excused today.'
    svg=f"""<svg xmlns='http://www.w3.org/2000/svg' width='1000' height='620' viewBox='0 0 1000 620'>
    <style>.title{{font:900 56px Arial,sans-serif;fill:#07353a}}.sub{{font:700 26px Arial,sans-serif;fill:#0b5f56}}.body{{font:700 32px Arial,sans-serif;fill:#141414}}.small{{font:600 22px Arial,sans-serif;fill:#52615c}}</style>
    <rect width='1000' height='620' fill='#f4f7f4'/><rect x='28' y='28' width='944' height='564' rx='38' fill='#ffffff' stroke='#002f35' stroke-width='8'/>
    <circle cx='180' cy='300' r='105' fill='#dffbe9' stroke='#002f35' stroke-width='7'/><text x='112' y='326' font-size='86'>🌿</text>
    <text x='330' y='150' class='title'>{html.escape(display)} is excused</text>
    <text x='334' y='208' class='sub'>No EOD required today</text>
    <rect x='330' y='255' width='540' height='165' rx='24' fill='#f4f7f4' stroke='#dde5e0' stroke-width='4'/>
    <text x='365' y='322' class='body'>Sick / excused pass.</text>
    <text x='365' y='372' class='small'>Meeting action: give them a break and move on.</text>
    <text x='56' y='550' class='small'>Respectful status — not a no-submission gag.</text>
    </svg>"""
    return svg_uri(svg)

def load_rainbow(date):
    candidates=[]
    for pat in (f'*rainbow*{date}*', f'*{date}*rainbow*', '*rainbow*'):
        candidates.extend(ROOT.glob(pat))
        candidates.extend((ROOT/'standup_archive'/date).glob(pat) if (ROOT/'standup_archive'/date).exists() else [])
        candidates.extend((ROOT/'local_delivery').glob(pat) if (ROOT/'local_delivery').exists() else [])
    files=sorted({str(p) for p in candidates if p.is_file()})
    return {'ok':bool(files),'files':files[:8],'reason':'' if files else 'Rainbow data file not found in atomix-ops, local_delivery, or today archive.'}

EXCUSED=load_excused(DATE)
slides=[]
good=[]
for pid,display,role in MEETING_PEOPLE:
    for a in by_person.get(pid,[]):
        q=clean(a.get('question_text','')); ans=clean(a.get('answer',''))
        if ans and classify(q,ans)=='good' and len(good)<10:
            good.append({'person':display,'text':ans,'q':q})
slides.append({'type':'good','title':'Good News','subtitle':'Rip through wins first, then go person by person.','people':[p[1] for p in MEETING_PEOPLE],'good':good})
slides.append({'type':'labor','title':'Analytics / Labor Intelligence','subtitle':'Analytics pull from LaborClock + saved order / pack-rate snapshots.','labor':load_labor(DATE)})

for pid,display,role in MEETING_PEOPLE:
    raw=[]
    for a in by_person.get(pid,[]):
        q=clean(a.get('question_text','')); ans=clean(a.get('answer',''))
        if not is_noise(ans): raw.append({'q':q,'a':ans,'kind':classify(q,ans)})
    fires=[x for x in raw if x['kind']=='fire']
    notes=[x for x in raw if x['kind']!='fire']
    png_img_path=pathlib.Path('comic_art')/DATE/f'{pid}_legit_comic.png'
    webp_img_path=pathlib.Path('comic_art')/DATE/f'{pid}_legit_comic.webp'
    img_path=png_img_path if (ROOT/png_img_path).exists() else webp_img_path
    story_chunks=list(chunks(raw,3)) if len(raw)>3 else []
    excused=pid in EXCUSED
    comic_pages=[]
    main_comic=data_uri(img_path)
    if main_comic:
        comic_pages.append({'label':'Comic page 1','image':main_comic})
    elif raw:
        comic_pages.append({'label':'Generated EOD comic','image':build_answer_comic(display,role,raw)})
    else:
        comic_pages.append({'label':'No EOD comic','image':MISSING_EOD_COMIC})
    for n,_part in enumerate(story_chunks,1):
        story_img=pathlib.Path('comic_art')/DATE/f'{pid}_story_{n}.webp'
        img=data_uri(story_img)
        if img:
            comic_pages.append({'label':f'Comic page {len(comic_pages)+1}','image':img})
    slides.append({'type':'person','pid':pid,'title':display,'role':role,'submitted':pid in latest,'excused':excused,'excused_reason':EXCUSED.get(pid,''),'submitted_at':latest.get(pid,{}).get('submitted_at',''),'answers':raw,'fires':fires,'notes':notes,'questions':STANDARD_QUESTIONS,'comic':main_comic,'comic_pages':comic_pages,'complexity':complexity_label(len(raw)),'comic_page_count':len(comic_pages)})
slides.append({'type':'close','title':'Closeout','subtitle':'Action items roll up here for the meeting recap.'})
payload=json.dumps({'date':DATE,'slides':slides,'questions':STANDARD_QUESTIONS,'missingEodComic':MISSING_EOD_COMIC},ensure_ascii=False)

def esc(s): return html.escape(str(s or ''))

html_doc=f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Atomix Standup — {DATE}</title>
<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin><link href='https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap' rel='stylesheet'>
<style>
:root{{--ink:#141414;--dark:#002f35;--dark2:#071a1d;--paper:#fff;--surface:#f4f7f4;--mint:#a3f5c4;--green:#007a63;--line:#dde5e0;--muted:#66736e;--warn:#fff4d6;--danger:#ffe7e2;--shadow:0 18px 50px rgba(0,47,53,.12)}}*{{box-sizing:border-box}}body{{margin:0;background:var(--surface);color:var(--ink);font-family:'DM Sans',system-ui,sans-serif}}button,input,textarea{{font:inherit}}.app{{min-height:100vh;display:grid;grid-template-columns:286px minmax(0,1fr)}}.side{{background:var(--dark);color:white;padding:22px 18px;position:sticky;top:0;height:100vh;overflow:auto}}.brand{{display:flex;align-items:center;gap:12px;margin-bottom:28px}}.mark{{width:38px;height:38px;border-radius:12px;background:var(--mint);box-shadow:inset 0 0 0 4px rgba(0,0,0,.08)}}.brand b{{font-family:'IBM Plex Sans';display:block;font-size:15px}}.brand span{{font-size:12px;color:#bad0cb}}.navbtn{{width:100%;display:flex;justify-content:space-between;gap:12px;align-items:center;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#dce9e5;border-radius:16px;padding:12px 13px;margin:7px 0;cursor:pointer;text-align:left}}.navbtn.active,.navbtn:hover{{background:var(--mint);color:#062b2f;border-color:var(--mint)}}.dot{{font-size:12px;opacity:.8}}main{{padding:30px;min-width:0}}.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}}.kicker{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--green);font-weight:900}}.count{{color:var(--muted);font-size:14px}}.slide{{display:none}}.slide.active{{display:block}}.layout{{display:grid;grid-template-columns:minmax(0,1fr) 376px;gap:22px;align-items:start}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:28px;box-shadow:var(--shadow);padding:28px}}h1{{font-family:'IBM Plex Sans';font-size:clamp(44px,6.4vw,86px);line-height:.9;margin:8px 0 10px;letter-spacing:-.06em}}.sub{{color:var(--muted);font-size:18px}}.cards{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:24px}}.card{{border:1px solid var(--line);border-radius:20px;padding:16px;background:#fbfdfb}}.card h3{{margin:0 0 10px;font-family:'IBM Plex Sans';font-size:15px}}.qa{{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}}.q{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--green);font-weight:900}}.a{{font-size:16px;line-height:1.45;margin-top:4px}}.fire{{background:var(--warn)}}.empty{{color:var(--muted);font-style:italic}}.takeaways{{margin-top:18px;border:1px solid var(--line);background:#f8fffb;border-radius:20px;padding:16px}}.takeaways h3{{margin:0 0 8px;font-family:'IBM Plex Sans';font-size:15px}}.takeaways ul{{margin:0;padding-left:18px;color:var(--muted);line-height:1.45}}.comic{{margin-top:18px;border:1px solid var(--line);background:#fff;border-radius:22px;padding:12px}}.comic img{{width:100%;max-height:620px;object-fit:contain;display:block;border-radius:14px;border:1px solid #111;background:#fafafa}}.comicPage{{margin-top:18px}}.comicPage:first-child{{margin-top:0}}.comicPageTitle{{font-size:13px;font-weight:900;color:var(--green);margin:0 0 8px;text-transform:uppercase;letter-spacing:.08em}}.comic small{{display:block;margin-top:8px;color:var(--muted)}}.miniComic{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}}.miniPanel{{min-height:150px;border:2px solid #111;border-radius:16px;background:linear-gradient(145deg,#f9fffb,#eaf7ef);padding:12px;display:flex;flex-direction:column;justify-content:space-between;box-shadow:inset 0 0 0 4px rgba(163,245,196,.25)}}.miniScene{{font-size:34px;line-height:1}}.miniQ{{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--green);font-weight:900}}.miniBubble{{background:#fff;border:2px solid #111;border-radius:14px;padding:8px;font-size:13px;line-height:1.25}}.notes{{background:var(--dark2);color:white;border-radius:26px;padding:20px;position:sticky;top:24px;box-shadow:var(--shadow)}}.notes h2{{margin:0 0 10px;font-family:'IBM Plex Sans'}}.notes p{{color:#bed1cc;font-size:13px}}textarea,input{{width:100%;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.06);color:white;border-radius:16px;padding:12px;outline:none}}textarea{{min-height:180px;resize:vertical}}input{{margin-top:10px}}.row{{display:flex;gap:10px;margin-top:10px}}.primary{{background:var(--mint);border:0;color:#062b2f;font-weight:900;border-radius:14px;padding:11px 14px;cursor:pointer}}.ghost{{background:transparent;border:1px solid rgba(255,255,255,.18);color:white;border-radius:14px;padding:11px 14px;cursor:pointer}}.actions{{padding-left:18px;color:white}}.actions li{{margin:8px 0}}.footerNav{{display:flex;justify-content:space-between;align-items:center;margin-top:18px}}.download{{background:var(--dark);color:white;border:0;border-radius:14px;padding:12px 16px;font-weight:900;cursor:pointer}}.namechips{{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}}.chip{{border:1px solid var(--line);border-radius:999px;padding:10px 14px;background:#fff;font-weight:800}}.emailBox{{background:#fff;color:#141414;border:1px solid var(--line);font-family:ui-monospace,Menlo,monospace;min-height:360px}}@media(max-width:980px){{.app{{grid-template-columns:1fr}}.side{{position:relative;height:auto}}.layout{{grid-template-columns:1fr}}.cards{{grid-template-columns:1fr}}.notes{{position:relative;top:0}}}}
</style></head><body><div class='app'><aside class='side'><div class='brand'><div class='mark'></div><div><b>Atomix Standup</b><span>Nucleus-style meeting control</span></div></div><div id='nav'></div></aside><main><div class='top'><div><div class='kicker'>Daily cadence</div><div class='count' id='counter'></div></div><button class='download' onclick='downloadHtml()'>Download site</button></div><section id='slides'></section><div class='footerNav'><button class='download' id='prev'>← Previous</button><span class='count'>Good news → names → closeout</span><button class='download' id='next'>Next →</button></div></main></div><script id='deck-data' type='application/json'>{payload}</script><script>
const data=JSON.parse(document.getElementById('deck-data').textContent),slides=data.slides;let idx=Number(localStorage.getItem('atomixNucleusIndex:'+data.date)||0);if(idx<0||idx>=slides.length)idx=0;const nav=document.getElementById('nav'),slidesEl=document.getElementById('slides'),counter=document.getElementById('counter');
function esc(s){{return String(s??'').replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]))}}function short(s,n=260){{s=String(s||'');return s.length>n?s.slice(0,n-1)+'…':s}}function slideKey(i,s){{return 'atomixNucleus:'+data.date+':'+i+':'+s}}function key(s){{return slideKey(idx,s)}}
function shell(inner,title,ph){{return `<article class="slide"><div class="layout"><div class="panel">${{inner}}</div>${{notes(title,ph)}}</div></article>`}}
function notes(title,ph){{return `<aside class="notes"><h2>${{esc(title)}}</h2><p>Meeting notes, takeaways, and owner commitments. Action items roll up on closeout.</p><textarea class="noteText" placeholder="${{esc(ph)}}"></textarea><input class="actionInput" placeholder="Action item: owner + due time"><div class="row"><button class="primary addAction">Add action</button><button class="ghost markDone">Done</button></div><ul class="actions"></ul></aside>`}}
function qaCards(items,empty){{return (items||[]).map(x=>`<div class="qa"><div class="q">${{esc(short(x.q,120))}}</div><div class="a">${{esc(short(x.a,360))}}</div></div>`).join('')||`<p class="empty">${{esc(empty)}}</p>`}}
function takeaways(items,extra='',excused=false){{const fires=(items||[]).filter(x=>x.kind==='fire').length, answered=(items||[]).length;const detail=answered>=7?'Full recap earned. More detail created more comic pages.':answered>=4?'Expanded recap earned. This gets extra comic pages.':answered?'Short recap. More detail would improve the comic.':'No submitted EOD. Same couch comic regardless of reason.';const reason=excused&&!answered?'<li>Sick/excused noted, but no EOD still uses the standard couch comic.</li>':'';return `<div class="takeaways"><h3>Notes & takeaways</h3><ul><li>${{answered}} useful answer${{answered===1?'':'s'}} captured.</li><li>${{fires}} fire / blocker item${{fires===1?'':'s'}} detected.</li><li>${{detail}}</li>${{reason}}${{extra}}</ul></div>`}}
function renderMiniComic(items,label){{const scenes=['🏭','🔥','✅'];const arr=(items&&items.length?items:[{{q:'No EOD submitted',a:'Couch, TV, and Cheez-Its.'}}]).slice(0,3);while(arr.length<3)arr.push({{q:'Story beat',a:'More detail would fill this panel.'}});return `<div class="comic"><h3>${{esc(label)}}</h3><div class="miniComic">${{arr.map((x,i)=>`<div class="miniPanel"><div class="miniScene">${{scenes[i]}}</div><div class="miniQ">${{esc(short(x.q,45))}}</div><div class="miniBubble">${{esc(short(x.a,90))}}</div></div>`).join('')}}</div><small>Small comic at the bottom. More EOD detail creates more comic/story slides.</small></div>`}}
function renderGood(s){{const people=s.people.map(p=>`<span class="chip">${{esc(p)}}</span>`).join('');const good=(s.good||[]).map(x=>`<div class="qa"><div class="q">${{esc(x.person)}} good news</div><div class="a">${{esc(short(x.text,220))}}</div></div>`).join('')||'<p class="empty">No good-news answers detected. Start with live wins.</p>';return shell(`<div class="kicker">Good news first</div><h1>${{esc(s.title)}}</h1><div class="sub">${{esc(s.subtitle)}}</div><div class="namechips">${{people}}</div><div class="cards"><div class="card"><h3>Meeting order</h3><p>Kody → Luis → Emyly → Hugh → Adam → Norman → Burke</p></div><div class="card"><h3>Prompt</h3><p>One quick win each. Keep it fast.</p></div><div class="card" style="grid-column:1/-1"><h3>Detected good news</h3>${{good}}</div></div>`,'Good news notes','Wins, shoutouts, quick positives')}}
function renderLabor(s){{const l=s.labor||{{}},snap=l.snapshot||{{}},pack=l.packRate||{{}},depts=(l.topDepts||[]).map(([name,h])=>`<div class="qa"><div class="q">${{esc(name)}}</div><div class="a">${{Number(h||0).toFixed(2)}} labor hours</div></div>`).join('');const body=l.ok?`<div class="kicker">Vetted analytics source</div><h1>${{esc(s.title)}}</h1><div class="sub">${{esc(s.subtitle)}}</div><div class="cards"><div class="card"><h3>Total labor</h3><p>${{Number(snap.totalHoursToday||0).toFixed(1)}} hrs • est. $${{Number(snap.estLaborCost||0).toLocaleString(undefined,{{maximumFractionDigits:0}})}}</p></div><div class="card"><h3>Orders snapshot</h3><p>${{Number(snap.ordersSnapshot||0).toLocaleString()}} orders • CPO $${{snap.ordersSnapshot?Number((snap.estLaborCost||0)/snap.ordersSnapshot).toFixed(2):'N/A'}}</p></div><div class="card"><h3>Pack-rate snapshot</h3><p>${{Number(pack.avgOrdersPerHour||snap.packRateAvgOPH||0).toFixed(1)}} OPH • ${{Number(pack.totalOrders||snap.packRateTotalOrders||0).toLocaleString()}} orders tracked</p></div><div class="card"><h3>Data source</h3><p>${{esc(l.source)}}</p>${{l.html?`<p><b>HTML:</b> ${{esc(l.html)}}</p>`:''}}${{l.md?`<p><b>MD:</b> ${{esc(l.md)}}</p>`:''}}</div><div class="card" style="grid-column:1/-1"><h3>Labor by area</h3>${{depts||'<p class="empty">No department totals found.</p>'}}</div></div><div class="takeaways"><h3>Takeaways</h3><ul><li>Uses saved same-day order snapshot instead of mixing live next-day order counts.</li><li>Labor hours and estimated labor cost came from analytics JSON, not invented comments.</li><li>Audit watch: open live segments / logged-hours fallback can inflate hours if not cleaned up.</li></ul></div>`:`<div class="kicker">Missing analytics source</div><h1>${{esc(s.title)}}</h1><div class="sub">${{esc(l.reason||'Labor data not found.')}}</div><div class="card"><h3>Expected file</h3><p>${{esc(l.source||'labor_intelligence/YYYY-MM-DD/labor_intelligence_YYYY-MM-DD.json')}}</p></div>`;return shell(body,'Labor notes','Labor exceptions, owner, and follow-up')}}
function renderRainbow(s){{const r=s.rainbow||{{}};const files=(r.files||[]).map(f=>`<div class="qa"><div class="q">Rainbow file found</div><div class="a">${{esc(f)}}</div></div>`).join('');const body=`<div class="kicker">Rainbow data check</div><h1>${{esc(s.title)}}</h1><div class="sub">${{esc(s.subtitle)}}</div><div class="cards"><div class="card" style="grid-column:1/-1"><h3>Status</h3>${{r.ok?files:`<p class="empty">${{esc(r.reason||'No Rainbow data available yet.')}}</p>`}}</div></div><div class="takeaways"><h3>Takeaways</h3><ul><li>${{r.ok?'Rainbow source is present and should be reviewed before meeting.':'Do not fake Rainbow metrics; slide stays as a missing-data callout until source is connected.'}}</li></ul></div>`;return shell(body,'Rainbow notes','Rainbow exceptions and follow-up')}}
function renderPerson(s){{const bucketBody=qaCards(s.answers,'No submitted answers. Meeting read: same couch, TV, and Cheez-Its comic no matter the reason — submit real EOD data and the comic gets real.');const buckets=`<div class="cards"><div class="card" style="grid-column:1/-1"><h3>Question / answer buckets</h3>${{bucketBody}}</div></div>`;const extra=s.comic_page_count>1?`<li>${{s.comic_page_count}} comic page${{s.comic_page_count>1?'s':''}} included below because this EOD had more detail.</li>`:'';const pages=(s.comic_pages||[]).map((p,i)=>`<div class="comicPage"><div class="comicPageTitle">${{esc(p.label||('Comic page '+(i+1)))}}</div><img src="${{p.image}}" alt="${{esc(s.title)}} comic page ${{i+1}}"></div>`).join('');const comic=`<div class="comic"><h3>${{esc(s.title)}} comic</h3>${{pages||'<small>Comic pending.</small>'}}<small>${{s.answers&&s.answers.length?'More useful EOD detail = more comic pages on this same person slide.':'No EOD = standard couch/TV/Cheez-Its comic, regardless of reason.'}}</small></div>`;return shell(`<div class="kicker">${{esc(s.role)}} • ${{s.submitted?'submitted':'no EOD'}} • ${{esc(s.complexity)}}</div><h1>${{esc(s.title)}}</h1><div class="sub">Name, Q&A buckets, notes/takeaways, then a larger readable comic below.</div>${{buckets}}${{takeaways(s.answers,extra,s.excused)}}${{comic}}`,s.title+' notes','Notes and commitments for '+s.title)}}
function renderStory(s){{const buckets=`<div class="cards"><div class="card" style="grid-column:1/-1"><h3>Question / answer buckets — chapter ${{s.chapter}} of ${{s.chapters}}</h3>${{qaCards(s.answers,'No story beats on this chapter.')}}</div></div>`;const comic=s.comic?`<div class="comic"><img src="${{s.comic}}" alt="${{esc(s.person)}} chapter comic strip"><small>Real comic chapter ${{s.chapter}} of ${{s.chapters}}. More detail creates more comic slides.</small></div>`:'<div class="comic"><small>Comic pending for this chapter.</small></div>';return shell(`<div class="kicker">${{esc(s.role)}} • ${{esc(s.complexity)}} • comic chapter ${{s.chapter}} of ${{s.chapters}}</div><h1>${{esc(s.person)}} Story</h1><div class="sub">This chapter exists because the EOD had enough detail to need more comic/story slides.</div>${{buckets}}${{takeaways(s.answers)}}${{comic}}`,s.title+' notes','Story notes and takeaways for '+s.person)}}
function allActions(){{return slides.map((s,i)=>({{slide:s.title,notes:localStorage.getItem(slideKey(i,'notes'))||'',actions:JSON.parse(localStorage.getItem(slideKey(i,'actions'))||'[]')}})).filter(x=>x.notes.trim()||x.actions.length)}}
function emailText(){{const lines=[`Atomix Standup Recap — ${{data.date}}`,'','Action Items:'];let n=0;allActions().forEach(x=>x.actions.forEach(a=>{{n++;lines.push(`${{n}}. [${{x.slide}}] ${{a}}`)}}));if(!n)lines.push('- No action items captured yet.');lines.push('','Notes:');allActions().forEach(x=>{{if(x.notes.trim())lines.push(`- ${{x.slide}}: ${{x.notes.trim()}}`)}});return lines.join('\\n')}}
function renderClose(s){{return shell(`<div class="kicker">Closeout</div><h1>${{esc(s.title)}}</h1><div class="sub">${{esc(s.subtitle)}}</div><div class="card" style="margin-top:22px"><h3>Email-ready recap</h3><textarea class="emailBox" id="emailBox"></textarea><div class="row"><button class="download" onclick="refreshEmail()">Refresh recap</button><button class="download" onclick="copyEmail()">Copy recap</button></div></div>`,'Final notes','Final commitments before sending recap')}}
function refreshEmail(){{const b=document.getElementById('emailBox');if(b)b.value=emailText()}}function copyEmail(){{refreshEmail();navigator.clipboard?.writeText(document.getElementById('emailBox').value)}}
function hydrate(){{const note=document.querySelector('.slide.active .noteText');if(!note)return;note.value=localStorage.getItem(key('notes'))||'';note.oninput=()=>localStorage.setItem(key('notes'),note.value);const input=document.querySelector('.slide.active .actionInput'),add=document.querySelector('.slide.active .addAction'),ul=document.querySelector('.slide.active .actions'),done=document.querySelector('.slide.active .markDone');const render=()=>{{const arr=JSON.parse(localStorage.getItem(key('actions'))||'[]');ul.innerHTML=arr.map((a,i)=>`<li>${{esc(a)}} <button data-rm="${{i}}">×</button></li>`).join('');ul.querySelectorAll('button').forEach(b=>b.onclick=()=>{{arr.splice(Number(b.dataset.rm),1);localStorage.setItem(key('actions'),JSON.stringify(arr));render()}})}};add.onclick=()=>{{const v=input.value.trim();if(!v)return;const arr=JSON.parse(localStorage.getItem(key('actions'))||'[]');arr.push(v);localStorage.setItem(key('actions'),JSON.stringify(arr));input.value='';render();refreshEmail()}};done.onclick=()=>{{localStorage.setItem(key('done'),'1');draw()}};render();refreshEmail()}}
function draw(){{slidesEl.innerHTML=slides.map(s=>s.type==='good'?renderGood(s):s.type==='labor'?renderLabor(s):s.type==='close'?renderClose(s):s.type==='story'?renderStory(s):renderPerson(s)).join('');nav.innerHTML=slides.map((s,i)=>`<button class="navbtn ${{i===idx?'active':''}}" data-i="${{i}}"><span>${{i+1}}. ${{esc(s.title)}}</span><span class="dot">${{localStorage.getItem(slideKey(i,'done'))?'✓':'●'}}</span></button>`).join('');document.querySelectorAll('.slide')[idx].classList.add('active');counter.textContent=`${{data.date}} • Slide ${{idx+1}} of ${{slides.length}}`;hydrate();document.querySelectorAll('.navbtn').forEach(b=>b.onclick=()=>go(Number(b.dataset.i)))}}
function go(i){{idx=Math.max(0,Math.min(slides.length-1,i));localStorage.setItem('atomixNucleusIndex:'+data.date,idx);draw()}}function downloadHtml(){{const a=document.createElement('a');a.href=location.href;a.download=`atomix-standup-${{data.date}}.html`;a.click()}}
document.getElementById('prev').onclick=()=>go(idx-1);document.getElementById('next').onclick=()=>go(idx+1);window.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')go(idx+1);if(e.key==='ArrowLeft')go(idx-1)}});draw();
</script></body></html>"""
OUT.write_text(html_doc); LEGACY.write_text(html_doc)
print(json.dumps({'out':str(OUT),'slides':len(slides),'people':[p[1] for p in MEETING_PEOPLE]},indent=2))
