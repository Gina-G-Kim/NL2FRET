"""Builds the vocabulary dictionary for the 59 Lockheed Martin items with one rule for every challenge.
Layers (each entry records which layers contain it):
  A  docx    : cells of the 'Input Scope' / 'Output Scope' tables and the NLGuidance 'Name | Variable Name | Definition' table of the original requirement docx (name, type, description)
  B  model   : ports of the original Simulink models for the FRET components that the challenge's reference sentences use (name, direction, type, dimensions), as extracted in LM_requirements.json (tool=Simulink); matrix and vector ports are also listed per element (name_ij, name_i)
  C  nasa    : variable declarations of the same FRET components in LM_requirements.json (name, direction, type only; assignment, description and mode fields are not copied)
No selection by item, no rewriting, no ordering by relevance. The dictionary is per challenge and identical for every item of that challenge."""
import json,re,collections,docx,glob,os
ROOT='/home/claude/lm_challenges/original_models'
L=[json.loads(l) for l in open('/home/claude/out/dataset2/lm_dataset_final.jsonl')]
NASA=json.load(open('/home/claude/nasa-sw-vnv/fret/caseStudies/LMCPS/LM_requirements.json'))
sim=[v for v in NASA['variables'] if v.get('tool')=='Simulink']
decl=[v for v in NASA['variables'] if 'idType' in v]
NUM2CH={x['challenge'].split('_')[0].lstrip('0') or '0':x['challenge'] for x in L}
SHALLOW=(os.environ.get('SHALLOW','1')=='1')
E=collections.OrderedDict()   # (challenge,name)->entry
def ent(ch,name):
    k=(ch,name)
    if k not in E: E[k]=dict(challenge=ch,name=name,direction=set(),type=set(),dims=set(),description=[],sources=set(),components=set(),scope=set())
    return E[k]
# layer A
for f in sorted(glob.glob(ROOT+'/*/*.docx')):
    base=os.path.basename(os.path.dirname(f)); ch=NUM2CH.get(base.split('_')[0])
    if ch is None: continue
    d=docx.Document(f)
    for t in d.tables:
        hdr=[c.text.strip() for c in t.rows[0].cells]
        if hdr and hdr[0] in('Input Scope','Output Scope'):
            direc='Input' if hdr[0]=='Input Scope' else 'Output'
            for r in t.rows[1:]:
                c=[x.text.strip().replace('\n',' ') for x in r.cells]
                if len(c)>=5 and c[1] and c[1]!='Name':
                    e=ent(ch,c[1]); e['direction'].add(direc); e['sources'].add('docx'); e['scope'].add(c[0])
                    if c[3]: e['type'].add(c[3])
                    if c[4] and c[4] not in e['description']: e['description'].append(c[4])
        elif hdr[:2]==['Name','Variable Name']:
            for r in t.rows[1:]:
                c=[x.text.strip().replace('\n',' ') for x in r.cells]
                if len(c)>=3 and c[1]:
                    e=ent(ch,c[1]); e['sources'].add('docx'); 
                    txt=c[0]+': '+c[2]
                    if txt not in e['description']: e['description'].append(txt)
# components used by each challenge
comp=collections.defaultdict(set)
for x in L:
    for p in x['reference_parts']:
        for v in p: comp[x['challenge']].add(re.search(r'(\S+)\s+shall\b',v['fretish']).group(1))
def expand(v):
    n=v['variable_name']; dm=v.get('dimensions') or [1,1]; out=[(n,'')]
    if len(dm)==3:
        for i in range(1,dm[1]+1):
            for j in range(1,dm[2]+1): out.append((f'{n}_{i}{j}',f'element of {n}'))
    elif len(dm)==2 and dm[1]>1:
        for i in range(1,dm[1]+1): out.append((f'{n}_{i}',f'element of {n}'))
    return out
depth={}
for v in sim:
    k=v['fretComponent']; dp=v['component_name'].count('/'); depth[k]=min(depth.get(k,99),dp)
for ch,cs in comp.items():
    for v in sim:
        if v['fretComponent'] in cs and (not SHALLOW or v['component_name'].count('/')==depth[v['fretComponent']]):
            for nm,note in expand(v):
                e=ent(ch,nm); e['sources'].add('model'); e['direction'].add(v.get('portType','')); e['components'].add(v['fretComponent'])
                if v.get('dataType'): e['type'].update(v['dataType'])
                if v.get('dimensions') and not note: e['dims'].add('x'.join(map(str,v['dimensions'][1:])) if len(v['dimensions'])==3 else str(v['dimensions'][-1]))
                if note and note not in e['description']: e['description'].append(note)
    for v in decl:
        if v['component_name'] in cs:
            e=ent(ch,v['variable_name']); e['sources'].add('nasa'); e['components'].add(v['component_name'])
            if v.get('idType'): e['direction'].add(v['idType'])
            if v.get('assignment') and v['idType']=='Internal': e.setdefault('definition',set()).add(v['assignment'].strip())
            if v['idType']=='Function': e.setdefault('kinds',set()).add('function')
            if v.get('dataType'): e['type'].add(v['dataType'] if isinstance(v['dataType'],str) else ','.join(v['dataType']))
