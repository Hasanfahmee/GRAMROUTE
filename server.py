"""GRAMROUTE prototype: stdlib-only offline server (http.server + sqlite3). All data is SIMULATED."""
import re, sqlite3, json, heapq, math, os, random, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
DB = os.environ.get("GR_DB", "gramroute.db")
C = None
def q(sql, a=(), one=False):
    cur = C.execute(sql, a); C.commit()
    rows = [dict(r) for r in cur.fetchall()]
    return (rows[0] if rows else None) if one else rows
def audit(ev, d=""): q("insert into audit(ts,event,detail) values(?,?,?)", (time.strftime("%H:%M:%S"), ev, d))
def init(reset=False):
    global C
    if reset and C: C.close()
    if reset and os.path.exists(DB) and DB != ":memory:": os.remove(DB)
    C = sqlite3.connect(DB, check_same_thread=False); C.row_factory = sqlite3.Row
    C.executescript("""pragma foreign_keys=on;
    create table if not exists vehicles(id text primary key,kind text,cap int check(cap>0),base text,status text,verified int,cost int,simulated int default 1);
    create table if not exists students(id integer primary key,name text,village text,priority text default 'none',exam_mins int,simulated int default 1);
    create table if not exists assign(student int primary key references students(id),vehicle text references vehicles(id),ref text);
    create table if not exists edges(a text,b text,km real,mins real,blocked int default 0,why text,primary key(a,b));
    create table if not exists reports(id integer primary key,kind text,detail text,ts text);
    create table if not exists history(day int,demand int);
    create table if not exists audit(id integer primary key,ts text,event text,detail text);
    create table if not exists sched(vid text primary key,dep text);
    create index if not exists ix_a on assign(vehicle);""")
    if not q("select 1 from vehicles limit 1"): seed()
def seed():
    V = [("B1","govt bus",40,"Kalpur"),("B2","govt bus",36,"Mudhol"),("B3","private bus",30,"Hosagram"),("A1","shared auto",3,"Kalpur"),("A2","shared auto",3,"Mudhol"),
         ("VN1","private van",12,"Hosagram"),("VN2","community van",8,"Kalpur")]
    for i,k,c,b in V: q("insert into vehicles values(?,?,?,?,'available',1,?,1)",(i,k,c,b,{"govt bus":20,"private bus":30}.get(k,50)))
    for a,b,km,m,bl,w in [("Kalpur","Junction",6,12,0,""),("Junction","College",8,15,0,""),("Mudhol","Junction",5,10,0,""),
        ("Kalpur","Mudhol",9,20,0,""),("Mudhol","College",14,30,0,""),("Hosagram","Junction",7,14,0,""),("Hosagram","College",15,32,0,""),
        ("Mudhol","Hosagram",6,15,1,"SIMULATED: culvert washed out (pre-existing disruption)")]:
        q("insert into edges values(?,?,?,?,?,?)",(a,b,km,m,bl,w)); q("insert into edges values(?,?,?,?,?,?)",(b,a,km,m,bl,w))
    n=0
    for v,cnt,veh in [("Kalpur",40,"B1"),("Mudhol",20,"B2"),("Hosagram",6,"VN1")]:
        for _ in range(cnt):
            n+=1; q("insert into students(id,name,village,priority,exam_mins) values(?,?,?,?,?)",(n,f"Student {n}",v,"exam" if n%3==0 else "access" if n%23==0 else "none",40+(n*7)%80 if n%3==0 else None))
            q("insert into assign values(?,?,?)",(n,veh,f"GR{n:04d}"))
    for k,v in {"B1":"07:15","B2":"07:30","B3":"07:45","A1":"07:20","A2":"07:25","VN1":"07:40","VN2":"07:35"}.items(): q("insert into sched values(?,?)",(k,v))
    for d in range(28): q("insert into history values(?,?)",(d,50+(12 if d%7 in(0,1) else 0)+random.Random(d).randint(-4,4)))
def addmin(h,m): t=int(h[:2])*60+int(h[3:])+int(m); return f"{t//60%24:02d}:{t%60:02d}"
def dep(vid): r=q("select dep from sched where vid=?",(vid,),True); return r["dep"] if r else "07:30"
def free(vid):
    v=q("select cap from vehicles where id=?",(vid,),True)
    return v["cap"]-q("select count(*) n from assign where vehicle=?",(vid,),True)["n"]
