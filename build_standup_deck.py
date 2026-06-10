import argparse, csv, io, json, urllib.request, html, pathlib, collections, datetime, subprocess, re
from zoneinfo import ZoneInfo

SID='130wcBqy6QUzPM9KID9fXAHUP47a8NGVPSxVOaPt3qo0'
GIDS={'Reports':'146026037','Answers':'489860443','People':'1868587579'}
STORY_STANDARD_QUESTIONS=[
    'What was the first thing you worked on today?',
    'What fires did you work on today?',
    'What fires did you put out today?',
    'What do you need to put out these fires?',
    'If you had a magic wand, what would you change about today?',
    'What was the last thing you worked on today?',
]
NOISE={'','n/a','na','no','none','.', 'nothing'}

parser=argparse.ArgumentParser(description='Build Cleo interactive morning standup meeting website from ShiftFlow Sheet exports.')
parser.add_argument('--date', help='Report date YYYY-MM-DD. Defaults to yesterday in America/Chicago.')
args=parser.parse_args()
DATE=args.date or (datetime.datetime.now(ZoneInfo('America/Chicago')).date()-datetime.timedelta(days=1)).isoformat()
ROOT=pathlib.Path('/home/fabric041/work/atomix-ops')
OUT=ROOT / f'cleo-standup-meeting-{DATE}.html'


def fetch(gid):
    url=f'https://docs.google.com/spreadsheets/d/{SID}/export?format=csv&gid={gid}'
    data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8-sig','replace')
    return list(csv.DictReader(io.StringIO(data)))

def clean(s): return re.sub(r'\s+', ' ', str(s or '')).strip()
def is_noise(ans): return clean(ans).lower() in NOISE

def classify_item(q,a):
    text=(q+' '+a).lower()
    if any(x in text for x in ['risk','issue','blocker','missing','not able','did not','could not','violation','broken process','low','running out','needs','left from today','batches left','not in wms','lock-location','lock location','fefo','fifo','fire']):
        return 'risk'
    if any(x in text for x in ['orders','labor','spend','hours','oph','completed','shipped','kitted']):
        return 'metric'
    return 'note'

def normalize_people(rows):
    people=[]
    for p in rows:
        pid=(p.get('person_id') or p.get('id') or '').strip().lower()
        if pid in {'ricardo','yaniel','yanyel'}:
            continue
        p=dict(p)
        p['person_id']=pid
        people.append(p)
    if not any(p.get('person_id')=='haley' for p in people):
        people.append({'person_id':'haley','name':'Haley','role':'Second Shift Outbound','site':'MKE','reports_to':'hugh'})
    # make sure public Sheet spelling drift cannot leak back into deck
    for p in people:
        if p.get('person_id')=='hugh':
            p.setdefault('name','Hugh')
    priority=['kody','hugh','haley','emyly','luis','adam','norman','santana','ana','christine','relly','ramar','brenda','ofelia','david','nate','maria','drake']
    rank={pid:i for i,pid in enumerate(priority)}
    people.sort(key=lambda p:(rank.get(p.get('person_id'),999), p.get('name','')))
    return people

reports=fetch(GIDS['Reports'])
answers=fetch(GIDS['Answers'])
people=normalize_people(fetch(GIDS['People']))

# Normalize stale Yaniel/Yanyel report ids out of the meeting website. Haley starts clean unless she submits under haley.
day_reports=[r for r in reports if r.get('date')==DATE and (r.get('person_id') or '').lower() not in {'yaniel','yanyel','ricardo'}]
day_answers=[a for a in answers if a.get('date')==DATE and (a.get('person_id') or '').lower() not in {'yaniel','yanyel','ricardo'}]
latest={}
for r in day_reports:
    pid=(r.get('person_id') or '').lower()
    if pid not in latest or r.get('submitted_at','')>latest[pid].get('submitted_at',''):
        latest[pid]=r
by_person=collections.defaultdict(list)
for a in day_answers:
    by_person[(a.get('person_id') or '').lower()].append(a)
