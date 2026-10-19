"""
build_solar_nav.py  --  builds a No Man's Sky-style navigation map of the REAL solar system.

Bodies: Sun, Mercury, Venus, Earth, Moon, Mars, Jupiter, Saturn.
Each one has a procedurally generated 3D model (no image downloads), a habitability
score, an NMS-style planet class, and its most valuable resources.

    python build_solar_nav.py            # build, then open in your browser
    python build_solar_nav.py --serve    # build, then serve at http://localhost:8001
    python build_solar_nav.py --no-open  # build only

Output: solar-nav/index.html  (next to this script).  Local only, nothing is pushed anywhere.
The first build downloads three.js once into solar-nav/three.min.js (falls back to the CDN if offline).

Controls
  TOUR MODE   <- / -> (or buttons) step through bodies, most habitable first.
              Drag = orbit, wheel = zoom.
  FREE ROAM   WASD fly, Q/E down/up, Shift = boost, drag = look, wheel = dolly.
              Click a planet (or its tag) to select, F / Enter / WARP button to jump to it.
  P pause orbits   Esc deselect
"""
import argparse
import http.server
import socketserver
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "solar-nav"
OUT_FILE = OUT_DIR / "index.html"
THREE_FILE = OUT_DIR / "three.min.js"
THREE_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SOL - Galactic Navigation</title>
<style>
:root{--cy:#7fe9ff;--cy2:#3aa8c4;--gold:#ffd24d;--bg:rgba(4,10,20,.74);--line:rgba(127,233,255,.34);--mute:#7f9bb0;--text:#e8f6ff}
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;background:#02040a;color:var(--text);font:13px/1.4 "Segoe UI",system-ui,sans-serif;user-select:none}
#gl{position:fixed;inset:0;width:100%;height:100%;display:block;cursor:grab}
#gl:active{cursor:grabbing}
.hud{position:fixed;inset:0;pointer-events:none}
.panel{pointer-events:auto;background:var(--bg);border:1px solid var(--line);backdrop-filter:blur(6px);
  clip-path:polygon(0 0,calc(100% - 14px) 0,100% 14px,100% 100%,14px 100%,0 calc(100% - 14px))}
h1{margin:0;font-size:15px;letter-spacing:.32em;font-weight:600;color:var(--cy)}
h1 small{display:block;font-size:10px;letter-spacing:.22em;color:var(--mute);font-weight:400;margin-top:2px}
#top{position:absolute;left:18px;top:14px;right:18px;display:flex;justify-content:space-between;align-items:flex-start}
#modes{display:flex;gap:6px;pointer-events:auto}
button{font:inherit;color:var(--cy);background:rgba(8,22,36,.8);border:1px solid var(--line);padding:7px 16px;letter-spacing:.18em;
  text-transform:uppercase;font-size:11px;cursor:pointer;clip-path:polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,8px 100%,0 calc(100% - 8px))}