FRET_FN=[('preBool(init,p)','FRET: value of boolean p at the previous time point; init is returned at the start of the trace'),
 ('preInt(init,n)','FRET: value of integer n at the previous time point; init is returned at the start of the trace'),
 ('preReal(init,x)','FRET: value of real x at the previous time point; init is returned at the start of the trace'),
 ('persisted(n,p)','FRET: p has held true for the previous n time points and the current time point, within the current scope interval; n is an integer literal'),
 ('occurred(n,p)','FRET: p held at least once in the previous n time points or at the current time point; n is an integer literal'),
 ('persists(n,p)','FRET: p holds for the next n time points and the current time point; n is an integer literal'),
 ('occurs(n,p)','FRET: p holds at least once in the next n time points or at the current time point; n is an integer literal'),
 ('absReal(x)','FRET built-in: absolute value of a real'),('absInt(x)','FRET built-in: absolute value of an integer'),
 ('maxReal(a,b)','FRET built-in: larger of two reals'),('maxInt(a,b)','FRET built-in: larger of two integers'),
 ('minReal(a,b)','FRET built-in: smaller of two reals'),('minInt(a,b)','FRET built-in: smaller of two integers')]
rows=[]
for (ch,nm),e in sorted(E.items(), key=lambda kv:(kv[0][0],kv[0][1].lower())):
    if ch not in comp: continue
    rows.append(dict(challenge=ch,name=nm,direction='/'.join(sorted({{'Inport':'Input','Outport':'Output'}.get(x,x) for x in e['direction'] if x})),type='/'.join(sorted(e['type'])),
        dims='/'.join(sorted(e['dims'])),description=' ; '.join(e['description']),sources='+'.join(s for s in ('docx','model','nasa') if s in e['sources']),
        components=','.join(sorted(e['components'])),
        kind=('function' if 'function' in e.get('kinds',()) else ('constant' if e.get('definition') and all(re.fullmatch(r'-?[0-9.]+',d) for d in e['definition']) else ('defined' if e.get('definition') else ('element' if any(x.startswith('element of') for x in e['description']) else 'signal')))),
        definition=' ; '.join(sorted(e.get('definition',()))),model_signal=''))
