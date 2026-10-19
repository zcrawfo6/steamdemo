"""
build_dashboard.py  --  builds the Steam "Taste Forge" demo dashboard.

Put this file inside your dtsc36 folder, then run it from VS Code
(Run Python File, or Ctrl+Shift+B once the task exists) or a terminal:

    python build_dashboard.py            # build, then open in your browser
    python build_dashboard.py --serve    # build, then serve at http://localhost:8000
    python build_dashboard.py --no-open  # build only

Output: steam-dashboard/index.html  (next to this script)
"""
import argparse
import http.server
import json
import socketserver
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # the dtsc36 folder
OUT_DIR = ROOT / "steam-dashboard"
OUT_FILE = OUT_DIR / "index.html"

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Taste Forge - Steam Category Tracker</title>
<style>
:root{--bg:#0e141b;--panel:#16202b;--panel2:#1c2937;--line:#2a3b4d;--text:#e6edf3;--mute:#8fa3b8;--accent:#66c0f4;--accent2:#c6ff4d;--hot:#ff6b81;--warn:#ffb84d}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 600px at 80% -10%,#1b3350 0,transparent 60%),var(--bg);color:var(--text);font:15px/1.45 system-ui,Segoe UI,Roboto,sans-serif}
header{padding:22px 28px 8px;display:flex;flex-wrap:wrap;gap:12px;align-items:end;justify-content:space-between}
h1{margin:0;font-size:26px;letter-spacing:.5px}
h1 span{color:var(--accent2)}
.sub{color:var(--mute);font-size:13px;max-width:640px}
main{display:grid;grid-template-columns:340px 1fr;gap:18px;padding:14px 28px 40px}
@media(max-width:900px){main{grid-template-columns:1fr;padding:12px 16px 40px}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
.card h2{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:1.5px;color:var(--mute)}
input[type=text],select{width:100%;background:var(--panel2);border:1px solid var(--line);color:var(--text);padding:9px 11px;border-radius:9px;font:inherit}
button{background:var(--panel2);border:1px solid var(--line);color:var(--text);padding:8px 12px;border-radius:9px;cursor:pointer;font:inherit}
button:hover{border-color:var(--accent)}
button.pri{background:var(--accent);color:#06121c;border-color:var(--accent);font-weight:600}
.list{max-height:300px;overflow:auto;margin-top:8px;display:flex;flex-direction:column;gap:5px}
.row{display:flex;align-items:center;gap:8px;padding:7px 9px;background:var(--panel2);border-radius:9px;border:1px solid transparent}
.row.on{border-color:var(--accent2)}
.row .n{flex:1;min-width:0}
.row .n b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600;font-size:14px}
.row .n small{color:var(--mute);font-size:11.5px}
.row input[type=number]{width:62px;background:#0e141b;border:1px solid var(--line);color:var(--text);border-radius:7px;padding:4px 6px}
.chip{display:inline-block;padding:3px 9px;border-radius:99px;font-size:12px;background:var(--panel2);border:1px solid var(--line);margin:2px 3px 2px 0;cursor:default}
.chip.sel{background:var(--accent2);color:#10200a;border-color:var(--accent2);cursor:pointer}
.chip.pick{cursor:pointer}.chip.pick:hover{border-color:var(--accent)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.tab{padding:8px 14px;border-radius:99px;background:var(--panel);border:1px solid var(--line);cursor:pointer;color:var(--mute)}
.tab.on{background:var(--accent);color:#06121c;border-color:var(--accent);font-weight:700}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:1100px){.grid2{grid-template-columns:1fr}}
.bar{height:9px;border-radius:5px;background:var(--panel2);overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.rec{display:grid;grid-template-columns:54px 1fr auto;gap:12px;align-items:center;padding:12px;background:var(--panel2);border-radius:12px;margin-bottom:9px}
.match{width:54px;height:54px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:15px;color:#0a1119}
.rec h3{margin:0;font-size:16px}
.why{color:var(--mute);font-size:13px}
.price{font-weight:700;color:var(--accent2);white-space:nowrap}
.ctl{display:grid;grid-template-columns:130px 1fr 46px;gap:8px;align-items:center;margin:6px 0;font-size:13px}
input[type=range]{width:100%;accent-color:var(--accent)}
.empty{color:var(--mute);padding:28px;text-align:center;border:1px dashed var(--line);border-radius:12px}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.kpi div{flex:1;min-width:120px;background:var(--panel2);padding:10px 12px;border-radius:10px}
.kpi b{display:block;font-size:22px;color:var(--accent2)}
.kpi span{font-size:12px;color:var(--mute)}
.note{font-size:12px;color:var(--mute);margin-top:12px}
svg text{fill:var(--text);font-size:11px}
.catcard{background:var(--panel2);border-radius:12px;padding:12px;margin-bottom:10px;border-left:4px solid var(--accent2)}
.catcard h3{margin:0 0 4px}
.x{float:right;cursor:pointer;color:var(--mute)}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--mute);font-weight:600;font-size:12px}
</style>
</head>
<body>
<header>
  <div>
    <h1>TASTE<span>FORGE</span></h1>
    <div class="sub">Pick games you've played, and the app builds your Player Profile from genre and price habits, lets you forge your own custom categories, then recommends what to play next.</div>
  </div>
  <div class="sub" style="text-align:right">Demo build &middot; sample dataset of 38 Steam games<br>(ratings, owners and prices are rounded and illustrative)</div>
</header>

<main>
  <aside class="card">
    <h2>1 &middot; Your played games</h2>
    <input type="text" id="search" placeholder="Search games or genres...">
    <div style="display:flex;gap:6px;margin-top:8px">
      <button id="demoBtn" class="pri" style="flex:1">Load demo profile</button>
      <button id="clearBtn">Clear</button>
    </div>
    <div class="list" id="gameList"></div>
    <div class="note">Tick a game and enter your hours played. In the real app this list would come from the Steam Web API (<code>GetOwnedGames</code>) after a Steam login.</div>
  </aside>

  <section>
    <div class="tabs" id="tabs"></div>
    <div id="view"></div>
  </section>
</main>

<script>
/* ---------- SAMPLE DATA (illustrative) ---------- */
const G=[
["Counter-Strike 2",["FPS","Multiplayer","Competitive"],0,86,50],
["Dota 2",["MOBA","Strategy","Competitive","Multiplayer"],0,82,40],
["Apex Legends",["FPS","Battle Royale","Multiplayer"],0,77,30],
["Elden Ring",["RPG","Soulslike","Open World","Action"],59.99,92,20],
["Dark Souls III",["Soulslike","RPG","Action"],59.99,93,9],
["Sekiro",["Soulslike","Action"],59.99,94,5],
["Stardew Valley",["Farming","Cozy","RPG","Indie"],14.99,98,25],
["Hades",["Roguelike","Action","Indie"],24.99,98,8],
["Baldur's Gate 3",["RPG","Strategy","Narrative"],59.99,96,15],
["Terraria",["Sandbox","Survival","Indie"],9.99,97,40],
["Portal 2",["Puzzle","Adventure"],9.99,98,15],
["Civilization VI",["Strategy","4X"],59.99,82,15],
["Hollow Knight",["Metroidvania","Indie","Action"],14.99,97,12],
["Slay the Spire",["Roguelike","Card","Strategy","Indie"],24.99,97,5],
["Balatro",["Roguelike","Card","Indie"],14.99,98,5],
["Valheim",["Survival","Co-op","Open World"],19.99,92,12],
["Cyberpunk 2077",["RPG","Open World","Action","Narrative"],59.99,86,25],
["The Witcher 3",["RPG","Open World","Narrative"],39.99,96,30],
["Factorio",["Automation","Strategy","Sandbox"],35,97,4],
["Satisfactory",["Automation","Open World","Co-op","Sandbox"],39.99,97,4],
["Celeste",["Platformer","Indie"],19.99,97,4],
["Cuphead",["Platformer","Action","Indie"],19.99,95,8],
["Disco Elysium",["RPG","Narrative","Indie"],39.99,97,3],
["Dave the Diver",["Adventure","Cozy","Indie"],19.99,96,3],
["Palworld",["Survival","Open World","Co-op"],29.99,90,20],
["Lethal Company",["Horror","Co-op","Indie"],9.99,97,10],
["Phasmophobia",["Horror","Co-op"],13.99,95,8],
["Left 4 Dead 2",["FPS","Co-op","Horror"],9.99,97,15],
["Doom Eternal",["FPS","Action"],39.99,91,5],
["Euro Truck Simulator 2",["Simulation","Cozy"],19.99,97,8],
["Cities: Skylines",["Simulation","Strategy","Sandbox"],29.99,87,8],
["Kerbal Space Program",["Simulation","Sandbox"],39.99,90,5],
["Among Us",["Social","Multiplayer","Indie"],4.99,87,10],
["Vampire Survivors",["Roguelike","Action","Indie"],4.99,98,5],
["Slime Rancher",["Cozy","Simulation","Adventure"],19.99,96,3],
["Undertale",["RPG","Indie","Narrative"],9.99,97,4],
["Subnautica",["Survival","Adventure","Open World"],29.99,96,8],
["Red Dead Redemption 2",["Open World","Action","Narrative"],59.99,93,12]
].map((g,i)=>({id:i,name:g[0],genres:g[1],price:g[2],rating:g[3],owners:g[4]}));
const ALL_GENRES=[...new Set(G.flatMap(g=>g.genres))].sort();
const DEMO=[["Stardew Valley",120],["Terraria",90],["Hades",60],["Slay the Spire",75],["Balatro",40],["Hollow Knight",35],["Valheim",50],["Portal 2",12],["Vampire Survivors",20],["Dave the Diver",18]];

/* ---------- STATE ---------- */
const S={played:{},tab:"dna",q:"",wGenre:70,budget:60,focus:"",cats:[{name:"Cozy Grind",genres:["Cozy","Farming","Simulation"]}],draft:[]};
const fmt=p=>p===0?"Free":"$"+p.toFixed(2);
const col=v=>`hsl(${Math.round(v*120)},80%,60%)`;

/* ---------- PROFILE MATH ---------- */
function profile(){
  const ids=Object.keys(S.played).filter(k=>S.played[k]>0);
  let tot=0;const aff={};let wp=0;
  ids.forEach(k=>{const g=G[k],h=S.played[k];tot+=h;wp+=Math.log(1+g.price)*h;g.genres.forEach(x=>aff[x]=(aff[x]||0)+h/g.genres.length)});
  Object.keys(aff).forEach(x=>aff[x]/=tot||1);
  const lp=tot?wp/tot:0;
  return{ids,tot,aff,lp,avgPrice:Math.exp(lp)-1};
}
function recommend(P){
  const maxA=Math.max(...Object.values(P.aff),0.0001);
  let pool=G.filter(g=>!(S.played[g.id]>0)&&g.price<=S.budget);
  if(S.focus){const c=S.cats.find(c=>c.name===S.focus);if(c)pool=pool.filter(g=>g.genres.some(x=>c.genres.includes(x)))}
  const wG=S.wGenre/100,wP=1-wG;
  return pool.map(g=>{
    const gm=g.genres.reduce((s,x)=>s+(P.aff[x]||0),0)/g.genres.length/maxA;
    const d=Math.log(1+g.price)-P.lp;const pm=Math.exp(-(d*d)/(2*1.1*1.1));
    const q=(g.rating-70)/30;
    const score=Math.max(0,Math.min(1,(wG*gm+wP*pm)*0.9+q*0.1));
    const best=g.genres.slice().sort((a,b)=>(P.aff[b]||0)-(P.aff[a]||0))[0];
    return{g,score,gm,pm,best};
  }).sort((a,b)=>b.score-a.score);
}

/* ---------- LEFT LIST ---------- */
function renderList(){
  const q=S.q.toLowerCase();
  const el=document.getElementById("gameList");
  el.innerHTML=G.filter(g=>!q||g.name.toLowerCase().includes(q)||g.genres.join(" ").toLowerCase().includes(q)).map(g=>{
    const on=g.id in S.played;
    return `<div class="row ${on?"on":""}"><input type="checkbox" data-id="${g.id}" ${on?"checked":""}>
      <div class="n"><b>${g.name}</b><small>${g.genres.join(" · ")} · ${fmt(g.price)}</small></div>
      ${on?`<input type="number" min="1" max="9999" value="${S.played[g.id]}" data-h="${g.id}" title="hours played">`:""}</div>`}).join("");
  el.querySelectorAll("input[type=checkbox]").forEach(c=>c.onchange=()=>{const id=c.dataset.id;c.checked?S.played[id]=20:delete S.played[id];renderList();renderView()});
  el.querySelectorAll("input[data-h]").forEach(n=>n.onchange=()=>{S.played[n.dataset.h]=Math.max(1,+n.value||1);renderView()});
}

/* ---------- VIEWS ---------- */
const TABS=[["dna","Player Profile"],["recs","Recommendations"],["cats","Custom Categories"],["success","Genre Success"]];
function renderTabs(){
  const t=document.getElementById("tabs");
  t.innerHTML=TABS.map(([k,l])=>`<div class="tab ${S.tab===k?"on":""}" data-k="${k}">${l}</div>`).join("");
  t.querySelectorAll(".tab").forEach(e=>e.onclick=()=>{S.tab=e.dataset.k;renderTabs();renderView()});
}
function needData(){return `<div class="empty">Add some games on the left (or hit <b>Load demo profile</b>) to build your Player Profile.</div>`}

function radar(entries){
  const n=entries.length,R=120,cx=170,cy=150;
  const pt=(i,r)=>{const a=-Math.PI/2+i*2*Math.PI/n;return[cx+Math.cos(a)*r,cy+Math.sin(a)*r]};
  let web="";[.25,.5,.75,1].forEach(f=>{web+=`<polygon points="${entries.map((_,i)=>pt(i,R*f).join(",")).join(" ")}" fill="none" stroke="#2a3b4d"/>`});
  const max=entries[0][1];
  const poly=entries.map((e,i)=>pt(i,R*Math.max(.08,e[1]/max)).join(",")).join(" ");
  const lab=entries.map((e,i)=>{const[x,y]=pt(i,R+18);return`<text x="${x}" y="${y}" text-anchor="${x<cx-5?"end":x>cx+5?"start":"middle"}" dominant-baseline="middle">${e[0]}</text>`}).join("");
  const axes=entries.map((_,i)=>{const[x,y]=pt(i,R);return`<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#2a3b4d"/>`}).join("");
  return `<svg viewBox="0 0 340 300" width="100%">${web}${axes}<polygon points="${poly}" fill="rgba(102,192,244,.35)" stroke="#66c0f4" stroke-width="2"/>${lab}</svg>`;
}

function viewDNA(){
  const P=profile();if(!P.ids.length)return needData();
  const top=Object.entries(P.aff).sort((a,b)=>b[1]-a[1]);
  const radarE=top.slice(0,Math.min(8,top.length));
  while(radarE.length<3)radarE.push(["—",0.0001]);
  const pb=[["Free",0,0],["Under $10",0.01,9.99],["$10–20",10,20],["$20–40",20.01,40],["$40+",40.01,999]].map(([l,a,b])=>{
    let h=0;P.ids.forEach(k=>{const g=G[k];if(g.price>=a&&g.price<=b)h+=S.played[k]});return[l,h]});
  const mx=Math.max(...pb.map(p=>p[1]),1);
  const archetype=top[0][0]+" "+(P.avgPrice<15?"Bargain Hunter":P.avgPrice<35?"Value Seeker":"Premium Collector");
  return `<div class="kpi"><div><b>${P.ids.length}</b><span>games tracked</span></div><div><b>${Math.round(P.tot)}h</b><span>total hours</span></div><div><b>${fmt(Math.round(P.avgPrice*100)/100)}</b><span>hour-weighted price</span></div><div><b style="font-size:15px">${archetype}</b><span>your archetype</span></div></div>
  <div class="grid2">
   <div class="card"><h2>Genre radar</h2>${radar(radarE)}</div>
   <div class="card"><h2>Where your hours go</h2>
     ${top.slice(0,7).map(([g,v])=>`<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;font-size:13px"><span>${g}</span><span>${Math.round(v*100)}%</span></div><div class="bar"><i style="width:${v/top[0][1]*100}%"></i></div></div>`).join("")}
     <h2 style="margin-top:18px">Price comfort zone</h2>
     ${pb.map(([l,h])=>`<div style="display:grid;grid-template-columns:90px 1fr 44px;gap:8px;align-items:center;font-size:13px;margin:5px 0"><span>${l}</span><div class="bar"><i style="width:${h/mx*100}%"></i></div><span>${Math.round(h)}h</span></div>`).join("")}
   </div></div>`;
}

function viewRecs(){
  const P=profile();if(!P.ids.length)return needData();
  const R=recommend(P).slice(0,8);
  const catOpts=`<option value="">All genres</option>`+S.cats.map(c=>`<option ${S.focus===c.name?"selected":""}>${c.name}</option>`).join("");
  return `<div class="card" style="margin-bottom:14px"><h2>Tune the recommender</h2>
    <div class="ctl"><span>Genre ↔ Price</span><input type="range" id="wG" min="0" max="100" value="${S.wGenre}"><span>${S.wGenre}%</span></div>
    <div class="note" style="margin:-2px 0 6px 138px">Left = prioritise matching your price habits &middot; Right = prioritise genre taste</div>
    <div class="ctl"><span>Max budget</span><input type="range" id="bud" min="0" max="60" step="5" value="${S.budget}"><span>${S.budget>=60?"any":"$"+S.budget}</span></div>
    <div class="ctl"><span>Focus category</span><select id="foc">${catOpts}</select><span></span></div></div>
  ${R.length?R.map(r=>`<div class="rec"><div class="match" style="background:${col(r.score)}">${Math.round(r.score*100)}%</div>
    <div><h3>${r.g.name}</h3><div>${r.g.genres.map(x=>`<span class="chip ${P.aff[x]?"sel":""}" style="cursor:default">${x}</span>`).join("")}</div>
    <div class="why">Genre fit ${Math.round(r.gm*100)}% (you play lots of <b>${r.best}</b>) · price fit ${Math.round(r.pm*100)}% · ${r.g.rating}% positive</div></div>
    <div class="price">${fmt(r.g.price)}</div></div>`).join(""):`<div class="empty">Nothing matches those filters. Raise the budget or change the focus category.</div>`}`;
}
function bindRecs(){
  const w=document.getElementById("wG");if(!w)return;
  w.oninput=()=>{S.wGenre=+w.value;renderView()};
  document.getElementById("bud").oninput=e=>{S.budget=+e.target.value;renderView()};
  document.getElementById("foc").onchange=e=>{S.focus=e.target.value;renderView()};
}

function viewCats(){
  const P=profile();
  const chips=ALL_GENRES.map(g=>`<span class="chip pick ${S.draft.includes(g)?"sel":""}" data-g="${g}">${g}</span>`).join("");
  const cards=S.cats.map((c,i)=>{
    const inLib=P.ids.filter(k=>G[k].genres.some(x=>c.genres.includes(x)));
    const hrs=inLib.reduce((s,k)=>s+S.played[k],0);
    const share=P.tot?Math.round(hrs/P.tot*100):0;
    const unplayed=G.filter(g=>!(S.played[g.id]>0)&&g.genres.some(x=>c.genres.includes(x))).sort((a,b)=>b.rating-a.rating).slice(0,3);
    return `<div class="catcard"><span class="x" data-del="${i}">✕</span><h3>${c.name}</h3>
      <div>${c.genres.map(x=>`<span class="chip sel" style="cursor:default">${x}</span>`).join("")}</div>
      <div class="why" style="margin:6px 0">${P.tot?`<b>${share}%</b> of your playtime (${Math.round(hrs)}h across ${inLib.length} games)`:"Add games to see your playtime share"}</div>
      <div class="bar"><i style="width:${share}%"></i></div>
      <div class="why" style="margin-top:8px">Top unplayed: ${unplayed.map(g=>`${g.name} (${fmt(g.price)})`).join(" · ")||"none"}</div></div>`}).join("");
  return `<div class="grid2"><div class="card"><h2>Forge a category</h2>
    <input type="text" id="catName" placeholder="Name it, e.g. 'Rage Quit Club'">
    <div style="margin:10px 0">${chips}</div>
    <button class="pri" id="addCat">Create category</button>
    <div class="note">Steam's built-in tags are broad. Combine genres into your own buckets, then track how much of your playtime each one owns and use them as a recommendation filter.</div></div>
    <div><div class="card"><h2>Your categories</h2>${cards||`<div class="empty">No categories yet.</div>`}</div></div></div>`;
}
function bindCats(){
  document.querySelectorAll(".chip.pick").forEach(c=>c.onclick=()=>{const g=c.dataset.g;S.draft=S.draft.includes(g)?S.draft.filter(x=>x!==g):[...S.draft,g];const nm=document.getElementById("catName").value;renderView();document.getElementById("catName").value=nm});
  const add=document.getElementById("addCat");if(!add)return;
  add.onclick=()=>{const nm=document.getElementById("catName").value.trim();if(!nm||!S.draft.length){alert("Give it a name and pick at least one genre.");return}S.cats.push({name:nm,genres:S.draft});S.draft=[];renderView()};
  document.querySelectorAll("[data-del]").forEach(x=>x.onclick=()=>{const c=S.cats.splice(+x.dataset.del,1)[0];if(S.focus===c.name)S.focus="";renderView()});
}

function viewSuccess(){
  const by={};
  G.forEach(g=>g.genres.forEach(x=>{(by[x]=by[x]||[]).push(g)}));
  const rows=Object.entries(by).filter(([,a])=>a.length>=2).map(([k,a])=>{
    const rating=a.reduce((s,g)=>s+g.rating,0)/a.length;
    const owners=a.reduce((s,g)=>s+g.owners,0);
    const price=a.reduce((s,g)=>s+g.price,0)/a.length;
    const idx=(rating-70)*Math.log10(1+owners)*10;
    return{k,n:a.length,rating,owners,price,idx};
  }).sort((a,b)=>b.idx-a.idx);
  const mx=rows[0].idx;
  return `<div class="card"><h2>Research question: which genres actually succeed, and does price explain it?</h2>
   <div class="why" style="margin-bottom:10px">Success Index = avg. positive-review % (above a 70% baseline) × log of combined owners. This is the view that turns the app into a research tool rather than just a recommender.</div>
   <table><tr><th>Genre</th><th>Games</th><th>Avg rating</th><th>Avg price</th><th style="width:38%">Success index</th></tr>
   ${rows.map(r=>`<tr><td>${r.k}</td><td>${r.n}</td><td>${r.rating.toFixed(1)}%</td><td>${fmt(+r.price.toFixed(2))}</td><td><div class="bar"><i style="width:${r.idx/mx*100}%"></i></div></td></tr>`).join("")}</table>
   <div class="note">Illustrative sample, not live Steam data. The full version would pull real figures from the Steam Store API and SteamSpy, and could test whether cheaper genres earn better ratings.</div></div>`;
}

function renderView(){
  const v=document.getElementById("view");
  v.innerHTML=S.tab==="dna"?viewDNA():S.tab==="recs"?viewRecs():S.tab==="cats"?viewCats():viewSuccess();
  if(S.tab==="recs")bindRecs();if(S.tab==="cats")bindCats();
}

/* ---------- INIT ---------- */
document.getElementById("search").oninput=e=>{S.q=e.target.value;renderList()};
document.getElementById("demoBtn").onclick=()=>{S.played={};DEMO.forEach(([n,h])=>{const g=G.find(x=>x.name===n);if(g)S.played[g.id]=h});renderList();renderView()};
document.getElementById("clearBtn").onclick=()=>{S.played={};renderList();renderView()};
renderTabs();renderList();renderView();
</script>
</body>
</html>
"""


def write_vscode_task():
    """Adds a VS Code task so Ctrl+Shift+B builds the dashboard."""
    vs = ROOT / ".vscode"
    vs.mkdir(exist_ok=True)
    tasks = vs / "tasks.json"
    if tasks.exists():
        return
    tasks.write_text(json.dumps({
        "version": "2.0.0",
        "tasks": [{
            "label": "Build Steam Dashboard",
            "type": "shell",
            "command": "python build_dashboard.py",
            "group": {"kind": "build", "isDefault": True},
            "problemMatcher": []
        }]
    }, indent=2), encoding="utf-8")


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(HTML, encoding="utf-8")
    write_vscode_task()
    print(f"Built {OUT_FILE}")


def serve(port=8000):
    def handler(*a, **k):
        return http.server.SimpleHTTPRequestHandler(*a, directory=str(OUT_DIR), **k)
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        print(f"Serving {OUT_DIR} at {url}  (Ctrl+C to stop)")
        webbrowser.open(url)
        httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the Steam Taste Forge dashboard")
    ap.add_argument("--serve", action="store_true", help="serve on localhost:8000 after building")
    ap.add_argument("--no-open", action="store_true", help="build only, do not open a browser")
    args = ap.parse_args()
    build()
    if args.serve:
        serve()
    elif not args.no_open:
        webbrowser.open(OUT_FILE.as_uri())