button:hover{background:rgba(30,80,110,.7);color:#fff}
button.on{background:var(--cy);color:#021018;font-weight:700}
#list{position:absolute;left:18px;top:128px;width:268px;padding:12px 10px 10px}
#list h2,#info h2{margin:0 0 8px;font-size:10px;letter-spacing:.26em;color:var(--mute);font-weight:500;text-transform:uppercase}
.row{display:grid;grid-template-columns:22px 1fr 44px;gap:8px;align-items:center;padding:7px 8px;border-left:2px solid transparent;cursor:pointer}
.row:hover{background:rgba(127,233,255,.08)}
.row.sel{background:rgba(127,233,255,.14);border-left-color:var(--gold)}
.row .rk{color:var(--mute);font-size:11px;text-align:right}
.row .nm{font-weight:600;letter-spacing:.06em}
.row .cl{font-size:10px;letter-spacing:.12em;text-transform:uppercase}
.row .pc{text-align:right;font-variant-numeric:tabular-nums;color:var(--gold);font-weight:600}
.mini{height:3px;background:rgba(255,255,255,.1);margin-top:4px}
.mini i{display:block;height:100%;background:var(--cy)}
#info{display:none;position:absolute;right:18px;top:70px;width:352px;max-height:calc(100% - 130px);overflow:auto;padding:16px 16px 14px;scrollbar-width:thin}
#info .nm{font-size:24px;letter-spacing:.2em;font-weight:300;margin:0}
#info .chip{display:inline-block;margin:6px 0 4px;padding:2px 10px;font-size:11px;letter-spacing:.16em;text-transform:uppercase;border:1px solid;font-weight:600}
#info .blurb{color:#b9cddb;margin:8px 0 12px}
.hab{display:flex;gap:3px;margin:4px 0 2px}
.hab i{flex:1;height:9px;background:rgba(255,255,255,.12)}
.hab i.f{background:var(--c,var(--gold))}
.habn{display:flex;justify-content:space-between;align-items:baseline;margin-top:10px;font-size:10px;letter-spacing:.2em;color:var(--mute);text-transform:uppercase}
.habn b{font-size:22px;letter-spacing:.04em;color:var(--gold);font-weight:600}
.sub{display:grid;grid-template-columns:78px 1fr 20px;gap:8px;align-items:center;margin:3px 0;font-size:11px;color:var(--mute)}
.sub div{height:4px;background:rgba(255,255,255,.1)}.sub div i{display:block;height:100%;background:var(--cy2)}
.sub span:last-child{text-align:right;color:var(--text)}
.sec{margin:14px 0 6px;font-size:10px;letter-spacing:.26em;color:var(--mute);text-transform:uppercase;border-top:1px solid var(--line);padding-top:10px}
.facts{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}
.facts div small{display:block;font-size:9px;letter-spacing:.18em;color:var(--mute);text-transform:uppercase}
.facts div{font-size:12px}
.res{display:grid;grid-template-columns:44px 1fr auto;gap:10px;align-items:center;padding:6px 0;border-bottom:1px solid rgba(127,233,255,.12)}
.res .sy{height:40px;display:grid;place-items:center;border:1px solid var(--line);font-weight:700;font-size:13px;background:rgba(127,233,255,.07)}
.res b{display:block;font-weight:600}
.res small{color:var(--mute);font-size:11px;line-height:1.25;display:block}
.res .st{color:var(--gold);letter-spacing:1px;font-size:11px;white-space:nowrap}
.haz{display:flex;flex-wrap:wrap;gap:6px}
.haz span{border:1px solid rgba(255,107,90,.6);color:#ff9d8f;padding:1px 8px;font-size:11px;letter-spacing:.08em}
#warpbtn{margin-top:12px;width:100%;border-color:var(--gold);color:var(--gold)}
#warpbtn:hover{background:var(--gold);color:#201600}
#empty{color:var(--mute);padding:6px 0 4px}
#tourbar{display:none;position:absolute;left:50%;bottom:56px;transform:translateX(-50%);display:flex;gap:10px;align-items:center;pointer-events:auto}
#tourbar .ct{min-width:190px;text-align:center;letter-spacing:.2em;color:var(--cy);font-size:12px;text-transform:uppercase}
#info.open{display:block}
#foot{position:absolute;left:0;right:0;bottom:0;height:34px;background:rgba(8,10,40,.72);display:flex;align-items:center;justify-content:space-between;padding:0 24px;font-size:13px;letter-spacing:.04em}
#footc{flex:1;text-align:center;color:#e8ecff}#footr{min-width:210px;text-align:right}
kbd{display:inline-block;min-width:22px;padding:0 6px;margin:0 2px;border:1px solid #cfd6ff;border-radius:4px;font:600 11px "Segoe UI",sans-serif;text-align:center;color:#fff}
#sys{padding:10px 26px 12px 18px}#sys .big{font-size:30px;font-weight:300;letter-spacing:.06em;line-height:1.1}
#sys .by{font-size:12px;color:#b9c3dd}#sys .cnt{margin-top:6px;font-size:15px;letter-spacing:.28em;font-weight:500}
.tag{position:absolute;pointer-events:auto;cursor:pointer;padding:3px 12px;border-radius:14px;font-size:13px;font-weight:600;white-space:nowrap;background:rgba(112,120,212,.9);color:#fff;display:none;box-shadow:0 2px 8px rgba(0,0,0,.35)}
.tag.sel{background:var(--gold);color:#1d1400}
.halo{position:absolute;pointer-events:none;border:1px solid rgba(255,255,255,.55);border-radius:50%;transform:translate(-50%,-50%);display:none}
.halo::after{content:"";position:absolute;inset:-9px;border:1px solid rgba(255,255,255,.26);border-radius:50%}
.halo.sel{border-color:var(--gold)}
#pop{position:absolute;pointer-events:none;width:300px;display:none;box-shadow:0 8px 30px rgba(0,0,0,.5)}
#pop .ph{background:#7078d4;padding:8px 14px}#pop .ph b{display:block;font-size:20px;font-weight:500}#pop .ph span{font-size:12px;opacity:.9}
#pop .pb{background:rgba(6,4,16,.93);padding:10px 14px 4px}
#pop .pc{font-size:15px;margin-bottom:2px}#pop .pm{font-size:11px;color:var(--mute);margin-bottom:8px}#pop .pm b{color:var(--gold)}
#pop ul{list-style:none;margin:0 0 8px;padding:0}#pop li{padding:1px 0 1px 20px;position:relative;font-size:14px}
#pop li::before{content:"C6";position:absolute;left:0;color:#cfd6ff;font-size:11px}
#pop li.hi,#pop li.hi::before{color:#6dff7a}
.pa{display:grid;grid-template-columns:52px 1fr;gap:8px;align-items:center;padding:7px 0;cursor:pointer}.pa:hover b{color:var(--gold)}
.pa b{letter-spacing:.2em;font-weight:500;font-size:15px}.pa small{display:block;color:#b9c3dd;font-size:11.5px}
#warptxt{position:absolute;left:50%;top:22%;transform:translateX(-50%);font-size:12px;letter-spacing:.6em;color:var(--cy);opacity:0;transition:opacity .25s}
#loading{position:fixed;inset:0;background:#02040a;display:grid;place-content:center;text-align:center;letter-spacing:.35em;color:var(--cy);z-index:9;transition:opacity .8s}
#loading small{display:block;margin-top:12px;font-size:10px;color:var(--mute);letter-spacing:.2em}
#bar{width:260px;height:2px;background:rgba(127,233,255,.2);margin:16px auto 0}#bar i{display:block;height:100%;width:0;background:var(--cy)}
</style>
</head>
<body>
<canvas id="gl"></canvas>
<div class="hud" id="hud">
  <div id="top">
    <div class="panel" id="sys"><div class="big">Sol</div><div class="by">Formed 4.6 billion years ago</div><div class="cnt">6 PLANETS / 1 MOON</div></div>
    <div id="modes"><button id="m-lock" class="on">Locked view</button><button id="m-roam">Free look</button></div>
  </div>
  <div id="list" class="panel"><h2>Habitability ranking</h2><div id="rows"></div></div>
  <div id="info" class="panel"></div>
  <div id="tourbar"><button id="prev">&lt; Prev</button><div class="ct" id="tourlabel"></div><button id="next">Next &gt;</button></div>
  <div id="warptxt">WARP</div>
  <div id="pop"></div>
  <div id="foot"><div></div><div id="footc"></div><div id="footr"></div></div>
</div>
<div id="loading"><div>INITIALISING NAV COMPUTER<small id="loadmsg">synthesising planetary surfaces...</small><div id="bar"><i id="barfill"></i></div></div></div>

<script src="three.min.js"></script>
<script>window.THREE||document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"><\/script>')</script>
<script>
"use strict";
/* ================= DATA (real solar system) ================= */
// sub-scores 0-10: temp, air, water, shield (radiation/magnetosphere), grav, surf (solid habitable surface)
const WEIGHTS={temp:2,air:2,water:2,shield:1,grav:1,surf:1};
const SUBLABEL={temp:'Temperature',air:'Atmosphere',water:'Water',shield:'Radiation',grav:'Gravity',surf:'Surface'};
const DATA=[
 {id:'sun',name:'Sol',cls:'Stellar - G2V',color:'#ffd24d',R:30,dist:0,
  sub:{temp:0,air:0,water:0,shield:0,grav:0,surf:0},
  blurb:'Our star. A 4.6-billion-year-old yellow dwarf holding 99.86% of the system\'s mass. Hard radiation, no surface, and the source of every other body\'s climate.',
  weather:'Radioactive - solar flares',
  facts:[['Radius','695,700 km'],['Gravity','27.9 g'],['Surface temp','5,500 C'],['Core temp','15,000,000 C'],['Composition','H 73% / He 25%'],['Rotation','~25 days (equator)'],['Distance','centre of system'],['Moons','8 planets']],
  hazards:['Lethal radiation','Plasma','Solar flares'],
  res:[['E','Solar Energy','Effectively unlimited fusion output',5],['H','Hydrogen','Fusion fuel, 73% of the star by mass',3],['He','Helium Plasma','Fusion by-product',3]]},
 {id:'mercury',name:'Mercury',cls:'Scorched',color:'#ff7a45',R:3,dist:80,w:0.05,spin:.02,tilt:0,
  sub:{temp:1,air:0,water:1,shield:0,grav:4,surf:4},
  blurb:'Cratered, airless and baked to 430 C by day, frozen to -180 C by night. Permanently shadowed polar craters still hold water ice.',
  weather:'Extreme temperature swings',
  facts:[['Radius','2,440 km'],['Gravity','0.38 g'],['Mean temp','167 C (-180 / 430)'],['Atmosphere','Exosphere (trace Na, O)'],['Pressure','~0 bar'],['Day (solar)','176 Earth days'],['Year','88 Earth days'],['Distance','0.39 AU / Moons: 0']],
  hazards:['Extreme heat','Extreme cold','Solar radiation','No atmosphere'],
  res:[['Fe','Iron-Nickel Core','Core is ~85% of the planet\'s radius',4],['E','Solar Flux','6x Earth\'s sunlight',5],['H2O','Polar Water Ice','In permanently shadowed craters',3],['S','Sulfur','Surface volatiles',2]]},
 {id:'venus',name:'Venus',cls:'Toxic Inferno',color:'#ffb347',R:5,dist:120,w:0.027,spin:-.004,tilt:3.09,
  sub:{temp:0,air:0,water:0,shield:4,grav:8,surf:1},
  blurb:'Earth\'s twin in size, a runaway greenhouse in practice. 464 C at the surface under 92 bar of CO2; the cloud tops at ~50 km are the only mild place.',
  weather:'Sulphuric acid clouds - 360 km/h upper winds',
  facts:[['Radius','6,052 km'],['Gravity','0.90 g'],['Mean temp','464 C'],['Atmosphere','CO2 96.5% / N2 3.5%'],['Pressure','92 bar'],['Day','243 days (retrograde)'],['Year','225 Earth days'],['Distance','0.72 AU / Moons: 0']],
  hazards:['Crushing pressure','Acid rain','Extreme heat'],
  res:[['E','Solar Flux','Strong, but under 100% cloud cover',3],['H2SO4','Sulphuric Acid','Cloud-layer droplets',2],['N2','Upper-Cloud Nitrogen','Aerostat-harvestable',2],['CO2','Carbon Dioxide','Dense atmosphere',1]]},
 {id:'earth',name:'Earth',cls:'Lush',color:'#6fe38a',R:5.2,dist:170,w:0.0181,spin:.35,tilt:0.409,
  sub:{temp:10,air:10,water:10,shield:10,grav:10,surf:10},
  blurb:'The only confirmed living world. Liquid oceans, a nitrogen-oxygen atmosphere, a strong magnetosphere and a stable climate. The benchmark every other body is scored against.',
  weather:'Temperate - rain, storms, seasons',
  facts:[['Radius','6,371 km'],['Gravity','1.00 g'],['Mean temp','15 C (-89 / 57)'],['Atmosphere','N2 78% / O2 21%'],['Pressure','1.01 bar'],['Day','24 hours'],['Year','365.25 days'],['Distance','1.00 AU / Moons: 1']],
  hazards:['Severe weather (local)'],
  res:[['H2O','Fresh Water','71% of the surface is ocean',5],['O2','Oxygen','Breathable atmosphere',4],['C','Biomass','Life-bearing biosphere',4],['CHx','Hydrocarbons','Fossil carbon deposits',3],['REE','Rare-Earth Ores','Crustal deposits',3]]},
 {id:'moon',name:'Luna',cls:'Airless Moon',color:'#9bb3c7',R:1.5,dist:16,w:0.25,parent:'earth',
  sub:{temp:3,air:0,water:1,shield:0,grav:3,surf:5},
  blurb:'Earth\'s tidally locked moon. No atmosphere, no magnetic shield, a day-night swing of 300 C, but ice in polar craters and the nearest solid ground to anywhere.',
  weather:'None - vacuum',
  facts:[['Radius','1,737 km'],['Gravity','0.165 g'],['Mean temp','-20 C (-173 / 127)'],['Atmosphere','Exosphere (trace)'],['Pressure','~0 bar'],['Day','29.5 Earth days'],['Orbit','27.3 days around Earth'],['Distance','384,400 km from Earth']],
  hazards:['Vacuum','Micrometeorites','Solar radiation','Lunar dust'],
  res:[['He3','Helium-3','Implanted by solar wind in regolith',5],['H2O','Polar Water Ice','Shadowed craters',4],['Ti','Titanium Ore','Ilmenite in the maria',3],['O2','Regolith Oxygen','~42% of regolith by mass',2],['Al','Aluminium','Highland anorthite',2]]},
 {id:'mars',name:'Mars',cls:'Arid Dust World',color:'#ff8f5a',R:4,dist:230,w:0.0117,spin:.34,tilt:0.44,
  sub:{temp:4,air:1,water:3,shield:2,grav:5,surf:6},
  blurb:'Cold, dry and thinly airy, but with a day almost exactly Earth\'s, polar ice caps and subsurface water. The most habitable world after our own.',
  weather:'Global dust storms (weeks to months)',
  facts:[['Radius','3,390 km'],['Gravity','0.38 g'],['Mean temp','-63 C (-153 / 20)'],['Atmosphere','CO2 95% / N2 2.8%'],['Pressure','0.006 bar'],['Day','24 h 37 min'],['Year','687 Earth days'],['Distance','1.52 AU / Moons: 2']],
  hazards:['Toxic perchlorate dust','Thin air','Radiation','Dust storms'],
  res:[['H2O','Water Ice','Polar caps and buried glaciers',4],['Fe2O3','Iron Oxide','The red in the red planet',3],['CO2','Carbon Dioxide','Feedstock for fuel and oxygen',2],['ClO4','Perchlorates','Oxidiser, toxic',2],['Si','Basalt','Abundant crust',1]]},
 {id:'jupiter',name:'Jupiter',cls:'Gas Giant - Storm',color:'#c9a0ff',R:14,dist:340,w:0.0071,spin:.7,tilt:0.055,
  sub:{temp:1,air:0,water:0,shield:0,grav:2,surf:0},
  blurb:'A world of hydrogen and helium with no solid surface, a 350-year-old storm bigger than Earth and some of the worst radiation belts in the system. Its 95 moons include four planet-sized ones.',
  weather:'Perpetual storms - Great Red Spot',
  facts:[['Radius','69,911 km'],['Gravity','2.53 g (cloud tops)'],['Cloud-top temp','-110 C'],['Atmosphere','H2 90% / He 10%'],['Pressure','1 bar at cloud tops'],['Day','9 h 56 min'],['Year','11.9 Earth years'],['Distance','5.20 AU / Moons: 90+']],
  hazards:['Lethal radiation belts','No surface','Extreme storms','2.5x gravity'],
  res:[['He3','Helium-3','Skimmable from the upper atmosphere',5],['H2','Hydrogen','Fuel at planetary scale',4],['H(m)','Metallic Hydrogen','Deep interior, theorised',5],['NH3','Ammonia','Cloud layers',2]]},
 {id:'saturn',name:'Saturn',cls:'Gas Giant - Ringed',color:'#e8cf8d',R:12,dist:450,w:0.0053,spin:.65,tilt:0.466,
  sub:{temp:1,air:0,water:0,shield:1,grav:6,surf:0},
  blurb:'Less dense than water and wrapped in rings of almost pure ice. A hexagonal storm sits on the north pole. Moons Titan and Enceladus are the long-term habitability candidates here.',
  weather:'Hexagonal polar storm - 1,800 km/h winds',
  facts:[['Radius','58,232 km'],['Gravity','1.07 g (cloud tops)'],['Cloud-top temp','-140 C'],['Atmosphere','H2 96% / He 3%'],['Pressure','1 bar at cloud tops'],['Day','10 h 33 min'],['Year','29.5 Earth years'],['Distance','9.58 AU / Moons: 140+']],
  hazards:['No surface','Extreme winds','Ring debris'],
  res:[['H2O','Ring Water Ice','~95% water ice, easily mined fuel',4],['H2','Hydrogen','Upper atmosphere',3],['He','Helium','Upper atmosphere',3],['NH3','Ammonia Ice','Cloud layers',2]]}
];
DATA.forEach(b=>{const t=Object.keys(WEIGHTS).reduce((s,k)=>s+WEIGHTS[k]*b.sub[k],0),m=Object.values(WEIGHTS).reduce((a,c)=>a+c,0)*10;b.hab=Math.round(t/m*100);});
const RANK=[...DATA].sort((a,b)=>b.hab-a.hab);
const byId=id=>DATA.find(d=>d.id===id);

/* ================= NOISE + PROCEDURAL TEXTURES ================= */
const TAU=Math.PI*2, clamp=(v,a=0,b=1)=>v<a?a:v>b?b:v;
const P=new Uint8Array(512);(function(){const p=[...Array(256).keys()];let s=1337;const r=()=>(s=(s*16807)%2147483647)/2147483647;
  for(let i=255;i>0;i--){const j=Math.floor(r()*(i+1));[p[i],p[j]]=[p[j],p[i]];}for(let i=0;i<512;i++)P[i]=p[i&255];})();
const hash3=(x,y,z)=>P[P[P[x&255]+(y&255)]+(z&255)]/255;
const sm=t=>t*t*(3-2*t), lr=(a,b,t)=>a+(b-a)*t;
function vnoise(x,y,z){const xi=Math.floor(x),yi=Math.floor(y),zi=Math.floor(z),xf=sm(x-xi),yf=sm(y-yi),zf=sm(z-zi);
  return lr(lr(lr(hash3(xi,yi,zi),hash3(xi+1,yi,zi),xf),lr(hash3(xi,yi+1,zi),hash3(xi+1,yi+1,zi),xf),yf),
            lr(lr(hash3(xi,yi,zi+1),hash3(xi+1,yi,zi+1),xf),lr(hash3(xi,yi+1,zi+1),hash3(xi+1,yi+1,zi+1),xf),yf),zf);}
function fbm(x,y,z,o){let s=0,a=1,t=0;for(let i=0;i<o;i++){s+=a*vnoise(x,y,z);t+=a;x*=2.03;y*=2.03;z*=2.03;a*=.5;}return s/t;}
function craters(x,y,z,sc){x*=sc;y*=sc;z*=sc;const xi=Math.floor(x),yi=Math.floor(y),zi=Math.floor(z);let h=0;
  for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++)for(let c=-1;c<=1;c++){const cx=xi+a,cy=yi+b,cz=zi+c,hv=hash3(cx,cy,cz);if(hv<.45)continue;
    const px=cx+hash3(cx+57,cy,cz),py=cy+hash3(cx,cy+91,cz),pz=cz+hash3(cx,cy,cz+33),d=Math.hypot(x-px,y-py,z-pz),r=.25+.3*hv;
    if(d<r){const t=d/r;h+=t<.8?-(1-t*t/.64)*.5:(1-Math.abs(t-.9)/.1)*.25;}}
  return h;}
const mix=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
function rowsInto(d,w,h,fn,y0,y1){for(let y=y0;y<y1;y++){const lat=(.5-(y+.5)/h)*Math.PI,cl=Math.cos(lat),sy=Math.sin(lat);
    for(let x=0;x<w;x++){const lon=(x+.5)/w*TAU,col=fn(cl*Math.cos(lon),sy,cl*Math.sin(lon),lat,lon),i=(y*w+x)*4;
      d[i]=col[0];d[i+1]=col[1];d[i+2]=col[2];d[i+3]=col.length>3?col[3]:255;}}}
function paint(w,h,fn){const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d'),im=g.createImageData(w,h);
  rowsInto(im.data,w,h,fn,0,h);g.putImageData(im,0,0);return c;}
function paintAsync(w,h,fn,prog){return new Promise(res=>{const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d'),im=g.createImageData(w,h);let y=0;
  (function slice(){const t0=performance.now();while(y<h&&performance.now()-t0<30){rowsInto(im.data,w,h,fn,y,y+1);y++;}
    prog&&prog(y/h);if(y<h)setTimeout(slice,0);else{g.putImageData(im,0,0);res(c);}})();});}
// storms: [lon, lat, half-width, half-height, colourA, colourB, dark-collar strength]
const JSTORMS=[[3.2,-.33,.30,.115,[190,78,52],[228,135,95],.5],[4.15,-.57,.09,.05,[200,110,80],[240,170,140],.3],
  [1.0,.42,.06,.035,[240,238,228],[255,252,245],.2],[2.2,.38,.05,.03,[240,238,228],[255,252,245],.2],[5.4,-.2,.07,.04,[240,238,228],[255,252,245],.2],
  [.3,.6,.05,.03,[240,238,228],[255,252,245],.2],[5.9,.28,.04,.025,[240,238,228],[255,252,245],.2],[4.8,.5,.05,.03,[240,238,228],[255,252,245],.2],
  [1.7,.22,.12,.03,[150,90,58],[190,120,80],.18],[5.0,.19,.10,.028,[150,90,58],[190,120,80],.18],[2.9,-.7,.06,.035,[235,230,220],[255,250,242],.2]];
const RECIPE={
 earth:(x,y,z)=>{const h=fbm(x*1.8+3,y*1.8,z*1.8,8),ice=Math.abs(y)+(fbm(x*5,y*5,z*5,4)-.5)*.18,fine=fbm(x*22,y*22,z*22,3);
   if(ice>.9)return mix([225,235,245],[250,252,255],fbm(x*8,y*8,z*8,4));
   if(h<.52){const d=clamp((.52-h)/.22);let c=mix([34,120,178],[8,28,84],d);const k=.93+fine*.14;return[c[0]*k,c[1]*k,c[2]*k];}
   const m=fbm(x*3+9,y*3,z*3,5),e=(h-.52)/.25;let c=mix([62,122,50],[34,86,40],m);
   c=mix(c,[192,162,100],clamp((m-.55)*4)*clamp(1-Math.abs(y)*1.5));c=mix(c,[112,100,90],clamp((e-.5)*3));
   if(e<.05)c=mix(c,[205,195,145],.8);if(ice>.8)c=mix(c,[242,246,250],clamp((ice-.8)*10));
   const k=.82+fine*.36;return[c[0]*k,c[1]*k,c[2]*k];},
 clouds:(x,y,z)=>{const c=fbm(x*3+11,y*5,z*3,8);return[255,255,255,clamp((c-.5)*3.2)*225];},
 moon:(x,y,z)=>{const b=fbm(x*2.2,y*2.2,z*2.2,7),maria=clamp((.5-fbm(x*1.2+5,y*1.2,z*1.2,4))*5);
   let v=.55+(b-.5)*.35-maria*.22+(craters(x,y,z,6)+craters(x,y,z,14)*.6+craters(x,y,z,32)*.4+craters(x,y,z,64)*.25)*.25;const g=clamp(v)*255;return[g,g*.98,g*.95];},
 mercury:(x,y,z)=>{const b=fbm(x*3,y*3,z*3,7),cr=craters(x,y,z,5)+craters(x,y,z,12)*.7+craters(x,y,z,25)*.5+craters(x,y,z,52)*.3,g=clamp(.45+(b-.5)*.35+cr*.22)*255;return[g,g*.95,g*.9];},
 venus:(x,y,z)=>{const ay=Math.abs(y),a=ay*2.1,ca=Math.cos(a),sa=Math.sin(a),X=x*ca-z*sa,Z=x*sa+z*ca;   // shear with latitude -> chevron cloud pattern
   const w=fbm(X*1.6,y*3.5,Z*1.6,4),s=fbm(X*2.6+w*2.4,y*7+w*1.5,Z*2.6+w*2.4,8),f=fbm(X*16+w*3,y*34,Z*16+w*3,4);
   let c=mix([196,150,78],[247,228,176],clamp(s*1.35-.12));
   const uv=clamp((fbm(X*1.2+9,y*2.6,Z*1.2,5)-.5)*3.2);c=mix(c,[150,112,66],uv*.45*(1-ay*.6));   // darker UV-absorbing streaks
   if(ay>.78)c=mix(c,[250,236,196],clamp((ay-.78)*4)*.55);   // bright polar collar
   const k=.9+f*.2;return[c[0]*k,c[1]*k,c[2]*k];},
 venusHaze:(x,y,z)=>{const a=Math.abs(y)*2.6,ca=Math.cos(a),sa=Math.sin(a),X=x*ca-z*sa,Z=x*sa+z*ca,c=fbm(X*3+4,y*8,Z*3,7);return[255,240,200,clamp((c-.46)*2.6)*150];},
 bandHaze:(x,y,z)=>{const c=fbm(x*4+2,y*30,z*4,6),L=fbm(x*9,y*80,z*9,3);return[255,246,230,clamp((c-.48)*2.4)*(80+L*90)];},
 mars:(x,y,z)=>{const b=fbm(x*2.5,y*2.5,z*2.5,8),dk=clamp((fbm(x*1.5+7,y*1.5,z*1.5,5)-.5)*4),fine=fbm(x*16,y*16,z*16,3);
   let c=mix([196,106,60],[150,78,48],b);c=mix(c,[70,42,36],dk*.7);c=mix(c,[225,170,120],clamp((b-.62)*4)*.5);
   const cr=1+(craters(x,y,z,7)+craters(x,y,z,18)*.6)*.18,k=cr*(.9+fine*.2);c=[c[0]*k,c[1]*k,c[2]*k];
   const pole=Math.abs(y)+(fbm(x*6,y*6,z*6,4)-.5)*.1;if(pole>.93)c=mix(c,[245,245,250],clamp((pole-.93)*30));return c;},
 jupiter:(x,y,z,lat,lon)=>{
   const turb=fbm(x*5,y*9,z*5,5),L=lat+(turb-.5)*.09*Math.cos(lat*14);   // band edges ripple
   const t=fbm(x*3,y*14,z*3,7),band=Math.sin(L*14+(t-.5)*3.2)*.7+Math.sin(L*31+(t-.5)*4)*.3;
   let c=mix([170,108,66],[236,222,196],(band+1)/2);
   c=mix(c,[140,86,58],clamp((fbm(x*2,y*30,z*2,4)-.6)*2)*.4);
   const f=fbm(x*9,y*55,z*9,3);c=mix(c,[250,240,225],clamp((f-.62)*3)*.3);
   c=mix(c,[225,200,160],Math.exp(-(lat*lat)/.02)*.5*fbm(x*14,y*6,z*14,3));   // chaotic equatorial zone
   c=mix(c,[112,122,142],clamp((Math.abs(lat)-1.05)*5)*(.5+.4*fbm(x*8,y*8,z*8,3)));   // bluish polar haze
   for(const s of JSTORMS){const dy=lat-s[1];if(Math.abs(dy)>s[3]*1.6)continue;let dl=lon-s[0];dl=Math.atan2(Math.sin(dl),Math.cos(dl));
     const e=(dl/s[2])**2+(dy/s[3])**2;
     if(e<1){const sw=Math.sin(Math.atan2(dy/s[3],dl/s[2])*2+e*7+fbm(x*14,y*14,z*14,3)*4)*.5+.5;c=mix(c,mix(s[4],s[5],sw),clamp((1-e)*2.4));}
     else if(e<2.4)c=mix(c,[96,64,48],(1-clamp((e-1)/1.4))*s[6]);}   // dark turbulent collar
   return c;},
 saturn:(x,y,z,lat,lon)=>{const t=fbm(x*2,y*18,z*2,6),L=lat+(fbm(x*6,y*8,z*6,4)-.5)*.04,band=Math.sin(L*20+(t-.5)*2)*.75+Math.sin(L*47+(t-.5)*3)*.25,f=fbm(x*6,y*50,z*6,3);
   let c=mix([196,168,118],[236,216,168],(band+1)/2*.7+t*.3);
   c=mix(c,[245,228,185],Math.exp(-((lat-.08)*(lat-.08))/.012)*.3);   // bright equatorial zone
   const rho=Math.PI/2-lat;   // north polar hexagon
   if(rho<.34){const m=((lon%(Math.PI/3))+Math.PI/3)%(Math.PI/3),hexR=.21/Math.cos(m-Math.PI/6),d=rho-hexR;
     c=mix(c,[112,132,150],clamp(-d*9+.5)*.55*clamp((.3-rho)*10));c=mix(c,[70,88,104],Math.exp(-d*d/.0004)*.6);
     if(rho<.07)c=mix(c,[60,75,92],clamp((.07-rho)*20)*.7);}
   const k=.94+f*.12;return[c[0]*k,c[1]*k,c[2]*k];},
 sun:(x,y,z)=>{const g=fbm(x*9,y*9,z*9,7),sp=clamp((fbm(x*3+4,y*3,z*3,4)-.62)*6),f=fbm(x*34,y*34,z*34,3);
   const c=mix(mix([255,120,10],[255,225,120],g),[120,40,5],sp*.8),k=.92+f*.16;return[Math.min(255,c[0]*k),Math.min(255,c[1]*k),c[2]*k];}
};
function ringTexture(){const w=4096,c=document.createElement('canvas');c.width=w;c.height=4;const g=c.getContext('2d');
  for(let x=0;x<w;x++){const u=x/w,r=1.25+u*1.1;let a,col;   // r in planet radii
    if(r<1.53){a=.1+(r-1.25)/.28*.22;col=[120,110,100];}                                       // C ring: faint and grey
    else if(r<1.95){const q=(r-1.53)/.42;a=.72+.26*Math.sin(q*9+vnoise(q*14,1,0)*3)**2;col=[222,196,150];if(q<.08)a*=.6+q*5;}   // B ring: densest
    else if(r<2.03){a=.05+.04*vnoise(r*50,2,0);col=[180,165,140];}                              // Cassini Division
    else if(r<2.27){a=.6;col=[214,196,160];if(Math.abs(r-2.21)<.012)a=.03;}                      // A ring + Encke gap
    else if(r<2.31){a=.02;col=[180,170,150];}
    else{a=Math.abs(r-2.33)<.012?.8:.03;col=[235,225,200];}                                      // F ring
    const fine=.55+.45*vnoise(r*220,5,0)+.2*Math.sin(r*480+vnoise(r*30,9,0)*6);                  // thousands of ringlets
    a=clamp(a*clamp(fine,.25,1.3));const k=.8+.3*vnoise(r*70,7,0);
    g.fillStyle=`rgba(${Math.min(255,col[0]*k)|0},${Math.min(255,col[1]*k)|0},${Math.min(255,col[2]*k)|0},${a})`;g.fillRect(x,0,1,4);}
  return c;}
const ringDens=r=>r<1.53?.18:r<1.95?1:r<2.03?.04:r<2.27?(Math.abs(r-2.21)<.012?.03:.6):r<2.31?.04:.35;
function rayTexture(){const c=document.createElement('canvas');c.width=c.height=512;const g=c.getContext('2d');g.translate(256,256);
  for(let i=0;i<64;i++){const a=Math.random()*TAU,len=110+Math.random()*146,wd=.012+Math.random()*.03;
    const gr=g.createLinearGradient(0,0,Math.cos(a)*len,Math.sin(a)*len);gr.addColorStop(0,'rgba(255,200,110,.55)');gr.addColorStop(1,'rgba(255,160,60,0)');
    g.fillStyle=gr;g.beginPath();g.moveTo(Math.cos(a-wd)*60,Math.sin(a-wd)*60);g.lineTo(Math.cos(a)*len,Math.sin(a)*len);g.lineTo(Math.cos(a+wd)*60,Math.sin(a+wd)*60);g.fill();}
  return c;}
function glowTexture(r,g,b){const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d'),gr=x.createRadialGradient(128,128,0,128,128,128);
  gr.addColorStop(0,`rgba(${r},${g},${b},1)`);gr.addColorStop(.25,`rgba(${r},${g},${b},.55)`);gr.addColorStop(1,`rgba(${r},${g},${b},0)`);x.fillStyle=gr;x.fillRect(0,0,256,256);return c;}

/* ================= SCENE ================= */
const renderer=new THREE.WebGLRenderer({canvas:document.getElementById('gl'),antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
const scene=new THREE.Scene();
const cam=new THREE.PerspectiveCamera(55,1,.1,14000);
function resize(){renderer.setSize(innerWidth,innerHeight);cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();}
addEventListener('resize',resize);resize();
const aniso=renderer.capabilities.getMaxAnisotropy();
const tex=(c,srgb)=>{const t=new THREE.CanvasTexture(c);t.anisotropy=aniso;return t;};

scene.add(new THREE.AmbientLight(0x3a4a75,.7));
const sunLight=new THREE.PointLight(0xfff2dd,1.9,0,1);scene.add(sunLight);

// star field + dark-matter backdrop
scene.background=new THREE.Color(0x02030a);
(function(){const mk=(n,rmin,rspan,lo)=>{const pos=new Float32Array(n*3),col=new Float32Array(n*3);
    for(let i=0;i<n;i++){const u=Math.random()*2-1,t=Math.random()*TAU,s=Math.sqrt(1-u*u),r=rmin+Math.random()*rspan;
      pos.set([r*s*Math.cos(t),r*u,r*s*Math.sin(t)],i*3);const k=lo+Math.random()*(1-lo),h=Math.random(),
        c=h<.2?[.6,.92,1]:h<.32?[1,.7,.95]:h<.45?[1,.92,.7]:[1,1,1];col.set([c[0]*k,c[1]*k,c[2]*k],i*3);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setAttribute('color',new THREE.BufferAttribute(col,3));return g;};
  const star=(()=>{const c=document.createElement('canvas');c.width=c.height=64;const x=c.getContext('2d'),g=x.createRadialGradient(32,32,0,32,32,32);
    g.addColorStop(0,'rgba(255,255,255,1)');g.addColorStop(.18,'rgba(255,255,255,.95)');g.addColorStop(.4,'rgba(255,255,255,.18)');g.addColorStop(1,'rgba(255,255,255,0)');x.fillStyle=g;x.fillRect(0,0,64,64);return new THREE.CanvasTexture(c);})();
  scene.add(new THREE.Points(mk(7000,6000,2000,.7),new THREE.PointsMaterial({size:2.4,sizeAttenuation:false,vertexColors:true,map:star,transparent:true,alphaTest:.05,depthWrite:false})));
  scene.add(new THREE.Points(mk(300,5800,2000,.85),new THREE.PointsMaterial({size:8,sizeAttenuation:false,vertexColors:true,map:star,transparent:true,depthWrite:false})));
  [[70,35,150,-.7,.15,.7,.2],[25,50,150,.8,-.3,-.5,.18],[110,25,110,-.2,.5,-.85,.14],[25,90,130,.3,-.6,.75,.12]].forEach(([r,g,b,x,y,z,o])=>{
    const s=new THREE.Sprite(new THREE.SpriteMaterial({map:tex(glowTexture(r,g,b)),transparent:true,opacity:o,blending:THREE.AdditiveBlending,depthWrite:false}));
    s.position.set(x*5500,y*5500,z*5500);s.scale.set(8000,5500,1);scene.add(s);});
})();

const atmoMat=(col,pow=3)=>new THREE.ShaderMaterial({uniforms:{c:{value:new THREE.Color(col)},p:{value:pow}},transparent:true,side:THREE.BackSide,blending:THREE.AdditiveBlending,depthWrite:false,
  vertexShader:'varying vec3 n;void main(){n=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
  fragmentShader:'uniform vec3 c;uniform float p;varying vec3 n;void main(){float i=pow(max(0.,.62-dot(n,vec3(0.,0.,1.))),p);gl_FragColor=vec4(c*min(i,1.2),1.);}'});

const proxyMat=new THREE.MeshBasicMaterial({visible:false});
const ATMO={earth:[0x4aa8ff,1.14,3],venus:[0xffb35a,1.1,2.4],mars:[0xff9060,1.07,3.4],jupiter:[0xe8c9a0,1.05,3.5],saturn:[0xf0dcaa,1.05,3.5]};
const orbitLines=[];

const SUNFS=`uniform float t;varying vec3 vP;varying vec3 vN;
float hash(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);
  return mix(mix(mix(hash(i),hash(i+vec3(1.,0.,0.)),f.x),mix(hash(i+vec3(0.,1.,0.)),hash(i+vec3(1.,1.,0.)),f.x),f.y),
             mix(mix(hash(i+vec3(0.,0.,1.)),hash(i+vec3(1.,0.,1.)),f.x),mix(hash(i+vec3(0.,1.,1.)),hash(i+vec3(1.,1.,1.)),f.x),f.y),f.z);}
float fbm(vec3 p){float s=0.,a=.5;for(int i=0;i<6;i++){s+=a*noise(p);p=p*2.03+vec3(1.7,9.2,3.1);a*=.5;}return s;}
void main(){vec3 p=vP;
  vec3 q=vec3(fbm(p*3.+t*.03),fbm(p*3.+5.2-t*.025),fbm(p*3.+9.1+t*.02));
  float gr=fbm(p*9.+q*1.6+vec3(0.,0.,t*.06));            // convection granules, flowing
  float cell=smoothstep(.38,.75,gr);
  float spots=smoothstep(.60,.70,fbm(p*2.2+vec3(7.,2.,t*.004)));   // sunspots
  float plage=smoothstep(.55,.8,fbm(p*5.+3.+t*.01));
  vec3 c=mix(vec3(.95,.28,.03),vec3(1.,.82,.35),cell);
  c+=vec3(.5,.35,.1)*plage*.35;c*=1.-spots*.78;
  float mu=clamp(dot(normalize(vN),vec3(0.,0.,1.)),0.,1.);
  c*=.38+.62*pow(mu,.55);                                     // limb darkening
  c+=vec3(.9,.35,.05)*pow(1.-mu,3.)*.35;                      // reddish rim
  gl_FragColor=vec4(c*1.25,1.);}`;
function sunMaterial(){return new THREE.ShaderMaterial({uniforms:{t:{value:0}},
  vertexShader:'varying vec3 vP;varying vec3 vN;void main(){vP=normalize(position);vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:SUNFS});}
function randDir(){const u=Math.random()*2-1,a=Math.random()*TAU,s=Math.sqrt(1-u*u);return new THREE.Vector3(s*Math.cos(a),u,s*Math.sin(a));}
function flareMaterial(R){return new THREE.ShaderMaterial({uniforms:{R:{value:R},grow:{value:0}},transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,
  vertexShader:'uniform float R;uniform float grow;varying float vH;void main(){float r=length(position);vec3 n=position/r;float Rb=R*.985;vH=clamp((r-Rb)/(R*.9),0.,1.);gl_Position=projectionMatrix*modelViewMatrix*vec4(n*(Rb+(r-Rb)*grow),1.);}',
  fragmentShader:'uniform float grow;varying float vH;void main(){vec3 c=mix(vec3(1.,.3,.04),vec3(1.,.85,.5),clamp(vH*1.6,0.,1.));gl_FragColor=vec4(c*1.3,grow*(.45+.55*vH));}'});}
function spawnFlare(f,R){f.meshes.forEach(m=>{f.group.remove(m);m.geometry.dispose();});f.meshes=[];
  const A=randDir(),T=randDir().cross(A).normalize(),span=.1+Math.random()*.4,H=R*(.18+Math.random()*.7)*(span*2.2+.3);
  for(let k=0;k<3;k++){const pts=[],sp=span*(1-.12*k),hh=H*(1+.25*k);
    for(let i=0;i<=24;i++){const u=i/24,ang=sp*(u-.5),pt=A.clone().multiplyScalar(Math.cos(ang)).addScaledVector(T,Math.sin(ang));pts.push(pt.multiplyScalar(R*.985+hh*Math.pow(Math.sin(Math.PI*u),.85)));}
    const m=new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),64,R*(.022-.006*k)*(.6+Math.random()*.8),6,false),f.mat);f.group.add(m);f.meshes.push(m);}
  f.age=0;f.dur=5+Math.random()*8;}
function buildSunFX(b){b.flares=[];for(let i=0;i<8;i++){const f={group:b.group,mat:flareMaterial(b.R),meshes:[]};spawnFlare(f,b.R);f.age=Math.random()*f.dur;b.flares.push(f);}
  b.rays=new THREE.Sprite(new THREE.SpriteMaterial({map:tex(rayTexture()),transparent:true,opacity:.75,blending:THREE.AdditiveBlending,depthWrite:false}));
  b.rays.scale.set(b.R*16,b.R*16,1);b.group.add(b.rays);}
function buildRingRocks(b){const R=b.R,N=7000,geo=new THREE.IcosahedronGeometry(1,0),
    im=new THREE.InstancedMesh(geo,new THREE.MeshStandardMaterial({roughness:.95,flatShading:true}),N),col=new THREE.Color();
  const rr=new Float32Array(N),th=new Float32Array(N),ww=new Float32Array(N),yy=new Float32Array(N),qs=[],ss=[];
  for(let i=0;i<N;i++){let r;do{r=1.26+Math.random()*1.08;}while(Math.random()>ringDens(r));
    rr[i]=r*R;th[i]=Math.random()*TAU;ww[i]=.05*Math.pow(1.6/r,1.5);yy[i]=(Math.random()-.5)*R*.01;
    const sz=R*(.005+Math.pow(Math.random(),4)*.05);ss.push(new THREE.Vector3(sz,sz*(.55+Math.random()*.5),sz*(.7+Math.random()*.5)));
    qs.push(new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.random()*TAU,Math.random()*TAU,Math.random()*TAU)));
    col.setHSL(.09,.2+Math.random()*.2,.35+Math.random()*.45);im.setColorAt(i,col);}
  im.frustumCulled=false;b.group.add(im);b.rocks={im,rr,th,ww,yy,qs,ss};
  const NP=24000,pp=new Float32Array(NP*3),pc=new Float32Array(NP*3);
  for(let i=0;i<NP;i++){let r;do{r=1.26+Math.random()*1.08;}while(Math.random()>ringDens(r));const a=Math.random()*TAU,k=.5+Math.random()*.5;
    pp.set([Math.cos(a)*r*R,(Math.random()-.5)*R*.012,Math.sin(a)*r*R],i*3);pc.set([k*.9,k*.82,k*.68],i*3);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pp,3));g.setAttribute('color',new THREE.BufferAttribute(pc,3));
  b.dust=new THREE.Points(g,new THREE.PointsMaterial({size:1.3,sizeAttenuation:false,vertexColors:true,transparent:true,opacity:.45,depthWrite:false}));
  b.dust.frustumCulled=false;b.group.add(b.dust);}
function shell(b,canvas,scale,spin){const m=new THREE.Mesh(new THREE.SphereGeometry(b.R*scale,96,72),
    new THREE.MeshStandardMaterial({map:tex(canvas),transparent:true,depthWrite:false,roughness:1}));m.userData.spin=spin;b.group.add(m);b.haze=m;return m;}

function buildBody(b,canvasMap){
  b.group=new THREE.Group();b.group.rotation.z=b.tilt||0;
  const geo=new THREE.SphereGeometry(b.R,160,112);let mat;
  if(b.id==='sun'){b.sunMat=sunMaterial();mat=b.sunMat;}
  else{const rocky=['mercury','moon','mars'].includes(b.id);
    mat=new THREE.MeshStandardMaterial({map:tex(canvasMap),roughness:rocky?.97:.8,metalness:0});
    const bump={mercury:2.6,moon:2.6,mars:1.8,earth:.6}[b.id];if(bump){mat.bumpMap=mat.map;mat.bumpScale=bump;}}
  b.mesh=new THREE.Mesh(geo,mat);b.group.add(b.mesh);
  if(b.id==='sun'){[[255,150,40,7,.9],[255,210,120,3.4,.8]].forEach(([r,g,bl,s,o])=>{
      const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:tex(glowTexture(r,g,bl)),transparent:true,opacity:o,blending:THREE.AdditiveBlending,depthWrite:false}));
      sp.scale.set(b.R*s*2,b.R*s*2,1);b.group.add(sp);});buildSunFX(b);}
  if(ATMO[b.id]){const[a,s,p]=ATMO[b.id],m=new THREE.Mesh(new THREE.SphereGeometry(b.R*s,64,48),atmoMat(a,p));b.group.add(m);}
  if(b.id==='earth'){b.clouds=new THREE.Mesh(new THREE.SphereGeometry(b.R*1.012,96,72),
      new THREE.MeshStandardMaterial({map:tex(paint(2048,1024,RECIPE.clouds)),transparent:true,depthWrite:false,roughness:1}));b.group.add(b.clouds);}
  if(b.id==='venus')shell(b,paint(2048,1024,RECIPE.venusHaze),1.01,-.03);
  if(b.id==='jupiter'||b.id==='saturn')shell(b,paint(2048,1024,RECIPE.bandHaze),1.006,b.spin*1.07);
  if(b.id==='saturn'){const inner=b.R*1.25,outer=b.R*2.35,rg=new THREE.RingGeometry(inner,outer,256,1),uv=rg.attributes.uv,p=rg.attributes.position;
    for(let i=0;i<uv.count;i++)uv.setXY(i,(Math.hypot(p.getX(i),p.getY(i))-inner)/(outer-inner),.5);
    // ring shader: textured bands, plus the planet's shadow falling across the rings (sun is at the origin)
    b.ringMat=new THREE.ShaderMaterial({uniforms:{map:{value:tex(ringTexture())},uC:{value:new THREE.Vector3()},uR:{value:b.R}},transparent:true,side:THREE.DoubleSide,depthWrite:false,
      vertexShader:'varying vec2 vUv;varying vec3 vW;void main(){vUv=uv;vW=(modelMatrix*vec4(position,1.)).xyz;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
      fragmentShader:'uniform sampler2D map;uniform vec3 uC;uniform float uR;varying vec2 vUv;varying vec3 vW;void main(){vec4 t=texture2D(map,vUv);vec3 d=normalize(-vW),oc=vW-uC;float bb=dot(oc,d),disc=bb*bb-(dot(oc,oc)-uR*uR),sh=0.;if(disc>0.&&(-bb-sqrt(disc))>0.)sh=smoothstep(0.,uR*uR*.06,disc);gl_FragColor=vec4(t.rgb*(1.-.88*sh),t.a);}'});
    const ring=new THREE.Mesh(rg,b.ringMat);ring.rotation.x=-Math.PI/2;b.group.add(ring);buildRingRocks(b);}
  b.proxy=new THREE.Mesh(new THREE.SphereGeometry(1,12,8),proxyMat);b.proxy.userData.body=b;scene.add(b.proxy);
  scene.add(b.group);
  if(b.dist&&!b.parent){const pts=[];for(let i=0;i<=256;i++){const a=i/256*TAU;pts.push(new THREE.Vector3(Math.cos(a)*b.dist,0,Math.sin(a)*b.dist));}
    const l=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0x4fc8e6,transparent:true,opacity:.16}));scene.add(l);orbitLines.push(l);}
  b.pos=new THREE.Vector3();b.vis=1;b.ang=b.phase??Math.random()*TAU;
}