def route(a,b,avoid_blocked=True,skip=()):
    g={}
    for e in q("select * from edges"+(" where blocked=0" if avoid_blocked else "")): g.setdefault(e["a"],[]).append(e)
    pq=[(0,0,a,[a])]; seen=set()
    while pq:
        m,km,u,p=heapq.heappop(pq)
        if u==b: return {"path":p,"mins":m,"km":km,"verified":False,"note":"Computed on local graph; not a guaranteed-safe route."}
        if u in seen: continue
        seen.add(u)
        for e in g.get(u,[]):
            if {e["a"],e["b"]}!=set(skip): heapq.heappush(pq,(m+e["mins"],km+e["km"],e["b"],p+[e["b"]]))
    return None
def usable(vid,village):
    v=q("select * from vehicles where id=?",(vid,),True)
    return v["status"]=="available" and v["verified"] and route(v["base"],village) and route(village,"College")
def rescue(vid):
    """Bus Rescue: reassign students of vid to other available verified vehicles within capacity."""
    q("update vehicles set status='cancelled' where id=?",(vid,))
    aff=q("select s.* from students s join assign a on a.student=s.id where a.vehicle=?",(vid,))
    q("delete from assign where vehicle=?",(vid,))
    aff.sort(key=lambda s:({"exam":0,"access":1}.get(s["priority"],2),s["village"])); used={}
    for s in aff:
        for v in sorted(q("select * from vehicles where id!=?",(vid,)),key=lambda v:(-free(v["id"]),v["cost"])):
            if free(v["id"])>0 and usable(v["id"],s["village"]):
                q("insert into assign values(?,?,?)",(s["id"],v["id"],f"GR{s['id']:04d}R")); used[v["id"]]=used.get(v["id"],0)+1; break
    waiting=len(aff)-sum(used.values())
    out={"vehicle":vid,"affected":len(aff),"accommodated":sum(used.values()),"waiting":waiting,"deployed":used,
         "remaining_seats":{v["id"]:free(v["id"]) for v in q("select id from vehicles where status='available'")},
         "suggest":f"Add {math.ceil(waiting/12)} van(s) of 12 seats" if waiting else "None needed"}
    q("insert into reports(kind,detail,ts) values('bus_cancellation',?,?)",(vid,time.strftime("%H:%M")))
    audit("bus_rescue",json.dumps(out)); return out
def road_close(a,b,why="SIMULATED closure"):
    q("update edges set blocked=1,why=? where (a=? and b=?) or (a=? and b=?)",(why,a,b,b,a))
    res={v:route(v,"College") for v in ["Kalpur","Mudhol","Hosagram"]}
    q("insert into reports(kind,detail,ts) values('road_closure',?,?)",(f"{a}-{b}",time.strftime("%H:%M")))
    audit("road_closure",f"{a}-{b}"); return {"closed":[a,b],"routes":res,"uses_closed":any(r and any({p[i],p[i+1]}=={a,b} for i in range(len(p)-1)) for r in res.values() for p in [r["path"]])}
def capacity(extra=0):
    """Capacity engine: recompute allocation from scratch with transparent priority (exam>access>none, then village)."""
    n0=q("select max(id) m from students",one=True)["m"]
    for i in range(extra): q("insert into students(id,name,village,priority) values(?,?,?,?)",(n0+i+1,f"Surge {i+1}",["Kalpur","Mudhol","Hosagram"][i%3],"none"))
    q("delete from assign")
    vs=[v for v in q("select * from vehicles where status='available' and verified=1")]
    st=q("select * from students"); st.sort(key=lambda s:({"exam":0,"access":1}.get(s["priority"],2),s["village"],s["id"])); ok=0
    for s in st:
        for v in sorted(vs,key=lambda v:(v["base"]!=s["village"],v["cost"])):
            if free(v["id"])>0 and usable(v["id"],s["village"]): q("insert into assign values(?,?,?)",(s["id"],v["id"],f"GR{s['id']:04d}")); ok+=1; break
    cap=sum(v["cap"] for v in vs); un=len(st)-ok
    out={"demand":len(st),"capacity":cap,"allocated":ok,"unallocated":un,"shortage":max(0,len(st)-cap),"recommend":f"{math.ceil(un/12)} extra 12-seat van(s) or {math.ceil(un/36)} extra bus(es)" if un else "None"}
    audit("capacity",json.dumps(out)); return out
