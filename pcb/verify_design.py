#!/usr/bin/env python3
"""Independent checks on KiCad-loaded PCB + KiCad-exported XML netlist.
Run with KiCad bundled Python. No assumptions taken from generator routes.
"""
import json,math,pathlib,xml.etree.ElementTree as ET
import pcbnew as k
ROOT=pathlib.Path(__file__).resolve().parent
b=k.LoadBoard(str(ROOT/'xz1-splitter/xz1-splitter.kicad_pcb'))
mm=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
pads={(f.GetReference(),p.GetNumber()):p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()}
expected={('W1','1'):'/HP_L',('W1','2'):'/HP_R',('W1','3'):'/MIC_L',('W1','4'):'/GND',('W1','4b'):'/GND',('W1','5'):'/MIC_R',('J1','2'):'/HP_L',('J1','5'):'/HP_R',('J1','3'):'/GND',('J2','2'):'/LINE_L',('J2','5'):'/LINE_R',('J2','3'):'/GND',('R1','1'):'/MIC_L',('R1','2'):'/LINE_L',('R2','1'):'/MIC_R',('R2','2'):'/LINE_R',('R3','1'):'/MIC_L',('R3','2'):'/GND',('R4','1'):'/MIC_R',('R4','2'):'/GND'}
xml=ET.parse(ROOT/'reports/netlist.xml').getroot(); sch={}
for n in xml.findall('./nets/net'):
 for p in n.findall('node'):sch[(p.get('ref'),p.get('pin'))]=n.get('name')
for key,net in expected.items():
 assert pads[key].GetNetname()==net,(key,pads[key].GetNetname(),net)
 assert sch[key]==net,(key,sch[key],net)
for ref in ['J1','J2']:
 for pin in ['4','6']:
  net=pads[(ref,pin)].GetNetname();assert net.startswith('unconnected-')
  assert sum(p.GetNetname()==net for p in pads.values())==1
  assert not any(t.GetNetname()==net for t in b.GetTracks())
values={c.get('ref'):c.findtext('value') for c in xml.findall('./components/comp')}
assert values['R1']==values['R2']=='10k';assert values['R3']==values['R4']=='2.2k'
assert set(values)=={'W1','J1','J2','R1','R2','R3','R4'}
assert len(b.Zones())==0,'Copper zones are forbidden'
assert b.GetCopperLayerCount()==2
assert abs(k.ToMM(b.GetDesignSettings().GetBoardThickness())-1)<1e-6
# Minimum trace widths and via drills actually used.
for t in b.GetTracks():
 if isinstance(t,k.PCB_VIA):assert k.ToMM(t.GetDrillValue())>=.3-1e-6
 else:assert k.ToMM(t.GetWidth())>=(.5 if t.GetNetname()=='/GND' else .25)-1e-6
# NPTH edges retain at least 0.5 mm FR4, including strain-relief holes.
for f in b.GetFootprints():
 for p in f.Pads():
  if p.GetAttribute()!=k.PAD_ATTRIB_NPTH:continue
  x,y=mm(p.GetPosition());r=k.ToMM(p.GetDrillSize().x)/2
  assert min(x-r,35-x-r,y-r,15-y-r)>=.5-1e-6
# Copper graph after removing star pad. Segments starting at the star are
# trimmed at its radius; capsule distance joins full-width copper, not just
# endpoints. Pad bounding circles conservatively overestimate SMD copper.
star=mm(pads[('W1','4')].GetPosition());radius=k.ToMM(pads[('W1','4')].GetSize().x)/2
norm=lambda a:math.hypot(*a)
sub=lambda a,z:(a[0]-z[0],a[1]-z[1])
def dpoint(p,a,z):
 az=sub(z,a);ap=sub(p,a);l=az[0]**2+az[1]**2
 t=max(0,min(1,(ap[0]*az[0]+ap[1]*az[1])/l)) if l else 0
 return norm(sub(p,(a[0]+az[0]*t,a[1]+az[1]*t)))
def cross(a,z,p):return (z[0]-a[0])*(p[1]-a[1])-(z[1]-a[1])*(p[0]-a[0])
def distance(a,z,c,d):
 if cross(a,z,c)*cross(a,z,d)<-1e-12 and cross(c,d,a)*cross(c,d,z)<-1e-12:return 0
 return min(dpoint(a,c,d),dpoint(z,c,d),dpoint(c,a,z),dpoint(d,a,z))
