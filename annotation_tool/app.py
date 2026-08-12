#!/usr/bin/env python3
"""Local, zero-dependency review UI for DermClin-MT-style records."""

import argparse
import html
import json
import mimetypes
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


TASKS = ("descriptors", "diagnosis", "differential", "management", "consultation")
SPLITS = ("train", "test")
STATUSES = ("approved", "revised", "rejected", "skipped")


def load_records(path: Path):
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array: {path}")
    return [item for item in data if isinstance(item, dict)]


def qa(record):
    question = answer = ""
    for turn in record.get("conversations", []):
        if turn.get("from") == "human":
            question = turn.get("value", "").replace("<image>", "").strip()
        elif turn.get("from") == "gpt":
            answer = turn.get("value", "").strip()
    return question, answer


class Dataset:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, task, split):
        if task not in TASKS or split not in SPLITS:
            return []
        key = (task, split)
        with self.lock:
            if key not in self.cache:
                records = load_records(self.root / task / f"{split}.json")
                for index, record in enumerate(records):
                    record["_sample_id"] = f"{task}/{split}/{index}"
                    record["_index"] = index
                self.cache[key] = records
        return self.cache[key]

    def counts(self):
        return {task: {split: len(self.get(task, split)) for split in SPLITS} for task in TASKS}