def forecast():
    h=[r["demand"] for r in q("select * from history order by day")]; wk=[sum(h[i::7])/len(h[i::7]) for i in range(7)]
    cap=sum(v["cap"] for v in q("select * from vehicles where status='available'"))
    return {"label":"ILLUSTRATIVE model: weekday mean of SEEDED demo history, not real observations","weekday_mean":[round(x) for x in wk],"capacity":cap,"shortage_days":[i for i,x in enumerate(wk) if x>cap]}
def book(village):
    for v in q("select * from vehicles where status='available' and verified=1"):
        if free(v["id"])>0 and usable(v["id"],village):
            sid=q("select max(id) m from students",one=True)["m"]+1
            q("insert into students(id,name,village) values(?,?,?)",(sid,f"Kiosk student {sid}",village)); ref=f"GR{sid:04d}"
            q("insert into assign values(?,?,?)",(sid,v["id"],ref)); audit("booking",ref); return {"ref":ref,"vehicle":v["id"],"free_after":free(v["id"])}
    return {"error":"No seats available; request logged","ref":None}
SAY={"en":{"seats":"{n} seats are free across {v} vehicles.","route":"Best route to college from {a}: {p}, about {m} minutes. Estimated, not verified safe.","rep":"Your report is saved.","book":"Seat reserved. Reference {r}, on vehicle {v}.","nobook":"Sorry, no seat is available right now.","unk":"Sorry, I did not understand. Try: how many seats, is there another route, my bus has not arrived, or book a seat."},
"hi":{"seats":"{n} सीटें खाली हैं।","route":"{a} से कॉलेज का रास्ता: {p}, लगभग {m} मिनट।","rep":"आपकी शिकायत दर्ज हो गई।","book":"सीट आरक्षित। संदर्भ {r}, वाहन {v}।","nobook":"क्षमा करें, अभी कोई सीट उपलब्ध नहीं।","unk":"क्षमा करें, समझ नहीं आया।"},
"kn":{"seats":"{n} ಆಸನಗಳು ಖಾಲಿ ಇವೆ.","route":"{a} ಇಂದ ಕಾಲೇಜಿಗೆ ಮಾರ್ಗ: {p}, ಸುಮಾರು {m} ನಿಮಿಷ.","rep":"ನಿಮ್ಮ ವರದಿ ದಾಖಲಾಗಿದೆ.","book":"ಆಸನ ಕಾಯ್ದಿರಿಸಲಾಗಿದೆ. ಉಲ್ಲೇಖ {r}.","nobook":"ಕ್ಷಮಿಸಿ, ಆಸನ ಲಭ್ಯವಿಲ್ಲ.","unk":"ಕ್ಷಮಿಸಿ, ಅರ್ಥವಾಗಲಿಲ್ಲ."}}
def intent(text,lang="en"):
    """Keyword intent matcher (not an LLM) -> calls real engines/DB, returns text to speak."""
    t=text.lower(); M=SAY.get(lang,SAY["en"]); f=lambda k:M.get(k,SAY["en"][k])
    vil=next((v for v in ["Kalpur","Mudhol","Hosagram"] if v.lower() in t),"Kalpur")
    K=[("exam",["exam","परीक्षा","ಪರೀಕ್ಷೆ","தேர்வு","పరీక్ష","പരീക്ഷ","পরীক্ষা","પરીક્ષા","ਪ੍ਰੀਖਿਆ","امتحان"]),("waiting",["waiting","stranded","how many students"]),("book",["book","reserve","बुक","आरक्षित","ಬುಕ್","ಕಾಯ್ದಿರಿಸ","புக்","బుక్","ബുക്ക്","বুক","બુક","ਬੁੱਕ","بک"]),("seats",["seat","सीट","ಆಸನ","இருக்கை","సీటు","സീറ്റ്","আসন","બેઠક","ਸੀਟ","سیٹ"]),("route",["route","road","way","रास्ता","मार्ग","ಮಾರ್ಗ","ರಸ್ತೆ","பாதை","దారి","വഴി","রাস্তা","રસ્તો","ਰਸਤਾ","راستہ"]),
       ("report",["not arrived","not come","cancel","breakdown","broke","late","नहीं आई","नहीं आयी","खराब","ಬಂದಿಲ್ಲ","ಬಸ್"])]
    for k,ws in K:
        if any(w in t for w in ws):
            if k=="waiting":
                w=q("select count(*) n from students where id not in (select student from assign)",one=True)["n"]; return {"intent":k,"answer":w,"say":f"{w} students currently have no seat."}
            if k=="exam":
                m=re.search(r"(\d+)",t); mins=int(m.group(1))*(60 if "hour" in t else 1) if m else 90; rt=route(vil,"College"); need=round(rt["mins"]) if rt else None
                r=request_ride({"name":"Exam student","village":vil,"seats":1,"problem":"normal"}); ok=need is not None and need<=mins
                sy=f"Exam in {mins} minutes. Travel from {vil} takes about {need} minutes, so "+("you can make it. " if ok else "you are at risk; ask the operator for express transport. ")+(f"Seat reserved, reference {r['ref']}." if r.get("allocated") else "No seat is available right now.")
                return {"intent":k,"answer":r,"say":sy}
            if k=="seats":
                av=[v for v in q("select id from vehicles where status='available'")]; n=sum(free(v["id"]) for v in av)
                return {"intent":k,"answer":{v["id"]:free(v["id"]) for v in av},"say":f("seats").format(n=n,v=len(av))}
            if k=="route":
                r=route(vil,"College"); return {"intent":k,"answer":r,"say":f("route").format(a=vil,p=" → ".join(r["path"]),m=round(r["mins"])) if r else "No open route."}
            if k=="book":
                r=request_ride({"name":"Voice request","village":vil,"seats":1,"problem":"normal"})
                return {"intent":k,"answer":r,"say":f("book").format(r=r["ref"],v=r["vehicles"][0]["id"]) if r.get("allocated") else f("nobook")}
            q("insert into reports(kind,detail,ts) values('voice_report',?,?)",(text[:200],time.strftime("%H:%M"))); audit("voice_report",text[:80])
            return {"intent":k,"answer":"Report stored","say":f("rep")}
    return {"intent":"unknown","answer":None,"say":f("unk")}
