import json, struct, sys, collections
f=open(sys.argv[1],'rb'); magic,ver,length=struct.unpack('<4sII',f.read(12))
clen,ctype=struct.unpack('<I4s',f.read(8)); g=json.loads(f.read(clen))
acc=g['accessors']; tris=0; per=collections.Counter()
for m in g['meshes']:
    for p in m['primitives']:
        n = acc[p['indices']]['count']//3 if 'indices' in p else acc[p['attributes']['POSITION']]['count']//3
        tris+=n; per[m.get('name','?')]+=n
print('meshes',len(g['meshes']),'tris',tris,'materials',len(g.get('materials',[])),'images',len(g.get('images',[])))
for k,v in per.most_common(): print(f'  {v:>9}  {k}')
sk=g.get('skins',[]); print('skins',len(sk),'joints',[len(s['joints']) for s in sk])
names=[g['nodes'][j].get('name') for j in sk[0]['joints']] if sk else []
print('joint names:',', '.join(names))
print('animations',len(g.get('animations',[])))
print(', '.join(a.get('name','?') for a in g.get('animations',[])))
print('extensionsUsed',g.get('extensionsUsed'))