class Reviews:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    sample_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    revised_answer TEXT,
                    comment TEXT,
                    annotator TEXT,
                    updated_at INTEGER NOT NULL
                )
            """)

    def get(self, sample_id):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM reviews WHERE sample_id=?", (sample_id,)).fetchone()
            return dict(row) if row else None

    def save(self, sample_id, status, revised_answer, comment, annotator):
        if status not in STATUSES:
            raise ValueError("Invalid review status")
        with sqlite3.connect(self.path) as db:
            db.execute("""
                INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(sample_id) DO UPDATE SET
                    status=excluded.status,
                    revised_answer=excluded.revised_answer,
                    comment=excluded.comment,
                    annotator=excluded.annotator,
                    updated_at=excluded.updated_at
            """, (sample_id, status, revised_answer, comment, annotator, int(time.time())))
        return self.get(sample_id)

    def statuses(self):
        with sqlite3.connect(self.path) as db:
            return dict(db.execute("SELECT sample_id, status FROM reviews"))

    def export(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM reviews ORDER BY sample_id")]


APP_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DermClin-MT Review Tool</title><style>
:root{font-family:system-ui,sans-serif;color:#172033;background:#f4f6fa}body{margin:0}header{padding:16px 22px;background:#132238;color:white}
header h1{margin:0;font-size:20px}.bar{display:flex;gap:10px;flex-wrap:wrap;padding:14px 22px;background:white;border-bottom:1px solid #dbe1ea}
select,input,textarea,button{font:inherit;border:1px solid #bec8d6;border-radius:7px;padding:8px}button{cursor:pointer;background:white}.layout{display:grid;grid-template-columns:280px 1fr 330px;gap:14px;padding:14px;height:calc(100vh - 136px)}
.panel{background:white;border:1px solid #dbe1ea;border-radius:10px;overflow:auto;padding:14px}.item{padding:9px;border-bottom:1px solid #edf0f5;cursor:pointer}.item.active{background:#e8f1ff}.item small{color:#6a7485}.status{float:right}.image{display:block;max-width:100%;max-height:45vh;margin:10px auto;border-radius:8px}.missing{padding:46px;text-align:center;background:#f0f2f5;color:#6a7485}
.qa{white-space:pre-wrap;line-height:1.5}.answer{background:#eef9f1;border-left:4px solid #3b9a5b;padding:12px}.buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px}.buttons button{padding:10px}.approved{border-color:#23964f}.revised{border-color:#d28b14}.rejected{border-color:#c33}.skipped{border-color:#758196}textarea{width:100%;box-sizing:border-box;min-height:90px;margin:8px 0}.muted{color:#6a7485;font-size:13px}@media(max-width:900px){.layout{grid-template-columns:1fr;height:auto}.panel{max-height:none}}
</style></head><body><header><h1>DermClin-MT local review tool</h1></header>
<div class="bar"><select id="task"></select><select id="split"><option>train</option><option>test</option></select><select id="filter"><option value="all">all reviews</option><option value="pending">pending</option><option value="approved">approved</option><option value="revised">revised</option><option value="rejected">rejected</option><option value="skipped">skipped</option></select><input id="annotator" placeholder="Annotator"><button id="export">Export reviews</button></div>
<main class="layout"><section class="panel" id="list"></section><section class="panel" id="sample"><p class="muted">Select a record.</p></section><section class="panel"><h3>Review</h3><div class="buttons"><button class="approved" data-status="approved">Approve</button><button class="revised" data-status="revised">Revise</button><button class="rejected" data-status="rejected">Reject</button><button class="skipped" data-status="skipped">Skip</button></div><label><p>Revised answer</p><textarea id="revision"></textarea></label><label><p>Comment</p><textarea id="comment"></textarea></label><button id="save">Save review</button><p id="message" class="muted"></p></section></main>
<script>
const $=id=>document.getElementById(id);let current=null,chosen='approved',items=[];
async function api(url,options){const r=await fetch(url,options);if(!r.ok)throw Error(await r.text());return r.json()}
async function init(){const meta=await api('/api/meta');$('task').innerHTML=meta.tasks.map(t=>`<option>${t}</option>`).join('');await refresh()}
async function refresh(){const q=new URLSearchParams({task:$('task').value,split:$('split').value,filter:$('filter').value});const data=await api('/api/list?'+q);items=data.items;$('list').innerHTML=items.map(x=>`<div class="item" data-index="${x.index}"><span class="status">${x.status||''}</span><b>#${x.index}</b><br><small>${escapeHtml(x.answer)}</small></div>`).join('')||'<p class="muted">No records.</p>';document.querySelectorAll('.item').forEach(n=>n.onclick=()=>openSample(+n.dataset.index))}
function escapeHtml(s){return(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function openSample(index){current=await api(`/api/sample?task=${encodeURIComponent($('task').value)}&split=${encodeURIComponent($('split').value)}&index=${index}`);document.querySelectorAll('.item').forEach(n=>n.classList.toggle('active',+n.dataset.index===index));const im=current.image_available?`<img class="image" src="${current.image_url}" alt="Private clinical sample">`:'<div class="missing">Image unavailable or withheld</div>';$('sample').innerHTML=`<h3>${escapeHtml(current.id)}</h3>${im}<h4>Prompt</h4><div class="qa">${escapeHtml(current.question)}</div><h4>Target</h4><div class="qa answer">${escapeHtml(current.answer)}</div>`;const a=current.review||{};$('revision').value=a.revised_answer||'';$('comment').value=a.comment||'';chosen=a.status||'approved'}
document.querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>{chosen=b.dataset.status;$('message').textContent='Selected: '+chosen});$('save').onclick=async()=>{if(!current)return;$('message').textContent='Saving...';await api('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sample_id:current.id,status:chosen,revised_answer:$('revision').value,comment:$('comment').value,annotator:$('annotator').value})});$('message').textContent='Saved';await refresh()};$('export').onclick=()=>location.href='/api/export';['task','split','filter'].forEach(id=>$(id).onchange=refresh);init().catch(e=>$('list').textContent=e.message);
</script></body></html>"""


