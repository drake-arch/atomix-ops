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
    ('adam','Adam','Special Projects'),
    ('luis','Luis','Inventory'),
    ('emyly','Emily','Inbound'),
    ('burke','Burke','BAL'),
    ('hugh','Hugh','PM Lead'),
    ('norman','Norman','SLC'),
]
NOISE={'','n/a','na','no','none','.', 'nothing'}
parser=argparse.ArgumentParser(description='Build Nucleus-style Atomix standup meeting site.')
parser.add_argument('--date', help='Report date YYYY-MM-DD. Defaults to yesterday in America/Chicago.')
args=parser.parse_args()
DATE=args.date or (datetime.datetime.now(ZoneInfo('America/Chicago')).date()-datetime.timedelta(days=1)).isoformat()
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

MISSING_EOD_COMIC=data_uri(pathlib.Path('comic_art')/'shared'/'no_submission_cheezits_comic.png')

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

slides=[]
good=[]
for pid,display,role in MEETING_PEOPLE:
    for a in by_person.get(pid,[]):
        q=clean(a.get('question_text','')); ans=clean(a.get('answer',''))
        if ans and classify(q,ans)=='good' and len(good)<10:
            good.append({'person':display,'text':ans,'q':q})
slides.append({'type':'good','title':'Good News','subtitle':'Rip through wins first, then go person by person.','people':[p[1] for p in MEETING_PEOPLE],'good':good})

for pid,display,role in MEETING_PEOPLE:
    raw=[]
    for a in by_person.get(pid,[]):
        q=clean(a.get('question_text','')); ans=clean(a.get('answer',''))
        if not is_noise(ans): raw.append({'q':q,'a':ans,'kind':classify(q,ans)})
    fires=[x for x in raw if x['kind']=='fire']
    notes=[x for x in raw if x['kind']!='fire']
    img_path=pathlib.Path('comic_art')/DATE/f'{pid}_legit_comic.png'
    story_chunks=list(chunks(raw,3)) if len(raw)>3 else []
    slides.append({'type':'person','pid':pid,'title':display,'role':role,'submitted':pid in latest,'submitted_at':latest.get(pid,{}).get('submitted_at',''),'answers':raw,'fires':fires,'notes':notes,'questions':STANDARD_QUESTIONS,'comic':data_uri(img_path),'complexity':complexity_label(len(raw)),'story_slide_count':len(story_chunks)})
    for n,part in enumerate(story_chunks,1):
        slides.append({'type':'story','pid':pid,'title':f'{display} Story {n}/{len(story_chunks)}','person':display,'role':role,'chapter':n,'chapters':len(story_chunks),'answers':part,'complexity':complexity_label(len(raw))})
slides.append({'type':'close','title':'Closeout','subtitle':'Action items roll up here for the meeting recap.'})
payload=json.dumps({'date':DATE,'slides':slides,'questions':STANDARD_QUESTIONS,'missingEodComic':MISSING_EOD_COMIC},ensure_ascii=False)

def esc(s): return html.escape(str(s or ''))

