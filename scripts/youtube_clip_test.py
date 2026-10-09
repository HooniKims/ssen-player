import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QCoreApplication,QThreadPool,QTimer
from app.clips import ClipJob
app=QCoreApplication([])
job=ClipJob('https://www.youtube.com/watch?v=M7lc1UVf-VE',2,4,str(ROOT/'artifacts/qa/web'),True)
job.events.progress.connect(lambda message:print(message,flush=True))
def done(path,error):
    result={'path':path,'error':error}
    print(json.dumps(result,ensure_ascii=False),flush=True)
    (ROOT/'artifacts/qa/web/clip-result.json').write_text(json.dumps(result,ensure_ascii=False),'utf-8')
    app.exit(1 if error else 0)
job.events.finished.connect(done)
QThreadPool.globalInstance().start(job)
QTimer.singleShot(120000,job.cancel.set)
raise SystemExit(app.exec())