def make_handler(dataset, reviews, image_root):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[{time.strftime('%H:%M:%S')}] {fmt % args}")

        def send_bytes(self, body, content_type, status=200, disposition=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if disposition:
                self.send_header("Content-Disposition", disposition)
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, value, status=200):
            self.send_bytes(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_048_576:
                raise ValueError("Request body exceeds 1 MiB")
            return json.loads(self.rfile.read(length) or b"{}")

        def selected(self, query):
            task = query.get("task", [""])[0]
            split = query.get("split", [""])[0]
            if task not in TASKS or split not in SPLITS:
                raise ValueError("Invalid task or split")
            return task, split, dataset.get(task, split)

        def image_path(self, raw):
            if not raw or raw == "<image-withheld>" or image_root is None:
                return None
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = image_root / candidate
            resolved = candidate.resolve()
            try:
                resolved.relative_to(image_root)
            except ValueError:
                return None
            return resolved if resolved.is_file() else None

        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/":
                    self.send_bytes(APP_HTML.encode(), "text/html; charset=utf-8")
                elif parsed.path == "/api/meta":
                    self.send_json({"tasks": TASKS, "splits": SPLITS, "counts": dataset.counts()})
                elif parsed.path == "/api/list":
                    _, _, records = self.selected(query)
                    filter_value = query.get("filter", ["all"])[0]
                    statuses = reviews.statuses()
                    output = []
                    for record in records:
                        status = statuses.get(record["_sample_id"])
                        if filter_value == "pending" and status is not None:
                            continue
                        if filter_value not in ("all", "pending") and status != filter_value:
                            continue
                        _, answer = qa(record)
                        output.append({"index": record["_index"], "answer": answer[:90], "status": status})
                    self.send_json({"items": output})
                elif parsed.path == "/api/sample":
                    task, split, records = self.selected(query)
                    index = int(query.get("index", ["-1"])[0])
                    if index < 0 or index >= len(records):
                        raise ValueError("Record index is out of range")
                    record = records[index]
                    question, answer = qa(record)
                    path = self.image_path(record.get("image"))
                    self.send_json({
                        "id": record["_sample_id"], "task": task, "split": split,
                        "question": question, "answer": answer,
                        "image_available": bool(path),
                        "image_url": f"/api/image?task={quote(task)}&split={quote(split)}&index={index}",
                        "review": reviews.get(record["_sample_id"]),
                    })
                elif parsed.path == "/api/image":
                    _, _, records = self.selected(query)
                    index = int(query.get("index", ["-1"])[0])
                    if index < 0 or index >= len(records):
                        raise ValueError("Record index is out of range")
                    path = self.image_path(records[index].get("image"))
                    if path is None:
                        self.send_json({"error": "Image unavailable"}, 404)
                    else:
                        self.send_bytes(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                elif parsed.path == "/api/export":
                    payload = json.dumps(reviews.export(), ensure_ascii=False, indent=2).encode()
                    self.send_bytes(payload, "application/json; charset=utf-8", disposition='attachment; filename="reviews.json"')
                else:
                    self.send_json({"error": "Not found"}, 404)
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json({"error": str(error)}, 400)

        def do_POST(self):
            if urlparse(self.path).path != "/api/review":
                self.send_json({"error": "Not found"}, 404)
                return
            try:
                value = self.body()
                sample_id = value.get("sample_id", "")
                parts = sample_id.split("/")
                if len(parts) != 3 or parts[0] not in TASKS or parts[1] not in SPLITS or not parts[2].isdigit():
                    raise ValueError("Invalid sample id")
                records = dataset.get(parts[0], parts[1])
                if int(parts[2]) >= len(records):
                    raise ValueError("Unknown sample id")
                review = reviews.save(sample_id, value.get("status"), value.get("revised_answer", ""), value.get("comment", ""), value.get("annotator", ""))
                self.send_json({"ok": True, "review": review})
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json({"error": str(error)}, 400)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True, help="Private task JSON root")
    parser.add_argument("--image-root", type=Path, help="Private image root")
    parser.add_argument("--database", type=Path, default=Path("reviews.sqlite3"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not args.data_root.is_dir():
        parser.error("--data-root must be an existing directory")
    image_root = args.image_root.resolve() if args.image_root else None
    if image_root is not None and not image_root.is_dir():
        parser.error("--image-root must be an existing directory")
    dataset = Dataset(args.data_root)
    reviews = Reviews(args.database)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(dataset, reviews, image_root))
    print(f"DermClin-MT review tool: http://{args.host}:{args.port}")
    print(f"Data: {args.data_root.resolve()}")
    print(f"Review database: {args.database.resolve()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