objects=[]
for t in b.GetTracks():
 if t.GetNetname()!='/GND':continue
 if isinstance(t,k.PCB_VIA):a=z=mm(t.GetPosition());layers={k.F_Cu,k.B_Cu}
 else:
  a=mm(t.GetStart());z=mm(t.GetEnd());layers={t.GetLayer()}
  if norm(sub(a,star))<1e-6:
   length=norm(sub(z,a));a=(a[0]+(z[0]-a[0])*radius/length,a[1]+(z[1]-a[1])*radius/length)
  if norm(sub(z,star))<1e-6:
   length=norm(sub(a,z));z=(z[0]+(a[0]-z[0])*radius/length,z[1]+(a[1]-z[1])*radius/length)
 objects.append({'a':a,'z':z,'r':k.ToMM(t.GetWidth(k.F_Cu) if isinstance(t,k.PCB_VIA) else t.GetWidth())/2,'layers':layers,'terminal':None})
for (ref,n),p in pads.items():
 if p.GetNetname()!='/GND' or (ref,n)==('W1','4'):continue
 pos=mm(p.GetPosition());sz=mm(p.GetSize())
 r=sz[0]/2 if p.GetShape()==k.PAD_SHAPE_CIRCLE else norm(sz)/2
 layers={k.F_Cu,k.B_Cu} if p.GetAttribute()==k.PAD_ATTRIB_PTH else {k.F_Cu}
 objects.append({'a':pos,'z':pos,'r':r,'layers':layers,'terminal':ref+'.'+n})
parent=list(range(len(objects)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for i,o in enumerate(objects):
 for j,p in enumerate(objects[:i]):
  if o['layers']&p['layers'] and distance(o['a'],o['z'],p['a'],p['z'])<=o['r']+p['r']+1e-7:parent[find(i)]=find(j)
groups={}
for i,o in enumerate(objects):
 groups.setdefault(find(i),[])
 if o['terminal']:groups[find(i)].append(o['terminal'])
expected_branches=[['J1.3'],['J2.3'],['R3.2'],['R4.2'],['W1.4b']]
assert sorted(groups.values())==sorted(expected_branches),('Non-star ground merge or open branch',groups)
# Guard narrow accidental same-net gaps away from star: between the P4b pad
# and other branches require >= 0.20 mm, beyond ordinary KiCad same-net DRC.
b_index=next(i for i,o in enumerate(objects) if o['terminal']=='W1.4b');p4b=objects[b_index];gaps=[]
for i,o in enumerate(objects):
 if find(i)==find(b_index) or not o['layers']&p4b['layers']:continue
 gap=distance(o['a'],o['z'],p4b['a'],p4b['z'])-o['r']-p4b['r'];gaps.append(gap)
assert min(gaps)>=.2-1e-6,min(gaps)
# Resistor-only circuit forms a tree: each measurement has at most one path.
graph={}
for r,ohm in [('R1',10000),('R2',10000),('R3',2200),('R4',2200)]:
 a,z=sch[(r,'1')],sch[(r,'2')]
 graph.setdefault(a,[]).append((z,ohm));graph.setdefault(z,[]).append((a,ohm))
def resistance(a,z,seen=None):
 if a==z:return 0
 seen=set() if seen is None else seen
 if a in seen:return math.inf
 seen=seen|{a}
 paths=[w+resistance(n,z,seen) for n,w in graph.get(a,[]) if n not in seen]
 return min(paths,default=math.inf)
def meas(a,z):return resistance(sch[tuple(a.split('.'))],sch[tuple(z.split('.'))])
cases=[('W1.1','J1.2',0),('W1.2','J1.5',0),('W1.4','J1.3',0),('W1.4','J2.3',0),('W1.4','W1.4b',0),('W1.3','W1.4',2200),('W1.5','W1.4',2200),('J2.2','W1.3',10000),('J2.5','W1.5',10000),('J2.2','J2.3',12200),('J2.5','J2.3',12200),('W1.3','W1.5',4400),('J2.2','J2.5',24400),('J2.2','W1.5',14400),('J2.5','W1.3',14400)]
for a in ['W1.1','W1.2']:
 for z in ['W1.3','W1.4','W1.5']:cases.append((a,z,math.inf))
cases.append(('W1.1','W1.2',math.inf))
measurements=[]
for a,z,want in cases:
 got=meas(a,z);assert got==want,(a,z,got,want)
 measurements.append({'from':a,'to':z,'ohms':'OL' if math.isinf(got) else got})
report={'result':'PASS','date':'2026-10-13','actual_copper_star_branches_after_removing_P4':sorted(groups.values()),'P4b_to_other_branches_min_clearance_mm':round(min(gaps),4),'copper_zones':0,'pcb_and_schematic_net_assignments':'MATCH','unpopulated_jack_pins':'4 and 6, both jacks','measurement_checks':measurements,'measurement_count':len(measurements),'limits':'Ideal DC topology; no physical prototype or audio/noise testing claimed.'}
(ROOT/'reports/design-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