submitted=set(latest)
missing=[p for p in people if p.get('person_id') not in submitted]

all_risks=[]; metrics=[]; good_news=[]
positive_terms=['all orders out','ready','prepared','completed','no call-ins','no call ins','caught up','good','cleaned','no issues','no blockers','all picked up','all caught up','resolved','put out']
bad_terms=['not able','did not','could not','issue','blocker','missing','violation','broken process','t force did not','already discussed','good night']
for a in day_answers:
    q=clean(a.get('question_text','')); ans=clean(a.get('answer',''))
    if is_noise(ans):
        continue
    kind=classify_item(q,ans)
    item={'person':a.get('person_name'), 'pid':(a.get('person_id') or '').lower(), 'q':q, 'a':ans, 'kind':kind}
    if kind=='risk': all_risks.append(item)
    if kind=='metric': metrics.append(item)
    txt=(q+' '+ans).lower()
    if any(t in txt for t in positive_terms) and not any(t in txt for t in bad_terms):
        good_news.append({'person':a.get('person_name'), 'q':q, 'a':ans})
good_news=good_news[:8]

slides=[]
slides.append({
    'type':'overview','title':'Good News First','subtitle':f'{DATE} EOD meeting website',
    'takeaways':[f'{len(submitted)}/{len(people)} active people submitted; {len(missing)} missing.',
                 'Use each person slide for playback, notes, and owner/action capture.',
                 'Closeout slide summarizes action items for email follow-up.'],
    'good_news':good_news,'risks':all_risks[:8],'missing':[p['name'] for p in missing]
})

for p in people:
    pid=p['person_id']
    cleaned=[]
    for a in by_person.get(pid,[]):
        q=clean(a.get('question_text','')); ans=clean(a.get('answer',''))
        cleaned.append({'q':q,'a':ans,'kind':classify_item(q,ans)})
    risks=[x for x in cleaned if x['kind']=='risk' and not is_noise(x['a'])]
    notes=[x for x in cleaned if x['kind']!='risk' and not is_noise(x['a'])]
    comic_file=ROOT/'comic_art'/DATE/f'{pid}_legit_comic.png'
    slides.append({
        'type':'person','pid':pid,'title':p.get('name') or pid.title(),'subtitle':f"{p.get('role','')} • {p.get('site','')}",
        'submitted':pid in submitted,'submitted_at':latest.get(pid,{}).get('submitted_at',''),
        'risks':risks,'notes':notes,'answers':cleaned,
        'comic_art':f'comic_art/{DATE}/{pid}_legit_comic.png' if comic_file.exists() else '',
        'prompt':f"{p.get('name') or pid.title()}, go ahead — what should the team know from your EOD?"
    })
slides.append({'type':'close','title':'Meeting Closeout','subtitle':'Review action items, copy email recap, send to team',
               'takeaways':['Confirm every action item has owner + due time.', 'Copy the email-ready recap after the meeting.', 'Send recap to the team from email once approved.']})

def clean_tts(text, limit=900): return clean(text)[:limit]
def narration(s):
    if s['type']=='overview':
        good='. '.join(f"{x.get('person')}: {x.get('a')}" for x in s.get('good_news',[])[:4]) or 'No positive callouts detected yet.'
        return clean_tts(f"Good news first. {good}. Submission coverage: {s['takeaways'][0]}. Missing EODs: {', '.join(s.get('missing', [])) or 'none'}.")
    if s['type']=='close':
        return clean_tts('Meeting closeout. Review every action item. Confirm owner and due time before sending the recap.')
    if not s.get('submitted'):
        return clean_tts(f"{s['title']} did not submit an EOD for {DATE}. Capture live notes and action items now.")
    qa='. '.join(f"{x.get('q')}: {x.get('a')}" for x in (s.get('answers') or []) if not is_noise(x.get('a')))[:700]
    return clean_tts(f"{s['title']}. {qa}. {s.get('prompt')}")

