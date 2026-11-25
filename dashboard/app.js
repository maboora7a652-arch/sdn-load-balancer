"use strict";
const el = id => document.getElementById(id);
const ns = "http://www.w3.org/2000/svg";
const flowKey = f => f.src_mac + ">" + f.dst_mac;
const edgeKey = (a,b) => Math.min(a,b) + "-" + Math.max(a,b);
function rate(value) {
    if (!Number.isFinite(value)) return "—";
    if (value === 0) return "0";
    return value < 0.01 ? value.toLocaleString("en-US", {maximumSignificantDigits: 2}) : value.toFixed(2);
}
function usePercent(port) {
    if (Number.isFinite(port.tx_mbps) && port.capacity_mbps > 0)
        return port.tx_mbps * 100 / port.capacity_mbps;
    return port.utilization_percent;
}
const route = path => path?.length ? path.map(n => "S" + n).join(" → ") : "Pending";
let sample, previous, lastSeen, selected = "", history = [];
function hostName(mac) {
    const host = sample.hosts.hosts.find(h => h.mac === mac);
    return host ? "H" + host.ip.split(".").pop() : mac;
}
function pair(f) { return hostName(f.src_mac) + " → " + hostName(f.dst_mac); }
function svg(tag, attrs, label) {
    const node = document.createElementNS(ns, tag);
    for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,value);
    if (label !== undefined) node.textContent = label;
    el("map").append(node);
    return node;
}
function networkMap(flow) {
    const {switches,links} = sample.topology;
    const fat = switches.some(n => n > 6);
    const points = new Map();
    const grid = {1:[150,90],2:[490,90],3:[830,90],4:[150,220],5:[490,220],6:[830,220]};
    el("map").replaceChildren();
    el("map").setAttribute("viewBox", fat ? "0 0 980 326" : "0 0 980 310");
    for (const id of switches) {
        let pos = grid[id];
        if (fat) {
            if (id <= 8) pos = [62+(id-1)*122,212];
            else if (id <= 16) pos = [62+(id-9)*122,121];
            else pos = [190+(id-17)*200,39];
        }
        if (pos) points.set(id,pos);
    }
    function line(a,b,color,width,dash) {
        const attrs = {x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:color,"stroke-width":width};
        if (dash) attrs["stroke-dasharray"]=dash;
        return svg("line",attrs);
    }
    const path = flow?.installed_path || [];
    const active = new Set(path.slice(1).map((b,i) => edgeKey(path[i],b)));
    const hot = new Set(sample.bandwidth.ports.filter(p=>p.congested && p.neighbor)
        .map(p=>edgeKey(p.switch,p.neighbor)));
    for (const l of [...links].sort((a,b)=>Number(active.has(edgeKey(a.source,a.destination)))-
                                              Number(active.has(edgeKey(b.source,b.destination))))) {
        const a = points.get(l.source), b = points.get(l.destination);
        if (!a || !b) continue;
        const key = edgeKey(l.source,l.destination), on = active.has(key);
        line(a,b,on ? "#147555" : "#a6b8ac",on ? 5 : 2);
        if (hot.has(key)) line(a,b,"#bf541a",3,"7 5");
    }
    for (const h of sample.hosts.hosts) {
        const p = points.get(h.switch);
        if (!p) continue;
        const num = Number(h.ip.split(".").pop());
        const x = p[0] + (fat ? (num%2 ? -29 : 29) : 0);
        const y = fat ? 278 : p[1] + (p[1]<150 ? -56 : 55);
        line(p,[x,y],"#a6b8ac",1.5);
        svg("circle",{cx:x,cy:y,r:5,fill:"#59776a"});
        svg("text",{x,y:y+20},"H"+num);
    }
    for (const [id,[x,y]] of points) {
        svg("rect",{x:x-23,y:y-13,width:46,height:26,rx:5,fill:"#fff",
            stroke:path.includes(id)?"#147555":"#71877b","stroke-width":2});
        svg("text",{x,y:y+5},"S"+id);
    }
}
function table(id, rows, empty) {
    const body=el(id);
    body.replaceChildren();
    if (!rows.length) rows=[[empty]];
    for (const row of rows) {
        const tr=body.insertRow();
        for (const value of row) {
            const td=tr.insertCell();
            td.textContent=value;
            if (value==="Congested" || value==="Elephant") td.className="hot";
        }
    }
}
function showSelection() {
    const f = sample.flows.flows.find(item=>flowKey(item)===selected);
    networkMap(f);
    el("detail").textContent=f ? pair(f)+"  ·  "+route(f.installed_path)+"  ·  priority "+
        (f.installed_priority ?? "—")+"  ·  "+rate(f.rate_mbps)+" Mbps" : "No flow selected";
}
function changes(old, now) {
    const edges = data=>new Set(data.topology.links.map(l=>edgeKey(l.source,l.destination)));
    const before=edges(old), after=edges(now);
    const messages=[];
    for (const key of before) if (!after.has(key)) messages.push("Link disappeared · S"+key.replace("-"," ↔ S"));
    for (const key of after) if (!before.has(key)) messages.push("Link appeared · S"+key.replace("-"," ↔ S"));
    const oldFlows=new Map(old.flows.flows.map(f=>[flowKey(f),f.installed_path]));
    for (const f of now.flows.flows) {
        const was=oldFlows.get(flowKey(f));
        if (was?.length && f.installed_path?.length && String(was)!==String(f.installed_path))
            messages.push(pair(f)+" · "+route(was)+" ⇒ "+route(f.installed_path));
    }
    return messages;
}
function render() {
    const {switches,links}=sample.topology;
    const flows=[...sample.flows.flows].sort((a,b)=>Number(b.elephant)-Number(a.elephant) ||
        (b.rate_mbps ?? -1)-(a.rate_mbps ?? -1));
    el("summary").textContent=switches.length+" switches   /   "+links.length+" inter-switch links   /   "+
        sample.hosts.hosts.length+" learned hosts";
    const picker=el("pick");
    if (!flows.some(f=>flowKey(f)===selected)) {
        const initial=flows.find(f=>pair(f)==="H1 → H6") || flows[0];
        selected=initial ? flowKey(initial) : "";
    }
    picker.replaceChildren(...flows.map(f=>new Option(pair(f),flowKey(f))));
    if (!flows.length) picker.add(new Option("No flows yet",""));
    picker.value=selected;
    showSelection();
    const linksPresent=new Set(links.map(l=>edgeKey(l.source,l.destination)));
    const ports=sample.bandwidth.ports.filter(p=>p.neighbor && linksPresent.has(edgeKey(p.switch,p.neighbor)))
        .sort((a,b)=>Number(b.congested)-Number(a.congested) || b.utilization_percent-a.utilization_percent);
    table("ports",ports.map(p=>["S"+p.switch+" → S"+p.neighbor,rate(p.tx_mbps),
        rate(usePercent(p))+"%",p.congested?"Congested":"Normal"]),"Waiting for port samples");
    table("flows",flows.map(f=>[pair(f),rate(f.rate_mbps),f.elephant?"Elephant":
        Number.isFinite(f.rate_mbps)?"Other":"Sampling"]),"Waiting for flow samples");
    const entries=history.length?history:["No changes observed yet."];
    el("events").replaceChildren(...entries.map(text=>{
        const li=document.createElement("li"); li.textContent=text; return li;
    }));
}
el("pick").onchange=()=>{selected=el("pick").value;showSelection();};
async function refresh() {
    try {
        const response=await fetch("/snapshot",{cache:"no-store"});
        if (!response.ok) throw new Error("Controller unavailable");
        sample=await response.json();
        const stamp=new Date().toLocaleTimeString();
        if (previous) history=changes(previous,sample).map(msg=>stamp+" · "+msg).concat(history).slice(0,60);
        render();
        previous=sample;
        lastSeen=stamp;
        el("status").textContent="Controller connected · last read "+stamp;
    } catch {
        previous=null;
        el("status").textContent=lastSeen?"Disconnected · last update "+lastSeen:"Waiting for controller · retrying";
    } finally { setTimeout(refresh,1000); }
}
refresh();
