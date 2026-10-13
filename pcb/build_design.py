#!/usr/bin/env python3
"""Rebuild with KiCad 10 bundled Python. All outputs remain under pcb-design.
Coordinates in mm. Footprint geometry derived from saved EasyEDA C381135
and cross-checked against XKB PJ-327AX-SMT top-view drawing.
"""
import json, math, pathlib, shutil, uuid
import pcbnew as k
ROOT=pathlib.Path(__file__).resolve().parent
PROJ=ROOT/'xz1-splitter'; LIB=PROJ/'lib'/'XZ1.pretty'
LIB.mkdir(parents=True,exist_ok=True)
SHARED=pathlib.Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport')
U=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'xz1-splitter-v1/'+s))
Q=lambda s:json.dumps(str(s),ensure_ascii=False)
M=k.FromMM
V=lambda x,y:k.VECTOR2I(M(x),M(y))
# Local footprint library: origin = rectangular plastic body's geometric centre.
jack='''(footprint "PJ-327A0-SMT_C381135" (version 20260206) (generator "xz1-builder") (layer "F.Cu")
(descr "XKB PJ-327A0-SMT C381135. EasyEDA official geometry, normalized to body centre; 2=T 5=R 3=S; 4/6 unused. https://easyeda.com https://lceda.cn")
(attr smd)
(property "Reference" "REF**" (at 0 -5.8) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
(property "Value" "PJ-327A0-SMT" (at 0 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
(fp_rect (start -6 -3.05) (end 6 3.05) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
(fp_rect (start -8 -2.5) (end -6 2.5) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
(fp_rect (start -8.3 -5.3) (end 6.3 5.3) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
'''
for n,x,y in [('4',-4.4,-3.5),('5',-.8,-3.5),('6',5.1,-3.5),('3',-3.4,3.5),('2',3.5,3.5)]:
 jack+=f'(pad "{n}" smd rect (at {x} {y}) (size 1.5 3) (layers "F.Cu" "F.Paste" "F.Mask"))\n'
for x in [-3,3]:jack+=f'(pad "" np_thru_hole circle (at {x} 0) (size 1.1 1.1) (drill 1.1) (layers "*.Cu" "*.Mask"))\n'
# Silkscreen only along clear regions; full outline remains on Fab.
for a,b in [((-6,-3.18),(-5.4,-3.18)),((-3.4,-3.18),(-1.8,-3.18)),((.2,-3.18),(4.1,-3.18)),((-2.4,3.18),(2.5,3.18)),((-6,-3.18),(-6,3.18)),((6,-3.18),(6,3.18))]:
 jack+=f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
# Official mesh: OBJ X centre is +3.9 mm; Y is already 3D Y-up.
# KiCad legacy VRML coordinates use 0.1 inch units, hence /2.54.
models=PROJ/'lib/models';models.mkdir(exist_ok=True)
verts=[];faces={};materials={};mat='default';newmat=None
for line in (ROOT/'sources/C381135-model.obj').read_text().splitlines():
 t=line.split()
 if not t:continue
 if t[0]=='v':verts.append(((float(t[1])-3.9)/2.54,float(t[2])/2.54,float(t[3])/2.54))
 elif t[0]=='newmtl':newmat=t[1]
 elif t[0]=='Kd':materials[newmat]=list(map(float,t[1:4]))
 elif t[0]=='usemtl':mat=t[1]
 elif t[0]=='f':faces.setdefault(mat,[]).append([int(i.split('/')[0])-1 for i in t[1:]])
vrml='#VRML V2.0 utf8\n# Source: JLCEDA/EasyEDA Official Library, https://lceda.cn/ https://easyeda.com/\n'
for mat,fs in faces.items():
 color=' '.join(map(str,materials.get(mat,[.2,.2,.2])))
 points=',\n'.join(' '.join(f'{n:.7f}' for n in v) for v in verts)
 indices=',\n'.join(' '.join(map(str,f))+ ' -1' for f in fs)
 vrml+=f'Shape {{ appearance Appearance {{ material Material {{ diffuseColor {color} }} }} geometry IndexedFaceSet {{ solid FALSE coord Coordinate {{ point [ {points} ] }} coordIndex [ {indices} ] }} }}\n'
