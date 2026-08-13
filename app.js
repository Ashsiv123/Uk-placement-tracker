const client=window.supabase.createClient(SUPABASE_URL,SUPABASE_PUBLISHABLE_KEY);
const state={placements:[],applications:new Map(),user:null,stage:'all'};
const $=id=>document.getElementById(id);
function esc(x){return String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));}
function fmtDate(d){if(!d)return'';const x=new Date(d);return isNaN(x)?'':x.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});}
function ageDays(d){if(!d)return 999;const x=new Date(d);return isNaN(x)?999:Math.max(0,Math.floor((Date.now()-x)/86400000));}
function isNew(p){return ageDays(p.first_seen_at)<=7;}
function closingSoon(p){if(!p.deadline&&!p.closes_at)return false;const d=new Date(p.closes_at||p.deadline);const n=Math.ceil((d-Date.now())/86400000);return n>=0&&n<=7;}
function company(p){return p.companies||{};}
function appFor(p){return state.applications.get(p.id);}
function priorityValue(p){return Math.max(1,Math.min(5,Number(p.priority||3)));}
function priorityClass(p){return `p${priorityValue(p)}`;}
function priorityStars(p){const n=priorityValue(p);return'★'.repeat(n)+'☆'.repeat(5-n);}
function priorityName(p){return({5:'URGENT · APPLY ASAP',4:'HIGH PRIORITY',3:'GOOD OPPORTUNITY',2:'LOWER PRIORITY',1:'OPTIONAL'})[priorityValue(p)];}
function statusClass(p){if(p.status==='Open')return'open';if(p.status==='Opening soon')return'soon';return'closed';}

function card(p){
 const c=company(p),a=appFor(p),pc=priorityClass(p),pv=priorityValue(p);
 const tags=[`<span class="pill">${esc(p.category||'Placement')}</span>`,`<span class="pill ${statusClass(p)}">${esc(p.status)}</span>`];
 if(isNew(p)&&p.status==='Open')tags.push('<span class="pill new">NEW</span>');
 if(p.is_rolling)tags.push('<span class="pill rolling">ROLLING — APPLY ASAP</span>');
 if(closingSoon(p))tags.push('<span class="pill deadline">CLOSING SOON</span>');
 if(p.deadline)tags.push(`<span class="pill">Deadline ${esc(fmtDate(p.deadline))}</span>`);
 const summary=p.description||p.eligibility_text||'Open the role for further details.';
 return `<article class="job priority-${pv}">
 <div><div class="company">${esc(c.name||'Employer')}</div><h3>${esc(p.title)}</h3>
 <div class="pills">${tags.join('')}</div>
 <div class="sub">${esc(p.location||'UK')}${p.placement_length_months?` · ${p.placement_length_months} months`:''}${p.salary_text?` · ${esc(p.salary_text)}`:''}</div>
 <p class="summary">${esc(summary.slice(0,220))}${summary.length>220?'…':''}</p>
 ${a?`<div class="app-stage">My application: ${esc(a.status)}${a.next_action?` · Next: ${esc(a.next_action)}`:''}</div>`:''}</div>
 <div class="side"><div class="priority-badge ${pc}">${priorityName(p)}</div>
 <div class="stars ${pc}">${priorityStars(p)}</div>
 <div class="priority-reason ${pc}">${esc(p.priority_reason||c.priority_reason||'')}</div>
 <div class="actions"><button class="detail-btn" onclick="openJob('${p.id}')">Job description</button>
 <button class="track-btn" onclick="trackPlacement('${p.id}')">${a?'Update application':'Track application'}</button></div></div></article>`;
}

