#!/usr/bin/env python3
"""Validate saved KiCad files, export fabrication/assembly files and previews.
Does not rebuild/overwrite an interactively edited schematic or PCB.
"""
import csv,hashlib,json,os,pathlib,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parent;os.chdir(ROOT)
proj=pathlib.Path('xz1-splitter/xz1-splitter');sch=str(proj)+'.kicad_sch';pcb=str(proj)+'.kicad_pcb'
cli=os.environ.get('KICAD_CLI','kicad-cli');py=os.environ.get('KICAD_PYTHON','/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9')
def run(*args):
 print('+',' '.join(args),flush=True);subprocess.run(args,check=True)
for d in ['reports','fab/gerbers','previews']:pathlib.Path(d).mkdir(parents=True,exist_ok=True)
run(cli,'sch','erc','--exit-code-violations','-o','reports/erc.rpt',sch)
run(cli,'pcb','drc','--schematic-parity','--exit-code-violations','-o','reports/drc.rpt',pcb)
run(cli,'sch','export','netlist','--format','kicadxml','-o','reports/netlist.xml',sch)
run(py,'verify_design.py')
run(cli,'pcb','export','gerbers','--layers','F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts','--use-drill-file-origin','--subtract-soldermask','-o','fab/gerbers/',pcb)
run(cli,'pcb','export','drill','--drill-origin','plot','--excellon-separate-th','--generate-report','--report-path','reports/drill.rpt','-o','fab/gerbers/',pcb)
run(cli,'pcb','export','pos','--format','csv','--units','mm','--side','front','--smd-only','--use-drill-file-origin','-o','reports/kicad-positions.csv',pcb)
with open('fab/BOM.csv','w',newline='') as f:
 w=csv.writer(f);w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
 w.writerows([['10k 1%','R1,R2','0603','C25804'],['2.2k 1%','R3,R4','0603','C4190'],['PJ-327A0-SMT','J1,J2','PJ-327A0-SMT_C381135','C381135']])
with open('reports/kicad-positions.csv',newline='') as f:rows=list(csv.DictReader(f))
assert {r['Ref'] for r in rows}=={'J1','J2','R1','R2','R3','R4'}
with open('fab/CPL.csv','w',newline='') as f:
 w=csv.writer(f);w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
 for r in rows:w.writerow([r['Ref'],r['PosX'],r['PosY'],'Top',r['Rot']])
with zipfile.ZipFile('fab/xz1-splitter-Gerber.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(pathlib.Path('fab/gerbers').iterdir()):z.write(p,p.name)
run(cli,'sch','export','svg','-o','previews/',sch)
run('rsvg-convert','-w','2200','-b','white','previews/xz1-splitter.svg','-o','previews/schematic.png')
for side,layer,extra in [('top','F',[]),('bottom','B',['--mirror'])]:
 run(cli,'pcb','export','svg','--mode-single','--layers',f'{layer}.Cu,{layer}.Silkscreen,Edge.Cuts','--fit-page-to-board','--exclude-drawing-sheet',*extra,'-o',f'previews/{side}-copper.svg',pcb)
 run('rsvg-convert','-w','1800','-b','#25352b',f'previews/{side}-copper.svg','-o',f'previews/{side}-copper.png')
 run(cli,'pcb','render','--width','1800','--height','900','--zoom','1.6','--side',side,'--quality','high','--background','opaque','-o',f'previews/{side}.png',pcb)
run(cli,'pcb','render','--width','1800','--height','1100','--zoom','1.35','--rotate','30,0,-20','--quality','high','--background','opaque','-o','previews/isometric.png',pcb)
# Gerber zip includes only manufacturing files; full source package made separately.
files=[pathlib.Path(sch),pathlib.Path(pcb),pathlib.Path(str(proj)+'.kicad_pro'),pathlib.Path('fab/xz1-splitter-Gerber.zip'),pathlib.Path('fab/BOM.csv'),pathlib.Path('fab/CPL.csv')]
manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
pathlib.Path('reports/release-sha256.json').write_text(json.dumps(manifest,indent=2))
print('Release complete. Review previews/ and read README.md before uploading.')
