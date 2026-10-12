const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const pretty=value=>Array.isArray(value)?value.join(' / '):String(value??'UNKNOWN');

function render(state){
  const line=document.querySelector('.status-line');
  line.classList.add('ready');
  document.getElementById('runtime-status').textContent='NERVES ONLINE';
  document.getElementById('runtime-detail').textContent=state.deviceId+' · '+state.version;
  const brain=state.primaryBrain||{};
  const brainChip=document.getElementById('brain-chip');
  brainChip.classList.toggle('ready',Boolean(brain.installed));
  brainChip.querySelector('b').textContent=brain.name||'CODEX';
  brainChip.querySelector('small').textContent=brain.installed?'primary conductor ready · workspace-write':'adapter configured · CLI not detected';
  const campaign=state.campaigns[0]||{};
  document.getElementById('campaign-name').textContent=campaign.name||'No active campaign';
  document.getElementById('campaign-purpose').textContent=campaign.northStar||state.authority;
  document.getElementById('stat-jobs').textContent=state.summary.openJobs;
  document.getElementById('stat-approvals').textContent=state.summary.pendingApprovals;
  document.getElementById('stat-providers').textContent=state.summary.installedProviders;
  document.getElementById('stat-outcomes').textContent=state.summary.verifiedOutcomes;
  document.getElementById('bottleneck').textContent=pretty(state.funnel.bottleneck?.value);

  document.getElementById('funnel').innerHTML=Object.entries(state.funnel).filter(([key])=>!['observedAt','bottleneck'].includes(key)).map(([key,item])=>{
    const known=item.value!=='UNKNOWN';
    return `<article class="${known?'known':'unknown'}"><strong>${esc(key.replace(/([A-Z])/g,' $1'))}</strong><span>${esc(pretty(item.value))}<br>${esc(item.status)}</span></article>`;
  }).join('');

  const roleNames=Object.fromEntries(state.roles.map(role=>[role.id,role.name]));
  document.getElementById('jobs').innerHTML=state.jobs.filter(job=>job.campaignId).map(job=>`<article class="job"><div class="role-num">${job.producerRoleId}</div><div><h3>${esc(roleNames[job.producerRoleId]||job.jobId)}</h3><p title="${esc(job.objective)}">${esc(job.objective)}</p></div><span class="state">${esc(job.state)}</span></article>`).join('');
  document.getElementById('roles').innerHTML=state.roles.map(role=>`<article class="role"><b>ROLE ${role.id}</b><h3>${esc(role.name)}</h3><p>${esc(role.title)}</p></article>`).join('');
  document.getElementById('providers').innerHTML=state.providers.map(provider=>`<div class="list-item"><span><i class="dot ${provider.installed?'up':''}"></i>${esc(provider.id)}</span><small>${provider.installed?esc(provider.version||'installed'):'not detected'}</small></div>`).join('');
  document.getElementById('approvals').innerHTML=state.approvals.length?state.approvals.map(item=>`<div class="list-item"><span>${esc(item.action.actionType)} → ${esc(item.action.target)}</span><small>${esc(item.status)}</small></div>`).join(''):'<p class="empty">No pending external actions. The gate is clean.</p>';
  document.getElementById('events').innerHTML=state.events.map(event=>`<div class="list-item"><strong>${esc(event.kind)}</strong><small>${esc(event.detail)}</small><time>${esc(event.at)}</time></div>`).join('')||'<p class="empty">No events yet.</p>';
  renderBrains(state.brains||[]);
  renderChat(state.chat||[]);
}

let chatBusy=false;
function renderBrains(brains){
  const select=document.getElementById('chat-engine');
  const current=select.value;
  select.innerHTML=brains.map(brain=>`<option value="${esc(brain.engine)}"${brain.installed?'':' disabled'}>${esc(brain.name)}${brain.installed?'':' (not installed)'}</option>`).join('');
  if(current&&brains.some(brain=>brain.engine===current&&brain.installed))select.value=current;
  const chip=document.querySelector('.brain-chip');
  if(chip&&brains.length){
    const primary=brains.find(brain=>brain.engine==='codex')||brains[0];
    const ready=brains.filter(brain=>brain.installed).length;
    chip.querySelector('small').textContent=ready+' of '+brains.length+' conductor brains ready';
    chip.classList.toggle('ready',ready>0);
  }
}