/* ================= UI ================= */
const $=id=>document.getElementById(id);
const ZERO=new THREE.Vector3(),Y=new THREE.Vector3(0,1,0),SYS={pos:ZERO,R:0};
let hovBody=null,hovTag=null,popBody=null;
let selected=null,focus=null,mode='locked',expanded=false,paused=false;
const stars=n=>'★'.repeat(n)+'<span style="opacity:.25">'+'★'.repeat(5-n)+'</span>';
const habCol=h=>`hsl(${Math.round(h*1.2)},85%,55%)`;   // 0% = red, 50% = yellow, 100% = green
const tierOf=h=>h>66?'Prime':h>25?'Marginal':h>5?'Hostile':'Uninhabitable';
const kc=k=>`<kbd>${k}</kbd>`;
function buildList(){$('rows').innerHTML=RANK.map((b,i)=>`<div class="row" data-id="${b.id}"><span class="rk">${i+1}</span>
  <div><div class="nm">${b.name}</div><div class="cl" style="color:${b.color}">${b.cls}</div><div class="mini"><i style="width:${b.hab}%;background:${habCol(b.hab)}"></i></div></div><span class="pc" style="color:${habCol(b.hab)}">${b.hab}%</span></div>`).join('');
  document.querySelectorAll('.row').forEach(r=>{r.onclick=()=>pick(byId(r.dataset.id));});}
