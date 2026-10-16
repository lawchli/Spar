#!/usr/bin/env python3
"""Upgrade saved Rev B board to B-M2 without replacing user project settings.
Rebuild only routing after enlarged mounting clearances; keep schematic/placement.
Run with KiCad's bundled Python, then release.py.
"""
import pathlib,math
import pcbnew as k
from route_signals import autoroute
ROOT=pathlib.Path(__file__).resolve().parent
M=k.FromMM; V=lambda x,y:k.VECTOR2I(M(x),M(y))
b=k.LoadBoard(str(ROOT/'kicad/xz1-direct.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
for p in fps['W1'].Pads():
 if p.GetAttribute()==k.PAD_ATTRIB_NPTH:
  x,y=k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y)
  if abs(x-19)<.01 or abs(x-18)<.01:p.SetPosition(V(18,9.5))
  elif abs(x-35)<.01:p.SetPosition(V(35,6.5))
  else:raise RuntimeError('Unexpected W1 NPTH')
  p.SetSize(V(2.2,2.2));p.SetDrillSize(V(2.2,2.2))
for t in list(b.GetTracks()):b.RemoveNative(t)
pads={(f.GetReference(),p.GetNumber()):p for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()}
nets={n.GetNetname().lstrip('/'):n for n in b.GetNetInfo().NetsByNetcode().values()}
def point(ref,n):
 p=pads[(ref,str(n))].GetPosition();return(round(k.ToMM(p.x),5),round(k.ToMM(p.y),5))
def route(net,pts,layer='F.Cu',width=None):
 for a,z in zip(pts,pts[1:]):
  if a==z:continue
  t=k.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*z));t.SetWidth(M(width or (.5 if net=='GND' else .3)));t.SetLayer(k.F_Cu if layer=='F.Cu' else k.B_Cu);t.SetNet(nets[net]);b.Add(t)
def via(net,x,y):
 v=k.PCB_VIA(b);v.SetPosition(V(x,y));v.SetWidth(M(.8 if net=='GND' else .6));v.SetDrill(M(.4 if net=='GND' else .3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(nets[net]);b.Add(v)
star=point('W1','4')
route('GND',[star,point('W1','4b')]);route('GND',[star,point('R3','2')])
route('GND',[star,(7.5,8.5),(7.5,11),point('R4','2')])
route('GND',[star,(10.5,8.5),(10.5,11.2),(12,12.7),(21,12.7),(21,2.6),point('J1','3')])
route('GND',[point('J2','3'),(37,2.6)]);via('GND',37,2.6)
route('GND',[star,(12,6),(31,6),(33,3),(35.4,2.6),(37,2.6)],'B.Cu')
autoroute(b,pads,route,via,point)
for drawing in b.GetDrawings():
 if isinstance(drawing,k.PCB_TEXT) and drawing.GetText()=='XZ1 B / 48x13.5':drawing.SetText('XZ1 B-M2 48x13.5')
 if isinstance(drawing,k.PCB_TEXT) and drawing.GetText()=='STAR GND - NO POUR':drawing.SetPosition(V(14,5.0))
b.BuildConnectivity();k.SaveBoard(str(ROOT/'kicad/xz1-direct.kicad_pcb'),b)
# Keep the local library consistent with the board's built-in footprint.
lib=ROOT/'kicad/lib/XZ1.pretty/WirePads_5Pole_Star.kicad_mod'
s=lib.read_text().replace('(at 19 10.5) (size 1.6 1.6) (drill 1.6)','(at 18 9.5) (size 2.2 2.2) (drill 2.2)').replace('(at 35 6.5) (size 1.6 1.6) (drill 1.6)','(at 35 6.5) (size 2.2 2.2) (drill 2.2)')
lib.write_text(s)
print('B-M2 mounting holes: (18,9.5), (35,6.5), NPTH diameter 2.2 mm')