function render(){
 const q=$('search').value.toLowerCase().trim(),cat=$('category').value,pri=$('priority').value,showClosed=$('showClosed').checked;
 let rows=state.placements.filter(p=>(showClosed||p.status==='Open'||p.status==='Opening soon')&&(!q||`${company(p).name} ${p.title} ${p.location}`.toLowerCase().includes(q))&&(cat==='all'||p.category===cat)&&(pri==='all'||Number(p.priority)>=Number(pri)));
 if(state.stage!=='all')rows=rows.filter(p=>appFor(p)?.status===state.stage);
 const sort=$('sort').value;
 rows.sort((a,b)=>{if(sort==='company')return(company(a).name||'').localeCompare(company(b).name||'');if(sort==='newest')return new Date(b.first_seen_at)-new Date(a.first_seen_at);if(sort==='deadline')return new Date(a.deadline||a.closes_at||'2999-01-01')-new Date(b.deadline||b.closes_at||'2999-01-01');return Number(b.priority||0)-Number(a.priority||0)||(company(a).priority||0)-(company(b).priority||0);});
 $('jobs').innerHTML=rows.length?rows.map(card).join(''):'<div class="empty">No placements match this view.</div>';
 $('shown').textContent=`${rows.length} shown`;
 const open=state.placements.filter(p=>p.status==='Open');
 $('openCount').textContent=open.length;$('newCount').textContent=open.filter(isNew).length;$('closingCount').textContent=open.filter(closingSoon).length;
 $('appliedCount').textContent=[...state.applications.values()].filter(a=>['Applied','Online Test','Assessment Centre','Interview','Offer'].includes(a.status)).length;
 const counts={};[...state.applications.values()].forEach(a=>counts[a.status]=(counts[a.status]||0)+1);
 $('nInterested').textContent=counts['Interested']||0;$('nApplied').textContent=counts['Applied']||0;$('nOnlineTest').textContent=counts['Online Test']||0;$('nAC').textContent=counts['Assessment Centre']||0;$('nInterview').textContent=counts['Interview']||0;$('nOffer').textContent=counts['Offer']||0;
}

async function loadPlacements(){
 const {data,error}=await client.from('placements').select('*, companies(name, priority, priority_reason, careers_url, expected_open_month, expected_open_note)').order('priority',{ascending:false});
 if(error){$('jobs').innerHTML=`<div class="empty">Could not load Supabase placements: ${esc(error.message)}</div>`;return;}
 state.placements=data||[];render();
}
async function loadApplications(){
 state.applications.clear();if(!state.user){render();return;}
 const {data,error}=await client.from('applications').select('*').eq('user_id',state.user.id);
 if(!error)(data||[]).forEach(a=>state.applications.set(a.placement_id,a));render();
}

window.openJob=id=>{
 const p=state.placements.find(x=>x.id===id);if(!p)return;const c=company(p),pc=priorityClass(p);
 $('jobDetail').innerHTML=`<div class="eyebrow">${esc(p.category||'PLACEMENT')}</div><h2>${esc(p.title)}</h2>
 <p class="muted"><strong>${esc(c.name||'Employer')}</strong> · ${esc(p.location||'UK')}</p>
 <div class="pills"><span class="pill ${statusClass(p)}">${esc(p.status)}</span>${p.is_rolling?'<span class="pill rolling">ROLLING — APPLY ASAP</span>':''}${p.deadline?`<span class="pill">Deadline ${esc(fmtDate(p.deadline))}</span>`:''}</div>
 <div class="detail-grid"><div class="detail-box priority-detail ${pc}"><span>Priority</span><strong class="stars ${pc}">${priorityStars(p)} · ${priorityName(p)}</strong></div>
 <div class="detail-box"><span>Duration</span><strong>${p.placement_length_months?`${p.placement_length_months} months`:'Check listing'}</strong></div>
 <div class="detail-box"><span>Salary</span><strong>${esc(p.salary_text||'Not stated')}</strong></div>
 <div class="detail-box"><span>Last verified</span><strong>${esc(fmtDate(p.last_verified_at)||'Not recorded')}</strong></div></div>
 ${p.priority_reason?`<div class="detail-section"><h3>Why this is a priority</h3><p>${esc(p.priority_reason)}</p></div>`:''}
 ${p.description?`<div class="detail-section"><h3>About the placement</h3><p>${esc(p.description)}</p></div>`:''}
 ${p.responsibilities?`<div class="detail-section"><h3>Responsibilities</h3><p>${esc(p.responsibilities)}</p></div>`:''}
 ${p.requirements||p.eligibility_text?`<div class="detail-section"><h3>Requirements / eligibility</h3><p>${esc(p.requirements||p.eligibility_text)}</p></div>`:''}
 ${p.desirable_skills?`<div class="detail-section"><h3>Useful skills</h3><p>${esc(p.desirable_skills)}</p></div>`:''}
 ${c.expected_open_note?`<div class="detail-section"><h3>Application timing</h3><p>${esc(c.expected_open_note)}</p></div>`:''}
 <a class="official" href="${esc(p.url)}" target="_blank" rel="noopener">Open official application ↗</a>`;
 $('jobModal').classList.remove('hidden');
};

