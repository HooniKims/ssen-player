"""Wrap unchanged CommonJS kit modules for an isolated Qt WebEngine engine page."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def prepare():
    base=ROOT/'assets/auth'
    pieces=[]
    for file,name in [('auth-service.cjs','SsenService'),('auth-throttle.cjs','SsenThrottle')]:
        source=(base/file).read_text('utf-8')
        pieces.append('globalThis.'+name+'=(()=>{const module={exports:{}}; const exports=module.exports;\n'+source+'\nreturn module.exports;})();')
    (base/'engine-kit.js').write_text('\n'.join(pieces),'utf-8')
if __name__=='__main__': prepare()
