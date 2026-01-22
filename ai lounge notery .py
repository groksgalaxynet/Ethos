# x0vs_lounge_notary.py — Pythonista 3 / no extra deps
import ui, sqlite3, hashlib, json, time, os, uuid

APP_DB = os.path.expanduser('~/Documents/x0vs_ledger.db')

LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS notarized (
  id TEXT PRIMARY KEY,
  created_ts REAL NOT NULL,
  creator_id TEXT NOT NULL,
  title TEXT NOT NULL,
  kind TEXT NOT NULL,            -- 'world' | 'tool' | 'art' | ...
  content_json TEXT NOT NULL,    -- canonical JSON for hashing
  sha256 TEXT NOT NULL,
  tags TEXT                      -- comma-separated
);
CREATE INDEX IF NOT EXISTS idx_sha ON notarized(sha256);
"""

def sha256_bytes(b: bytes) -> str:
  h = hashlib.sha256()
  h.update(b)
  return h.hexdigest()

def canonical_json(obj) -> str:
  # Stable, ASCII-only, sorted keys
  return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(',', ':'))

class Notary:
  def __init__(self, db_path=APP_DB):
    self.db_path = db_path
    self._ensure_db()
    self.ephemeral_cache = []  # clears on app exit

  def _ensure_db(self):
    con = sqlite3.connect(self.db_path)
    try:
      cur = con.cursor()
      for stmt in LEDGER_SCHEMA.strip().split(';'):
        s = stmt.strip()
        if s:
          cur.execute(s)
      con.commit()
    finally:
      con.close()

  def notarize(self, payload: dict):
    """
    payload keys:
      creator_id, title, kind, data(dict), tags(list[str])
    returns: record dict with sha256 and id
    """
    # Build canonical content to hash
    body = {
      'creator_id': payload['creator_id'],
      'title': payload['title'],
      'kind': payload['kind'],
      'data': payload['data'],
      'tags': payload.get('tags', [])
    }
    cjson = canonical_json(body).encode('utf-8')
    digest = sha256_bytes(cjson)
    rec_id = str(uuid.uuid4())
    row = {
      'id': rec_id,
      'created_ts': time.time(),
      'creator_id': payload['creator_id'],
      'title': payload['title'],
      'kind': payload['kind'],
      'content_json': cjson.decode('utf-8'),
      'sha256': digest,
      'tags': ','.join(payload.get('tags', []))
    }
    con = sqlite3.connect(self.db_path)
    try:
      cur = con.cursor()
      cur.execute("""INSERT INTO notarized
        (id, created_ts, creator_id, title, kind, content_json, sha256, tags)
        VALUES (:id, :created_ts, :creator_id, :title, :kind, :content_json, :sha256, :tags)""", row)
      con.commit()
    finally:
      con.close()
    return row

  def list_recent(self, limit=20):
    con = sqlite3.connect(self.db_path)
    try:
      cur = con.cursor()
      cur.execute("SELECT created_ts, title, kind, sha256 FROM notarized ORDER BY created_ts DESC LIMIT ?", (limit,))
      return cur.fetchall()
    finally:
      con.close()

  def add_ephemeral(self, payload: dict):
    # Not hashed, not stored. Visible for this session only.
    self.ephemeral_cache.append({
      'created_ts': time.time(),
      **payload
    })
    return self.ephemeral_cache[-1]

# ---------------- UI ----------------

class NotaryView(ui.View):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.bg_color = (0.06, 0.10, 0.18)
    self.notary = Notary()
    self._build()

  def _label(self, txt):
    l = ui.Label(text=txt)
    l.text_color = (0.9, 1.0, 1.0)
    l.font = ('<System>', 14)
    return l

  def _textfield(self, ph=''):
    t = ui.TextField(placeholder=ph, clear_button_mode='while_editing')
    t.tint_color = (0.8, 0.95, 1.0)
    t.text_color = (0.95, 0.98, 1.0)
    t.background_color = (0.08, 0.12, 0.22)
    t.border_width = 0
    t.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
    return t

  def _textview(self):
    tv = ui.TextView()
    tv.text_color = (0.95, 0.98, 1.0)
    tv.background_color = (0.08, 0.12, 0.22)
    tv.font = ('<System>', 13)
    return tv

  def _seg(self, items):
    s = ui.SegmentedControl(segments=items)
    s.selected_index = 0
    return s

  def _switch(self):
    sw = ui.Switch()
    sw.value = True  # default to Ledger
    return sw

  def _btn(self, title, action):
    b = ui.Button(title=title)
    b.action = action
    b.tint_color = (0.2, 0.9, 0.7)
    b.background_color = (0.10, 0.14, 0.26)
    b.corner_radius = 6
    return b

  def _build(self):
    pad = 8
    y = pad

    self.add_subview(self._label('Creator (emoji/id)'))
    self.subviews[-1].frame = (pad, y, self.width-2*pad, 22); y += 22
    self.tf_creator = self._textfield('🧪🐜stack123')
    self.tf_creator.frame = (pad, y, self.width-2*pad, 32); self.add_subview(self.tf_creator); y += 36

    self.add_subview(self._label('Title'))
    self.subviews[-1].frame = (pad, y, self.width-2*pad, 22); y += 22
    self.tf_title = self._textfield('My VR Lab Build v1')
    self.tf_title.frame = (pad, y, self.width-2*pad, 32); self.add_subview(self.tf_title); y += 36

    self.add_subview(self._label('Kind'))
    self.subviews[-1].frame = (pad, y, self.width-2*pad, 22); y += 22
    self.kind_seg = self._seg(['world','tool','art','other'])
    self.kind_seg.frame = (pad, y, self.width-2*pad, 32); self.add_subview(self.kind_seg); y += 40

    self.add_subview(self._label('Tags (comma-separated)'))
    self.subviews[-1].frame = (pad, y, self.width-2*pad, 22); y += 22
    self.tf_tags = self._textfield('xovs,vr,prototype')
    self.tf_tags.frame = (pad, y, self.width-2*pad, 32); self.add_subview(self.tf_tags); y += 36

    self.add_subview(self._label('Content JSON (minimal spec below)'))
    self.subviews[-1].frame = (pad, y, self.width-2*pad, 22); y += 22
    self.tv_json = self._textview()
    self.tv_json.frame = (pad, y, self.width-2*pad, 160); self.add_subview(self.tv_json); y += 168

    # default content schema
    default_payload = {
      "version": 1,
      "assets": [],                # list of URIs or local file refs
      "parameters": {              # tunables the AI/world exposes
        "seed": 1234,
        "scale": 1.0
      },
      "notes": "Describe intent, provenance, or build steps."
    }
    self.tv_json.text = canonical_json(default_payload)

    # Ledger toggle
    self.add_subview(self._label('Ledger toggle (ON = notarize, OFF = ephemeral)'))
    self.subviews[-1].frame = (pad, y, self.width-2*pad-60, 22)
    self.sw_ledger = self._switch()
    self.sw_ledger.frame = (self.width-60-pad, y, 60, 28); self.add_subview(self.sw_ledger); y += 36

    # Buttons row
    self.btn_save = self._btn('Save', self.on_save)
    self.btn_preview = self._btn('Preview Hash', self.on_preview)
    bw = (self.width - 3*pad) / 2.0
    self.btn_save.frame = (pad, y, bw, 36)
    self.btn_preview.frame = (pad+bw+pad, y, bw, 36)
    self.add_subview(self.btn_save); self.add_subview(self.btn_preview); y += 44

    # Output
    self.out = self._textview()
    self.out.editable = False
    self.out.frame = (pad, y, self.width-2*pad, 160)
    self.add_subview(self.out); y += 168

    # Recent
    self.btn_recent = self._btn('Show Recent Ledger', self.on_recent)
    self.btn_recent.frame = (pad, y, self.width-2*pad, 36)
    self.add_subview(self.btn_recent)

  def layout(self):
    # keep responsive
    self.subviews[:]  # no-op; frames handled in _build for simplicity

  def _collect(self):
    creator = (self.tf_creator.text or '').strip()
    title = (self.tf_title.text or '').strip()
    kind = self.kind_seg.segments[self.kind_seg.selected_index]
    tags = [t.strip() for t in (self.tf_tags.text or '').split(',') if t.strip()]
    try:
      content = json.loads(self.tv_json.text)
    except Exception as e:
      raise ValueError(f'Content JSON invalid: {e}')
    if not creator or not title:
      raise ValueError('Creator and Title are required.')
    return creator, title, kind, tags, content

  def on_preview(self, sender):
    try:
      creator, title, kind, tags, content = self._collect()
      body = {
        'creator_id': creator,
        'title': title,
        'kind': kind,
        'data': content,
        'tags': tags
      }
      dig = sha256_bytes(canonical_json(body).encode('utf-8'))
      self.out.text = f'Preview SHA-256:\n{dig}\n\nThis will be identical on notarize.'
    except Exception as e:
      self.out.text = f'Error: {e}'

  def on_save(self, sender):
    try:
      creator, title, kind, tags, content = self._collect()
      payload = {'creator_id': creator,'title': title,'kind': kind,'data': content,'tags': tags}
      if self.sw_ledger.value:
        rec = self.notary.notarize(payload)
        self.out.text = (
          'LEDGER WRITE OK\n'
          f"Title: {rec['title']}\nKind: {rec['kind']}\nSHA-256: {rec['sha256']}\n"
          f"ID: {rec['id']}\nTS: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(rec['created_ts']))}"
        )
      else:
        rec = self.notary.add_ephemeral(payload)
        self.out.text = (
          'EPHEMERAL SAVE OK (session-only)\n'
          f"Title: {title}\nKind: {kind}\nItems in session: {len(self.notary.ephemeral_cache)}"
        )
    except Exception as e:
      self.out.text = f'Error: {e}'

  def on_recent(self, sender):
    rows = self.notary.list_recent(20)
    if not rows:
      self.out.text = 'Ledger empty.'
      return
    lines = ['Recent notarized:']
    for ts, title, kind, sh in rows:
      lines.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))} | {kind:<5} | {title} | {sh[:12]}...")
    self.out.text = '\n'.join(lines)

def main():
  w, h = 420, 720
  v = NotaryView(frame=(0,0,w,h))
  v.name = 'X_0VS • AI Lounge Notary'
  v.present('sheet')

if __name__ == '__main__':
  main()
