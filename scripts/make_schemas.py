import json
from pathlib import Path
S={'type':'string','minLength':1}
A=lambda item: {'type':'array','items':item,'maxItems':20000}
O=lambda fields, required=None: {'type':'object','properties':fields,'required':list(fields) if required is None else required,'additionalProperties':False}
ref=S
shape=A({'oneOf':[{'type':'integer','minimum':1},S,{'type':'null'}]})
entity=lambda fields: O({'id':S,**fields})
source=entity(dict(path=S,symbol=S,start={'type':'integer','minimum':1},end={'type':'integer','minimum':1},hash=S,snippet={'type':'string'}))
evidence=entity(dict(kind={'enum':['source','config','static','teaching','unknown','runtime']},target=S,sourceRefs=A(ref),assumptions=A(S),text=S))
architecture=O(dict(kind={'const':'architecture'},schemaVersion={'const':'1.0'},snapshot=O(dict(id=S,model=S,sourceHash=S,config={'type':'object'},mode={'const':'static'},toolVersion=S,executed={'const':False},parameterCount={'type':['integer','null'],'minimum':0})),definitions=A(entity(dict(symbol=S,sourceRef=ref))),instances=A(entity(dict(path=S,definition={'type':['string','null']},config={'type':'object'},parameterIds=A(ref)))),parameters=A(entity(dict(name=S,shape=shape,count={'type':'integer','minimum':0},instances=A(ref),shared={'type':'boolean'},evidence=ref))),scopes=A(entity(dict(label=S,parent={'type':['string','null']},owner={'type':['string','null']},bindings=A(O(dict(parentPort=ref,childPort=ref))),sourceRef=ref))),nodes=A(entity(dict(scope=ref,label=S,role=S,instance={'type':['string','null']},childScope={'type':['string','null']},sourceRef=ref,explanation=ref,opaque={'type':'boolean'}))),ports=A(entity(dict(node=ref,direction={'enum':['in','out']},name=S,tensor=ref))),edges=A(entity(dict(scope=ref,source=ref,target=ref,tensor=ref,condition={'type':['string','null']}))),tensors=A(entity(dict(name=S,shape=shape,dtype=S,unknownReason={'type':['string','null']},producer=ref,consumers=A(ref),evidence=ref))),sourceRefs=A(source),evidence=A(evidence),claims=A(entity(dict(target=S,text=S,evidence=A(ref)))),explanations=A(entity(dict(intuition=S,calculation=S,implementation=S,evidence=A(ref)))),views=A(entity(dict(instances=A(ref),relation=S,checked={'type':'boolean'}))),limitations=A(O(dict(reason=S,sourceRef={'type':['string','null']},scope={'type':['string','null']})))))
match=entity(dict(left=A(ref),right=A(ref),status={'enum':['suggested','accepted','rejected']},origin={'enum':['rule','manual']},reason=S))
comparison=O(dict(kind={'const':'comparison'},schemaVersion={'const':'1.0'},leftSnapshot=ref,rightSnapshot=ref,matches=A(match),differences=A(O(dict(type={'enum':['configuration','shape','parameters','topology','sharing','implementation','unknown']},match={'type':['string','null']},text=S,evidence=A(S)))),summary={'type':'object'},limitations=A(S)))
session=O(dict(kind={'const':'session'},schemaVersion={'const':'1.0'},notes=A(O(dict(snapshot=ref,anchor=ref,status={'enum':['understood','review','question']},text={'type':'string'},association={'enum':['exact','pending']})))))
for name, schema in [('architecture',architecture),('comparison',comparison),('session',session)]:
 schema={'$schema':'http://json-schema.org/draft-07/schema#',**schema}
 for base in ['schemas','src/model_atlas/resources']:
  Path(base,f'{name}.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')