function renderInfo(){const b=selected,el=$('info');
  el.classList.toggle('open',expanded&&!!b);
  if(!b){el.innerHTML='';return;}
  const segs=Array.from({length:10},(_,i)=>`<i class="${i<Math.round(b.hab/10)?'f':''}" style="--c:${habCol(b.hab)}"></i>`).join('');
  el.innerHTML=`<h2>All gathered information <span style="float:right">${kc('R')} close</span></h2><p class="nm">${b.name.toUpperCase()}</p><span class="chip" style="color:${b.color};border-color:${b.color}">${b.cls}</span>
  <div style="color:var(--mute);font-size:11px;letter-spacing:.08em">Weather: ${b.weather}</div><p class="blurb">${b.blurb}</p>
  <div class="habn"><span>Habitability - ${tierOf(b.hab)}</span><b style="color:${habCol(b.hab)}">${b.hab}%</b></div><div class="hab">${segs}</div>
  ${Object.keys(WEIGHTS).map(k=>`<div class="sub"><span>${SUBLABEL[k]}</span><div><i style="width:${b.sub[k]*10}%"></i></div><span>${b.sub[k]}</span></div>`).join('')}
  <div class="sec">Planetary data</div><div class="facts">${b.facts.map(f=>`<div><small>${f[0]}</small>${f[1]}</div>`).join('')}</div>
  <div class="sec">Valuable resources</div>${b.res.map(r=>`<div class="res"><div class="sy" style="color:${b.color}">${r[0]}</div><div><b>${r[1]}</b><small>${r[2]}</small></div><span class="st">${stars(r[3])}</span></div>`).join('')}
  <div class="sec">Hazards</div><div class="haz">${b.hazards.map(h=>`<span>${h}</span>`).join('')}</div>
  ${focus?'':`<button id="warpbtn">${mode==='roam'?'Warp to ':'Close-up of '}${b.name}</button>`}`;
  const wb=$('warpbtn');if(wb)wb.onclick=()=>warpTo(b);}
