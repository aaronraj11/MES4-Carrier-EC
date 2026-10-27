import re
def parse(text):
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
    stack=[[]]
    for m in tok.finditer(text):
        t=m.group(0)
        if t=='(':
            stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        else:
            if t.startswith('"'): t=t[1:-1].replace('\\"','"').replace('\\\\','\\')
            stack[-1].append(t)
    return stack[0]
def find(node,name):
    return [c for c in node if isinstance(c,list) and c and c[0]==name]
def first(node,name):
    r=find(node,name); return r[0] if r else None
