#!/usr/bin/env python3
# make_vybe.py — creates the whole Vybe app in the current folder.
# Run:  python make_vybe.py
import json, os, subprocess, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ===================== index.html (frontend) =====================
INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Vybe</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1"></script>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  :root{--red:#fe2c55;--bg:#000;--line:#222}
  html,body{height:100%;background:var(--bg);color:#fff;font-family:system-ui,sans-serif;overscroll-behavior:none}
  a{color:#fff;text-decoration:none}
  button{font-family:inherit}
  .view{height:100dvh;display:flex;flex-direction:column}
  .feed{flex:1;overflow-y:scroll;scroll-snap-type:y mandatory;scrollbar-width:none}
  .feed::-webkit-scrollbar{display:none}
  .card{position:relative;height:100dvh;scroll-snap-align:start;background:#111}
  .card video{width:100%;height:100%;object-fit:cover}
  .overlay{position:absolute;inset:auto 0 0 0;padding:14px 14px 70px;display:flex;justify-content:space-between;align-items:flex-end;gap:10px;background:linear-gradient(transparent,rgba(0,0,0,.65))}
  .who{display:flex;align-items:center;gap:10px;margin-bottom:6px;cursor:pointer}
  .who img{width:36px;height:36px;border-radius:50%;object-fit:cover;background:#333}
  .uname{font-weight:700}.cap{font-size:14px;opacity:.9;max-width:70vw}
  .meta{font-size:12px;opacity:.6;margin-top:4px}
  .acts{display:flex;flex-direction:column;gap:16px;align-items:center}
  .acts button{background:none;border:none;color:#fff;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:3px;font-size:12px}
  .acts .ic{font-size:30px;line-height:1}
  .liked .ic{color:var(--red)}
  .follow{background:none;border:1px solid var(--red);color:var(--red);border-radius:6px;padding:2px 10px;font-weight:700;font-size:13px;cursor:pointer}
  .following{border-color:#555;color:#999}
  .nav{height:58px;display:flex;justify-content:space-around;align-items:center;background:#0a0a0a;border-top:1px solid var(--line);flex-shrink:0}
  .nav a{display:flex;flex-direction:column;align-items:center;font-size:11px;opacity:.6;position:relative;gap:2px}
  .nav a.active{opacity:1;font-weight:700}
  .nav .plus{width:42px;height:28px;background:#fff;color:#000;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:18px;opacity:1!important}
  .badge{position:absolute;top:-4px;right:-10px;background:var(--red);color:#fff;font-size:10px;font-weight:700;border-radius:10px;padding:1px 5px}
  .page{flex:1;overflow-y:auto;padding:20px;max-width:520px;width:100%;margin:0 auto}
  h2{margin-bottom:16px}
  label{display:block;font-size:13px;opacity:.7;margin:12px 0 4px}
  input,textarea{width:100%;background:#161616;border:1px solid #333;color:#fff;border-radius:10px;padding:12px;font-size:15px}
  textarea{resize:vertical;min-height:70px}
  .btn{width:100%;background:var(--red);border:none;color:#fff;font-weight:700;font-size:16px;padding:13px;border-radius:10px;margin-top:18px;cursor:pointer}
  .btn:disabled{opacity:.5}
  .btn.gray{background:#222;color:#fff}
  .small{font-size:13px;opacity:.6;margin-top:14px;text-align:center}
  .err{color:var(--red);font-size:13px;margin-top:10px;min-height:18px}
  .bar{height:6px;background:#222;border-radius:3px;margin-top:12px;overflow:hidden;display:none}
  .bar div{height:100%;width:0%;background:var(--red)}
  .phead{display:flex;gap:16px;align-items:center}
  .phead img.big{width:80px;height:80px;border-radius:50%;object-fit:cover;background:#333;cursor:pointer}
  .pstats{display:flex;gap:22px;font-size:14px}
  .pstats b{display:block;font-size:17px}
  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;margin-top:16px}
  .grid .g{position:relative;aspect-ratio:9/14;background:#161616;cursor:pointer;overflow:hidden}
  .grid img{width:100%;height:100%;object-fit:cover}
  .grid .g .pl{position:absolute;bottom:6px;left:8px;font-size:12px;font-weight:700;pointer-events:none}
  .sheet{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;z-index:50}
  .sheet .inner{position:absolute;bottom:0;left:0;right:0;max-height:70dvh;background:#111;border-radius:16px 16px 0 0;padding:16px;display:flex;flex-direction:column}
  .clist{overflow-y:auto;flex:1;margin:10px 0}
  .cmt{margin-bottom:14px;font-size:14px}
  .cmt b{margin-right:6px}
  .cmt .t{color:#888;font-size:11px;margin-left:6px}
  .nrow{display:flex;gap:10px;padding:12px 0;border-bottom:1px solid var(--line);font-size:14px;align-items:center}
  .nrow.unread{background:#141414}
  .nrow img{width:34px;height:34px;border-radius:50%;background:#333;object-fit:cover}
  .toast{position:fixed;top:14px;left:50%;transform:translateX(-50%);background:#222;padding:10px 18px;border-radius:10px;font-size:14px;z-index:99;max-width:90vw}
  .banner{background:#331111;color:#fbb;padding:8px 14px;font-size:13px;text-align:center}
</style>
</head>
<body>
<div id="app" class="view"></div>
<div id="sheet" class="sheet"><div class="inner" id="sheetInner"></div></div>

<script>
const $=s=>document.querySelector(s), app=$('#app');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ago=t=>{const d=(Date.now()-new Date(t))/1e3;return d<60?'now':d<3600?~~(d/60)+'m':d<86400?~~(d/3600)+'h':~~(d/86400)+'d'};
const av=u=>u?esc(u):'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="%23333"/><text x="20" y="26" text-anchor="middle" fill="%23999" font-size="18">?</text></svg>';

function toast(m){const t=document.createElement('div');t.className='toast';t.textContent=m;document.body.appendChild(t);setTimeout(()=>t.remove(),2600)}

async function api(path,opts={}){
  const o={credentials:'include',...opts};
  if(o.json){o.method=o.method||'POST';o.headers={'Content-Type':'application/json'};o.body=JSON.stringify(o.json);delete o.json}
  const r=await fetch(path,o);
  if(r.status===401&&path!=='/api/me')location.hash='#/login';
  const d=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(d.error||r.statusText);
  return d;
}
function upload(path,form,onProgress){return new Promise((res,rej)=>{
  const x=new XMLHttpRequest();x.open('POST',path);x.withCredentials=true;
  x.upload.onprogress=e=>onProgress&&onProgress(e.loaded/e.total);
  x.onload=()=>{try{const d=JSON.parse(x.responseText);x.status<300?res(d):rej(new Error(d.error||'Upload failed'))}catch{rej(new Error('Bad response'))}};
  x.onerror=()=>rej(new Error('Network error'));x.send(form)})}

let me=null, apiUp=true;

const feedState={videos:[],cursor:null,loading:false};

const DEMO=[
 {id:'d1',username:'bunny',avatar_url:null,caption:'demo mode - API not connected yet',src:'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',likes:1200,comments:3,liked:false,following:false,views:4200},
 {id:'d2',username:'dream',avatar_url:null,caption:'elephants dream a lil',src:'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',likes:340,comments:1,liked:false,following:false,views:800},
 {id:'d3',username:'blaze',avatar_url:null,caption:'fire fire fire',src:'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',likes:89,comments:0,liked:false,following:false,views:120},
];

const fmt=n=>n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(1)+'K':n;
function cardHTML(v){return `
 <section class="card" data-id="${esc(v.id)}">
  <video src="${esc(v.src)}" loop muted playsinline preload="metadata" poster="${esc(v.thumb||'')}"></video>
  <div class="overlay">
   <div>
    <div class="who" data-go="#/profile/${esc(v.username)}">
      <img src="${av(v.avatar_url)}"><span class="uname">@${esc(v.username)}</span>
      ${me&&!v.own?`<button class="follow ${v.following?'following':''}" data-follow="${esc(v.username)}">${v.following?'✓':'+'}</button>`:''}
    </div>
    <div class="cap">${esc(v.caption)}</div>
    <div class="meta">${v.views??0} views</div>
   </div>
   <div class="acts">
    <button class="like ${v.liked?'liked':''}" data-like="${esc(v.id)}"><span class="ic">♥</span><span class="count">${fmt(v.likes)}</span></button>
    <button data-comments="${esc(v.id)}"><span class="ic">💬</span><span>${fmt(v.comments)}</span></button>
   </div>
  </div>
 </section>`}

async function loadFeed(){
  if(feedState.loading)return; feedState.loading=true;
  try{
    const d=apiUp?await api('/api/feed'+(feedState.cursor?`?cursor=${feedState.cursor}`:'')):null;
    const vids=d?d.videos:DEMO;
    feedState.cursor=d?.next_cursor||null;
    const f=$('#feed'); const sentinel=()=>f.querySelector('.sentinel');
    vids.forEach(v=>{if(!feedState.videos.find(x=>x.id===v.id)){feedState.videos.push(v);f.insertAdjacentHTML('beforeend',cardHTML(v))}});
    watchCards();
    if(!sentinel()){f.insertAdjacentHTML('beforeend','<div class="sentinel" style="height:1px"></div>');
      new IntersectionObserver(async es=>{if(es[0].isIntersecting&&feedState.cursor)await loadFeed()},{root:f}).observe(sentinel())}
  }catch(e){ if(feedState.videos.length===0){$('#feed').innerHTML=`<div class="page"><h2>API offline</h2><p class="small">Start your server, or wait - showing demo videos. (${esc(e.message)})</p></div>`+DEMO.map(cardHTML).join('');apiUp=false;feedState.videos=DEMO.slice();watchCards()} }
  feedState.loading=false;
}

function watchCards(){
  const f=$('#feed'); if(!f)return;
  const io=new IntersectionObserver(es=>es.forEach(e=>{
    const vid=e.target.querySelector('video'), id=e.target.dataset.id;
    if(e.isIntersecting){vid.play().catch(()=>{});
      if(!e.target.dataset.viewed&&apiUp){e.target.dataset.viewed=1;api(`/api/videos/${id}/view`,{method:'POST'}).catch(()=>{})}}
    else{vid.pause();vid.currentTime=0}
  }),{root:f,threshold:.6});
  f.querySelectorAll('.card').forEach(c=>{if(!c.dataset.obs){c.dataset.obs=1;io.observe(c)}});
  f.onscroll=()=>{if(f.scrollTop+f.clientHeight>f.scrollHeight-800&&feedState.cursor)loadFeed()};
  f.onclick=async e=>{
    const likeBtn=e.target.closest('[data-like]'), fol=e.target.closest('[data-follow]'),
          com=e.target.closest('[data-comments]'), who=e.target.closest('[data-go]'), vid=e.target.closest('video');
    if(vid){vid.paused?vid.play():vid.pause();return}
    if(who&&!fol){location.hash=who.dataset.go;return}
    if(fol){const u=fol.dataset.follow;try{const d=await api(`/api/users/${u}/follow`,{method:'POST'});
      document.querySelectorAll(`[data-follow="${u}"]`).forEach(b=>{b.classList.toggle('following',d.following);b.textContent=d.following?'✓':'+'});}catch(err){toast(err.message)}return}
    if(likeBtn){const id=likeBtn.dataset.like,c=likeBtn.querySelector('.count');
      try{const d=apiUp?await api(`/api/videos/${id}/like`,{method:'POST'})
        :{liked:!likeBtn.classList.contains('liked'),likes:+c.textContent+(likeBtn.classList.contains('liked')?-1:1)};
        likeBtn.classList.toggle('liked',d.liked);c.textContent=fmt(d.likes)}catch(err){toast(err.message)}return}
    if(com){openComments(com.dataset.comments)}
  };
}

async function openComments(id){
  const sh=$('#sheet'),inner=$('#sheetInner');
  sh.style.display='block'; inner.innerHTML='<h3>Comments</h3><div class="clist">Loading…</div>';
  sh.onclick=e=>{if(e.target===sh)sh.style.display='none'};
  const list=inner.querySelector('.clist');
  try{
    const d=apiUp?await api(`/api/videos/${id}/comments`):{comments:[]};
    list.innerHTML=d.comments.map(c=>`<div class="cmt"><b>@${esc(c.username)}</b>${esc(c.body)}<span class="t">${ago(c.created_at)}</span></div>`).join('')||'<p class="small">No comments yet</p>';
  }catch(e){list.textContent=e.message}
  inner.insertAdjacentHTML('beforeend',`
    <form id="cform"><input name="body" placeholder="Add a comment…" maxlength="500" required>
    <button class="btn" style="margin-top:8px">Post</button></form>`);
  $('#cform').onsubmit=async ev=>{ev.preventDefault();
    try{const body=new FormData(ev.target).get('body').trim();
      await api(`/api/videos/${id}/comments`,{json:{body}});
      list.insertAdjacentHTML('afterbegin',`<div class="cmt"><b>@${esc(me.username)}</b>${esc(body)}<span class="t">now</span></div>`);
      ev.target.reset()}catch(e){toast(e.message)}};
}

function authHTML(mode){return `
 <div class="page">
  <h2>${mode==='login'?'Log in':'Sign up'}</h2>
  <form id="authform">
   <label>Username</label><input name="username" pattern="[a-z0-9_]{3,20}" placeholder="a-z, 0-9, _ (3-20 chars)" required>
   <label>Password</label><input name="password" type="password" minlength="8" placeholder="min 8 characters" required>
   <div class="err" id="autherr"></div>
   <button class="btn">${mode==='login'?'Log in':'Create account'}</button>
  </form>
  <p class="small">${mode==='login'?`No account? <a href="#/register">Sign up</a>`:`Have an account? <a href="#/login">Log in</a>`}</p>
 </div>`}
function mountAuth(mode){
  $('#authform').onsubmit=async e=>{e.preventDefault();
    const f=e.target,err=$('#autherr');err.textContent='';f.querySelector('button').disabled=true;
    try{const d=await api(mode==='login'?'/api/login':'/api/register',{json:{username:f.username.value.trim(),password:f.password.value}});
      me=d.user; toast(mode==='login'?'Welcome back!':'Account created!'); location.hash='#/'; render()}
    catch(ex){err.textContent=ex.message}
    f.querySelector('button').disabled=false};
}

function uploadHTML(){return `
 <div class="page">
  <h2>Upload</h2>
  <form id="upform">
   <label>Video (mp4/webm, max 100MB)</label>
   <input type="file" name="file" accept="video/mp4,video/webm,video/quicktime" required>
   <label>Caption</label><textarea name="caption" maxlength="300" placeholder="Say something… #fyp"></textarea>
   <div class="bar" id="ubar"><div></div></div>
   <div class="err" id="uerr"></div>
   <button class="btn">Post</button>
  </form>
 </div>`}
function mountUpload(){
  $('#upform').onsubmit=async e=>{e.preventDefault();
    const f=e.target,err=$('#uerr'),bar=$('#ubar'),fill=bar.firstElementChild;
    err.textContent='';f.querySelector('.btn').disabled=true;bar.style.display='block';
    try{
      const fd=new FormData(); fd.append('file',f.file.files[0]); fd.append('caption',f.caption.value.trim());
      const d=await upload('/api/videos',fd,p=>fill.style.width=(p*100)+'%');
      toast('Uploaded! Processing…'); setTimeout(()=>location.hash='#/',600);
    }catch(ex){err.textContent=ex.message;bar.style.display='none'}
    f.querySelector('.btn').disabled=false};
}

async function profileHTML(username){
  const own=me&&me.username===username;
  let p;
  try{p=apiUp?await api(`/api/users/${username}`):{user:{username,avatar_url:null,bio:'demo'},stats:{followers:0,following:0},videos:[],following:false}}
  catch(e){return `<div class="page"><h2>@${esc(username)}</h2><p class="small">${esc(e.message)}</p></div>`}
  const u=p.user,s=p.stats;
  return `
  <div class="page">
   <div class="phead">
    <img class="big" id="avatar" src="${av(u.avatar_url)}" title="${own?'Click to change pfp':''}">
    <div>
     <h2 style="margin:0 0 8px">@${esc(u.username)}</h2>
     <div class="pstats">
      <span><b>${fmt(p.videos.length)}</b>videos</span>
      <span><b>${fmt(s.followers)}</b>followers</span>
      <span><b>${fmt(s.following)}</b>following</span>
     </div>
    </div>
   </div>
   ${own?`<p class="small">Tap your avatar to upload a pfp</p>
     <label>Bio</label><textarea id="bio" maxlength="200">${esc(u.bio||'')}</textarea>
     <button class="btn gray" id="savebio">Save bio</button>
     <button class="btn gray" id="logout">Log out</button>
     <input type="file" id="avatarkin" accept="image/*" hidden>`
   :`<button class="btn" id="pfollow">${p.following?'Following ✓':'Follow'}</button>`}
   <div class="grid">
    ${p.videos.map(v=>`<div class="g" data-vid="${esc(v.id)}">${v.thumb?`<img src="${esc(v.thumb)}">`:''}<span class="pl">▶ ${fmt(v.views||0)}</span></div>`).join('')||'<p class="small" style="grid-column:1/-1">No videos yet</p>'}
   </div>
  </div>`}
function mountProfile(username){
  const own=me&&me.username===username;
  if(own){
    $('#avatar').onclick=()=>$('#avatarkin').click();
    $('#avatarkin').onchange=async e=>{const f=e.target.files[0];if(!f)return;
      try{const fd=new FormData();fd.append('file',f);
        const d=await upload('/api/me/avatar',fd);me.avatar_url=d.avatar_url;toast('PFP updated!');render()}catch(ex){toast(ex.message)}};
    $('#savebio').onclick=async()=>{try{const d=await api('/api/me',{method:'PATCH',json:{bio:$('#bio').value}});me=d.user;toast('Bio saved')}catch(e){toast(e.message)}};
    $('#logout').onclick=async()=>{await api('/api/logout',{method:'POST'}).catch(()=>{});me=null;location.hash='#/';render()};
  }else{
    const b=$('#pfollow');
    b.onclick=async()=>{try{const d=await api(`/api/users/${username}/follow`,{method:'POST'});
      b.textContent=d.following?'Following ✓':'Follow'}catch(e){toast(e.message)}};
  }
  document.querySelectorAll('[data-vid]').forEach(g=>g.onclick=()=>{location.hash='#/';setTimeout(()=>document.querySelector(`.card[data-id="${g.dataset.vid}"]`)?.scrollIntoView({behavior:'smooth'}),150)});
}

async function notifHTML(){
  let d={notifications:[],unread:0};
  if(apiUp)try{d=await api('/api/notifications')}catch(e){}
  const t={like:'liked your video',comment:'commented:',follow:'started following you'};
  return `
  <div class="page">
   <h2>Notifications ${d.unread?`<span style="color:var(--red)">(${d.unread})</span>`:''}</h2>
   <button class="btn gray" id="markread" style="width:auto;padding:8px 16px;margin:0 0 10px">Mark all read</button>
   ${d.notifications.map(n=>`
    <div class="nrow ${n.read?'':'unread'}">
     <img src="${av(n.avatar_url)}">
     <span><b>@${esc(n.actor||'someone')}</b> ${t[n.type]||n.type}${n.video_id?` · <a href="#/">view video</a>`:''}</span>
     <span class="small" style="margin-left:auto">${ago(n.created_at)}</span>
    </div>`).join('')||'<p class="small">Nothing yet. Go post something!</p>'}
  </div>`}
function mountNotif(){
  $('#markread')?.addEventListener('click',async()=>{await api('/api/notifications/read',{method:'POST'}).catch(()=>{});render()});
}

const routes=[
 [/^#?\/?$/,()=>({html:`<main class="feed" id="feed"></main>`,mount:loadFeed,feed:true})],
 [/^#\/login$/,()=>({html:authHTML('login'),mount:()=>mountAuth('login')})],
 [/^#\/register$/,()=>({html:authHTML('register'),mount:()=>mountAuth('register')})],
 [/^#\/upload$/,()=>({html:uploadHTML(),mount:mountUpload})],
 [/^#\/profile\/([a-z0-9_]+)$/,async m=>({html:await profileHTML(m[1]),mount:()=>mountProfile(m[1])})],
 [/^#\/notifications$/,async()=>({html:await notifHTML(),mount:mountNotif})],
];

async function render(){
  const h=location.hash||'#/';
  for(const[re,fn]of routes){
    const m=h.match(re);
    if(m){const v=await fn(m);
      app.innerHTML=(me?'':`<div class="banner">Browsing logged-out - log in to like, follow and upload.</div>`)+v.html+navHTML(v.feed);
      v.mount&&v.mount();
      bindNav();updateBadge();
      return}}
  location.hash='#/';
}
function navHTML(active){return `
 <nav class="nav">
  <a href="#/" class="${active?'active':''}">🏠<span>Home</span></a>
  <a href="#/upload" class="${location.hash==='#/upload'?'active':''}"><span class="plus">+</span></a>
  <a href="#/notifications" class="${location.hash==='#/notifications'?'active':''}">🔔<span>Inbox</span><span class="badge" id="badge" style="display:none"></span></a>
  <a href="${me?`#/profile/${esc(me.username)}`:'#/login'}" class="${location.hash.startsWith('#/profile')?'active':''}">👤<span>${me?'Me':'Login'}</span></a>
 </nav>`}
function bindNav(){app.querySelectorAll('.nav a').forEach(a=>a.onclick=e=>{e.preventDefault();location.hash=a.getAttribute('href')})}

async function updateBadge(){
  if(!me||!apiUp)return;
  try{const d=await api('/api/notifications');const b=$('#badge');
    if(b){b.style.display=d.unread?'block':'none';b.textContent=d.unread}}catch{}
}
setInterval(updateBadge,30000);

(async function init(){
  try{const d=await api('/api/me');me=d.user}
  catch(e){apiUp=false}
  window.addEventListener('hashchange',render);
  render();
})();
</script>
</body>
</html>
"""

# ===================== server.js (the API) =====================
SERVER_JS = r"""// Vybe API — run with: node --env-file=.env server.js
import Fastify from 'fastify'
import cookie from '@fastify/cookie'
import multipart from '@fastify/multipart'
import fastifyStatic from '@fastify/static'
import postgres from 'postgres'
import argon2 from 'argon2'
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { pipeline } from 'node:stream/promises'

const sql = postgres(process.env.DATABASE_URL, { max: 10, prepare: false })
const app = Fastify()
const TOKEN_DAYS = 30
const sha = s => crypto.createHash('sha256').update(s).digest('hex')

await app.register(cookie)
await app.register(multipart, { limits: { fileSize: 100 * 1024 * 1024 } })
await app.register(fastifyStatic, { root: path.resolve('public') })
await app.register(fastifyStatic, { root: path.resolve('uploads'), prefix: '/uploads/', decorateReply: false })
fs.mkdirSync('uploads/avatars', { recursive: true })
fs.mkdirSync('uploads/videos', { recursive: true })

app.decorateRequest('user', null)
app.addHook('onRequest', async req => {
  if (!req.cookies.sid) return
  const [u] = await sql`
    SELECT u.id, u.username, u.avatar_url, u.bio
    FROM sessions s JOIN users u ON u.id = s.user_id
    WHERE s.token_hash = ${sha(req.cookies.sid)} AND s.expires_at > now()`
  req.user = u || null
})
const requireAuth = req => {
  if (!req.user) { const e = new Error('Please log in'); e.statusCode = 401; throw e }
}

async function startSession(reply, userId) {
  const token = crypto.randomBytes(32).toString('hex')
  await sql`INSERT INTO sessions (token_hash, user_id, expires_at)
            VALUES (${sha(token)}, ${userId}, now() + make_interval(days => ${TOKEN_DAYS}))`
  reply.setCookie('sid', token, { httpOnly: true, sameSite: 'lax', path: '/', maxAge: TOKEN_DAYS * 86400 })
}
async function notify(recipientId, actorId, type, videoId) {
  if (recipientId && recipientId !== actorId)
    await sql`INSERT INTO notifications (user_id, actor_id, type, video_id) VALUES (${recipientId}, ${actorId}, ${type}, ${videoId})`
}

app.post('/api/register', async (req, reply) => {
  const { username = '', password = '' } = req.body || {}
  if (!/^[a-z0-9_]{3,20}$/.test(username)) return reply.code(400).send({ error: 'Username: 3-20 chars, a-z 0-9 _' })
  if (String(password).length < 8) return reply.code(400).send({ error: 'Password must be 8+ characters' })
  try {
    const [user] = await sql`INSERT INTO users (username, password_hash)
      VALUES (${username}, ${await argon2.hash(password)}) RETURNING id, username, avatar_url, bio`
    await startSession(reply, user.id)
    return { user }
  } catch (e) {
    return reply.code(e.code === '23505' ? 409 : 400).send({ error: e.code === '23505' ? 'Username taken' : 'Bad request' })
  }
})
app.post('/api/login', async (req, reply) => {
  const { username = '', password = '' } = req.body || {}
  const [u] = await sql`SELECT * FROM users WHERE username = ${username}`
  if (!u || !(await argon2.verify(u.password_hash, password)))
    return reply.code(401).send({ error: 'Wrong username or password' })
  await startSession(reply, u.id)
  return { user: { id: u.id, username: u.username, avatar_url: u.avatar_url, bio: u.bio } }
})
app.post('/api/logout', async req => {
  if (req.cookies.sid) await sql`DELETE FROM sessions WHERE token_hash = ${sha(req.cookies.sid)}`
  req.user = null
  return {}
})
app.get('/api/me', async (req, reply) => {
  if (!req.user) return reply.code(401).send({ error: 'Not logged in' })
  return { user: req.user }
})
app.patch('/api/me', async (req, reply) => {
  requireAuth(req)
  const bio = String(req.body?.bio || '').slice(0, 200)
  const [user] = await sql`UPDATE users SET bio = ${bio} WHERE id = ${req.user.id} RETURNING id, username, avatar_url, bio`
  return { user }
})
app.post('/api/me/avatar', async (req, reply) => {
  requireAuth(req)
  const f = await req.file()
  const ext = path.extname(f.filename || '').toLowerCase()
  if (!['.jpg', '.jpeg', '.png', '.webp'].includes(ext)) return reply.code(400).send({ error: 'Image only' })
  const name = crypto.randomUUID() + ext
  await pipeline(f.file, fs.createWriteStream(path.join('uploads/avatars', name)))
  const avatar_url = `/uploads/avatars/${name}`
  await sql`UPDATE users SET avatar_url = ${avatar_url} WHERE id = ${req.user.id}`
  return { avatar_url }
})

app.get('/api/feed', async req => {
  const meId = req.user?.id ?? null
  let q = sql`
    SELECT v.id, u.username, u.avatar_url, v.caption, v.views, v.created_at,
           COALESCE(v.src_hls, v.src_mp4) AS src, v.thumb_url AS thumb,
           (SELECT count(*) FROM likes l WHERE l.video_id = v.id)::int AS likes,
           (SELECT count(*) FROM comments c WHERE c.video_id = v.id)::int AS comments,
           (${meId} IS NOT NULL AND EXISTS (SELECT 1 FROM likes l WHERE l.video_id = v.id AND l.user_id = ${meId})) AS liked,
           (${meId} IS NOT NULL AND EXISTS (SELECT 1 FROM follows f WHERE f.followee_id = v.user_id AND f.follower_id = ${meId})) AS following
    FROM videos v JOIN users u ON u.id = v.user_id
    WHERE v.status = 'ready'`
  const [ts, cid] = decodeURIComponent(req.query.cursor || '').split(',')
  if (ts && cid)
    q = sql`${q} AND (v.created_at, v.id) < (${ts}::timestamptz, ${Number(cid)}::bigint)`
  const rows = await sql`${q} ORDER BY v.created_at DESC, v.id DESC LIMIT 10`
  const last = rows.at(-1)
  return { videos: rows, next_cursor: last ? `${new Date(last.created_at).toISOString()},${last.id}` : null }
})
app.post('/api/videos', async (req, reply) => {
  requireAuth(req)
  const f = await req.file()
  if (!f) return reply.code(400).send({ error: 'No file' })
  const name = crypto.randomUUID() + (path.extname(f.filename || '') || '.mp4')
  await pipeline(f.file, fs.createWriteStream(path.join('uploads/videos', name)))
  const caption = String(f.fields.caption?.value || '').slice(0, 300)
  const [v] = await sql`INSERT INTO videos (user_id, caption, status, src_mp4)
                        VALUES (${req.user.id}, ${caption}, 'ready', ${'/uploads/videos/' + name}) RETURNING id`
  return { id: v.id, status: 'ready' }
})
app.post('/api/videos/:id/view', async req => {
  await sql`UPDATE videos SET views = views + 1 WHERE id = ${Number(req.params.id)}`
  return {}
})
app.post('/api/videos/:id/like', async (req, reply) => {
  requireAuth(req)
  const id = Number(req.params.id)
  const [video] = await sql`SELECT user_id FROM videos WHERE id = ${id}`
  if (!video) return reply.code(404).send({ error: 'No such video' })
  const removed = await sql`DELETE FROM likes WHERE user_id = ${req.user.id} AND video_id = ${id} RETURNING video_id`
  if (removed.length === 0) {
    await sql`INSERT INTO likes (user_id, video_id) VALUES (${req.user.id}, ${id}) ON CONFLICT DO NOTHING`
    await notify(video.user_id, req.user.id, 'like', id)
  }
  const [{ likes }] = await sql`SELECT count(*)::int AS likes FROM likes WHERE video_id = ${id}`
  return { liked: removed.length === 0, likes }
})

app.get('/api/videos/:id/comments', async req => {
  const rows = await sql`
    SELECT c.id, c.body, c.created_at, u.username
    FROM comments c JOIN users u ON u.id = c.user_id
    WHERE c.video_id = ${Number(req.params.id)}
    ORDER BY c.created_at DESC, c.id DESC LIMIT 50`
  return { comments: rows, next_cursor: null }
})
app.post('/api/videos/:id/comments', async (req, reply) => {
  requireAuth(req)
  const id = Number(req.params.id), body = String(req.body?.body || '').trim().slice(0, 500)
  if (!body) return reply.code(400).send({ error: 'Empty comment' })
  const [video] = await sql`SELECT user_id FROM videos WHERE id = ${id}`
  if (!video) return reply.code(404).send({ error: 'No such video' })
  const [c] = await sql`INSERT INTO comments (video_id, user_id, body) VALUES (${id}, ${req.user.id}, ${body})
                        RETURNING id, body, created_at`
  await notify(video.user_id, req.user.id, 'comment', id)
  return { ...c, username: req.user.username }
})

app.post('/api/users/:username/follow', async (req, reply) => {
  requireAuth(req)
  const [target] = await sql`SELECT id FROM users WHERE username = ${req.params.username}`
  if (!target) return reply.code(404).send({ error: 'No such user' })
  if (target.id === req.user.id) return reply.code(400).send({ error: "Can't follow yourself" })
  const removed = await sql`DELETE FROM follows WHERE follower_id = ${req.user.id} AND followee_id = ${target.id} RETURNING followee_id`
  if (removed.length === 0) {
    await sql`INSERT INTO follows (follower_id, followee_id) VALUES (${req.user.id}, ${target.id}) ON CONFLICT DO NOTHING`
    await notify(target.id, req.user.id, 'follow', null)
  }
  const [{ followers }] = await sql`SELECT count(*)::int AS followers FROM follows WHERE followee_id = ${target.id}`
  return { following: removed.length === 0, followers }
})
app.get('/api/users/:username', async (req, reply) => {
  const [u] = await sql`SELECT id, username, avatar_url, bio FROM users WHERE username = ${req.params.username}`
  if (!u) return reply.code(404).send({ error: 'No such user' })
  const [[{ followers }], [{ following }]] = await Promise.all([
    sql`SELECT count(*)::int AS followers FROM follows WHERE followee_id = ${u.id}`,
    sql`SELECT count(*)::int AS following FROM follows WHERE follower_id = ${u.id}`,
  ])
  const videos = await sql`
    SELECT id, thumb_url AS thumb, views FROM videos
    WHERE user_id = ${u.id} AND status = 'ready'
    ORDER BY created_at DESC, id DESC LIMIT 60`
  return {
    user: { username: u.username, avatar_url: u.avatar_url, bio: u.bio },
    stats: { followers, following },
    videos,
    following: req.user
      ? (await sql`SELECT 1 AS x FROM follows WHERE follower_id = ${req.user.id} AND followee_id = ${u.id}`).length > 0
      : false,
  }
})

app.get('/api/notifications', async req => {
  requireAuth(req)
  const notifications = await sql`
    SELECT n.id, n.type, n.video_id, n.read, n.created_at, a.username AS actor, a.avatar_url
    FROM notifications n LEFT JOIN users a ON a.id = n.actor_id
    WHERE n.user_id = ${req.user.id}
    ORDER BY n.created_at DESC, n.id DESC LIMIT 50`
  const [{ unread }] = await sql`SELECT count(*)::int AS unread FROM notifications WHERE user_id = ${req.user.id} AND read = false`
  return { notifications, unread }
})
app.post('/api/notifications/read', async req => {
  requireAuth(req)
  await sql`UPDATE notifications SET read = true WHERE user_id = ${req.user.id}`
  return {}
})

const port = Number(process.env.PORT || 3000)
app.listen({ port, host: '0.0.0.0' }).then(() => console.log(`> Vybe running: http://localhost:${port}`))
"""

# ===================== schema.sql (run in Neon SQL Editor) =====================
SCHEMA_SQL = r"""-- Run this ONCE in the Neon console -> SQL Editor
CREATE TABLE IF NOT EXISTS users (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  username      TEXT NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9_]{3,20}$'),
  password_hash TEXT NOT NULL,
  bio           TEXT NOT NULL DEFAULT '',
  avatar_url    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash  TEXT PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS videos (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  caption    TEXT NOT NULL DEFAULT '' CHECK (char_length(caption) <= 300),
  status     TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
  src_hls    TEXT,
  src_mp4    TEXT,
  thumb_url  TEXT,
  duration_s NUMERIC NOT NULL DEFAULT 0 CHECK (duration_s >= 0),
  views      BIGINT NOT NULL DEFAULT 0 CHECK (views >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (status <> 'ready' OR src_hls IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_videos_feed ON videos (created_at DESC, id DESC) WHERE status = 'ready';
CREATE INDEX IF NOT EXISTS idx_videos_user ON videos (user_id, created_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS likes (
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  video_id   BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, video_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_video ON likes (video_id);

CREATE TABLE IF NOT EXISTS comments (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  video_id   BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body       TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comments_video ON comments (video_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_comments_user ON comments (user_id);

CREATE TABLE IF NOT EXISTS follows (
  follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  followee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (follower_id, followee_id),
  CHECK (follower_id <> followee_id)
);
CREATE INDEX IF NOT EXISTS idx_follows_followee ON follows (followee_id);

CREATE TABLE IF NOT EXISTS notifications (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  actor_id   BIGINT REFERENCES users(id) ON DELETE SET NULL,
  type       TEXT NOT NULL CHECK (type IN ('like', 'comment', 'follow')),
  video_id   BIGINT REFERENCES videos(id) ON DELETE CASCADE,
  read       BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, created_at DESC, id DESC);
"""

def write_file(path, content, force=False):
    if os.path.exists(path) and not force:
        print(f"[skip] {path} (already exists)")
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"[ok]   {path}")

def main():
    # 1. code files
    write_file("public/index.html", INDEX_HTML)
    write_file("server.js", SERVER_JS)
    write_file("schema.sql", SCHEMA_SQL)
    for d in ("uploads/avatars", "uploads/videos", "public/media"):
        os.makedirs(d, exist_ok=True)
    print("[ok]   folders: uploads/avatars, uploads/videos, public/media")

    # 2. package.json
    if os.path.exists("package.json"):
        data = json.load(open("package.json", encoding="utf-8"))
    else:
        data = {"name": "vybe", "version": "1.0.0", "scripts": {}}
    data.setdefault("type", "module")
    data.setdefault("scripts", {})["start"] = "node --env-file=.env server.js"
    with open("package.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("[ok]   package.json (type=module, start script)")

    # 3. npm install (only if node_modules missing)
    if not os.path.isdir("node_modules"):
        print("[..]   running npm install (this takes a minute)...")
        subprocess.run(["npm", "install", "fastify", "@fastify/cookie", "@fastify/multipart",
                        "@fastify/static", "postgres", "argon2"], shell=(os.name == "nt"))
    else:
        print("[skip] node_modules already exists")

    # 4. .env — ask for the Neon URL if not set
    env_url = ""
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if line.startswith("DATABASE_URL=") and len(line.strip()) > len("DATABASE_URL="):
                env_url = line.strip().split("=", 1)[1]
    if env_url:
        print("[skip] .env already has DATABASE_URL")
    else:
        print("\nPaste your Neon POOLED connection string")
        print("(console.neon.tech -> your project -> Connect -> Pooled connection)")
        env_url = input("> ").strip().strip('"').strip("'")
        if env_url:
            with open(".env", "a", encoding="utf-8") as f:
                f.write(f"\nDATABASE_URL={env_url}\n")
            print("[ok]   DATABASE_URL saved to .env")
        else:
            print("[!!]   Skipped - add DATABASE_URL to .env yourself later!")

    print("""
=====================================================
 DONE. Two steps left:

 1) Run schema.sql:  open console.neon.tech -> your
    project -> SQL Editor -> paste schema.sql -> Run

 2) Start the app:
        python -c "print('node --env-file=.env server.js')"
    ...just run this instead:
        node --env-file=.env server.js

    then open:  http://localhost:3000
=====================================================""")

if __name__ == "__main__":
    main()