def state():
    vs=q("select * from vehicles")
    for v in vs: v["free"]=free(v["id"])
    return {"vehicles":vs,"students":q("select count(*) n from students",one=True)["n"],"waiting":q("select count(*) n from students where id not in (select student from assign)",one=True)["n"],
        "edges":[e for e in q("select * from edges") if e["a"]<e["b"]],"reports":q("select * from reports order by id desc limit 10"),"audit":q("select * from audit order by id desc limit 8"),"forecast":forecast(),"note":"ALL DATA SIMULATED"}
def request_ride(d):
    """Kiosk request: allocate up to N seats on verified, available vehicles (capacity-checked, reachability via open graph, avoiding reported road)."""
    q("create table if not exists jr(ref text primary key,name text,village text,problem text,seats int,allocated int,status text,detail text)")
    v0=d.get("village","Kalpur"); n=max(1,min(int(d.get("seats",1)),10)); pr=d.get("problem","normal")
    skip=tuple(d.get("road") or ()) if pr=="road" else (); excl=d.get("bus") if pr=="bus" else None
    if v0 not in ("Kalpur","Mudhol","Hosagram"): return {"error":"Unknown village"}
    got={}; ids=[]
    for i in range(n):
        sid=q("select max(id) m from students",one=True)["m"]+1; ids.append(sid)
        q("insert into students(id,name,village) values(?,?,?)",(sid,(d.get("name") or "Student")[:40]+("" if i==0 else f" (+{i})"),v0))
        for v in sorted(q("select * from vehicles where status='available' and verified=1"),key=lambda v:v["cost"]):
            if v["id"]!=excl and free(v["id"])>0 and route(v["base"],v0,skip=skip) and route(v0,"College",skip=skip):
                q("insert into assign values(?,?,?)",(sid,v["id"],f"GR{ids[0]:04d}")); got[v["id"]]=got.get(v["id"],0)+1; break
    al=sum(got.values()); ref=f"GR{ids[0]:04d}"; rt=route(v0,"College",skip=skip)
    st="BOOKED" if al else "NO VEHICLE AVAILABLE"
    warn=["Recommendation only: operator confirmation is not implemented in this prototype.","Estimated route, not verified safe.","Departure time is not scheduled in demo data."]
    if al<n: warn.insert(0,f"Only {al} of {n} seats found; {n-al} still waiting.")
    if pr=="road":
        q("insert into reports(kind,detail,ts) values('road_blocked_UNVERIFIED',?,?)",("-".join(skip),time.strftime("%H:%M")))
    vk={v["id"]:v["kind"] for v in q("select id,kind from vehicles")}
    b2=[{"vehicle":v["id"],"dep":addmin(dep(v["id"]),round(2*(rt["mins"] if rt else 60)))} for v in q("select id from vehicles where status='available' and verified=1")][:2] if al<n else []
    out={"ref":ref,"status":st,"requested":n,"allocated":al,"waiting":n-al,"vehicles":[{"id":k,"kind":vk[k],"seats":c,"pickup":v0,"dep":dep(k),"arrive":addmin(dep(k),rt["mins"]) if rt else None} for k,c in got.items()],"route":rt,"warnings":[],"batch2":b2}
    q("insert into jr values(?,?,?,?,?,?,?,?)",(ref,d.get("name","")[:40],v0,pr,n,al,st,json.dumps(out))); audit("kiosk_request",ref); return out