(models/'PJ-327A0-SMT.wrl').write_text(vrml)
jack+='(model "${KIPRJMOD}/lib/models/PJ-327A0-SMT.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n'
jack+=')\n';(LIB/'PJ-327A0-SMT_C381135.kicad_mod').write_text(jack)
shutil.copyfile(SHARED/'3dmodels/Resistor_SMD.3dshapes/R_0603_1608Metric.step',models/'R_0603_1608Metric.step')
resfp=(SHARED/'footprints/Resistor_SMD.pretty/R_0603_1608Metric.kicad_mod').read_text().replace('${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0603_1608Metric.step','${KIPRJMOD}/lib/models/R_0603_1608Metric.step')
(LIB/'R_0603_1608Metric.kicad_mod').write_text(resfp)
# One six-pad footprint, no purchased connector. Pad 4b is the second ground wire.
wirepos={'1':(5,2),'2':(5,4.5),'3':(5,7),'4':(5,9.5),'5':(5,12),'4b':(8,9.5)}
w='''(footprint "WirePads_5Pole_Star" (version 20260206) (generator "xz1-builder") (layer "F.Cu")
(attr through_hole exclude_from_pos_files exclude_from_bom)
(property "Reference" "REF**" (at 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
(property "Value" "Five pole cable" (at 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
'''
for n,(x,y) in wirepos.items():
 w+=f'(pad "{n}" thru_hole circle (at {x} {y}) (size 2 2) (drill 1) (layers "*.Cu" "*.Mask"))\n'
# Tie-down holes: within this footprint, excluded from assembly; no additional components.
for y in [1.2,13.8]:w+=f'(pad "" np_thru_hole circle (at 1.2 {y}) (size 1.3 1.3) (drill 1.3) (layers "*.Cu" "*.Mask"))\n'
w+='(fp_rect (start .6 .8) (end 9.2 13.2) (stroke (width .05) (type solid)) (fill none) (layer "B.CrtYd"))\n)';(LIB/'WirePads_5Pole_Star.kicad_mod').write_text(w)
(PROJ/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "XZ1") (type "KiCad") (uri "${KIPRJMOD}/lib/XZ1.pretty") (options "") (descr "Project local verified footprints")))\n')
# Schematic symbols use passive pins; all circuit parts are passive.
effect='(effects (font (size 1.27 1.27)))'
def prop(name,value,x=0,y=0,hide=False):return f'(property {Q(name)} {Q(value)} (at {x} {y} 0) (effects (font (size 1.27 1.27))'+(' (hide yes)' if hide else '')+'))'
def pin(n,name,x,y,angle=0,length=2.54):return f'(pin passive line (at {x} {y} {angle}) (length {length}) (name {Q(name)} {effect}) (number {Q(n)} {effect}))'
def libsymbol(name,ref,graphics,pins):return f'(symbol "{name}" (pin_names (offset 0.635)) (in_bom yes) (on_board yes) '+prop('Reference',ref,0,3.81)+prop('Value',name,0,-3.81)+f'(symbol "{name}_0_1" {graphics}) (symbol "{name}_1_1" '+''.join(pins)+'))'
rect=lambda x1,y1,x2,y2:f'(rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width .254) (type default)) (fill (type background)))'
res=libsymbol('R','R',rect(-2.54,1.016,2.54,-1.016),[pin('1','~',-5.08,0),pin('2','~',5.08,0,180)])
jpins=[('2','TIP',5.08),('5','RING',0),('3','SLEEVE',-5.08),('4','S_AUX',-10.16),('6','T_SWITCH',-15.24)]
jsym=libsymbol('PJ327','J',rect(-5.08,8.89,10.16,-17.78),[pin(n,name,-7.62,y) for n,name,y in jpins])
wps=[('1','L',0),('2','R',-5.08),('3','ML',-10.16),('4','G',-15.24),('4b','G2',-20.32),('5','MR',-25.4)]
wsym=libsymbol('Cable','W',rect(-5.08,3.81,5.08,-29.21),[pin(n,name,7.62,y,180) for n,name,y in wps])
libs=[res,jsym,wsym]
(PROJ/'lib/XZ1.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "xz1-builder") '+''.join(libs)+')')
(PROJ/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "XZ1") (type "KiCad") (uri "${KIPRJMOD}/lib/XZ1.kicad_sym") (options "") (descr "Project local symbols")))')
rootid=U('sheet'); items=[]
inst={}
def sym(name,ref,val,x,y,fp,lcsc='',bom=True):
 uid=U(ref); inst[ref]=uid
 props=prop('Reference',ref,x,y-(13.97 if name=='PJ327' else 7.62))+prop('Value',val,x,y-(11.43 if name=='PJ327' else 5.08))+prop('Footprint','XZ1:'+fp,x,y,True)+prop('Datasheet','',x,y,True)+prop('LCSC',lcsc,x,y,True)
 items.append(f'(symbol (lib_id "XZ1:{name}") (at {x} {y} 0) (unit 1) (in_bom {"yes" if bom else "no"}) (on_board yes) (dnp no) (uuid "{uid}") {props} (instances (project "xz1-splitter" (path "/{rootid}" (reference "{ref}") (unit 1)))))')