function renderPop(b){const el=$('pop');if(!b){el.innerHTML='';return;}
  const top=[...b.res].sort((a,c)=>c[3]-a[3]).slice(0,5);
  el.innerHTML=`<div class="ph"><b>${b.name}</b><span>${b.id==='earth'?'Home world':b.id==='sun'?'Primary star':'Sol system'}</span></div>
  <div class="pb"><div class="pc" style="color:${b.color}">${b.cls}</div><div class="pm">Habitability <b style="color:${habCol(b.hab)}">${b.hab}%</b> - ${tierOf(b.hab)}</div>
  <ul>${top.map((r,i)=>`<li class="${i===0?'hi':''}">${r[1]}</li>`).join('')}</ul>
  <div class="pa">${kc('Click')}<div><b>EXPAND</b><small>View all information gathered on this body</small></div></div></div>`;}
function updateTourLabel(){const i=selected?RANK.indexOf(selected):-1;$('tourbar').style.display=focus?'flex':'none';
  $('tourlabel').textContent=selected?`${i+1} / ${RANK.length}  -  ${selected.name}`:'';}
function updateFoot(){let c,r='';
  if(mode==='roam'){c=`${kc('Space')} Lock view &nbsp; ${kc('W')}${kc('A')}${kc('S')}${kc('D')} fly &nbsp; ${kc('Shift')} boost &nbsp; ${selected?kc('F')+' Warp to '+selected.name+' &nbsp; '+kc('R')+' Expand':''}`;if(selected)r='Deselect';}
  else if(focus){c=`${kc('←')}${kc('→')} Next body &nbsp; ${kc('R')} Expand &nbsp; ${kc('Space')} Enter free-look`;r='Return to system';}
  else{c=`${kc('Space')} Enter free-look &nbsp; ${kc('←')}${kc('→')} Select &nbsp; ${selected?kc('R')+' Panel &nbsp; '+kc('Enter')+' Close-up':'Hover for a summary, click to expand'}`;if(selected)r='Deselect';}
  $('footc').innerHTML=c;$('footr').innerHTML=r?kc('Esc')+' '+r:'';}
