// Shared by every lab page. Nothing here touches the network.
function el(tag, props, children) {
  const node = document.createElement(tag);
  Object.keys(props || {}).forEach((key) => {
    if (key === 'text') node.textContent = props[key];
    else if (key === 'class') node.className = props[key];
    else node.setAttribute(key, props[key]);
  });
  (children || []).forEach((child) => node.append(child));
  return node;
}
function svgEl(tag, props, children) {
  const node = document.createElementNS('http:' + '//www.w3.org/2000/svg', tag);
  Object.keys(props || {}).forEach((key) => {
    if (key === 'text') node.textContent = props[key];
    else node.setAttribute(key, props[key]);
  });
  (children || []).forEach((child) => node.append(child));
  return node;
}
// buildVerdicts is pure so it can be checked without a browser. It reads only a demo's name, verdict
// and note, so no track data can reach the export.
function buildVerdicts(state) {
  const demos = {};
  (state.demos || []).forEach((demo) => {
    const entry = (state.verdicts || {})[demo.name] || {};
    if (['keep', 'rework', 'drop'].indexOf(entry.verdict) < 0) return;
    demos[demo.name] = { verdict: entry.verdict, note: String(entry.note || '').trim() };
  });
  return { exported_at: state.today, demos: demos };
}
// Drafts live in localStorage when it works. The page works without it: choices are kept in memory.
const DRAFT_KEY = 'sidetrack-lab-verdicts';
const verdicts = {};
function loadDrafts() {
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    const saved = raw ? JSON.parse(raw) : {};
    Object.keys(saved).forEach((name) => {
      if (!(name in verdicts)) verdicts[name] = saved[name];
    });
  } catch (error) {
    /* storage unavailable: keep to memory */
  }
}
function setVerdict(name, patch) {
  verdicts[name] = Object.assign({}, verdicts[name] || {}, patch);
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(verdicts));
  } catch (error) {
    /* ok */
  }
}
// One keep / rework / drop control with a note, for one demo.
function verdictControl(name) {
  const current = verdicts[name] || {};
  const row = el('div', { class: 'verdict' });
  const buttons = ['keep', 'rework', 'drop'].map((value) => {
    const button = el('button', {
      type: 'button',
      text: value,
      'aria-pressed': String(current.verdict === value),
    });
    button.addEventListener('click', () => {
      setVerdict(name, { verdict: value });
      buttons.forEach((other) => other.setAttribute('aria-pressed', String(other === button)));
    });
    return button;
  });
  const note = el('textarea', { 'aria-label': 'Note on ' + name, placeholder: 'Note' });
  note.value = current.note || '';
  note.addEventListener('input', () => setVerdict(name, { note: note.value }));
  buttons.forEach((button) => row.append(button));
  row.append(note);
  return row;
}
function today() {
  return new Date().toISOString().slice(0, 10);
}
function download(filename, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }),
  );
  const link = el('a', { href: url, download: filename });
  link.click();
  URL.revokeObjectURL(url);
}
function labData() {
  return JSON.parse(document.getElementById('data').textContent);
}