html_doc=f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Atomix Standup — {DATE}</title>
<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin><link href='https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap' rel='stylesheet'>
<style>
:root{{--ink:#141414;--dark:#002f35;--dark2:#071a1d;--paper:#fff;--surface:#f4f7f4;--mint:#a3f5c4;--green:#007a63;--line:#dde5e0;--muted:#66736e;--warn:#fff4d6;--danger:#ffe7e2;--shadow:0 18px 50px rgba(0,47,53,.12)}}*{{box-sizing:border-box}}body{{margin:0;background:var(--surface);color:var(--ink);font-family:'DM Sans',system-ui,sans-serif}}button,input,textarea{{font:inherit}}.app{{min-height:100vh;display:grid;grid-template-columns:286px minmax(0,1fr)}}.side{{background:var(--dark);color:white;padding:22px 18px;position:sticky;top:0;height:100vh;overflow:auto}}.brand{{display:flex;align-items:center;gap:12px;margin-bottom:28px}}.mark{{width:38px;height:38px;border-radius:12px;background:var(--mint);box-shadow:inset 0 0 0 4px rgba(0,0,0,.08)}}.brand b{{font-family:'IBM Plex Sans';display:block;font-size:15px}}.brand span{{font-size:12px;color:#bad0cb}}.navbtn{{width:100%;display:flex;justify-content:space-between;gap:12px;align-items:center;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#dce9e5;border-radius:16px;padding:12px 13px;margin:7px 0;cursor:pointer;text-align:left}}.navbtn.active,.navbtn:hover{{background:var(--mint);color:#062b2f;border-color:var(--mint)}}.dot{{font-size:12px;opacity:.8}}main{{padding:30px;min-width:0}}.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}}.kicker{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--green);font-weight:900}}.count{{color:var(--muted);font-size:14px}}.slide{{display:none}}.slide.active{{display:block}}.layout{{display:grid;grid-template-columns:minmax(0,1fr) 376px;gap:22px;align-items:start}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:28px;box-shadow:var(--shadow);padding:28px}}h1{{font-family:'IBM Plex Sans';font-size:clamp(44px,6.4vw,86px);line-height:.9;margin:8px 0 10px;letter-spacing:-.06em}}.sub{{color:var(--muted);font-size:18px}}.cards{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:24px}}.card{{border:1px solid var(--line);border-radius:20px;padding:16px;background:#fbfdfb}}.card h3{{margin:0 0 10px;font-family:'IBM Plex Sans';font-size:15px}}.qa{{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}}.q{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--green);font-weight:900}}.a{{font-size:16px;line-height:1.45;margin-top:4px}}.fire{{background:var(--warn)}}.empty{{color:var(--muted);font-style:italic}}.comic{{margin-top:22px;border:1px solid var(--line);background:#fff;border-radius:22px;padding:12px}}.comic img{{width:100%;display:block;border-radius:14px;border:1px solid #111}}.comic small{{display:block;margin-top:8px;color:var(--muted)}}.notes{{background:var(--dark2);color:white;border-radius:26px;padding:20px;position:sticky;top:24px;box-shadow:var(--shadow)}}.notes h2{{margin:0 0 10px;font-family:'IBM Plex Sans'}}.notes p{{color:#bed1cc;font-size:13px}}textarea,input{{width:100%;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.06);color:white;border-radius:16px;padding:12px;outline:none}}textarea{{min-height:180px;resize:vertical}}input{{margin-top:10px}}.row{{display:flex;gap:10px;margin-top:10px}}.primary{{background:var(--mint);border:0;color:#062b2f;font-weight:900;border-radius:14px;padding:11px 14px;cursor:pointer}}.ghost{{background:transparent;border:1px solid rgba(255,255,255,.18);color:white;border-radius:14px;padding:11px 14px;cursor:pointer}}.actions{{padding-left:18px;color:white}}.actions li{{margin:8px 0}}.footerNav{{display:flex;justify-content:space-between;align-items:center;margin-top:18px}}.download{{background:var(--dark);color:white;border:0;border-radius:14px;padding:12px 16px;font-weight:900;cursor:pointer}}.namechips{{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}}.chip{{border:1px solid var(--line);border-radius:999px;padding:10px 14px;background:#fff;font-weight:800}}.emailBox{{background:#fff;color:#141414;border:1px solid var(--line);font-family:ui-monospace,Menlo,monospace;min-height:360px}}@media(max-width:980px){{.app{{grid-template-columns:1fr}}.side{{position:relative;height:auto}}.layout{{grid-template-columns:1fr}}.cards{{grid-template-columns:1fr}}.notes{{position:relative;top:0}}}}
</style></head><body><div class='app'><aside class='side'><div class='brand'><div class='mark'></div><div><b>Atomix Standup</b><span>Nucleus-style meeting control</span></div></div><div id='nav'></div></aside><main><div class='top'><div><div class='kicker'>Daily cadence</div><div class='count' id='counter'></div></div><button class='download' onclick='downloadHtml()'>Download site</button></div><section id='slides'></section><div class='footerNav'><button class='download' id='prev'>← Previous</button><span class='count'>Good news → names → closeout</span><button class='download' id='next'>Next →</button></div></main></div><script id='deck-data' type='application/json'>{payload}</script><script>
const data=JSON.parse(document.getElementById('deck-data').textContent),slides=data.slides;let idx=Number(localStorage.getItem('atomixNucleusIndex:'+data.date)||0);if(idx<0||idx>=slides.length)idx=0;const nav=document.getElementById('nav'),slidesEl=document.getElementById('slides'),counter=document.getElementById('counter');
function esc(s){{return String(s??'').replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]))}}function short(s,n=260){{s=String(s||'');return s.length>n?s.slice(0,n-1)+'…':s}}function slideKey(i,s){{return 'atomixNucleus:'+data.date+':'+i+':'+s}}function key(s){{return slideKey(idx,s)}}
function shell(inner,title,ph){{return `<article class="slide"><div class="layout"><div class="panel">${{inner}}</div>${{notes(title,ph)}}</div></article>`}}
function notes(title,ph){{return `<aside class="notes"><h2>${{esc(title)}}</h2><p>Capture decisions, blockers, and owner commitments. Action items roll up on the closeout page.</p><textarea class="noteText" placeholder="${{esc(ph)}}"></textarea><input class="actionInput" placeholder="Action item: owner + due time"><div class="row"><button class="primary addAction">Add action</button><button class="ghost markDone">Done</button></div><ul class="actions"></ul></aside>`}}
function renderGood(s){{const people=s.people.map(p=>`<span class="chip">${{esc(p)}}</span>`).join('');const good=(s.good||[]).map(x=>`<div class="qa"><div class="q">${{esc(x.person)}} good news</div><div class="a">${{esc(short(x.text,220))}}</div></div>`).join('')||'<p class="empty">No good-news answers detected. Start with live wins.</p>';return shell(`<div class="kicker">Good news first</div><h1>${{esc(s.title)}}</h1><div class="sub">${{esc(s.subtitle)}}</div><div class="namechips">${{people}}</div><div class="cards"><div class="card"><h3>Meeting order</h3><p>Kody → Adam → Luis → Emily → Burke → Hugh → Norman</p></div><div class="card"><h3>Prompt</h3><p>One quick win each. Keep it fast.</p></div><div class="card" style="grid-column:1/-1"><h3>Detected good news</h3>${{good}}</div></div>`,'Good news notes','Wins, shoutouts, quick positives')}}
function renderPerson(s){{const qlist=s.questions.map(q=>`<li>${{esc(q)}}</li>`).join('');const answers=(s.answers||[]).map(x=>`<div class="qa"><div class="q">${{esc(short(x.q,110))}}</div><div class="a">${{esc(short(x.a,300))}}</div></div>`).join('')||'<p class="empty">No submitted answers. Meeting read: they look like they did nothing all day — couch, TV, and Cheez-Its until they give us real data.</p>';const fires=(s.fires||[]).map(x=>`<div class="qa"><div class="q">Fire / blocker</div><div class="a">${{esc(short(x.a,260))}}</div></div>`).join('')||'<p class="empty">No active fires detected.</p>';const comic=s.comic?`<div class="comic"><img src="${{s.comic}}" alt="${{esc(s.title)}} comic strip"><small>More EOD detail = richer comic strip. Small input gets a small story; detailed input earns a bigger, better strip.</small></div>`:`<div class="comic heroComic"><img src="${{data.missingEodComic}}" alt="No EOD submission couch TV Cheez-Its comic"><small>No EOD data = couch, TV, and Cheez-Its. Submit real work and the comic gets real.</small></div>`;const extra=s.story_slide_count?`<p><b>${{s.story_slide_count}} extra story slide${{s.story_slide_count>1?'s':''}}</b> added because this EOD had more detail.</p>`:'';return shell(`<div class="kicker">${{esc(s.role)}} • ${{s.submitted?'submitted':'live capture'}} • ${{esc(s.complexity)}}</div><h1>${{esc(s.title)}}</h1><div class="sub">Standard question pass, then notes/actions. ${{extra}}</div>${{comic}}<div class="cards"><div class="card"><h3>Standard questions</h3><ol>${{qlist}}</ol></div><div class="card fire"><h3>Fires / needs</h3>${{fires}}</div><div class="card" style="grid-column:1/-1"><h3>Answers pulled from EOD</h3>${{answers}}</div></div>`,s.title+' notes','Notes and commitments for '+s.title)}}
function renderStory(s){{const beats=(s.answers||[]).map((x,i)=>`<div class="qa"><div class="q">Beat ${{i+1}} — ${{esc(short(x.q,90))}}</div><div class="a">${{esc(short(x.a,420))}}</div></div>`).join('');const comic=s.comic?`<div class="comic"><img src="${{s.comic}}" alt="${{esc(s.person)}} comic strip"><small>This detail earns extra story time. More data = more panels/slides.</small></div>`:'';return shell(`<div class="kicker">${{esc(s.role)}} • ${{esc(s.complexity)}} • chapter ${{s.chapter}} of ${{s.chapters}}</div><h1>${{esc(s.person)}} Story</h1><div class="sub">Extra slide generated because this EOD had enough detail to deserve more story.</div>${{comic}}<div class="cards"><div class="card" style="grid-column:1/-1"><h3>Story beats from the EOD</h3>${{beats}}</div></div>`,s.title+' notes','Story notes and commitments for '+s.person)}}
function allActions(){{return slides.map((s,i)=>({{slide:s.title,notes:localStorage.getItem(slideKey(i,'notes'))||'',actions:JSON.parse(localStorage.getItem(slideKey(i,'actions'))||'[]')}})).filter(x=>x.notes.trim()||x.actions.length)}}
function emailText(){{const lines=[`Atomix Standup Recap — ${{data.date}}`,'','Action Items:'];let n=0;allActions().forEach(x=>x.actions.forEach(a=>{{n++;lines.push(`${{n}}. [${{x.slide}}] ${{a}}`)}}));if(!n)lines.push('- No action items captured yet.');lines.push('','Notes:');allActions().forEach(x=>{{if(x.notes.trim())lines.push(`- ${{x.slide}}: ${{x.notes.trim()}}`)}});return lines.join('\\n')}}
function renderClose(s){{return shell(`<div class="kicker">Closeout</div><h1>${{esc(s.title)}}</h1><div class="sub">${{esc(s.subtitle)}}</div><div class="card" style="margin-top:22px"><h3>Email-ready recap</h3><textarea class="emailBox" id="emailBox"></textarea><div class="row"><button class="download" onclick="refreshEmail()">Refresh recap</button><button class="download" onclick="copyEmail()">Copy recap</button></div></div>`,'Final notes','Final commitments before sending recap')}}
function refreshEmail(){{const b=document.getElementById('emailBox');if(b)b.value=emailText()}}function copyEmail(){{refreshEmail();navigator.clipboard?.writeText(document.getElementById('emailBox').value)}}
function hydrate(){{const note=document.querySelector('.slide.active .noteText');if(!note)return;note.value=localStorage.getItem(key('notes'))||'';note.oninput=()=>localStorage.setItem(key('notes'),note.value);const input=document.querySelector('.slide.active .actionInput'),add=document.querySelector('.slide.active .addAction'),ul=document.querySelector('.slide.active .actions'),done=document.querySelector('.slide.active .markDone');const render=()=>{{const arr=JSON.parse(localStorage.getItem(key('actions'))||'[]');ul.innerHTML=arr.map((a,i)=>`<li>${{esc(a)}} <button data-rm="${{i}}">×</button></li>`).join('');ul.querySelectorAll('button').forEach(b=>b.onclick=()=>{{arr.splice(Number(b.dataset.rm),1);localStorage.setItem(key('actions'),JSON.stringify(arr));render()}})}};add.onclick=()=>{{const v=input.value.trim();if(!v)return;const arr=JSON.parse(localStorage.getItem(key('actions'))||'[]');arr.push(v);localStorage.setItem(key('actions'),JSON.stringify(arr));input.value='';render();refreshEmail()}};done.onclick=()=>{{localStorage.setItem(key('done'),'1');draw()}};render();refreshEmail()}}
function draw(){{slidesEl.innerHTML=slides.map(s=>s.type==='good'?renderGood(s):s.type==='close'?renderClose(s):s.type==='story'?renderStory(s):renderPerson(s)).join('');nav.innerHTML=slides.map((s,i)=>`<button class="navbtn ${{i===idx?'active':''}}" data-i="${{i}}"><span>${{i+1}}. ${{esc(s.title)}}</span><span class="dot">${{localStorage.getItem(slideKey(i,'done'))?'✓':'●'}}</span></button>`).join('');document.querySelectorAll('.slide')[idx].classList.add('active');counter.textContent=`${{data.date}} • Slide ${{idx+1}} of ${{slides.length}}`;hydrate();document.querySelectorAll('.navbtn').forEach(b=>b.onclick=()=>go(Number(b.dataset.i)))}}
function go(i){{idx=Math.max(0,Math.min(slides.length-1,i));localStorage.setItem('atomixNucleusIndex:'+data.date,idx);draw()}}function downloadHtml(){{const a=document.createElement('a');a.href=location.href;a.download=`atomix-standup-${{data.date}}.html`;a.click()}}
document.getElementById('prev').onclick=()=>go(idx-1);document.getElementById('next').onclick=()=>go(idx+1);window.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')go(idx+1);if(e.key==='ArrowLeft')go(idx-1)}});draw();
</script></body></html>"""
OUT.write_text(html_doc); LEGACY.write_text(html_doc)
print(json.dumps({'out':str(OUT),'slides':len(slides),'people':[p[1] for p in MEETING_PEOPLE]},indent=2))
