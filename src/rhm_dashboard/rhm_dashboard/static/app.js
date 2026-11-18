"use strict";
/* Live read-only interface. No dummy telemetry, actuator commands, or third-party CDNs. */
const $ = id => document.getElementById(id);
const statusNames = ["HEALTHY", "WARNING", "CRITICAL", "STALE"];
const statusClasses = ["ok", "warn", "error", "stale"];
let socket = null;
let retryDelay = 750;
let retryTimer = null;
let connectedSocket = false;
let latest = null;
const history = [];
function token(){return sessionStorage.getItem("rhm_token") || "";}
function setConnection(state){
  const live = state === "LIVE";
  $("connection-state").textContent = state;
  $("nav-connection").textContent = live ? "Connected" : state === "RECONNECTING" ? "Reconnecting" : "Disconnected";
  ["nav-signal","top-signal"].forEach(id => $(id).classList.toggle("live",live));
  $("data-source").textContent = live ? "DATA: ROS 2 LIVE" : "DATA: UNAVAILABLE";
}
function showAuth(show, message=""){$("token-modal").classList.toggle("hidden",!show);$("token-error").textContent=message;}
function fmt(value, digits=1){return value==null||!Number.isFinite(Number(value))?"—":Number(value).toFixed(digits);}
function fmtTime(seconds){if(seconds==null)return "—";const d=new Date(seconds*1000);return isNaN(d.getTime())?"—":d.toLocaleTimeString([], {hour12:false});}
function statusLabel(value){return statusNames[value]||"UNKNOWN";}
function klass(value){return statusClasses[value]||"unknown";}
function setStatus(element,value){element.className="state-pill "+klass(value);element.textContent=statusLabel(value);}
function node(tag, cls, txt){const el=document.createElement(tag);if(cls)el.className=cls;if(txt!==undefined)el.textContent=txt;return el;}
function render(snapshot){
  latest=snapshot;
  const hasData=snapshot.received_health&&snapshot.connected;
  setConnection(hasData?"LIVE":"NO TELEMETRY");
  setStatus($("mobile-status"),hasData?snapshot.status:null);
  const score=hasData?snapshot.health_score:null;
  $("score").textContent=score===null?"—":Math.round(score);
  const percent=Math.max(0,Math.min(100,score||0));
  const shade=score===null?"#41536a":score>=80?"#41d8a3":score>=50?"#e9b661":"#ff737d";
  $("health-gauge").style.background=`conic-gradient(${shade} 0 ${percent}%,#263647 ${percent}% 100%)`;
  $("mobile-description").textContent=hasData?"Live ROS health observations":"No current robot telemetry";
  $("mobile-led").classList.toggle("live",hasData);
  const sensors=snapshot.sensors||[];
  $("sensor-count").textContent=hasData?String(sensors.length):"—";
  $("healthy-count").textContent=hasData?String(sensors.filter(s=>s.status===0).length):"—";
  $("warning-count").textContent=hasData?String(sensors.filter(s=>s.status===1||s.status===2).length):"—";
  $("last-observed").textContent=hasData?fmtTime(snapshot.last_ros_time):"—";
  $("insight-connection").textContent=hasData?"ROS health messages received":"ROS stream unavailable";
  $("insight-issues").textContent=hasData?`${sensors.filter(s=>s.status!==0).length} of ${sensors.length} are not healthy`:"Unknown";
  $("sensor-summary").textContent=hasData?`${sensors.length} OBSERVED SUBSYSTEMS`:"NO LIVE OBSERVATIONS";
  $("data-source").textContent=hasData?"DATA: ROS 2 LIVE":"DATA: UNKNOWN / STALE";
  const tbody=$("sensor-rows");tbody.replaceChildren();
  if(!hasData||sensors.length===0){const tr=node("tr");const td=node("td","empty-row","No live subsystem health available.");td.colSpan=5;tr.append(td);tbody.append(tr);}
  for(const s of sensors){
    const tr=node("tr");
    const main=node("td");main.append(node("span","sensor-name",s.name.replace(/^mobile\//,"")));
    const stat=node("td");stat.append(node("span","status-badge "+klass(s.status),statusLabel(s.status)));
    const rate=node("td","",s.rate_hz==null?"—":fmt(s.rate_hz,2)+" Hz");
    const age=node("td","",s.age_seconds==null?"—":fmt(s.age_seconds,2)+" s");
    const topic=node("td");topic.append(node("span","subtle",s.topic||s.summary||"Observed diagnostic"));
    tr.append(main,stat,rate,age,topic);tbody.append(tr);
  }
  const events=snapshot.events||[];$("event-count").textContent=`${events.length} EVENTS`;
  const eventList=$("event-list");eventList.replaceChildren();
  if(events.length===0){const empty=node("div","no-events");empty.append(node("span","","◌"),node("p","","No observed status changes or fault events yet."));eventList.append(empty);}
  for(const e of events.slice(0,15)){
    const row=node("div","timeline-entry");row.append(node("span","timeline-led "+klass(e.severity)));
    const body=node("div","timeline-copy");body.append(node("strong","",e.subsystem),node("p","",e.text),node("span","",`${e.origin==="transition"?"OBSERVED CHANGE":"FAULT EVENT"} · ${new Date(e.time_utc).toLocaleTimeString()}`));row.append(body);eventList.append(row);
  }
  if(hasData&&score!==null){
    history.push(score);if(history.length>80)history.shift();
    $("sample-total").textContent=`${history.length} OBSERVATIONS`;
    $("chart-empty").classList.toggle("hidden",history.length>1);
    drawChart();
  }
}
function drawChart(){
  const canvas=$("health-chart"); const rect=canvas.getBoundingClientRect();
  const dpr=Math.min(2,window.devicePixelRatio||1),w=rect.width,h=rect.height;
  if(w<10||h<10)return;canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  const ctx=canvas.getContext("2d");ctx.scale(dpr,dpr);
  ctx.strokeStyle="#28394d";ctx.lineWidth=1;for(let i=0;i<=4;i++){const y=12+(h-25)*i/4;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
  if(history.length<2)return;
  const points=history.map((v,i)=>[i*w/(history.length-1),12+(100-v)/100*(h-25)]);
  const gradient=ctx.createLinearGradient(0,0,0,h);gradient.addColorStop(0,"rgba(70,214,227,.23)");gradient.addColorStop(1,"rgba(70,214,227,0)");
  ctx.beginPath();ctx.moveTo(points[0][0],h);for(const p of points)ctx.lineTo(p[0],p[1]);ctx.lineTo(points[points.length-1][0],h);ctx.closePath();ctx.fillStyle=gradient;ctx.fill();
  ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.lineWidth=2;ctx.strokeStyle="#46d6e3";ctx.stroke();
  const last=points[points.length-1];ctx.beginPath();ctx.arc(last[0],last[1],4,0,Math.PI*2);ctx.fillStyle="#7df3ff";ctx.fill();
}
async function fetchSnapshot(){
  const headers=token()?{Authorization:"Bearer "+token()}:{};
  try{const response=await fetch("/api/snapshot",{headers,cache:"no-store"});if(response.status===401){showAuth(true);return;}if(response.ok){const data=await response.json();render(data);}}catch(_){/* websocket retry handles connectivity */}
}
function scheduleRetry(){
  clearTimeout(retryTimer);setConnection("RECONNECTING");
  retryTimer=setTimeout(connect,retryDelay+Math.random()*250);
  retryDelay=Math.min(30000,Math.round(retryDelay*1.7));
}
function connect(){
  if(socket){try{socket.close();}catch(_){}}
  const url=(location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws/health";
  socket=new WebSocket(url);
  socket.onopen=()=>{retryDelay=750;connectedSocket=true;setConnection("CONNECTING");if(token())socket.send(JSON.stringify({token:token()}));};
  socket.onmessage=event=>{try{const obj=JSON.parse(event.data);if(obj.type==="snapshot"&&obj.version===1)render(obj.data);}catch(_){}};
  socket.onclose=()=>{connectedSocket=false;scheduleRetry();};
  socket.onerror=()=>{connectedSocket=false;};
}
$("token-form").addEventListener("submit",e=>{e.preventDefault();sessionStorage.setItem("rhm_token",$("token-input").value.trim());$("token-input").value="";showAuth(false);connect();fetchSnapshot();});
$("refresh").addEventListener("click",()=>fetchSnapshot());
window.addEventListener("resize",drawChart);
setInterval(()=>{$("clock-utc").textContent=new Date().toLocaleTimeString([],{hour12:false})+" LOCAL";},1000);
setInterval(()=>{if(!connectedSocket)fetchSnapshot();},5000);
connect();fetchSnapshot();