def wire(a,b):items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{U(str(a)+str(b))}"))')
def label(name,x,y):items.append(f'(label "{name}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{U(name+str(x)+str(y))}"))')
def text(s,x,y,size=1.27):items.append(f'(text {Q(s)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid "{U(s)}"))')
def labwire(net,x,y,dx=-7.62):
 e=(round(x+dx,4),y);wire((x,y),e);label(net,*e)
sym('Cable','W1','XZ1 FIVE-POLE CABLE',38.1,55.88,'WirePads_5Pole_Star',bom=False)
wn={'1':'HP_L','2':'HP_R','3':'MIC_L','4':'GND','4b':'GND','5':'MIC_R'}
for n,name,dy in wps:labwire(wn[n],45.72,round(55.88-dy,4),12.7)
for ref,y in [('J1',60.96),('J2',127)]:
 sym('PJ327',ref,'PJ-327A0-SMT',213.36,y,'PJ-327A0-SMT_C381135','C381135')
 for n,net,dy in jpins:
  py=round(y-dy,4)
  if n in ['4','6']:items.append(f'(no_connect (at 205.74 {py}) (uuid "{U(ref+n)}"))')
  else:labwire(({'2':'HP_L','5':'HP_R','3':'GND'} if ref=='J1' else {'2':'LINE_L','5':'LINE_R','3':'GND'})[n],205.74,py,-17.78)
for ref,val,x,y,a,b,lc in [('R1','10k',116.84,121.92,'MIC_L','LINE_L','C25804'),('R2','10k',116.84,142.24,'MIC_R','LINE_R','C25804'),('R3','2.2k',76.2,99.06,'MIC_L','GND','C4190'),('R4','2.2k',121.92,99.06,'MIC_R','GND','C4190')]:
 sym('R',ref,val,x,y,'R_0603_1608Metric',lc);labwire(a,round(x-5.08,4),y);labwire(b,round(x+5.08,4),y,7.62)