function select(b){selected=b;document.querySelectorAll('.row').forEach(r=>r.classList.toggle('sel',r.dataset.id===b?.id));
  DATA.forEach(d=>{if(d.tag){d.tag.classList.toggle('sel',d===b);d.halo.classList.toggle('sel',d===b);}});
  expanded=!!b;renderInfo();updateTourLabel();updateFoot();}
function setExpanded(v){expanded=v&&!!selected;renderInfo();}
function enterFocus(b){focus=b;expanded=true;select(b);startWarp(b,'tour');updateTourLabel();updateFoot();}
function leaveFocus(){focus=null;expanded=false;renderInfo();startWarp(SYS,'sys');updateTourLabel();updateFoot();}
const pick=b=>focus?enterFocus(b):select(b);
function step(d){const i=selected?RANK.indexOf(selected):-1,b=RANK[(i+d+RANK.length)%RANK.length];pick(b);}
function setMode(m){if(m===mode)return;mode=m;$('m-lock').classList.toggle('on',m==='locked');$('m-roam').classList.toggle('on',m==='roam');
  if(m==='roam'){warp=null;$('warptxt').style.opacity=0;focus=null;cam.fov=55;cam.updateProjectionMatrix();const e=new THREE.Euler().setFromQuaternion(cam.quaternion,'YXZ');yaw=e.y;pitch=e.x;}
  else{focus=null;expanded=false;startWarp(SYS,'sys');}
  renderInfo();updateTourLabel();updateFoot();}
