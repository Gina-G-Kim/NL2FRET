"""Builds the 60-item Lockheed Martin dataset from the 59-item file plus NASA material that closes the gaps found in the audit.
 - LM-07_AP-1.2 and LM-07_AP-1.8 are restored with the activation-condition sentences that NASA recorded in the comments of AP-002 and AP-008 in LM_requirements.json (AP-002A, AP-008A).
 - LM-09_EUL-N1 part 7 gets a second reference version from NASA's CoCoSpec file euler321_Spec.lus (guarantee EUL-001.3).
 - LM-06_EB-N2 stays out: its NASA sentence conflicts with the original requirement and no other NASA material gives a different version."""
import json,csv,re
old=[json.loads(l) for l in open('/home/claude/out/dataset/lm_dataset_61.jsonl')]
L=[json.loads(l) for l in open('/home/claude/out/dataset/lm_dataset_59.jsonl')]
nasa=json.load(open('/home/claude/nasa-sw-vnv/fret/caseStudies/LMCPS/LM_requirements.json'))
R={r['reqid']:r for r in nasa['requirements']}
def com(rid,tag):
    m=re.search(re.escape(tag)+r':\s*(.*?)\n(?:AP-|\Z)',R[rid]['comments']+'\n',flags=re.S)
    return re.sub(r'\s+',' ',m.group(1)).strip()
SRC='fret/caseStudies/LMCPS/LM_requirements.json'
ap2=com('AP-002','AP-002A'); ap8=com('AP-008','AP-008A')
print(ap2,'|',ap8)
for x in old:
    if x['item_id']=='LM-07_AP-1.2':
        y=dict(x); y.pop('stratum',None)
        y['reference_parts']=[[{'reqid':'AP-002A','fretish':ap2,'source':SRC+' (comments of AP-002)'}]]
        y['n_parts']=1; y['n_reference_versions']=1; y['mapping_basis']='id_order'
        y['mapping_note']='NASA comments of AP-002 record the original split AP-002A (activation condition) and AP-002B (command); AP-002A is the sentence for requirement 1.2. NASA CoCoSpec RollAutopilotSpec.lus has the same condition in mode roll_hold_mode (require no_other_lateral_mode and autopilot_engaged)'
        L.append(y)
    if x['item_id']=='LM-07_AP-1.8':
        y=dict(x); y.pop('stratum',None)
        y['reference_parts']=[[{'reqid':'AP-008A','fretish':ap8,'source':SRC+' (comments of AP-008)'}]]
        y['n_parts']=1; y['n_reference_versions']=1; y['mapping_basis']='id_order'
        y['mapping_note']='NASA comments of AP-008 record the earlier split AP-008A (activation) and AP-008B (command); AP-008A is the sentence for requirement 1.8. NASA CoCoSpec RollAutopilotSpec.lus has the same condition in mode hdg_hold_mode (require HDGmode)'
        L.append(y)
for x in L:
    if x['item_id']=='LM-09_EUL-N1':
        p=[p for p in x['reference_parts'] if p[0]['reqid']=='EUL-001G'][0]
        p.append({'reqid':'EUL-001G@lus','fretish':'Euler shall always satisfy DCM321_31 = sin(phi) * sin(psi) + cos(phi) * sin(theta) * cos(psi)','source':'FRET_CoCoSim/9_euler/FRET/euler321_Spec.lus guarantee "EUL-001.3" (DCM321_3_1)'})
        x['n_reference_versions']=sum(len(q) for q in x['reference_parts'])
for x in L:
    if x['item_id']=='LM-09_EUL-N4':
        p=[p for p in x['reference_parts'] if p[0]['reqid']=='EUL-004'][0]
        p.append({'reqid':'EUL-004@lus','fretish':'Euler shall always satisfy absReal(theta) != pi/2.0 => det_3x3(DCM321_11, DCM321_21, DCM321_31, DCM321_12, DCM321_22, DCM321_32, DCM321_13, DCM321_23, DCM321_33) != 0.0','source':'FRET_CoCoSim/9_euler/FRET/euler321_Spec.lus guarantee "EUL-004" (DCM_det = det_3x3 of the nine DCM321 elements, defined at line 49)'})
        x['n_reference_versions']=sum(len(q) for q in x['reference_parts'])
    if x['item_id']=='LM-09_EUL-N8':
        p=[p for p in x['reference_parts'] if p[0]['reqid']=='EUL-008'][0]
        p.append({'reqid':'EUL-008@lus','fretish':'Euler shall always satisfy det_3x3(DCM321_11, DCM321_21, DCM321_31, DCM321_12, DCM321_22, DCM321_32, DCM321_13, DCM321_23, DCM321_33) = 1.0','source':'FRET_CoCoSim/9_euler/FRET/euler321_Spec.lus guarantee "EUL-008" (DCM_det = 1.0)'})
        x['n_reference_versions']=sum(len(q) for q in x['reference_parts'])