def track(ref):
    q("create table if not exists jr(ref text primary key,name text,village text,problem text,seats int,allocated int,status text,detail text)")
    r=q("select * from jr where ref=?",(ref.strip().upper(),),True); return json.loads(r["detail"]) if r else {"error":"Reference not found"}
def exam_crisis(pct=40):
    """Surprise hurdle: 2 govt buses down + demand +pct% + flood closes Junction-College + exams within 2h. Exam students first (earliest deadline), capacity-checked."""
    init(True); VL=["Kalpur","Mudhol","Hosagram"]; base=q("select count(*) n from students",one=True)["n"]; t0=time.strftime("%H:%M")
    lost={b:q("select count(*) n from assign where vehicle=?",(b,),True)["n"] for b in("B1","B2")}
    for b in lost: q("update vehicles set status='cancelled' where id=?",(b,)); q("insert into reports(kind,detail,ts) values('bus_breakdown',?,?)",(b,t0))
    q("delete from assign"); q("update edges set blocked=1,why='Flooding (reported)' where (a='Junction' and b='College') or (a='College' and b='Junction')")
    q("insert into reports(kind,detail,ts) values('flood_road_closure','Junction-College',?)",(t0,))
    extra=math.ceil(base*pct/100)
    for i in range(extra): q("insert into students(id,name,village,priority,exam_mins) values(?,?,?,?,?)",(base+i+1,f"Surge {i+1}",VL[i%3],"exam" if i%2==0 else "none",45+(i*11)%75 if i%2==0 else None))
    vs=q("select * from vehicles where status='available' and verified=1"); st=q("select * from students")
    st.sort(key=lambda s:(0 if s["priority"]=="exam" else 1 if s["priority"]=="access" else 2,s["exam_mins"] or 999,s["village"],s["id"]))
    mins={v:(route(v,"College") or {}).get("mins") for v in VL}; used={}; un=[]
    for s in st:
        ok=False
        if mins[s["village"]] is not None:
            for v in sorted(vs,key=lambda v:(v["base"]!=s["village"],v["cost"])):
                if free(v["id"])>0 and route(v["base"],s["village"]):
                    q("insert into assign values(?,?,?)",(s["id"],v["id"],f"GR{s['id']:04d}")); used.setdefault(v["id"],[]).append(s); ok=True; break
        if not ok: un.append(s)
    seated={s["id"] for l in used.values() for s in l}; ex=[s for s in st if s["priority"]=="exam"]
    ont=[s for s in ex if s["id"] in seated and mins[s["village"]] is not None and mins[s["village"]]<=s["exam_mins"]]
    risk=[s for s in ex if s not in ont]; cap=sum(v["cap"] for v in vs); ubv={v:sum(1 for s in un if s["village"]==v) for v in VL}
    slow=max(m for m in mins.values() if m); t2=addmin(max(dep(v['id']) for v in vs),round(2*slow)); s2=min(len(un),cap)
    out={"scenario":{"buses_down":lost,"base_students":base,"surge_added":extra,"flood":"Junction–College road closed (reported)","time":t0},
     "demand":len(st),"capacity":cap,"seated":len(seated),"unallocated":len(un),"without_system":sum(lost.values())+extra,
     "exam_total":len(ex),"exam_seated":sum(1 for s in ex if s["id"] in seated),"exam_on_time":len(ont),
     "at_risk":[{"village":s["village"],"exam_in_min":s["exam_mins"],"travel_min":mins[s["village"]],"seated":s["id"] in seated,"late_by":round(mins[s["village"]]-s["exam_mins"]) if mins[s["village"]] else None} for s in risk][:8],
     "vehicles":[{"id":v["id"],"kind":v["kind"],"cap":v["cap"],"seated":len(used.get(v["id"],[])),"exam":sum(1 for s in used.get(v["id"],[]) if s["priority"]=="exam")} for v in vs],
     "second_batch":{"time":t2,"seated":s2},"travel_min":{k:(round(m) if m else None) for k,m in mins.items()},"unallocated_by_village":ubv,
     "recommend":[(f"Second batch departs {t2}: {s2} more students seated, so {len(seated)+s2} of {len(st)} are transported" + (f"; {len(un)-s2} still need {math.ceil((len(un)-s2)/12)} extra van(s)" if len(un)>s2 else "")) if un else "All students seated in the first wave",
        f"Exam centre notified: {len(risk)} student(s) arrive up to {max((round(mins[s['village']]-s['exam_mins']) for s in risk if mins[s['village']]),default=0)} min late (flood detour)" if risk else "All exam students arrive on time"],
     "explain":["Cancelled B1 and B2, released their seats, and closed the flooded road in the routing graph.",f"Added {extra} students (+{pct}% demand).","Seated exam students first by earliest exam time, then accessibility needs, then others.","Every vehicle checked for capacity and reachability on the open road graph; travel times are estimates."]}
    audit("exam_crisis",json.dumps({k:out[k] for k in("demand","capacity","seated","unallocated")})); return out