window.trackPlacement=async id=>{
 if(!state.user){$('authModal').classList.remove('hidden');return;}
 const p=state.placements.find(x=>x.id===id),a=appFor(p);
 $('appPlacementId').value=id;$('appTitle').textContent=`${p.title} — ${company(p).name}`;$('appStatus').value=a?.status||'Interested';
 $('appliedAt').value=a?.applied_at?a.applied_at.slice(0,10):'';$('nextAction').value=a?.next_action||'';$('nextActionAt').value=a?.next_action_at?a.next_action_at.slice(0,16):'';$('appNotes').value=a?.notes||'';$('appMessage').textContent='';$('appModal').classList.remove('hidden');
};

$('saveApplication').onclick=async()=>{
 if(!state.user)return;const placement_id=$('appPlacementId').value,status=$('appStatus').value;
 const payload={user_id:state.user.id,placement_id,status,applied_at:$('appliedAt').value?new Date($('appliedAt').value).toISOString():null,next_action:$('nextAction').value.trim()||null,next_action_at:$('nextActionAt').value?new Date($('nextActionAt').value).toISOString():null,notes:$('appNotes').value.trim()||null,updated_at:new Date().toISOString()};
 if(status==='Applied'&&!payload.applied_at)payload.applied_at=new Date().toISOString();
 const {error}=await client.from('applications').upsert(payload,{onConflict:'user_id,placement_id'});
 $('appMessage').textContent=error?error.message:'Saved.';if(!error){await loadApplications();setTimeout(()=>$('appModal').classList.add('hidden'),450);}
};

async function authState(){const {data:{session}}=await client.auth.getSession();state.user=session?.user||null;updateAccount();await loadApplications();}
function updateAccount(){$('signedOut').classList.toggle('hidden',!!state.user);$('signedIn').classList.toggle('hidden',!state.user);$('userEmail').textContent=state.user?.email||'';}
$('loginBtn').onclick=()=>$('authModal').classList.remove('hidden');
$('logoutBtn').onclick=async()=>{await client.auth.signOut();state.user=null;updateAccount();await loadApplications();};
$('signInBtn').onclick=async()=>{const email=$('authEmail').value.trim(),password=$('authPassword').value;const {data,error}=await client.auth.signInWithPassword({email,password});$('authMessage').textContent=error?error.message:'Signed in.';if(!error){state.user=data.user;updateAccount();await loadApplications();setTimeout(()=>$('authModal').classList.add('hidden'),400);}};
$('signUpBtn').onclick=async()=>{const email=$('authEmail').value.trim(),password=$('authPassword').value;const {data,error}=await client.auth.signUp({email,password});$('authMessage').textContent=error?error.message:(data.session?'Account created and signed in.':'Account created. Check your email if confirmation is required.');if(data.session){state.user=data.user;updateAccount();await loadApplications();}};
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).classList.add('hidden'));
document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)m.classList.add('hidden')}));
document.querySelectorAll('.pipe').forEach(b=>b.onclick=()=>{document.querySelectorAll('.pipe').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.stage=b.dataset.stage;render();});
['search','category','priority','sort','showClosed'].forEach(id=>$(id).addEventListener('input',render));
client.auth.onAuthStateChange((_event,session)=>{state.user=session?.user||null;updateAccount();loadApplications();});
loadPlacements();authState();