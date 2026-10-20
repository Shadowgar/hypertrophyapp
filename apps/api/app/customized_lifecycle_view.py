"""Small isolated review flow reusing the actual C3A candidate renderer."""
from html import escape
import json

from .customized_preview_models import PreviewResponse
from .customized_preview_view import render_preview
from .customized_comparison_view import render_comparison


def render_lifecycle(document):
    preview=PreviewResponse.model_validate(document['snapshot']['preview'])
    html=render_preview(preview)
    summary=(f'<section aria-label="Candidate lifecycle"><h2>Inactive candidate: {escape(document["state"])}</h2>'
        f'<p>Proposal {escape(document["proposal_id"])} · plan version {document["plan_version"]} · event revision {document["revision"]}</p>'
        '<p>Acceptance records a candidate choice only. No workout exists and activation is disabled.</p>'
        '<ul>'+''.join(f'<li>{escape(r)}</li>' for r in document['blocking_reasons'])+'</ul></section>')
    return html.replace('<body>','<body>'+summary+render_comparison(document['snapshot'])+'<details id="full-workout"><summary>View the complete proposed three-day workout</summary>',1).replace('</body>','</details></body>',1)


def render_shell(server,initial_request,*,consent_protocol="granular-candidate-consent-v1"):
    initial=json.dumps(initial_request or {},indent=2)
    options=''.join(f'<option value="{escape(b.bundle_id,quote=True)}">{escape(b.display_name)}</option>' for b in server.bundles)
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Customized inactive candidate review</title><style>
body{font:16px system-ui;margin:1rem auto;padding:0 1rem;max-width:1100px;background:#101827;color:#edf2fa}label{display:block;margin:.6rem 0}input,select,textarea,button{font:inherit;max-width:100%;box-sizing:border-box;padding:.6rem}textarea{width:100%;height:12rem}button{margin:.4rem .4rem .4rem 0}input[type=password]{width:100%}#preview{background:white;color:#111;padding:1rem;overflow-wrap:anywhere}#notice{white-space:pre-wrap;overflow-wrap:anywhere}#acknowledgements label{padding:.5rem;border:1px solid #8798ad;overflow-wrap:anywhere}h1{font-size:1.5rem}.comparison-table{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:.5rem;border:1px solid #9ba6b3;text-align:left;overflow-wrap:anywhere}caption{font-size:.9rem}#consent-binding{overflow-wrap:anywhere;font-size:.9rem}</style>
<script src="/customized/lifecycle.js" defer></script></head><body>
<h1>Customized inactive candidate review</h1><p>Nonproduction only. No Start Workout or live activation. Rules and inventories are provisional; no optimality claim.</p>
<label>Isolated bearer credential <input id="credential" type="password" autocomplete="off"></label>
<label>Candidate <select id="candidate">'''+options+'''</select></label>
<label>Hard session cap (minutes) <input id="cap" type="number" min="1" max="240" value="60"></label>
<details><summary>Explicit profile and selected local dates</summary><p>Review skill, restrictions, equipment, timezone and exact dates. Unknown inputs stay unknown. Revising preserves prior history.</p>
<label>Profile JSON <textarea id="profile" spellcheck="false">'''+escape(initial)+'''</textarea></label></details>
<button id="preview-button">Preview candidate</button><button id="revise" disabled>Save new revision</button>
<button id="prepare" disabled>Review consent terms</button><button id="decline" disabled>Decline candidate</button>
<button id="withdraw" disabled>Withdraw acceptance</button><button id="authorization" disabled>Show activation blockers</button>
<p id="notice" role="status"></p><div id="preview"></div><section id="consent" hidden><h2>Explicit candidate consent</h2><p id="terms"></p><p id="consent-binding"></p><div id="acknowledgements"></div>
<label><input id="agree" type="checkbox"> I explicitly choose Customized and accept this exact inactive candidate revision.</label>
<button id="accept">Accept inactive candidate</button></section></body></html>'''


SCRIPT = r'''
"use strict";
let current=null,challenge=null,generation=0,inputsDirty=false;
const el=id=>document.getElementById(id);
const notice=text=>{el("notice").textContent=text;};
const operation=()=>{const version=generation,token=el("credential").value;return {token,valid:()=>version===generation&&token===el("credential").value};};
function verify(op){if(!op.valid())throw new Error("stale_account_or_inputs");}
function controls(){
 el("preview-button").disabled=false;
 for(const id of ["revise","decline","authorization"])el(id).disabled=!current;
 el("prepare").disabled=inputsDirty||!current||!["previewed","review_required"].includes(current.state);
 el("withdraw").disabled=!current||!current.consent_receipt;
 el("accept").disabled=!challenge;
}
function body(){const data=JSON.parse(el("profile").value);data.bundle_id=el("candidate").value;data.cap_minutes=Number(el("cap").value);return data;}
async function call(path,data,op,key=crypto.randomUUID()){
 verify(op);
 const response=await fetch(path,{method:data===undefined?"GET":"POST",credentials:"omit",headers:{"Authorization":"Bearer "+op.token,"Content-Type":"application/json","Idempotency-Key":key},body:data===undefined?undefined:JSON.stringify(data)});
 verify(op);const result=await response.json();verify(op);
 if(!response.ok)throw new Error(result.status||"request_denied");return result;
}
function resetConsent(){challenge=null;el("consent").hidden=true;el("agree").checked=false;}
async function show(document,op,confirmedInputs=false){
 verify(op);
 const response=await fetch("/customized/proposals/"+document.proposal_id+"/render",{credentials:"omit",headers:{Authorization:"Bearer "+op.token}});
 verify(op);if(!response.ok)throw new Error("preview_unavailable");
 const text=await response.text();verify(op);
 const parsed=new DOMParser().parseFromString(text,"text/html");
 if(confirmedInputs)inputsDirty=false;
 current=document;resetConsent();el("preview").replaceChildren(...Array.from(parsed.body.childNodes));
 notice(document.state+" · plan version "+document.plan_version+" · event revision "+document.revision+" · activation disabled");controls();
}
function action(id,fn){el(id).addEventListener("click",async()=>{
 generation++;const op=operation();el(id).disabled=true;
 try{await fn(op);}catch(error){if(op.valid())notice(error.message);}
 finally{if(op.valid())controls();}
});}
action("preview-button",async op=>show(await call("/customized/proposals",body(),op),op,true));
action("revise",async op=>show(await call("/customized/proposals/"+current.proposal_id+"/revisions",{expected_revision:current.revision,request:body()},op),op,true));
for(const id of ["decline","withdraw","authorization"])action(id,async op=>show(await call("/customized/proposals/"+current.proposal_id+"/"+id,{expected_revision:current.revision},op),op));
action("prepare",async op=>{
 const result=await call("/customized/proposals/"+current.proposal_id+"/challenge",{expected_revision:current.revision,snapshot_hash:current.snapshot_hash},op);
 verify(op);challenge=result;current=result;
 el("terms").textContent=challenge.terms.text;el("acknowledgements").replaceChildren();el("agree").checked=false;
 if(challenge.consent_protocol==="compact-candidate-consent-v2"){
  el("consent-binding").textContent="Plan version "+challenge.plan_version+" · summary "+challenge.summary_hash+" · inactive candidate only";
 }else{
  el("consent-binding").textContent="Legacy isolated audit stress test";
  for(const text of challenge.required_acknowledgements){const label=document.createElement("label"),check=document.createElement("input");check.type="checkbox";check.value=text;label.append(check,document.createTextNode(" "+text));el("acknowledgements").append(label);}
 }
 el("consent").hidden=false;notice("Review the comparison above. One explicit acknowledgement covers this exact version; scientific approval remains separate.");
});
action("accept",async op=>{
 if(!challenge||!el("agree").checked)throw new Error("Explicit agreement required");
 const acknowledgements=Array.from(el("acknowledgements").querySelectorAll("input:checked")).map(x=>x.value);
 const payload={expected_revision:challenge.revision,snapshot_hash:challenge.snapshot_hash,challenge:challenge.challenge,terms_hash:challenge.terms_hash,mode:"customized",agree:true};
 if(challenge.consent_protocol==="compact-candidate-consent-v2"){payload.protocol=challenge.consent_protocol;payload.summary_hash=challenge.summary_hash;}else{payload.acknowledgements=acknowledgements;}
 await show(await call("/customized/proposals/"+current.proposal_id+"/accept",payload,op),op);
});
for(const id of ["profile","candidate","cap"])el(id).addEventListener("input",()=>{
 generation++;inputsDirty=true;resetConsent();if(current)notice("Inputs changed. Save and review a new revision before accepting.");controls();el("prepare").disabled=true;
});
el("credential").addEventListener("input",()=>{
 generation++;current=null;resetConsent();el("preview").replaceChildren();controls();notice("Account credential changed; previous account preview cleared.");
});
const initial=JSON.parse(el("profile").value);if(initial.bundle_id)el("candidate").value=initial.bundle_id;controls();
'''