$('m-lock').onclick=()=>setMode('locked');$('m-roam').onclick=()=>setMode('roam');
$('prev').onclick=()=>step(-1);$('next').onclick=()=>step(1);
document.addEventListener('click',e=>{if(e.target.tagName==='BUTTON')e.target.blur();});

/* ================= CAMERA ================= */
let warp=null,yaw=0,pitch=0,orb={theta:.6,phi:1.3,r:30},sys={theta:.7,phi:1.05,r:760},dragging=false;const keys={};
function startWarp(b,m){const fromPos=cam.position.clone(),fwd=new THREE.Vector3(0,0,-1).applyQuaternion(cam.quaternion),fromLook=fromPos.clone().addScaledVector(fwd,200);
  let dir,dist;
  if(m==='sys'){dir=new THREE.Vector3(Math.sin(sys.phi)*Math.sin(sys.theta),Math.cos(sys.phi),Math.sin(sys.phi)*Math.cos(sys.theta));dist=sys.r;}
  else if(m==='tour'){dir=b.pos.length()>1?b.pos.clone().negate().normalize():new THREE.Vector3(.3,.2,1);dir.applyAxisAngle(Y,.8);dir.y+=.25;dir.normalize();dist=b.R*3.4;}
  else{dir=fromPos.clone().sub(b.pos).normalize();dist=b.R*5;}
  warp={t:0,dur:Math.min(3.4,1.3+fromPos.distanceTo(b.pos.lengthSq()?b.pos:ZERO)/320),fromPos,fromLook,dir,dist,body:b,mode:m};$('warptxt').style.opacity=1;}
function warpTo(b){if(!b)return;if(mode==='roam'){select(b);startWarp(b,'roam');}else enterFocus(b);}
function finishWarp(){const w=warp;warp=null;$('warptxt').style.opacity=0;cam.fov=55;cam.updateProjectionMatrix();
  if(w.mode==='tour'){const o=cam.position.clone().sub(w.body.pos),r=o.length();orb={theta:Math.atan2(o.x,o.z),phi:Math.acos(clamp(o.y/r,-1,1)),r};}
  else if(w.mode==='roam'){const e=new THREE.Euler().setFromQuaternion(cam.quaternion,'YXZ');yaw=e.y;pitch=e.x;}}
const tmp=new THREE.Vector3();
function updateCamera(dt){
  if(warp){warp.t+=dt;const k=Math.min(1,warp.t/warp.dur),e=k<.5?4*k*k*k:1-Math.pow(-2*k+2,3)/2;
    const target=warp.body.pos.clone().addScaledVector(warp.dir,warp.dist);
    cam.position.lerpVectors(warp.fromPos,target,e);cam.position.y+=Math.sin(Math.PI*e)*Math.min(160,warp.fromPos.distanceTo(target)*.2);
    cam.lookAt(tmp.lerpVectors(warp.fromLook,warp.body.pos,e));cam.fov=55+Math.sin(Math.PI*k)*26;cam.updateProjectionMatrix();
    if(k>=1)finishWarp();return;}
  if(mode==='locked'){
    if(focus){const b=focus;orb.phi=clamp(orb.phi,.15,Math.PI-.15);orb.r=clamp(orb.r,b.R*1.6,b.R*14);
      cam.position.set(b.pos.x+orb.r*Math.sin(orb.phi)*Math.sin(orb.theta),b.pos.y+orb.r*Math.cos(orb.phi),b.pos.z+orb.r*Math.sin(orb.phi)*Math.cos(orb.theta));cam.lookAt(b.pos);}
    else{sys.phi=clamp(sys.phi,.12,Math.PI-.12);sys.r=clamp(sys.r,160,2400);
      cam.position.set(sys.r*Math.sin(sys.phi)*Math.sin(sys.theta),sys.r*Math.cos(sys.phi),sys.r*Math.sin(sys.phi)*Math.cos(sys.theta));cam.lookAt(ZERO);}
    return;}
  let near=1e9;for(const b of DATA)near=Math.min(near,cam.position.distanceTo(b.pos)-b.R*b.vis);
  const sp=clamp(near*.9,6,700)*(keys.shift?4:1),fwd=new THREE.Vector3(0,0,-1).applyQuaternion(cam.quaternion),right=new THREE.Vector3(1,0,0).applyQuaternion(cam.quaternion),mv=new THREE.Vector3();
  if(keys.w)mv.add(fwd);if(keys.s)mv.sub(fwd);if(keys.d)mv.add(right);if(keys.a)mv.sub(right);if(keys.e)mv.y+=1;if(keys.q)mv.y-=1;
  if(mv.lengthSq())cam.position.addScaledVector(mv.normalize(),sp*dt);
  for(const b of DATA){const d=cam.position.distanceTo(b.pos),m=b.R*b.vis*1.08;if(d<m)cam.position.sub(b.pos).setLength(m).add(b.pos);}
  cam.quaternion.setFromEuler(new THREE.Euler(pitch,yaw,0,'YXZ'));}

/* ================= INPUT ================= */
const cv=$('gl'),ray=new THREE.Raycaster();let down=null;
cv.addEventListener('pointerdown',e=>{if(e.button!==0)return;down={x:e.clientX,y:e.clientY,moved:0};dragging=true;cv.setPointerCapture(e.pointerId);});
function hoverAt(e){const r=cv.getBoundingClientRect();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-((e.clientY-r.top)/r.height)*2+1),cam);
  const hit=ray.intersectObjects(DATA.map(b=>b.proxy))[0];hovBody=hit?hit.object.userData.body:null;cv.style.cursor=hit?'pointer':'';}
cv.addEventListener('pointerleave',()=>{hovBody=null;});
cv.addEventListener('pointermove',e=>{if(!down){if(!focus)hoverAt(e);return;}const dx=e.clientX-down.x,dy=e.clientY-down.y;down.x=e.clientX;down.y=e.clientY;down.moved+=Math.abs(dx)+Math.abs(dy);
  if(warp)return;if(mode==='locked'){const o=focus?orb:sys;o.theta-=dx*.005;o.phi-=dy*.005;}else{yaw-=dx*.0032;pitch=clamp(pitch-dy*.0032,-1.5,1.5);}});
