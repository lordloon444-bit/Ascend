from playwright.sync_api import sync_playwright
from pathlib import Path
import hashlib,base64,json,time
html=(Path(__file__).resolve().parents[1]/'index.html').read_text()
class GitHub:
 def __init__(self):self.files={};self.requests=[];self.failures=0;self.reject=0
 def sha(self,raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 def mock(self,x):
  url=x['url'];method=x.get('method') or 'GET';self.requests.append((method,url));body=x.get('body')
  def r(status,body=None):return {'status':status,'body':body or {}}
  if self.failures and method=='PUT':self.failures-=1;return r(503)
  if '/repos/testowner/ASCEND-Data' not in url:return r(404)
  path=url.split('/repos/testowner/ASCEND-Data',1)[1].split('?')[0].lstrip('/')
  if not path:return r(200,{'private':True,'name':'ASCEND-Data'})
  if path=='contents/snapshots':
   data=[{'name':k.split('/')[-1],'path':k,'sha':v[0],'type':'file'} for k,v in self.files.items() if k.startswith('snapshots/')]
   return r(200,data) if data else r(404)
  if path.startswith('contents/'):
   file=path[len('contents/'):]
   if method=='GET':
    if file not in self.files:return r(404)
    sha,data=self.files[file];return r(200,{'sha':sha,'type':'file','content':base64.b64encode(data).decode(),'encoding':'base64'})
   if method=='PUT':
    blob=json.loads(body);raw=base64.b64decode(blob['content']);cur=self.files.get(file)
    if self.reject:self.reject-=1;return r(409)
    if (cur and cur[0]!=blob.get('sha')) or (not cur and blob.get('sha')):return r(409)
    sha=self.sha(raw);self.files[file]=(sha,raw);return r(200 if cur else 201,{'content':{'sha':sha},'commit':{'sha':'commit'+sha}})
   if method=='DELETE':
    b=json.loads(body);cur=self.files.get(file)
    if not cur or cur[0]!=b.get('sha'):return r(409)
    del self.files[file];return r(200)
  if path.startswith('git/blobs/'):
   sha=path.split('/')[-1]
   for blob_sha,data in self.files.values():
    if sha==blob_sha:return r(200,{'encoding':'base64','content':base64.b64encode(data).decode()})
  return r(404)
repo=GitHub()
def init(page,seed=None):
 page.expose_function('__githubMock',repo.mock)
 page.evaluate('''(seed) => {
  const cache=seed||{};window.__testStore=cache;
  Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>(Object.hasOwn(cache,k)?cache[k]:null),setItem:(k,v)=>{cache[k]=String(v)},removeItem:k=>{delete cache[k]},key:i=>Object.keys(cache)[i]||null,get length(){return Object.keys(cache).length}}});
  const original=window.fetch.bind(window);
  window.fetch=async (url,opt={})=>{
   if(!String(url).startsWith('https://api.github.com/'))return original(url,opt);
   const result=await window.__githubMock({url:String(url),method:opt.method||'GET',body:opt.body||null});
   return new Response(JSON.stringify(result.body),{status:result.status,headers:{'Content-Type':'application/json'}});
  };
 }''',seed)
 page.set_content(html,wait_until='load')

def state(page):return page.locator('#cloudState').inner_text()
def connect(page):
 page.locator('#cloudOpen').click();page.locator('#cloudOwner').fill('testowner');page.locator('#cloudToken').fill('github_pat_FAKE_NOT_SECRET');page.locator('#cloudConnect').click()

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None,headless=True,args=['--no-sandbox'])
 pc=browser.new_page(viewport={'width':1440,'height':900});errors=[];pc.on('pageerror',lambda e:errors.append(str(e)))
 init(pc)
 print('initial',pc.locator('#page-daily.active').count(),'modal',pc.locator('#cloudOpen').count(),'js_err',errors[:2]);
 assert pc.locator('#page-daily.active').count()==1
 assert pc.locator('#page-vision .mood-art').count()==11,pc.locator('#page-vision img').count()
 assert pc.locator('.side-nav button[data-page]').count()==6
 for target in ['journal','fitness','goals','affirmations','vision','daily']:
  pc.locator('.side-nav button[data-page="'+target+'"]').click()
  assert pc.locator('#page-'+target+'.active').count()==1
 pc.locator('.side-nav button[data-page="goals"]').click();pc.locator('#newGoal').fill('Gym consistency')
 pc.locator('#goalForm button[type=submit]').click()
 pc.locator('.side-nav button[data-page="daily"]').click();pc.locator('#dailyOpenCompose').click();pc.locator('#dailyName').fill('Study every day');pc.locator('#dailyForm button[type=submit]').click()
 connect(pc)
 pc.wait_for_timeout(2500); print('DBG',state(pc),pc.locator('#cloudStatusMessage').inner_text(),'files',list(repo.files),'reqs',repo.requests[-8:],'errors',errors)
 pc.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=12000)
 print('connected',state(pc),'files',list(repo.files),'err',errors[:2]);assert 'data/latest.json' in repo.files
 assert any(k.startswith('snapshots/') for k in repo.files)
 assert not any('FAKE_NOT_SECRET' in str(v) for v in pc.evaluate('window.__testStore').values())
 payload=json.loads(repo.files['data/latest.json'][1])['payload'];assert 'Gym consistency' in str(payload['goals'])
 assert 'Study every day' in str(payload['dailyTasks'])
 print("before manual sync")
 writes=sum(k=='PUT' for k,u in repo.requests)
 pc.locator('#cloudSyncNow').click();pc.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=5000)
 assert sum(k=='PUT' for k,u in repo.requests)==writes
 # New device: compare without altering local data. Manual cloud import.
 print("before new device")
 mobile=browser.new_page(viewport={'width':390,'height':844});mobile.on('pageerror',lambda e:errors.append('mobile:'+str(e)));init(mobile)
 print("before mobile connect")
 connect(mobile)
 print("after mobile connect click")
 mobile.wait_for_function('document.querySelector("#cloudState").textContent==="Conflict"',timeout=6000)
 assert 'Gym consistency' not in str(mobile.evaluate('window.__testStore'))
 print("before restore")
 mobile.locator('#cloudChooseRemote').click()
 mobile.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=6000)
 assert 'Gym consistency' in str(mobile.evaluate('window.__testStore'))
 assert 'Study every day' in str(mobile.evaluate('window.__testStore'))
 # Second device updates remote
 print("before device two update")
 mobile.locator('#cloudClose').click();mobile.locator('.mobile-nav [data-page="goals"]').click()
 mobile.locator('#newGoal').fill('Remote Device Goal');mobile.locator('#goalForm button[type=submit]').click();mobile.locator('#cloudOpen').click();mobile.locator('#cloudSyncNow').click()
 mobile.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=6000)
 # First device has pending older version, changing locally should not overwrite remote
 print("before device one conflict")
 pc.locator('#cloudClose').click();pc.locator('.side-nav [data-page="goals"]').click();pc.locator('#newGoal').fill('Local Device Goal');pc.locator('#goalForm button[type=submit]').click();pc.locator('#cloudOpen').click();pc.locator('#cloudSyncNow').click()
 pc.wait_for_function('document.querySelector("#cloudState").textContent==="Conflict"',timeout=6000)
 assert 'Local Device Goal' not in str(repo.files['data/latest.json'])
 print("before keep local")
 pc.on('dialog',lambda d:d.accept());pc.locator('#cloudChooseLocal').click()
 pc.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=6000)
 assert 'Local Device Goal' in str(repo.files['data/latest.json'])
 # Stale SHA 409 must show Conflict and not call Synced.
 print("before device one conflict")
 pc.locator('#cloudClose').click();pc.locator('#newGoal').fill('Must not sync on 409');pc.locator('#goalForm button[type=submit]').click()
 repo.reject=1;pc.locator('#cloudOpen').click();pc.locator('#cloudSyncNow').click();pc.wait_for_function('document.querySelector("#cloudState").textContent==="Conflict"',timeout=6000)
 assert 'Must not sync on 409' not in str(repo.files['data/latest.json'])
 # Resolve forced 409 without accepting newer remote data blindly.
 pc.locator('#cloudChooseRemote').click()
 pc.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=6000)
 # Offline: local changes persist but cloud backup must not be claimed.
 pc.locator('#cloudClose').click()
 pc.evaluate("Object.defineProperty(navigator, 'onLine', {configurable:true,value:false})")
 pc.locator('#newGoal').fill('Offline entry')
 pc.locator('#goalForm button[type=submit]').click()
 assert 'Offline entry' in str(pc.evaluate('window.__testStore'))
 pc.locator('#cloudOpen').click()
 assert state(pc)=='Offline'
 assert 'Offline entry' not in str(repo.files['data/latest.json'])
 # One transient HTTP 503, followed by a successful retry.
 pc.evaluate("Object.defineProperty(navigator, 'onLine', {configurable:true,value:true})")
 repo.failures=1
 pc.locator('#cloudSyncNow').click()
 pc.wait_for_function('document.querySelector("#cloudState").textContent==="Error"',timeout=6000)
 assert 'Offline entry' not in str(repo.files['data/latest.json'])
 pc.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=12000)
 assert 'Offline entry' in str(repo.files['data/latest.json'])
 # Backup History lists snapshots and allows download/restore actions.
 pc.locator('#cloudHistory').click()
 pc.wait_for_function('document.querySelectorAll(".cloud-history-row").length>0',timeout=6000)
 assert pc.locator('.cloud-history-row').count()>0
 # Journal attachments are serialized into the private backup, not discarded.
 pc.evaluate("""() => {
   fileGet=async id=>id==='attached-demo' ? {blob:new Blob(['private journal text'],{type:'text/plain'}),name:'note.txt',size:20,type:'text/plain'} : null;
   entries.unshift({id:'journal-demo',title:'Attachment cross-device test',text:'backup',created:new Date().toISOString(),updated:new Date().toISOString(),attachments:[{id:'attached-demo',name:'note.txt',size:20,type:'text/plain'}]});
   save('journal',entries);
 }""")
 pc.locator('#cloudSyncNow').click()
 pc.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=6000)
 restored_payload=json.loads(repo.files['data/latest.json'][1])['payload']
 assert any(f['id']=='attached-demo' and 'cHJpdmF0ZSBqb3VybmFsIHRleHQ=' in f['data'] for f in restored_payload['files'])
 third=browser.new_page();third.on('pageerror',lambda e:errors.append('third:'+str(e)));init(third)
 third.evaluate("""() => {window.__restoredFiles=[];filePut=async f=>{window.__restoredFiles.push({id:f.id,size:f.blob.size})};}""")
 connect(third)
 third.wait_for_function('document.querySelector("#cloudState").textContent==="Conflict"',timeout=6000)
 third.locator('#cloudChooseRemote').click()
 third.wait_for_function('document.querySelector("#cloudState").textContent==="Synced"',timeout=6000)
 assert any(f['id']=='attached-demo' for f in third.evaluate('window.__restoredFiles'))
 assert errors==[],errors
 mobile.screenshot(path=str(Path(__file__).resolve().parent/'mobile-cloud-preview.png'))
 pc.screenshot(path=str(Path(__file__).resolve().parent/'desktop-cloud-preview.png'))
 print('PASS all; requests',len(repo.requests),'writes',sum(k=='PUT' for k,u in repo.requests),'errors',errors)
 browser.close()