def page():
    b=os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(b,"static","kiosk.html"),os.path.join(b,"kiosk.html")):
        if os.path.exists(p): return open(p,"rb").read()
    return b"kiosk.html not found: upload it next to server.py"
class H(BaseHTTPRequestHandler):
    def reply(s,o,ct="application/json"):
        b=o if isinstance(o,bytes) else json.dumps(o).encode(); s.send_response(200); s.send_header("Content-Type",ct); s.end_headers(); s.wfile.write(b)
    def do_GET(s):
        p=s.path.split("?")[0]
        if p in("/","/demo"): return s.reply(page(),"text/html; charset=utf-8")
        if p=="/api/track": return s.reply(track(s.path.split("ref=")[1]))
        if p=="/api/state": return s.reply(state())
        if p=="/api/route": a,b=s.path.split("?")[1].split("&"); return s.reply(route(a.split("=")[1],b.split("=")[1]))
        s.send_error(404)
    def do_POST(s):
        p=s.path; d=json.loads(s.rfile.read(int(s.headers.get("Content-Length",0))) or b"{}")
        try:
            r={"/api/sim/exam":lambda:exam_crisis(),"/api/sim/bus":lambda:rescue("B1"),"/api/sim/road":lambda:road_close("Junction","College"),"/api/sim/surge":lambda:capacity(80),
               "/api/reset":lambda:(init(True),{"ok":1})[1],"/api/request":lambda:request_ride(d),"/api/book":lambda:book(d["village"]),"/api/report":lambda:intent(d["text"],d.get("lang","en")),"/api/intent":lambda:intent(d["text"],d.get("lang","en"))}[p]()
            s.reply(r)
        except Exception as e: s.reply({"error":str(e)})
    def log_message(s,*a): pass
if __name__=="__main__":
    init(); print("GRAMROUTE on http://localhost:8000 (offline, stdlib only)"); ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT",8000))),H).serve_forever()