cv.addEventListener('pointerup',e=>{dragging=false;if(down&&down.moved<5&&!focus){const r=cv.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-((e.clientY-r.top)/r.height)*2+1),cam);
    const hit=ray.intersectObjects(DATA.map(b=>b.proxy))[0];if(hit)select(hit.object.userData.body);else if(selected)select(null);}down=null;});
cv.addEventListener('wheel',e=>{e.preventDefault();if(warp)return;
  if(mode==='locked'){const o=focus?orb:sys;o.r*=1+e.deltaY*.001;}
  else cam.position.addScaledVector(new THREE.Vector3(0,0,-1).applyQuaternion(cam.quaternion),-e.deltaY*.05*Math.max(2,cam.position.length()*.01));},{passive:false});
function goBack(){if(focus)leaveFocus();else if(selected)select(null);}
addEventListener('contextmenu',e=>{e.preventDefault();goBack();});
addEventListener('keydown',e=>{const k=e.key.toLowerCase();
  if(k==='shift'){keys.shift=true;return;}
  if(k===' '){e.preventDefault();setMode(mode==='locked'?'roam':'locked');return;}
  if(k==='arrowright'&&mode==='locked'){step(1);return;}
  if(k==='arrowleft'&&mode==='locked'){step(-1);return;}
  if(k==='escape'){goBack();return;}
  if(k==='r'){if(selected)setExpanded(!expanded);return;}
  if(k==='p'){paused=!paused;return;}
  if((k==='enter'||k==='f')&&selected){if(mode==='roam')warpTo(selected);else if(k==='enter'&&!focus)enterFocus(selected);return;}
  if(mode==='roam'&&k.length===1&&'wasdqe'.includes(k))keys[k]=true;});
addEventListener('keyup',e=>{const k=e.key.toLowerCase();if(k==='shift')keys.shift=false;else keys[k]=false;});
addEventListener('blur',()=>{for(const k in keys)keys[k]=false;});

/* ================= LOOP ================= */
const links=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0xb4bfff,transparent:true,opacity:.2}));links.frustumCulled=false;
let linkPairs=[];
function updateBodies(dt){const run=!paused&&!selected;   // orbits hold still while a body is selected
  for(const b of DATA){
    if(b.parent){const p=byId(b.parent);if(run)b.ang+=b.w*dt;const off=b.dist*(1+(p.vis-1)*1.3);b.pos.set(p.pos.x+Math.cos(b.ang)*off,0,p.pos.z+Math.sin(b.ang)*off);b.mesh.rotation.y=-b.ang+Math.PI;}
    else{if(run&&b.dist)b.ang+=b.w*dt;b.pos.set(Math.cos(b.ang)*b.dist,0,Math.sin(b.ang)*b.dist);if(!paused&&b.spin)b.mesh.rotation.y+=b.spin*dt;}
    // map-style scaling: far away bodies are drawn bigger so they stay readable; up close they are true to the scene scale
    const dc=cam.position.distanceTo(b.pos);b.vis=b.id==='sun'?clamp(dc*.014/b.R,1,2.2):clamp(dc*(.012+b.R*.0012)/b.R,1,8);
    b.group.scale.setScalar(b.vis);b.group.position.copy(b.pos);if(b.clouds&&!paused)b.clouds.rotation.y+=b.spin*1.25*dt;
    if(b.haze&&!paused)b.haze.rotation.y+=b.haze.userData.spin*dt;
    if(b.ringMat){b.ringMat.uniforms.uC.value.copy(b.pos);b.ringMat.uniforms.uR.value=b.R*b.vis;}
    b.proxy.position.copy(b.pos);b.proxy.scale.setScalar(Math.max(b.R*b.vis*1.15,dc*.03));}
  const a=links.geometry.attributes.position.array;linkPairs.forEach(([p,c],i)=>{a.set([p.pos.x,p.pos.y,p.pos.z,c.pos.x,c.pos.y,c.pos.z],i*6);});
  links.geometry.attributes.position.needsUpdate=true;links.visible=!focus;}
function updateOverlays(){const ov=!focus&&!(warp&&warp.mode==='tour'),f=innerHeight/2/Math.tan(cam.fov*Math.PI/360),pop=$('pop');let popOk=false;const hovered=focus?null:(hovTag||hovBody);if(hovered!==popBody){popBody=hovered;renderPop(hovered);}
  for(const b of DATA){const v=tmp.copy(b.pos).project(cam);
    if(!ov||v.z>1||Math.abs(v.x)>1.08||Math.abs(v.y)>1.08){b.tag.style.display='none';b.halo.style.display='none';continue;}
    const sx=(v.x+1)/2*innerWidth,sy=(1-v.y)/2*innerHeight,px=Math.max(b.R*b.vis/cam.position.distanceTo(b.pos)*f,5),hs=px*2*1.45;
    b.halo.style.display='block';b.halo.style.left=sx+'px';b.halo.style.top=sy+'px';b.halo.style.width=b.halo.style.height=hs+'px';
    b.tag.style.display='block';b.tag.style.left=(sx+px*.8+6)+'px';b.tag.style.top=(sy+px*1.0+2)+'px';
    if(b===hovered&&!(b===selected&&expanded)){popOk=true;pop.style.display='block';const w=pop.offsetWidth,h=pop.offsetHeight;
      let x=sx+px*1.5+26;if(x+w>innerWidth-16)x=sx-px*1.5-26-w;pop.style.left=clamp(x,12,innerWidth-w-12)+'px';pop.style.top=clamp(sy-70,70,innerHeight-h-50)+'px';}}
  if(!popOk)pop.style.display='none';}
const clock=new THREE.Clock(),_m=new THREE.Matrix4(),_p=new THREE.Vector3();
function updateFX(dt){const t=clock.elapsedTime,sun=byId('sun');
  if(sun.sunMat){sun.sunMat.uniforms.t.value=t;sun.rays.material.rotation=t*.02;
    sun.flares.forEach(f=>{f.age+=dt;if(f.age>=f.dur)spawnFlare(f,sun.R);const a=f.age/f.dur;f.mat.uniforms.grow.value=Math.pow(Math.sin(Math.PI*Math.min(a,1)),.7)*(1+.05*Math.sin(t*4+f.dur));});}
  const s=byId('saturn');
  if(s.rocks&&!paused){s.dust.rotation.y+=.012*dt;const k=s.rocks;
    if(cam.position.distanceTo(s.pos)<s.R*s.vis*70){   // farther away the rocks are sub-pixel, so skip the work
      for(let i=0;i<k.rr.length;i++){k.th[i]+=k.ww[i]*dt;_p.set(Math.cos(k.th[i])*k.rr[i],k.yy[i],Math.sin(k.th[i])*k.rr[i]);_m.compose(_p,k.qs[i],k.ss[i]);k.im.setMatrixAt(i,_m);}
      k.im.instanceMatrix.needsUpdate=true;}}}
function frame(){requestAnimationFrame(frame);const dt=Math.min(.05,clock.getDelta());updateBodies(dt);updateFX(dt);updateCamera(dt);updateOverlays();renderer.render(scene,cam);}

/* ================= BOOT ================= */
function boot(){buildList();
  DATA.forEach(b=>{const h=document.createElement('div');h.className='halo';$('hud').appendChild(h);b.halo=h;
    const t=document.createElement('div');t.className='tag';t.textContent=b.name;t.onclick=()=>pick(b);t.onmouseenter=()=>{hovTag=b;};t.onmouseleave=()=>{hovTag=null;};$('hud').appendChild(t);b.tag=t;});
  linkPairs=DATA.filter(b=>b.id!=='sun').map(b=>[b.parent?byId(b.parent):byId('sun'),b]);
  links.geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(linkPairs.length*6),3));scene.add(links);
  $('pop').style.display='none';updateFoot();updateTourLabel();
  requestAnimationFrame(frame);
  $('loading').style.opacity=0;setTimeout(()=>$('loading').remove(),900);}
(async function generate(){const n=DATA.length;
  for(let i=0;i<n;i++){const b=DATA[i];$('loadmsg').textContent='synthesising '+b.name.toLowerCase()+'...';
    const canvas=b.id==='sun'?null:await paintAsync(2048,1024,RECIPE[b.id],f=>{$('barfill').style.width=((i+f)/n*100)+'%';});buildBody(b,canvas);}
  boot();})();
</script>
</body>
</html>
"""


def ensure_three():
    if THREE_FILE.exists():
        return
    try:
        print("Downloading three.js (one time)...")
        req = urllib.request.Request(THREE_URL, headers={"User-Agent": "Mozilla/5.0"})
        THREE_FILE.write_bytes(urllib.request.urlopen(req, timeout=20).read())
    except Exception as exc:  # page falls back to the CDN
        print(f"  could not cache three.js ({exc}); the page will load it from the CDN instead")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    ensure_three()
    OUT_FILE.write_text(HTML, encoding="utf-8")
    print(f"Built {OUT_FILE}")

    if args.serve:
        port = 8001

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(OUT_DIR), **k)

        with socketserver.TCPServer(("", port), Handler) as srv:
            url = f"http://localhost:{port}/"
            print(f"Serving {url}  (Ctrl+C to stop)")
            if not args.no_open:
                webbrowser.open(url)
            try:
                srv.serve_forever()
            except KeyboardInterrupt:
                pass
    elif not args.no_open:
        webbrowser.open(OUT_FILE.as_uri())


if __name__ == "__main__":
    main()
