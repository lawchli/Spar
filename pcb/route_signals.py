"""Deterministic two-layer clearance-aware signal routing; KiCad DRC is authoritative."""
import heapq, math, os
import pcbnew as k
STEP=.1; NX=481; NY=136; N=NX*NY
mm=k.ToMM

def autoroute(b,pads,route,via,point):
 def xy(p):return mm(p.x),mm(p.y)
 def grid(p):return round(p[0]/STEP),round(p[1]/STEP)
 def occupancy(net,rad):
  blocked=[bytearray(N),bytearray(N)]
  def paint(box,inside,layers):
   x0,y0,x1,y1=box
   for iy in range(max(0,math.floor(y0/STEP)),min(NY,math.ceil(y1/STEP)+1)):
    for ix in range(max(0,math.floor(x0/STEP)),min(NX,math.ceil(x1/STEP)+1)):
     if inside(ix*STEP,iy*STEP):
      for l in layers:blocked[l][iy*NX+ix]=1
  def circ(x,y,r,ls):paint((x-r,y-r,x+r,y+r),lambda a,c:(a-x)**2+(c-y)**2<=r*r,ls)
  def seg(a,z,r,ls):
   dx=z[0]-a[0];dy=z[1]-a[1];ll=dx*dx+dy*dy
   def inside(x,y):
    t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/ll)) if ll else 0
    return (x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2<=r*r
   paint((min(a[0],z[0])-r,min(a[1],z[1])-r,max(a[0],z[0])+r,max(a[1],z[1])+r),inside,ls)
  for fp in b.GetFootprints():
   for p in fp.Pads():
    x,y=xy(p.GetPosition());sz=xy(p.GetSize());attr=p.GetAttribute()
    if attr==k.PAD_ATTRIB_NPTH:
     clear=1.5 if abs(mm(p.GetDrillSize().x)-2.2)<.001 else .25
     circ(x,y,mm(p.GetDrillSize().x)/2+clear+rad+.06,[0,1]);continue
    if p.GetNetname()==net:continue
    ls=[0,1] if attr==k.PAD_ATTRIB_PTH else [0]
    extra=.2+rad+.06
    if p.GetShape()==k.PAD_SHAPE_CIRCLE:circ(x,y,sz[0]/2+extra,ls)
    else:
     if round(p.GetOrientationDegrees())%180==90:sz=sz[::-1]
     hx=sz[0]/2+extra;hy=sz[1]/2+extra
     paint((x-hx,y-hy,x+hx,y+hy),lambda a,c:abs(a-x)<=hx and abs(c-y)<=hy,ls)
  for t in b.GetTracks():
   if t.GetNetname()==net:continue
   if isinstance(t,k.PCB_VIA):
    x,y=xy(t.GetPosition());circ(x,y,mm(t.GetWidth(k.F_Cu))/2+.2+rad+.06,[0,1])
   else:seg(xy(t.GetStart()),xy(t.GetEnd()),mm(t.GetWidth())/2+.2+rad+.06,[0 if t.GetLayer()==k.F_Cu else 1])
  # Via drills must also avoid all existing holes, including same-net pads/vias.
  if rad>.2:
   for fp in b.GetFootprints():
    for p in fp.Pads():
     dr=mm(p.GetDrillSize().x)/2
     if dr>0:
      x,y=xy(p.GetPosition());circ(x,y,dr+.15+.25+.06,[0,1])
   for t in b.GetTracks():
    if isinstance(t,k.PCB_VIA):
     x,y=xy(t.GetPosition());circ(x,y,mm(t.GetDrillValue())/2+.15+.25+.06,[0,1])
  edge=.3+rad+.1
  for y in range(NY):
   for x in range(NX):
    if min(x*STEP,48-x*STEP,y*STEP,13.5-y*STEP)<edge:
     blocked[0][y*NX+x]=blocked[1][y*NX+x]=1
  return blocked
 pairs=[('MIC_L',('W1','3'),('R3','1')),('MIC_L',('R3','1'),('R1','1')),
        ('MIC_R',('W1','5'),('R4','1')),('MIC_R',('R4','1'),('R2','1')),
        ('HP_L',('W1','1'),('J1','2')),('HP_R',('W1','2'),('J1','5')),
        ('LINE_L',('R1','2'),('J2','2')),('LINE_R',('R2','2'),('J2','5'))]
 order=os.environ.get('XZ1_ROUTE_ORDER','LINE_L,LINE_R,HP_R,MIC_L,MIC_R,HP_L').split(',')
 pairs.sort(key=lambda item: order.index(item[0]))
 for net,a,z in pairs:
  blk=occupancy('/'+net,.15);vblk=occupancy('/'+net,.3)
  sx,sy=grid(point(*a));tx,ty=grid(point(*z));target=ty*NX+tx
  starts=[sy*NX+sx]
  if pads[a].GetAttribute()==k.PAD_ATTRIB_PTH:starts.append(N+sy*NX+sx)
  q=[];dist={};prev={}
  def heur(x,y):
   dx=abs(tx-x);dy=abs(ty-y);return max(dx,dy)+.41421356*min(dx,dy)
  for st in starts:dist[st]=0;heapq.heappush(q,(heur(sx,sy),0,st))
  end=None
  while q:
   _,d,u=heapq.heappop(q)
   if d!=dist.get(u):continue
   layer=u//N;idx=u%N;y,x=divmod(idx,NX)
   if idx==target and (layer==0 or pads[z].GetAttribute()==k.PAD_ATTRIB_PTH):end=u;break
   moves=[]
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    xx=x+dx;yy=y+dy
    if not(0<=xx<NX and 0<=yy<NY):continue
    ni=yy*NX+xx
    if blk[layer][ni]:continue
    if dx and dy and (blk[layer][y*NX+xx] or blk[layer][yy*NX+x]):continue
    moves.append((layer*N+ni,1.41421356 if dx and dy else 1,xx,yy))
   if not vblk[0][idx] and not vblk[1][idx]:moves.append(((1-layer)*N+idx,15,x,y))
   for v,c,xx,yy in moves:
    nd=d+c
    if nd<dist.get(v,1e20):dist[v]=nd;prev[v]=u;heapq.heappush(q,(nd+heur(xx,yy),nd,v))
  if end is None:raise RuntimeError(('No route',net,a,z))
  path=[end]
  while path[-1] in prev:path.append(prev[path[-1]])
  path.reverse();start=point(*a);layer=path[0]//N;pts=[start];lastdir=None
  def pos(u):idx=u%N;return ((idx%NX)*STEP,(idx//NX)*STEP)
  pts.append(pos(path[0]))
  for i in range(1,len(path)):
   p=pos(path[i]);before=pos(path[i-1]);nl=path[i]//N
   if nl!=layer:
    pts.append(p);route(net,pts,'F.Cu' if layer==0 else 'B.Cu');via(net,*p);layer=nl;pts=[p];lastdir=None
   else:
    direction=(round(p[0]-before[0],5),round(p[1]-before[1],5))
    if lastdir is not None and direction!=lastdir:pts.append(before)
    lastdir=direction
  pts.extend([pos(path[-1]),point(*z)]);route(net,pts,'F.Cu' if layer==0 else 'B.Cu')
  print('Routed',net,a,z,flush=True)