function fmtReply(text){
  let html=esc(text||'');
  html=html.replace(/```([\s\S]*?)```/g,(m,code)=>'<code class="chat-block">'+code.replace(/^\n/,'')+'</code>');
  html=html.replace(/`([^`\n]+)`/g,'<code>$1</code>');
  html=html.replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>');
  html=html.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g,'$1<em>$2</em>');
  html=html.replace(/^###\s+(.*)$/gm,'<h4>$1</h4>');
  html=html.replace(/^##\s+(.*)$/gm,'<h3>$1</h3>');
  html=html.replace(/^#\s+(.*)$/gm,'<h3>$1</h3>');
  html=html.replace(/\n/g,'<br>');
  return html;
}

function chatBubble(turn){
  const out=document.createElement('article');
  out.className='chat-turn';
  out.innerHTML=`<p class="chat-ask">${esc(turn.message)}</p><div class="chat-reply">${fmtReply(turn.reply)}</div><p class="chat-meta">${esc(turn.brainName||turn.engine)} · ${esc(turn.at)}${turn.write?' · edits allowed':''}</p>`;
  return out;
}

async function loadThreads(){
  const list=document.getElementById('chat-list');
  if(!list)return;
  try{
    const response=await fetch('/api/chat/threads',{cache:'no-store'});
    if(!response.ok)return;
    const data=await response.json();
    const threads=data.threads||[];
    list.innerHTML='';
    for(const thread of threads){
      const item=document.createElement('li');
      const button=document.createElement('button');
      button.type='button';
      button.className=thread.active?'active':'';
      button.textContent=thread.title||'Chat';
      const meta=document.createElement('span');
      meta.className='chat-meta';
      meta.textContent=(thread.turns||0)+' turn'+(thread.turns===1?'':'s')+' · '+(thread.updatedAt||'').slice(0,16).replace('T',' ');
      button.appendChild(meta);
      button.addEventListener('click',()=>switchTo(thread.id));
      item.appendChild(button);
      list.appendChild(item);
    }
    const title=document.getElementById('chat-title');
    if(title)title.textContent=(data.current&&data.current.title)||'New chat';
  }catch(error){/* threads are optional context */}
}

async function switchTo(threadId){
  if(chatBusy||!threadId)return;
  try{
    await fetch('/api/chat/switch',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({threadId})});
    await loadThreads();
    const response=await fetch('/api/status',{cache:'no-store'});
    if(response.ok)renderChat((await response.json()).chat.history||[]);
  }catch(error){/* surfaced by the next send */}
}

async function startNewChat(){
  if(chatBusy)return;
  try{
    await fetch('/api/chat/new',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    await loadThreads();
    const log=document.getElementById('chat-log');
    log.innerHTML='<p class="empty">New conversation. Earlier chats stay saved on the left.</p>';
  }catch(error){/* surfaced by the next send */}
}

document.getElementById('chat-new-side').addEventListener('click',startNewChat);

function renderChat(history){
  const log=document.getElementById('chat-log');
  if(!history.length)return;
  log.innerHTML='';
  for(const turn of [...history].reverse())log.appendChild(chatBubble(turn));
  log.scrollTop=log.scrollHeight;
}

// Enter sends the message. Shift+Enter (or Ctrl/Cmd+Enter) inserts a newline,
// which is what people expect from a chat box rather than a notes field.
document.getElementById('chat-input').addEventListener('keydown',event=>{
  if(event.key!=='Enter'||event.shiftKey||event.ctrlKey||event.metaKey||event.altKey)return;
  if(event.isComposing)return;
  event.preventDefault();
  document.getElementById('chat-form').requestSubmit();
});

document.getElementById('chat-form').addEventListener('submit',async event=>{
  event.preventDefault();
  if(chatBusy)return;
  const input=document.getElementById('chat-input');
  const message=input.value.trim();
  if(!message)return;
  const log=document.getElementById('chat-log');
  const button=document.getElementById('chat-send');
  chatBusy=true;button.disabled=true;button.textContent='Working…';
  const pending=document.createElement('article');
  pending.className='chat-turn pending';
  pending.innerHTML=`<p class="chat-ask">${esc(message)}</p><div class="chat-reply">Thinking… this can take a minute.</div>`;
  if(log.querySelector('.empty'))log.innerHTML='';
  log.appendChild(pending);log.scrollTop=log.scrollHeight;
  input.value='';
  try{
    const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,engine:document.getElementById('chat-engine').value,write:document.getElementById('chat-write').checked})});
    const result=await response.json();
    if(!response.ok)throw new Error(result.error||'Chat failed');
    pending.replaceWith(chatBubble(result.turn));
  }catch(error){
    pending.querySelector('.chat-reply').innerHTML='<span class="chat-error">'+esc(String(error.message||error))+'</span>';
  }finally{
    chatBusy=false;button.disabled=false;button.textContent='Send';log.scrollTop=log.scrollHeight;
  }
});

async function connect(){
  const label=document.getElementById('runtime-status');
  const detail=document.getElementById('runtime-detail');
  try{
    const response=await fetch('/api/status',{cache:'no-store'});
    if(!response.ok)throw new Error('HTTP '+response.status);
    render(await response.json());
  }catch(error){
    document.querySelector('.status-line').classList.remove('ready');
    label.textContent='RUNTIME OFFLINE';
    detail.textContent=String(error.message||error);
  }
}

document.getElementById('demo-button').addEventListener('click',async event=>{
  const button=event.currentTarget;
  button.disabled=true;button.textContent='Running local lifecycle…';
  try{const response=await fetch('/api/demo',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const result=await response.json();if(!response.ok)throw new Error(result.error||'Demo failed');button.textContent='Passed · '+result.jobId;await connect();}
  catch(error){button.textContent='Failed · '+String(error.message||error)}
  finally{setTimeout(()=>{button.disabled=false;button.textContent='Run safety demonstration'},3500)}
});

connect();
setInterval(connect,15000);