text('XZ1 STEREO SPLITTER  /  Rev A',25.4,25.4,2.54)
text('Fixed circuit: R1/R2 10k, R3/R4 2.2k, all 0603 1%.',25.4,33.02)
text('P4 = star point. Four independent returns: J1.S, J2.S, R3, R4. NO copper pours.',25.4,38.1)
text('1 PHONES (TRS)',190.5,43.18,1.524);text('2 LINE IN (TRS)',190.5,109.22,1.524)
text('W1.1-5 = P1-5. W1.4b = P4b (second ground wire).',25.4,170.18)
text('J1/J2: 2=Tip, 5=Ring, 3=Sleeve. Pins 4 and 6 intentionally unconnected.',25.4,175.26)
text('Do not substitute another PJ-327 variant. See sources/C381135-PJ-327A0-SMT.pdf.',25.4,180.34)
embedded=''.join(s.replace(f'(symbol "{n}"',f'(symbol "XZ1:{n}"',1) for s,n in zip(libs,['R','PJ327','Cable']))
(PROJ/'xz1-splitter.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{rootid}") (paper "A4") (title_block (title "XZ1 Stereo Splitter") (date "2026-10-13") (rev "A")) (lib_symbols {embedded}) '+''.join(items)+f'(sheet_instances (path "/" (page "1"))))')
# Project defaults with explicit fabricator minima and project netclasses.
pr=json.loads((SHARED/'template/kicad.kicad_pro').read_text())
pr['meta']['filename']='xz1-splitter.kicad_pro'
rules=pr['board']['design_settings']['rules']
rules.update(min_clearance=.2,min_track_width=.25,min_via_diameter=.6,min_through_hole_diameter=.3,min_hole_clearance=.25,min_copper_edge_clearance=.3)
pr['net_settings']={'classes':[{'name':'Default','clearance':.2,'track_width':.3,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.3,'diff_pair_gap':.25,'diff_pair_via_gap':.25},{'name':'Ground','clearance':.2,'track_width':.5,'via_diameter':.8,'via_drill':.4,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.5,'diff_pair_gap':.25,'diff_pair_via_gap':.25}], 'meta':{'version':4},'netclass_patterns':[{'netclass':'Ground','pattern':'/GND'}]}
(PROJ/'xz1-splitter.kicad_pro').write_text(json.dumps(pr,indent=2))
(PROJ/'xz1-splitter.kicad_dru').write_text('''(version 1)
(rule "Ground trace width" (condition "A.Type == 'Track' && A.NetName == '/GND'") (constraint track_width (min 0.5mm)))
(rule "Signal trace width" (condition "A.Type == 'Track' && A.NetName != '/GND'") (constraint track_width (min 0.25mm)))
''')
b=k.BOARD();b.SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(M(1.0));b.GetDesignSettings().SetAuxOrigin(V(0,15))
netnames=['GND','HP_L','HP_R','MIC_L','MIC_R','LINE_L','LINE_R']+[f'unconnected-({r}-{pn}-Pad{n})' for r in ['J1','J2'] for n,pn in [('4','S_AUX'),('6','T_SWITCH')]]
nets={}
for name in netnames:
 ni=k.NETINFO_ITEM(b,name if name.startswith("unconnected-") else "/"+name);b.Add(ni);nets[name]=ni
fps={};pads={}
def addfp(name,ref,val,x,y,angle,connections):
 fp=k.FootprintLoad(str(LIB),name);b.Add(fp);fp.SetReference(ref);fp.SetValue(val);fp.SetPosition(V(x,y));fp.SetOrientationDegrees(angle);fp.SetFPID(k.LIB_ID('XZ1',name));fp.SetPath(k.KIID_PATH('/'+rootid+'/'+inst[ref]));fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
 for p in fp.Pads():
  n=p.GetNumber()
  if n in connections:p.SetNet(nets[connections[n]])
  if n:pads[(ref,n)]=p
 field=k.PCB_FIELD(fp,k.FIELD_T_USER);field.SetName('LCSC');field.SetText({'J1':'C381135','J2':'C381135','R1':'C25804','R2':'C25804','R3':'C4190','R4':'C4190','W1':''}[ref]);field.SetVisible(False);fp.Add(field)
 fps[ref]=fp;return fp
addfp('WirePads_5Pole_Star','W1','XZ1 FIVE-POLE CABLE',0,0,0,wn)
for ref,x in [('J1',18.5),('J2',29.5)]:
 con={'2':'HP_L','5':'HP_R','3':'GND'} if ref=='J1' else {'2':'LINE_L','5':'LINE_R','3':'GND'}
 con.update({n:f'unconnected-({ref}-{pn}-Pad{n})' for n,pn in [('4','S_AUX'),('6','T_SWITCH')]})
 addfp('PJ-327A0-SMT_C381135',ref,'PJ-327A0-SMT',x,7,90,con)
for ref,val,x,y,angle,na,nb in [('R3','2.2k',8.5,6.5,0,'MIC_L','GND'),('R4','2.2k',8.5,12,0,'MIC_R','GND'),('R1','10k',11.5,5,0,'MIC_L','LINE_L'),('R2','10k',11.5,9.5,0,'MIC_R','LINE_R')]:
 addfp('R_0603_1608Metric',ref,val,x,y,angle,{'1':na,'2':nb})
def point(ref,n):
 p=pads[(ref,str(n))].GetPosition();return (round(k.ToMM(p.x),5),round(k.ToMM(p.y),5))
def route(net,pts,layer='F.Cu',width=None):
 width=width or (.5 if net=='GND' else .3)
 for a,z in zip(pts,pts[1:]):
  if a==z:continue
  t=k.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*z));t.SetWidth(M(width));t.SetLayer(k.F_Cu if layer=='F.Cu' else k.B_Cu);t.SetNet(nets[net]);b.Add(t)
