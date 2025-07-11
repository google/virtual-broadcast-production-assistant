(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))t(s);new MutationObserver(s=>{for(const n of s)if(n.type==="childList")for(const o of n.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&t(o)}).observe(document,{childList:!0,subtree:!0});function i(s){const n={};return s.integrity&&(n.integrity=s.integrity),s.referrerPolicy&&(n.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?n.credentials="include":s.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function t(s){if(s.ep)return;s.ep=!0;const n=i(s);fetch(s.href,n)}})();class d{constructor(){this.ws=null,this.activities=[],this.isConnected=!1,this.init()}init(){this.connectWebSocket(),this.setupEventListeners(),this.loadInitialActivities()}connectWebSocket(){const i=`${window.location.protocol==="https:"?"wss:":"ws:"}//${window.location.host}`;this.ws=new WebSocket(i),this.ws.onopen=()=>{console.log("WebSocket connected"),this.isConnected=!0,this.updateConnectionStatus(!0)},this.ws.onmessage=t=>{const s=JSON.parse(t.data);this.handleWebSocketMessage(s)},this.ws.onclose=()=>{console.log("WebSocket disconnected"),this.isConnected=!1,this.updateConnectionStatus(!1),setTimeout(()=>this.connectWebSocket(),3e3)},this.ws.onerror=t=>{console.error("WebSocket error:",t)}}handleWebSocketMessage(e){switch(e.type){case"initial_activities":this.activities=e.data,this.renderActivities();break;case"new_activity":this.addActivity(e.data);break;case"activities_cleared":this.activities=[],this.renderActivities();break}}addActivity(e){this.activities.unshift(e),this.activities.length>100&&(this.activities=this.activities.slice(0,100)),this.renderNewActivity(e)}renderNewActivity(e){const i=document.getElementById("activity-feed"),t=this.createActivityElement(e);t.style.opacity="0",t.style.transform="translateY(-20px)",i.insertBefore(t,i.firstChild),requestAnimationFrame(()=>{t.style.transition="all 0.3s ease-out",t.style.opacity="1",t.style.transform="translateY(0)"}),this.hideEmptyState()}renderActivities(){const e=document.getElementById("activity-feed");if(document.getElementById("loading").classList.add("hidden"),this.activities.length===0){this.showEmptyState();return}this.hideEmptyState(),e.innerHTML="",this.activities.forEach(t=>{const s=this.createActivityElement(t);e.appendChild(s)})}createActivityElement(e){const i=document.createElement("div"),t={graphics:"border-blue-500 bg-blue-500/10",vision:"border-green-500 bg-green-500/10",sofie:"border-purple-500 bg-purple-500/10",system:"border-red-500 bg-red-500/10",user:"border-yellow-500 bg-yellow-500/10"},s={graphics:"🎨",vision:"👁️",sofie:"📋",system:"⚙️",user:"👤"},n={critical:"ring-2 ring-red-400 animate-pulse",high:"ring-1 ring-yellow-400",normal:"",low:"opacity-75"},o=this.formatTimeAgo(e.timestamp),a=t[e.type]||t.system,c=s[e.type]||s.system,l=n[e.priority]||"";return i.className=`
      p-4 rounded-xl border backdrop-blur-sm transition-all hover:scale-[1.02]
      ${a} ${l}
    `,i.innerHTML=`
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <div class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
            <span class="text-lg">${c}</span>
          </div>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center space-x-2">
              <span class="text-xs font-semibold px-2 py-1 rounded-full bg-gray-700 text-gray-300 uppercase">
                ${e.type}
              </span>
              ${e.priority==="critical"?'<span class="text-xs font-bold text-red-400">CRITICAL</span>':""}
              ${e.priority==="high"?'<span class="text-xs font-semibold text-yellow-400">HIGH</span>':""}
            </div>
            <span class="text-xs text-gray-500">${o}</span>
          </div>
          <h4 class="text-sm font-semibold text-white mb-1">${this.escapeHtml(e.title)}</h4>
          <p class="text-sm text-gray-300 leading-relaxed">${this.escapeHtml(e.message)}</p>
          ${e.agent!=="unknown"?`
            <div class="mt-2 text-xs text-gray-500">
              by ${this.escapeHtml(e.agent)}
            </div>
          `:""}
          ${Object.keys(e.metadata||{}).length>0?`
            <details class="mt-2">
              <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
                Show metadata
              </summary>
              <pre class="text-xs text-gray-500 mt-1 bg-gray-800 p-2 rounded overflow-x-auto">
${JSON.stringify(e.metadata,null,2)}
              </pre>
            </details>
          `:""}
        </div>
      </div>
    `,i}formatTimeAgo(e){const i=new Date,t=new Date(e),s=i-t,n=Math.floor(s/1e3),o=Math.floor(n/60),a=Math.floor(o/60);return n<60?"just now":o<60?`${o}m ago`:a<24?`${a}h ago`:t.toLocaleDateString()}escapeHtml(e){const i=document.createElement("div");return i.textContent=e,i.innerHTML}updateConnectionStatus(e){const i=document.getElementById("connection-status"),t=i.querySelector("div"),s=i.querySelector("span");e?(t.className="w-2 h-2 bg-green-400 rounded-full animate-pulse",s.textContent="Connected"):(t.className="w-2 h-2 bg-red-400 rounded-full",s.textContent="Disconnected")}showEmptyState(){document.getElementById("empty-state").classList.remove("hidden")}hideEmptyState(){document.getElementById("empty-state").classList.add("hidden")}async loadInitialActivities(){try{const i=await(await fetch("/api/activities")).json();this.activities=i,this.renderActivities()}catch(e){console.error("Failed to load activities:",e),document.getElementById("loading").classList.add("hidden"),this.showEmptyState()}}setupEventListeners(){document.getElementById("clear-btn").addEventListener("click",async()=>{if(confirm("Are you sure you want to clear all activities?"))try{await fetch("/api/activities",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:"system",title:"Feed Cleared",message:"Activity feed was cleared by user",metadata:{action:"clear"}})})}catch(e){console.error("Failed to clear activities:",e)}}),document.querySelectorAll(".test-btn").forEach(e=>{e.addEventListener("click",async()=>{const i=e.dataset.type;await this.postTestActivity(i)})})}async postTestActivity(e){const t={graphics:{title:"Name strap updated",message:"Added name graphic for John Smith, News Anchor",metadata:{person:"John Smith",role:"News Anchor"}},vision:{title:"Screenshot analyzed",message:"Detected person speaking in bottom-left corner of screen",metadata:{detected:"person",location:"bottom-left",confidence:.95}},sofie:{title:"Rundown activated",message:"Evening News rundown is now live and ready for playout",metadata:{rundown:"evening-news",segments:8,duration:"30:00"}},system:{title:"System Alert",message:"Camera 2 signal lost - switching to backup feed",metadata:{camera:2,action:"backup_switch",severity:"warning"}}}[e];if(t)try{await fetch("/api/activities",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type:e,title:t.title,message:t.message,metadata:t.metadata,priority:e==="system"?"high":"normal",agent:"test-interface"})})}catch(s){console.error("Failed to post test activity:",s)}}}new d;
//# sourceMappingURL=index-Ydf5HZXR.js.map