def key(x): return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)',x['item_id'])]
L.sort(key=key)
for x in L: x.pop('stratum',None)
import subprocess,os
vs=[v for x in L for p in x['reference_parts'] for v in p]
json.dump([v['fretish'] for v in vs],open('/tmp/ref_in.json','w'))
env=dict(os.environ,NODE_PATH='/home/claude/fretnode/node_modules:/home/claude/fretnode/stub')
out=json.loads(subprocess.run(['node','/home/claude/fretnode/pf.js','/tmp/ref_in.json'],capture_output=True,text=True,env=env,timeout=600).stdout)
strip=lambda t: re.sub(r'</?[bi]>','',t)
for v,o in zip(vs,out):
    if o['ok']: v['ltl_ft'],v['ltl_pt']=o['ltl_ft'],o['ltl_pt']; v['ltl_source']='FRET parser (FretSemantics.js)'
    else:
        sem=R[v['reqid']]['semantics']   # FRET parser rejects the variable name T; NASA's stored semantics are used
        v['ltl_ft'],v['ltl_pt']=strip(sem['ftExpanded']),strip(sem['ptExpanded']); v['ltl_source']='NASA LM_requirements.json semantics'
with open('lm_dataset_final.jsonl','w',encoding='utf-8') as f:
    for x in L: f.write(json.dumps(x,ensure_ascii=False)+'\n')
rows=[]
for x in L:
    for pi,p in enumerate(x['reference_parts'],1):
        for vi,v in enumerate(p,1):
            rows.append(dict(item_id=x['item_id'],n_parts=len(x['reference_parts']),part=pi,n_versions=len(p),version=vi,reqid=v['reqid'],fretish=v['fretish'],natural_language=x['natural_language'],nl_locator=x['nl_source']['locator'],mapping_basis=x['mapping_basis'],mapping_note=x['mapping_note'],reference_source=v['source']))
F=list(rows[0].keys())
print(len(L),len(rows))

# one Excel workbook: dataset (grouped), excluded, audit
import openpyxl
from openpyxl.styles import Alignment,PatternFill,Border,Side,Font
wb=openpyxl.Workbook(); ws=wb.active; ws.title='데이터셋'
H=['항목 ID','자연어 요구사항','파트','버전','정답 ID','정답 FRETish','짝짓기 근거','정답 출처','대표(판정 후 기록)']
ws.append(H)
for c in ws[1]: c.font=Font(bold=True); c.fill=PatternFill('solid',fgColor='D9D9D9')
thick=Side(style='medium'); thin=Side(style='thin',color='BBBBBB'); r0=2
fills=['FFFFFF','F2F2F2']
for k,x in enumerate(L):
    start=ws.max_row+1
    for pi,p in enumerate(x['reference_parts'],1):
        for vi,v in enumerate(p,1):
            ws.append([x['item_id'],x['natural_language'],f"{pi}/{len(x['reference_parts'])}",f"{vi}/{len(p)}",v['reqid'],v['fretish'],x['mapping_basis'],v['source'],None])
    end=ws.max_row
    if end>start:
        for col in (1,2,7):
            ws.merge_cells(start_row=start,start_column=col,end_row=end,end_column=col)
    for r in range(start,end+1):
        for c in range(1,10):
            cell=ws.cell(r,c); cell.fill=PatternFill('solid',fgColor=fills[k%2]); cell.alignment=Alignment(wrap_text=True,vertical='top')
            cell.border=Border(top=thick if r==start else thin,bottom=thick if r==end else thin,left=thin,right=thin)
for col,w in zip('ABCDEFGHI',(16,60,7,7,14,70,12,40,18)): ws.column_dimensions[col].width=w
ws.freeze_panes='A2'
ws2=wb.create_sheet('제외'); ws2.append(['항목 ID','제외 규칙','제외 사유','확인한 NASA 자료'])
ws2.append(['LM-06_EB-N2','NASA 자료 안에서 NL과 기준이 서로 모순이고 NASA 다른 자료로도 복구되지 않는 항목은 제외','NASA EB-002 설명문(> 1e-12, ridge_on False)과 형식화(<= eps12 => ridge_on)가 반대. docx 방향 기준은 NASA 자료에 없음','LM_requirements.json EB-001/EB-002; EBSpec.lus 121-126; RE2020 NASA 논문'])
ws3=wb.create_sheet('감사'); A=json.load(open('/home/claude/out/audit/entries.json'))
K=['item_id','class','excluded','exclusion_reason','restore_source','nl_evidence','ref_evidence','remark','recheck_source']
ws3.append(K)
for e in A.values(): ws3.append([str(e.get(k,'')) if k!='excluded' else bool(e.get(k,False)) for k in K])
for w_ in (ws2,ws3):
    for col in 'ABCDEFGHI': w_.column_dimensions[col].width=34
wb.save('lm_dataset_table.xlsx')
