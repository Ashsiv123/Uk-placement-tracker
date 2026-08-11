const state={jobs:[]};
const $=id=>document.getElementById(id);
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));}
function card(j){
 const tags=[`<span class="pill">${esc(j.area)}</span>`,`<span class="pill">${esc(j.status)}</span>`];
 if(j.isNew) tags.push('<span class="pill new">NEW</span>');
 if(j.deadline) tags.push(`<span class="pill">Deadline: ${esc(j.deadline)}</span>`);
 return `<article class="job"><div><div class="company">${esc(j.company)}</div><h3>${esc(j.title)}</h3><div class="meta">${tags.join('')}</div><p>${esc(j.location)} · ${esc(j.duration)}</p><p>${esc(j.note)}</p></div><div class="right"><div>${'★'.repeat(j.priority)}${'☆'.repeat(5-j.priority)}</div><a class="apply" target="_blank" rel="noopener" href="${esc(j.url)}">Apply / View role ↗</a></div></article>`;
}
function render(){
 const q=$('search').value.toLowerCase(),a=$('area').value,s=$('status').value,p=$('priority').value;
 const rows=state.jobs.filter(j=>(!q||(`${j.company} ${j.title} ${j.location}`).toLowerCase().includes(q))&&(a==='all'||j.area===a)&&(s==='all'||j.status===s)&&(p==='all'||j.priority>=Number(p)));
 $('jobs').innerHTML=rows.length?rows.map(card).join(''):'<div class="empty">No placements match those filters.</div>';
 $('count').textContent=`${rows.length} shown`;
 $('total').textContent=state.jobs.length;
 $('open').textContent=state.jobs.filter(j=>j.status==='Open').length;
 $('new').textContent=state.jobs.filter(j=>j.isNew).length;
}
fetch('data/jobs.json?'+Date.now()).then(r=>r.json()).then(d=>{state.jobs=d.jobs||[];$('updated').textContent=d.updated_at||'Unknown';render()}).catch(()=>{$('jobs').innerHTML='<div class="empty">Could not load the jobs database.</div>'});
['search','area','status','priority'].forEach(id=>$(id).addEventListener('input',render));