(async()=>{
 const live=new URLSearchParams(location.search).get('mode')==='live';
 const bar=document.createElement('nav');bar.className='experience-bar';bar.setAttribute('aria-label','Experience mode');
 bar.innerHTML='<strong>AgentCoSign · judge experience</strong><a href="/visits/1/?mode=recorded" '+(!live?'aria-current="page"':'')+'>Explore recorded run</a><a href="/live/new" '+(live?'aria-current="page"':'')+'>Try a new live shopper</a>';
 bar.addEventListener('click',e=>{const link=e.target.closest('a');if(link){e.preventDefault();e.stopPropagation();location.assign(link.href);}},true);
 document.body.prepend(bar);
 const runbar=document.createElement('aside');runbar.className='experience-runbar';runbar.setAttribute('aria-label','Run identities');
 const leftRun=document.createElement('span'),rightRun=document.createElement('span');
 leftRun.textContent='LEFT · Historical Nisolo replay · October 14';
 rightRun.textContent=live?'RIGHT · NEW LIVE RUN · Not started':'RIGHT · RECORDED · Historical visit';
 runbar.append(leftRun,rightRun);document.body.prepend(runbar);
 new ResizeObserver(()=>{document.documentElement.style.setProperty('--experience-header-height',Math.ceil(runbar.getBoundingClientRect().bottom)+'px');}).observe(runbar);
 const context=document.createElement('div');context.className='experience-context';context.textContent=live?'LEFT: historical Nisolo replay · RIGHT: a NEW live Channel3 test cart. These are separate tasks. No payment.':'Historical Nisolo store replay · original captured pages and messages · October 14. Resoling gap found afterward; no live CoSign block in this visit.';
 let evidence;
 if(!live){try{const r=await fetch('/recorded-evidence');if(!r.ok)throw Error();evidence=await r.json();}catch(e){bar.append(document.createTextNode('Recorded evidence unavailable. No result generated.'));return;}}
 const disclosure='<aside class="experience-disclosure"><p>We may earn a commission when you buy through product links. No retailer purchase is placed here.</p><p>Channel3-powered use is subject to the <a href="/demo-terms" target="_blank" rel="noopener">Demo terms and data notice</a>. Product data remains owned by its rights holders.</p></aside>';
 const panel=document.createElement('section');panel.className='experience-panel';panel.id='experience-recorded';
 let step=0,auto=false,requestSubmitted=false;
 const titles=['Watch the original shopping visit','Inspect the missing evidence','See the agent recover','Inspect the recorded buyer approval','Inspect the separate PayPal result'];
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money=c=>'$'+(c/100).toFixed(2);
 function render(){
  const run=evidence.recovery,a=run.approval,p=evidence.payment,v=p.verification;
  rightRun.textContent='RIGHT · RECORDED · '+(step===0?'Historical visit':step===4?p.run:run.run)+' · Read-only';
  context.textContent=step===0?'Historical Nisolo store replay · original captures and messages · October 14. No live CoSign block in this historical visit.':'LEFT: historical Nisolo replay · RIGHT: saved '+(step===4?p.run:run.run)+' evidence. Different tasks and carts; read-only, no new payment.';
  let content='';
  if(step===0)content='<div class="card"><h3>A real shopping visit, replayed</h3><p>The buyer requested black lace-up shoes, size 11 Wide, resolable, under $250. Play the original captured store pages alongside the agent messages.</p><p class="muted">This historical run continued to cart. The resoling gap was found afterward, not blocked live.</p></div><div class="actions"><button id="play-visit" class="primary">Play full store replay</button><button id="pause-visit">Pause replay</button></div><p id="play-note" class="muted">Uses the original report player. Guided play resumes its key-moment pauses.</p>';
  if(step===1)content='<div class="card"><h3>Separate task · '+esc(run.run)+'</h3><p>'+esc(run.request)+'</p><p class="muted">Real Channel3 products in a test merchant; $10 shipping and 6% tax simulated. Not a retailer checkout. Intent confirmation was automated test setup.</p></div>'+eventHTML(run.events.slice(0,2))+'<div class="card result"><h3>Approval paused</h3><p>The required leather material was not documented. A product title and an affordable price were not enough.</p></div>';
  if(step===2)content='<div class="card"><h3>Same cart. Same requirements.</h3><p>This is a preset retry challenge. The controller reopened the cart; the model chose a replacement and used visible browser controls. No script replaced the product.</p></div>'+eventHTML(run.events.slice(2))+'<div class="card result"><h3>Eligible for buyer review</h3><p>Documented leather evidence now matches. Eligibility is not permission to pay.</p></div>';
  if(step===3)content='<div class="card result"><h3>Previously approved · '+money(a.total_cents)+'</h3><p>The human buyer approved this exact quote in the same report card. This is a saved record, not a new approval button.</p><dl><dt>Cart version</dt><dd>'+a.cart_version+'</dd><dt>Payment calls</dt><dd>'+a.payment_calls+'</dd></dl><p><strong>Approval expired. No current permission to pay.</strong></p></div><details><summary>Exact quote binding</summary><p>Quote: '+esc(a.quote_id)+'</p><p>Quote SHA-256: '+esc(a.quote_sha256)+'</p><p>Intent SHA-256: '+esc(a.intent_sha256)+'</p></details>';
  if(step===4)content='<div class="card"><h3>Different cart · '+esc(p.run)+'</h3><p>Earlier PayPal sandbox purchase. This is not payment for the '+money(a.total_cents)+' Channel3 cart.</p></div><div class="card result"><h3>'+money(v.total_cents)+' · sandbox payment verified</h3><dl><dt>Order</dt><dd>'+esc(v.order_status)+'</dd><dt>Capture</dt><dd>'+esc(v.capture_status)+'</dd><dt>Sequential repeats</dt><dd>'+p.repeat_capture_ids.length+'</dd><dt>Capture POSTs</dt><dd>'+p.capture_post_count+'</dd><dt>Merchant receipts</dt><dd>'+p.merchant_receipt_count+'</dd></dl><p>Both repeated requests returned the same capture. This does not establish concurrent exactly-once safety.</p></div><details><summary>Recorded order and capture IDs</summary><p>'+esc(v.order_id)+'</p><p>'+esc(v.capture_id)+'</p></details>';
  panel.innerHTML='<p class="muted">RECORDED EVIDENCE · READ-ONLY · '+(step===0?'historical store visit':step===4?esc(p.run):esc(run.run))+'</p><h2>'+titles[step]+'</h2><div class="actions"><button id="previous" '+(step===0?'disabled':'')+'>Previous</button><button id="next" class="primary" '+(step===4?'disabled':'')+'>Next: '+(titles[step+1]||'Complete')+'</button></div>'+content+disclosure+'<p class="muted">Step '+(step+1)+' of 5 · These buttons reveal existing evidence. They do not run a shopper, approve a purchase or contact PayPal.</p>';
  panel.querySelector('#previous').onclick=()=>change(step-1);panel.querySelector('#next').onclick=()=>change(step+1);
  if(step===0){panel.querySelector('#play-visit').onclick=play;panel.querySelector('#pause-visit').onclick=stop;}
 }
 function eventHTML(events){return events.map(e=>'<div class="event"><span class="muted">Saved '+e.elapsed_seconds.toFixed(2)+'s · cart v'+e.cart_version+'</span><p><strong>'+esc(e.decision?'CoSign: '+e.decision:e.name)+'</strong></p>'+e.facts.map(f=>'<p>'+esc(f.field)+': required '+esc(f.required)+' · observed '+esc(f.observed===null?'not documented':f.observed)+'</p>').join('')+'</div>').join('');}
 function control(name){return document.querySelector('[data-slot="replay"] button[aria-label="'+name+'"]');}
 function leaveGuided(){auto=false;const note=document.querySelector('#play-note');if(note)note.textContent='Manual replay controls active. Guided playback is off.';}
 function stop(){leaveGuided();control('Pause')?.click();}
 // Trusted input means the viewer is taking control, not our key-moment resume.
 document.addEventListener('click',e=>{
  if(e.isTrusted&&e.target.closest('[data-slot="replay"] button[aria-label="Play"], [data-slot="replay"] button[aria-label="Pause"]'))leaveGuided();
 },true);
 document.addEventListener('pointerdown',e=>{
  if(e.isTrusted&&e.target.closest('[data-slot="replay"] [role="slider"], [data-slot="replay"] [data-slot="slider"], [data-slot="replay"] [aria-label="The visit, page by page"], [data-slot="replay"] table'))leaveGuided();
 },true);
 document.addEventListener('keydown',e=>{
  if(e.isTrusted&&e.target.closest('[data-slot="replay"]')&&[' ','Spacebar','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(e.key))leaveGuided();
 },true);
 function play(){
  auto=true;const slider=document.querySelector('[data-slot="replay"] [role="slider"]');
  if(slider){slider.focus();slider.dispatchEvent(new KeyboardEvent('keydown',{key:'Home',bubbles:true}));}
  setTimeout(()=>{if(auto)control('Play')?.click();},100);
  const note=document.querySelector('#play-note');if(note)note.textContent='Playing original captures. Guided mode resumes key-moment pauses; the speed is shown on the player.';
 }
 function change(n){stop();step=n;render();panel.scrollIntoView({block:'start',behavior:'smooth'});}
 setInterval(()=>{if(!auto)return;const slider=document.querySelector('[data-slot="replay"] [role="slider"]');if(slider&&Number(slider.getAttribute('aria-valuenow'))>=Number(slider.getAttribute('aria-valuemax'))){auto=false;const note=document.querySelector('#play-note');if(note)note.textContent='Replay complete. Inspect the post-run evidence gap, then continue to the separate recovery run.';return;}control('Play')?.click();},400);
 document.addEventListener('submit',e=>{
  if(live&&e.target.matches('form[action="/request"]')){
   requestSubmitted=true;
   const current=document.querySelector('#cosign-report-panel'),buyer=current?.querySelector('#buyer-card');
   if(buyer){buyer.closest('article').hidden=false;buyer.onload=()=>{
    const form=current.querySelector('form[action="/request"]');
    if(buyer.contentDocument?.querySelector('form[action="/confirm"]')){form?.closest('article').remove();current.querySelector('.experience-live-waiting')?.remove();}
   };}
  }
 },true);
 let ready=false;
 const mount=()=>{
  const replay=document.querySelector('[data-slot="replay"]');const chat=document.querySelector('[data-slot="chat"]');
  if(replay&&!context.isConnected)replay.prepend(context);
  if(live){const current=document.querySelector('#cosign-report-panel');if(current){
   const h=current.querySelector('h3');if(h&&h.textContent!=='NEW LIVE RUN · separate from historical replay')h.textContent='NEW LIVE RUN · separate from historical replay';
   const buyer=current.querySelector('#buyer-card');
   const pending=!!current.querySelector('form[action="/request"]');
   if(buyer){const article=buyer.closest('article');if(article)article.hidden=pending&&!requestSubmitted;
    if(!buyer.dataset.liveReturnBound){
     buyer.dataset.liveReturnBound='true';
     const bindReturn=()=>{const d=buyer.contentDocument;if(d)for(const link of d.querySelectorAll('a[href="/agent"],a[href="/conversation"]')){link.href='/visits/1/?mode=live';link.target='_top';}};
     buyer.addEventListener('load',bindReturn);bindReturn();
    }
   }
   let waiting=current.querySelector('.experience-live-waiting');
   if(!current.querySelector('.experience-disclosure')){const notice=document.createElement('div');notice.innerHTML=disclosure;current.prepend(notice.firstElementChild);}
   if(pending&&!waiting){waiting=document.createElement('p');waiting.className='experience-live-waiting';waiting.textContent='Send a request to begin. Your confirmation and approval card will appear here.';current.querySelector('form[action="/request"]').closest('article').after(waiting);}
   if(waiting&&!pending)waiting.remove();
   const cart=current.querySelector('#cart')?.textContent;
   const identity='RIGHT · NEW LIVE RUN · '+(cart||'Not started');if(rightRun.textContent!==identity)rightRun.textContent=identity;
   if(!ready){ready=true;current.scrollIntoView({block:'start'});}
  }return;}
  if(chat&&!chat.contains(panel))chat.append(panel);
  if(chat&&!ready){ready=true;render();panel.scrollIntoView({block:'nearest'});}
 };
 mount();new MutationObserver(mount).observe(document.body,{childList:true,subtree:true});
})();