audio_dir=OUT.parent / f'standup_audio_{DATE}'
audio_dir.mkdir(exist_ok=True)
for i,s in enumerate(slides, start=1):
    mp3=audio_dir / f'slide_{i:02d}_andrew.mp3'
    txt=audio_dir / f'slide_{i:02d}_andrew.txt'
    txt.write_text(narration(s))
    if not mp3.exists() or mp3.stat().st_size < 1000:
        subprocess.run(['edge-tts','--voice','en-US-AndrewNeural','--file',str(txt),'--write-media',str(mp3)], check=True, timeout=60)
    s['audio']=f'{audio_dir.name}/{mp3.name}'

payload=json.dumps({'date':DATE,'slides':slides,'story_questions':STORY_STANDARD_QUESTIONS},ensure_ascii=False)

html_doc=f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Atomix Standup Meeting — {DATE}</title>
<style>
:root{{--bg:#071512;--panel:#10241e;--ink:#f6fffb;--muted:#a9c6bd;--mint:#65f4bf;--gold:#ffd166;--red:#ff6b6b;--line:#21443a}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top left,#173a31,#071512 44%,#030706);color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}}button,input,textarea{{font:inherit}}.app{{min-height:100vh;display:grid;grid-template-columns:282px 1fr}}aside.nav{{border-right:1px solid var(--line);background:rgba(4,12,10,.82);padding:18px;position:sticky;top:0;height:100vh;overflow:auto}}.brand{{display:flex;gap:10px;align-items:center;margin-bottom:16px}}.mark{{width:38px;height:38px;border-radius:13px;background:var(--mint);border:3px solid #020605;box-shadow:5px 5px 0 #000}}.brand b{{display:block}}.brand span,.muted{{color:var(--muted);font-size:12px}}.navbtn{{width:100%;text-align:left;border:1px solid transparent;background:transparent;color:var(--muted);border-radius:12px;padding:10px;margin:4px 0;cursor:pointer;display:flex;gap:8px;justify-content:space-between}}.navbtn:hover,.navbtn.active{{background:#112922;color:var(--ink);border-color:#2f5d50}}main{{padding:26px;min-width:0}}.top{{display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:18px}}.pill{{background:#17382f;border:1px solid #2d5c4f;color:var(--muted);border-radius:999px;padding:8px 11px;font-size:13px}}.slide{{display:none}}.slide.active{{display:block}}.workspace{{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:18px;align-items:start}}.hero{{background:rgba(16,36,30,.85);border:1px solid #2d5c4f;border-radius:28px;padding:28px;box-shadow:0 28px 70px rgba(0,0,0,.28)}}.eyebrow{{color:var(--mint);font-size:12px;letter-spacing:.14em;text-transform:uppercase;font-weight:900}}h1{{font-size:clamp(34px,5.6vw,70px);line-height:.95;margin:8px 0 10px;letter-spacing:-.055em}}.subtitle{{color:var(--muted);font-size:18px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:22px}}.card{{background:#f8fffc;color:#10241e;border:3px solid #050b0a;border-radius:20px;padding:16px;box-shadow:7px 7px 0 #050b0a}}.card h3{{margin:0 0 8px}}.card.good{{background:#dcfff0}}.card.risk{{background:#fff2d0}}.card.missing{{background:#ffe0e0}}.q{{color:#31564c;font-weight:900;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}.a{{font-size:17px;line-height:1.42;margin-top:4px}}.answerBlock,.riskLine{{border-top:1px solid #c8ded5;padding-top:10px;margin-top:10px}}.inspector{{background:rgba(248,255,252,.97);color:#10241e;border-radius:26px;border:3px solid #050b0a;box-shadow:10px 10px 0 #050b0a;padding:18px;position:sticky;top:20px}}.voiceBox{{background:#e8fff6;border:2px solid #17382f;border-radius:16px;padding:12px;margin:12px 0}}audio{{width:100%;margin:8px 0}}.actionRow{{display:flex;gap:8px;margin-top:10px}}button.primary{{background:var(--mint);color:#06110f;border:2px solid #06110f;border-radius:14px;padding:10px 13px;font-weight:900;box-shadow:4px 4px 0 #06110f;cursor:pointer}}button.ghost{{background:#10241e;color:var(--ink);border:1px solid #2d5c4f;border-radius:14px;padding:10px 13px;cursor:pointer}}textarea,input{{width:100%;border:2px solid #17382f;border-radius:14px;padding:11px;background:#fbfffd;color:#10241e}}textarea{{min-height:155px;resize:vertical}}.actions{{padding-left:18px}}.actions li{{margin:7px 0}}.comic{{margin-top:22px;background:#fdf7df;color:#10241e;border:4px solid #050b0a;border-radius:22px;padding:14px;box-shadow:8px 8px 0 #050b0a}}.comic img,.comic svg{{width:100%;display:block;border-radius:14px;border:3px solid #06110f;background:#fff}}.comic-note{{font-size:13px;color:#36564d;margin-top:8px}}.pause{{margin-top:18px;border:2px dashed #4f8778;border-radius:18px;padding:16px;background:rgba(101,244,191,.08)}}.controls{{display:flex;justify-content:space-between;align-items:center;margin-top:18px}}.emailBox{{width:100%;min-height:300px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}}@media(max-width:980px){{.app{{grid-template-columns:1fr}}aside.nav{{position:relative;height:auto}}.workspace{{grid-template-columns:1fr}}.grid{{grid-template-columns:1fr}}.inspector{{position:relative;top:0}}}}
</style></head><body><div class='app'><aside class='nav'><div class='brand'><div class='mark'></div><div><b>Atomix Standup</b><span>{DATE} EOD review</span></div></div><div id='nav'></div></aside><main><div class='top'><div><div class='eyebrow'>Meeting website</div><div id='counter' class='subtitle'></div></div><button class='primary' onclick='downloadHtml()'>Download this site</button></div><section id='slides'></section><div class='controls'><button class='ghost' id='prev'>← Previous</button><div class='muted'>Use → through each person • notes/actions save in this browser</div><button class='primary' id='next'>Next →</button></div></main></div><script id='deck-data' type='application/json'>{payload}</script><script>
const data=JSON.parse(document.getElementById('deck-data').textContent);const slides=data.slides;let idx=Number(localStorage.getItem('atomixStandupIndex:'+data.date)||0);if(idx<0||idx>=slides.length)idx=0;const nav=document.getElementById('nav'),slidesEl=document.getElementById('slides'),counter=document.getElementById('counter');
function esc(s){{return String(s??'').replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]))}}function short(s,n=220){{s=String(s||'');return s.length>n?s.slice(0,n-1)+'…':s}}function slideKey(i,s){{return 'atomixStandup:'+data.date+':'+i+':'+s}}function key(s){{return slideKey(idx,s)}}
function card(title,body,cls=''){{return `<div class="card ${{cls}}"><h3>${{esc(title)}}</h3>${{body}}</div>`}}
function renderOverview(s){{const good=(s.good_news||[]).map(x=>`<li><b>${{esc(x.person)}}:</b> ${{esc(short(x.a,150))}}</li>`).join('');const risks=(s.risks||[]).slice(0,6).map(x=>`<li><b>${{esc(x.person)}}:</b> ${{esc(short(x.a,140))}}</li>`).join('');return `<article class="slide"><div class="workspace"><div class="hero"><div class="eyebrow">Good News First</div><h1>${{esc(s.title)}}</h1><div class="subtitle">${{esc(s.subtitle)}}</div><div class="grid">${{card('Good news',`<ul>${{good||'<li>No positive callouts detected yet.</li>'}}</ul>`,'good')}}${{card('Coverage',`<p>${{esc(s.takeaways[0])}}</p>`)}}${{card('Missing EODs',`<p>${{esc((s.missing||[]).join(', ')||'None')}}</p>`,'missing')}}${{card('Risks to listen for',`<ul>${{risks||'<li>No risks detected.</li>'}}</ul>`,'risk')}}</div></div>${{inspectorHtml('Meeting notes','Good news / opening notes')}}</div></article>`}}
function answerBy(s,terms,fallback){{const arr=s.answers||[];const hit=arr.find(a=>terms.some(t=>(a.q||'').toLowerCase().includes(t)));return hit&&!(new Set(['','n/a','na','no','none','.','nothing']).has((hit.a||'').trim().toLowerCase()))?hit.a:fallback}}
function fallbackComic(s){{if(!s.submitted)return `<div class="comic"><h3>Missing EOD comic</h3><svg viewBox="0 0 1200 360"><rect width="1200" height="360" fill="#fffef7"/><g stroke="#06110f" stroke-width="5" fill="none"><rect x="18" y="18" width="364" height="324"/><rect x="418" y="18" width="364" height="324"/><rect x="818" y="18" width="364" height="324"/></g><text x="44" y="60" font-size="25" font-weight="900">EOD BELL</text><text x="456" y="60" font-size="25" font-weight="900">TEAM WAITS</text><text x="856" y="60" font-size="25" font-weight="900">RESET</text><text x="100" y="210" font-size="80">💤</text><text x="500" y="210" font-size="80">?</text><text x="930" y="210" font-size="80">📝</text></svg><div class="comic-note">No report submitted. Capture the story live in notes/action items.</div></div>`;const first=answerBy(s,['first thing','worked on today','what did you work on'],s.notes?.[0]?.a||'Started priority work.');const fire=answerBy(s,['fire','blocker','issue'],s.risks?.[0]?.a||s.notes?.[1]?.a||'Handled the main pressure.');const last=answerBy(s,['last thing','handoff','tomorrow'],s.notes?.[2]?.a||s.notes?.[1]?.a||'Closed with a handoff.');return `<div class="comic"><h3>Daily story comic</h3><svg viewBox="0 0 1200 420"><defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#eafff5"/><stop offset="1" stop-color="#fff3c4"/></linearGradient></defs><rect width="1200" height="420" fill="#fdf7df"/><g stroke="#06110f" stroke-width="5"><rect x="18" y="18" width="364" height="384" fill="url(#g)"/><rect x="418" y="18" width="364" height="384" fill="#ffe8d6"/><rect x="818" y="18" width="364" height="384" fill="#dcfff0"/></g><g font-weight="900" fill="#06110f"><text x="44" y="58" font-size="24">FIRST TASK</text><text x="444" y="58" font-size="24">FIRE / PRESSURE</text><text x="844" y="58" font-size="24">HANDOFF</text></g><g font-size="90"><text x="135" y="220">📦</text><text x="535" y="220">🔥</text><text x="935" y="220">✅</text></g><foreignObject x="44" y="260" width="310" height="105"><div xmlns="http://www.w3.org/1999/xhtml" style="font:800 16px system-ui;line-height:1.15;background:white;border:3px solid #06110f;border-radius:16px;padding:10px">${{esc(short(first,95))}}</div></foreignObject><foreignObject x="444" y="260" width="310" height="105"><div xmlns="http://www.w3.org/1999/xhtml" style="font:800 16px system-ui;line-height:1.15;background:white;border:3px solid #06110f;border-radius:16px;padding:10px">${{esc(short(fire,95))}}</div></foreignObject><foreignObject x="844" y="260" width="310" height="105"><div xmlns="http://www.w3.org/1999/xhtml" style="font:800 16px system-ui;line-height:1.15;background:white;border:3px solid #06110f;border-radius:16px;padding:10px">${{esc(short(last,95))}}</div></foreignObject></svg><div class="comic-note">Fallback comic board. Replace with generated production art when available.</div></div>`}}
function comicHtml(s){{if(s.comic_art)return `<div class="comic"><h3>Comic strip: ${{esc(s.title)}}'s day</h3><img src="${{esc(s.comic_art)}}" alt="${{esc(s.title)}} comic strip"><div class="comic-note">Three-panel operator story: setup → problem → handoff.</div></div>`;return ''}}
function renderPerson(s){{let body='';if(!s.submitted)body=card('No EOD submitted',`<p>Use live discussion to capture blockers, support needs, and current priority.</p>`,'missing');else body=`${{s.risks.length?card('Cleo flags',s.risks.slice(0,4).map(x=>`<div class="riskLine"><div class="q">${{esc(short(x.q,90))}}</div><div class="a">${{esc(short(x.a,260))}}</div></div>`).join(''),'risk'):''}}${{card('Questions answered',(s.answers||[]).filter(x=>x.a&&!['n/a','na','no','none','.'].includes(String(x.a).trim().toLowerCase())).slice(0,8).map(x=>`<div class="answerBlock"><div class="q">${{esc(short(x.q,105))}}</div><div class="a">${{esc(short(x.a,280))}}</div></div>`).join('')||'<p>No non-empty answers.</p>')}}`;return `<article class="slide"><div class="workspace"><div class="hero"><div class="eyebrow">Person slide</div><h1>${{esc(s.title)}}</h1><div class="subtitle">${{esc(s.subtitle)}} ${{s.submitted?'• submitted '+esc(s.submitted_at):'• missing EOD'}}</div><div class="grid">${{body}}</div>${{comicHtml(s)}}<div class="pause"><b>Talk track:</b><br>${{esc(s.prompt)}}</div></div>${{inspectorHtml(s.title+' notes','Notes, corrections, owner commitments')}}</div></article>`}}
function renderClose(s){{return `<article class="slide"><div class="workspace"><div class="hero"><div class="eyebrow">Closeout</div><h1>${{esc(s.title)}}</h1><div class="subtitle">${{esc(s.subtitle)}}</div><div class="grid">${{s.takeaways.map(t=>card('Rule',`<p>${{esc(t)}}</p>`)).join('')}}</div><div class="card" style="margin-top:18px"><h3>Email-ready recap</h3><textarea class="emailBox" id="emailBox"></textarea><div class="actionRow"><button class="primary" onclick="refreshEmailBox()">Refresh recap</button><button class="ghost" onclick="copyEmailBox()">Copy recap</button></div></div></div>${{inspectorHtml('Final notes','Final decisions before sending recap')}}</div></article>`}}
function inspectorHtml(title,placeholder){{return `<aside class="inspector"><h2>${{esc(title)}}</h2><div class="voiceBox"><b>Playback</b><audio class="deckAudio" preload="metadata" controls src="${{esc(slides[idx].audio||'')}}"></audio><div class="actionRow"><button class="primary speakSlide">Play</button><button class="ghost stopSpeak">Stop</button></div></div><p class="muted">Notes and action items save in this browser.</p><textarea class="notes" placeholder="${{esc(placeholder)}}"></textarea><div class="actionRow"><input class="actionInput" placeholder="Action item: owner + due time"><button class="primary addAction">Add</button></div><ul class="actions"></ul><div class="actionRow"><button class="ghost markDone">Mark discussed</button></div></aside>`}}
function getAllActions(){{return slides.map((s,i)=>({{slide:s.title,actions:JSON.parse(localStorage.getItem(slideKey(i,'actions'))||'[]'),notes:localStorage.getItem(slideKey(i,'notes'))||''}})).filter(x=>x.actions.length||x.notes.trim())}}
function emailText(){{const lines=[`Atomix Standup Recap — ${{data.date}}`,'', 'Action Items:'];const items=getAllActions();let count=0;items.forEach(x=>x.actions.forEach(a=>{{count++;lines.push(`${{count}}. [${{x.slide}}] ${{a}}`)}}));if(!count)lines.push('- No action items captured yet.');lines.push('', 'Notes by slide:');items.forEach(x=>{{if(x.notes.trim())lines.push(`- ${{x.slide}}: ${{x.notes.trim()}}`)}});return lines.join('\\n')}}
function refreshEmailBox(){{const box=document.getElementById('emailBox');if(box)box.value=emailText()}}function copyEmailBox(){{refreshEmailBox();navigator.clipboard?.writeText(document.getElementById('emailBox').value)}}
function playAudio(){{const a=document.querySelector('.slide.active .deckAudio');if(!a)return;a.currentTime=0;const p=a.play();if(p&&p.catch)p.catch(()=>{{a.controls=true;}})}}function stopAudio(){{const a=document.querySelector('.slide.active .deckAudio');if(a){{a.pause();a.currentTime=0}}}}
function hydrateInspector(){{const notes=document.querySelector('.slide.active .notes');if(!notes)return;notes.value=localStorage.getItem(key('notes'))||'';notes.oninput=()=>localStorage.setItem(key('notes'),notes.value);const ul=document.querySelector('.slide.active .actions'),input=document.querySelector('.slide.active .actionInput'),add=document.querySelector('.slide.active .addAction'),done=document.querySelector('.slide.active .markDone'),speak=document.querySelector('.slide.active .speakSlide'),stop=document.querySelector('.slide.active .stopSpeak');if(speak)speak.onclick=playAudio;if(stop)stop.onclick=stopAudio;const render=()=>{{const arr=JSON.parse(localStorage.getItem(key('actions'))||'[]');ul.innerHTML=arr.map((a,i)=>`<li>${{esc(a)}} <button data-rm="${{i}}">×</button></li>`).join('');ul.querySelectorAll('button').forEach(b=>b.onclick=()=>{{arr.splice(Number(b.dataset.rm),1);localStorage.setItem(key('actions'),JSON.stringify(arr));render()}})}};add.onclick=()=>{{const v=input.value.trim();if(!v)return;const arr=JSON.parse(localStorage.getItem(key('actions'))||'[]');arr.push(v);localStorage.setItem(key('actions'),JSON.stringify(arr));input.value='';render()}};done.onclick=()=>{{localStorage.setItem(key('done'),'1');draw()}};render();refreshEmailBox()}}
function draw(){{slidesEl.innerHTML=slides.map(s=>s.type==='overview'?renderOverview(s):s.type==='close'?renderClose(s):renderPerson(s)).join('');nav.innerHTML=slides.map((s,i)=>`<button class="navbtn ${{i===idx?'active':''}}" data-i="${{i}}"><span>${{i+1}}. ${{esc(s.title)}}</span><span>${{localStorage.getItem(slideKey(i,'done'))?'✓':'●'}}</span></button>`).join('');document.querySelectorAll('.slide')[idx].classList.add('active');counter.textContent=`Slide ${{idx+1}} of ${{slides.length}}`;hydrateInspector();document.querySelectorAll('.navbtn').forEach(b=>b.onclick=()=>go(Number(b.dataset.i)))}}
function go(i){{stopAudio();idx=Math.max(0,Math.min(slides.length-1,i));localStorage.setItem('atomixStandupIndex:'+data.date,idx);draw()}}function downloadHtml(){{const a=document.createElement('a');a.href=location.href;a.download=`atomix-standup-${{data.date}}.html`;a.click()}}
document.getElementById('prev').onclick=()=>go(idx-1);document.getElementById('next').onclick=()=>go(idx+1);window.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')go(idx+1);if(e.key==='ArrowLeft')go(idx-1)}});draw();
</script></body></html>"""
OUT.write_text(html_doc)
legacy=ROOT / f'cleo-standup-deck-{DATE}.html'
legacy.write_text(html_doc)
print(json.dumps({'out':str(OUT),'legacy_out':str(legacy),'slides':len(slides),'people':len(people),'submitted':len(submitted),'missing':[p['name'] for p in missing]},indent=2))