def via(net,x,y):
 v=k.PCB_VIA(b);v.SetPosition(V(x,y));v.SetWidth(M(.8 if net=='GND' else .6));v.SetDrill(M(.4 if net=='GND' else .3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(nets[net]);b.Add(v)
# No zones. Star branches meet only inside W1.4's 2 mm pad.
star=point('W1','4')
route('GND',[star,point('W1','4b')])
route('GND',[star,(6.8,7.8),(9.325,7.8),point('R3','2')])
route('GND',[star,(6.5,11.05),(9.325,11.05),point('R4','2')])
route('GND',[star,(3.5,11),(3.5,13.8),(21,13.8),(22,12.8),point('J1','3')])
route('GND',[point('J2','3'),(33,11.7)]);via('GND',33,11.7)
route('GND',[star,(7,7.5),(12,7.5),(13.3,8.8),(30.1,8.8),(33,11.7)],'B.Cu')
# Headphone traces mostly on top, upper edge.
route('HP_L',[point('W1','1'),(6.5,.7),(20,.7),(22,2.7),point('J1','2')])
route('HP_R',[point('W1','2'),(10,3.2),(13.5,3.2),(14,3.7),(14,6.8),point('J1','5')])
# Short microphone nets near cable pads.
route('MIC_L',[point('W1','3'),point('R3','1')])
route('MIC_L',[point('R3','1'),(7.675,5),(10.675,5)])
route('MIC_R',[point('W1','5'),point('R4','1')])
route('MIC_R',[point('R4','1'),(7.675,13),(10,13),(10.675,12.325),point('R2','1')])
# Line signals on bottom, spatially separated from headphone traces.
route('LINE_L',[point('R1','2'),(12.8,5)]);via('LINE_L',12.8,5)
route('LINE_L',[(12.8,5),(15,2.5),(30,2.5),(31,3.5),(31,4.8)],'B.Cu');via('LINE_L',31,4.8)
route('LINE_L',[(31,4.8),(33,4.8),point('J2','2')])
route('LINE_R',[point('R2','2'),(13,9.5),(13.5,9),(24,9),point('J2','5')])
# Board outline 35 x 15, straight edges for simple routing/panelization.
for a,z in [((0,0),(35,0)),((35,0),(35,15)),((35,15),(0,15)),((0,15),(0,0))]:
 s=k.PCB_SHAPE();s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(V(*a));s.SetEnd(V(*z));s.SetLayer(k.Edge_Cuts);s.SetWidth(M(.05));b.Add(s)
def silk(txt,x,y,size=.8,back=False,angle=0):
 size=max(size,.8)
 t=k.PCB_TEXT(b);t.SetText(txt);t.SetPosition(V(x,y));t.SetTextSize(V(size,size));t.SetTextThickness(M(.12));t.SetLayer(k.B_SilkS if back else k.F_SilkS);t.SetMirrored(back);t.SetTextAngle(k.EDA_ANGLE(angle,k.DEGREES_T));b.Add(t)
for n,l in [('1','L'),('2','R'),('3','ML'),('4','G'),('5','MR')]:
 x,y=wirepos[n];silk(f'{n} {l}',2.1,y+(.6 if n=='1' else 0),.8)
silk('4b G',7.6,8.0,.8)
for ref,x,y in [('R1',11.5,3.9),('R2',11.5,8.4),('R3',8.5,5.4),('R4',8.5,13.2)]:silk(ref,x,y,.65)
silk('1 PHONES',18.5,13.9,.7,True);silk('2 LINE IN',29.5,13.9,.7,True)
silk('XZ1  REV A',21,6.5,1,True);silk('STAR GND / NO POUR',21,8, .7,True)
silk('1',18.5,.5,.8);silk('2',29.5,.5,.8)
# Labels on top beside the jacks where plastic does not hide them.
silk('PHONES',12.4,12.4,.65,False,90);silk('LINE IN',24,7.5,.65,False,90)
b.BuildConnectivity();k.SaveBoard(str(PROJ/'xz1-splitter.kicad_pcb'),b)
(ROOT/'reports/layout-pads.json').write_text(json.dumps({r+'.'+n:point(r,n) for r,n in pads},indent=2))
print('Generated schematic, board and local libraries:',PROJ)