# names used as functions in the reference sentences of the challenge
used_fn=collections.defaultdict(set)
for x in L:
    for p in x['reference_parts']:
        for v in p: used_fn[x['challenge']]|=set(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)\s*\(',v['fretish']))
for r in rows:
    if r['name'] in used_fn[r['challenge']] and r['kind'] in('signal',): r['kind']='function'
# component rows and FRET function rows
for ch,cs in sorted(comp.items()):
    for c in sorted(cs):
        rows.append(dict(challenge=ch,name=c,direction='',type='',dims='',description='FRET component that the requirement sentences name as subject',sources='nasa',components=c,kind='component',definition='',model_signal=''))
    for nm,ds in FRET_FN:
        rows.append(dict(challenge=ch,name=nm,direction='',type='',dims='',description=ds,sources='fret_docs',components='',kind='function',definition='',model_signal=''))
rows.append(dict(challenge='04_NLG',name='pre_yout',direction='',type='',dims='',description='used by NLG-004..006 sentence text; NASA spec file NLGuidanceSpec.lus writes the same requirement with the term "pre yout"',sources='nasa_spec',components='NLGuidance',kind='defined',definition='pre yout',model_signal=''))

# layer D (nasa_lus): contract-level definitions and function nodes of NASA's CoCoSpec files that sit next to the FRET project
LUS_ROOT='/home/claude/lm_challenges/FRET_CoCoSim'
STD={'H','SI','S','O','OTlore','OT','HT','ST','SIT','delay'}
byk={(r['challenge'],r['name']):r for r in rows}
def getrow(ch,name,**kw):
    r=byk.get((ch,name))
    if r is None:
        r=dict(challenge=ch,name=name,direction='',type='',dims='',description='',sources='',components='',kind='signal',definition='',model_signal='')
        rows.append(r); byk[(ch,name)]=r
    return r
def addsrc(r,src):
    ss=r['sources'].split('+') if r['sources'] else []
    if src not in ss: ss.append(src)
    r['sources']='+'.join(ss)
for d in sorted(glob.glob(LUS_ROOT+'/*/')):
    base=os.path.basename(d.rstrip('/')); ch=NUM2CH.get(base.split('_')[0])
    if ch is None: continue
    fd=[x for x in glob.glob(d+'*') if os.path.basename(x).lower()=='fret']
    if not fd: continue
    for f in sorted(glob.glob(fd[0]+'/*Spec.lus')):
        if f.endswith('V2.lus'): continue
        txt=open(f,errors='ignore').read()
        for m in re.finditer(r'^[ \t]*var[ \t]+([A-Za-z_][A-Za-z_0-9]*)[ \t]*:[ \t]*([^=;]+?)[ \t]*=[ \t]*([^;]*);',txt,flags=re.M):
            nm,ty,ex=m.group(1),m.group(2).strip(),re.sub(r'\s+',' ',m.group(3)).strip()
            if nm in ('D',) or nm.startswith('FTP'): continue
            r=getrow(ch,nm); addsrc(r,'nasa_lus')
            if not r['definition']: r['definition']=ex
            if not r['type']: r['type']=ty
            if not r['direction']: r['direction']='Internal'
            r['kind']='constant' if re.fullmatch(r'-?[0-9.]+',ex) else 'defined'

        for m in re.finditer(r'contract[ \t]+[A-Za-z_0-9]+[ \t]*\((.*?)\)\s*returns\s*\((.*?)\)\s*;',txt,flags=re.S):
            for grp,direc in ((m.group(1),'Input'),(m.group(2),'Output')):
                for decl_ in grp.split(';'):
                    if ':' not in decl_: continue
                    names_,ty_=decl_.split(':',1)
                    for nm_ in [n.strip() for n in names_.split(',') if n.strip()]:
                        r=getrow(ch,nm_); addsrc(r,'nasa_lus')
                        if not r['direction']: r['direction']=direc
                        if not r['type']: r['type']=re.sub(r'\s+',' ',ty_).strip()
        if re.search(r'#open\s*[<"]lustrec_math',txt):
            for nm_ in ('sin','cos','sqrt'):
                r=byk.get((ch,nm_))
                if r is not None and r['kind']=='function' and not r['definition']:
                    r['definition']='provided by the lustrec_math library (opened with #open in '+os.path.basename(f)+')'; addsrc(r,'nasa_lus')
        ntxt=re.sub(r'\(\*.*?\*\)','',txt,flags=re.S)
        for m in re.finditer(r'^[ \t]*node[ \t]+([A-Za-z_][A-Za-z_0-9]*)[ \t]*\((.*?)\)\s*returns.*?\blet\b(.*?)\btel\b',ntxt,flags=re.M|re.S):
            nm=m.group(1)
            if nm in STD: continue
            body=re.sub(r'\s+',' ',m.group(3)).strip()
            r=getrow(ch,nm); addsrc(r,'nasa_lus'); r['kind']='function'
            r['definition']='('+re.sub(r'\s+',' ',m.group(2)).strip()+') '+body
# mag is inside a comment block in NLGuidanceSpec.lus
r=getrow('04_NLG','mag'); addsrc(r,'nasa_lus'); r['kind']='function'; r['definition']='(x : real^3) y = sqrt( x[0] * x[0] + x[1] * x[1] + x[2] * x[2] )'
r['description']='definition is inside a comment block of NLGuidanceSpec.lus'
r=getrow('04_NLG','dot'); addsrc(r,'nasa_lus'); r['kind']='function'; r['definition']='dot_product (x : real^3; y : real^3) z = x[0] * y[0] + x[1] * y[1] + x[2] * y[2]'
r['description']='NLGuidanceSpec.lus translates the FRETish sentence "yout * Xr > 0" (NLG-004) to dot_product(yout, Xr) > 0'
r=getrow('07_AP','hdg_mode_is_active'); addsrc(r,'nasa'); r['kind']='signal'; r['type']='boolean'
r['description']='named in NASA comment AP-008A and in the NASA description of hdg_hold; the NASA CoCoSpec mode hdg_hold_mode requires HDGmode'
# model signal name (modeldoc_id) of NASA declarations
for v in decl:
    if v.get('modeldoc_id'):
        for ch,cs in comp.items():
            if v['component_name'] in cs:
                r=byk.get((ch,v['variable_name']))
                if r is not None and not r.get('model_signal'): r['model_signal']=v['modeldoc_id']
import csv
with open('lm_dictionary.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows),collections.Counter(r['challenge'] for r in rows))
print(collections.Counter(r['sources'] for r in rows))
