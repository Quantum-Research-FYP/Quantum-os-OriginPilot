/* ═══════════════════════════════════════════════════════════
   PilotProbe Dashboard — Main Application
   ═══════════════════════════════════════════════════════════ */

const SYSTEM_COLORS = {
  superconducting: '#3b82f6',
  ion_trap: '#10b981',
  neutral_atom: '#8b5cf6',
  photonic: '#f59e0b',
};

const DIR_LABELS = { REQUEST: '← REQ', RESPONSE: '→ RES', PUB: '◆ PUB' };
const DIR_CLASS = { REQUEST: 'req', RESPONSE: 'res', PUB: 'pub' };

let ws = null;
let autoScroll = true;
let messages = [];
let stats = { total: 0, requests: 0, responses: 0, pubs: 0, errors: 0 };
let validationIssues = [];

// ── Navigation ─────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    item.classList.add('active');
    const viewId = 'view-' + item.dataset.view;
    document.getElementById(viewId).classList.add('active');

    if (item.dataset.view === 'systems') refreshSystems();
    if (item.dataset.view === 'profiler') { loadRecentTasks(); loadPipelineStats(); }
    if (item.dataset.view === 'validation') refreshValidation();
  });
});

// ── WebSocket ──────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws/stream`);

  ws.onopen = () => {
    document.getElementById('ws-status-dot').className = 'status-dot connected';
    document.getElementById('ws-status-text').textContent = 'Connected';
  };

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      onMessage(msg);
    } catch (err) { console.error('WS parse error:', err); }
  };

  ws.onclose = () => {
    document.getElementById('ws-status-dot').className = 'status-dot disconnected';
    document.getElementById('ws-status-text').textContent = 'Reconnecting...';
    setTimeout(connectWS, 2000);
  };

  ws.onerror = () => ws.close();
}

// ── Message Handler ────────────────────────────────────────
function onMessage(msg) {
  messages.push(msg);
  stats.total++;
  if (msg.direction === 'REQUEST') stats.requests++;
  else if (msg.direction === 'RESPONSE') stats.responses++;
  else if (msg.direction === 'PUB') stats.pubs++;
  if (!msg.is_valid) stats.errors++;

  // Track validation issues
  if (msg.validation_errors) {
    validationIssues.push(msg);
  }

  updateHeaderStats();
  appendStreamMsg(msg);
}

function updateHeaderStats() {
  document.getElementById('stat-total').textContent = stats.total;
  document.getElementById('stat-requests').textContent = stats.requests;
  document.getElementById('stat-responses').textContent = stats.responses;
  document.getElementById('stat-pubs').textContent = stats.pubs;
  document.getElementById('stat-errors').textContent = stats.errors;
}

// ── Live Stream ────────────────────────────────────────────
function appendStreamMsg(msg) {
  const list = document.getElementById('stream-list');
  const empty = document.getElementById('stream-empty');
  if (empty) empty.remove();

  // Apply filters
  const fSys = document.getElementById('filter-system').value;
  const fDir = document.getElementById('filter-direction').value;
  const fSearch = document.getElementById('filter-search').value.toLowerCase();

  if (fSys && msg.system_type !== fSys) return;
  if (fDir && msg.direction !== fDir) return;
  if (fSearch) {
    const haystack = `${msg.msg_type || ''} ${msg.task_id || ''} ${msg.system_type}`.toLowerCase();
    if (!haystack.includes(fSearch)) return;
  }

  const ts = new Date(msg.timestamp * 1000).toLocaleTimeString('en-GB', { hour12: false, fractionalSecondDigits: 3 });
  const valid = msg.is_valid ? '✅' : (msg.validation_errors?.includes('⚠') ? '⚠️' : '❌');

  let metaParts = [];
  if (msg.sn != null) metaParts.push(`SN=${msg.sn}`);
  if (msg.task_id) metaParts.push(`TaskId=${msg.task_id.substring(0, 12)}`);
  if (msg.parsed_fields) {
    try {
      const pf = JSON.parse(msg.parsed_fields);
      if (pf.TaskStatus != null) metaParts.push(`Status=${pf.TaskStatus}`);
      if (pf.ErrCode != null && pf.ErrCode !== 0) metaParts.push(`Err=${pf.ErrCode}`);
    } catch (_) {}
  }

  const el = document.createElement('div');
  el.className = `stream-msg ${msg.system_type} ${msg.is_valid ? '' : 'invalid'}`;
  el.innerHTML = `
    <span class="ts">${ts}</span>
    <span class="dir ${DIR_CLASS[msg.direction] || ''}">${DIR_LABELS[msg.direction] || msg.direction}</span>
    <span class="sys" style="color:${SYSTEM_COLORS[msg.system_type] || '#888'}">${msg.system_type}</span>
    <span class="type">${msg.msg_type || '???'}</span>
    <span class="meta">${metaParts.join('  ')}</span>
    <span class="valid">${valid}</span>
  `;
  el.addEventListener('click', () => openModal(msg));
  list.appendChild(el);

  // Keep max 500 messages in DOM
  while (list.children.length > 500) list.removeChild(list.firstChild);

  if (autoScroll) list.scrollTop = list.scrollHeight;
}

// Filter change handlers
['filter-system', 'filter-direction'].forEach(id => {
  document.getElementById(id).addEventListener('change', rebuildStream);
});
document.getElementById('filter-search').addEventListener('input', debounce(rebuildStream, 300));

function rebuildStream() {
  const list = document.getElementById('stream-list');
  list.innerHTML = '';
  messages.forEach(m => appendStreamMsg(m));
}

function clearStream() {
  messages = [];
  stats = { total: 0, requests: 0, responses: 0, pubs: 0, errors: 0 };
  validationIssues = [];
  document.getElementById('stream-list').innerHTML = '';
  updateHeaderStats();
}

function toggleAutoScroll() {
  autoScroll = !autoScroll;
  document.getElementById('btn-autoscroll').classList.toggle('active', autoScroll);
}

// ── Message Inspector Modal ────────────────────────────────
function openModal(msg) {
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('modal-title').textContent = `${msg.msg_type || 'Message'} — ${msg.system_type}`;

  const ts = new Date(msg.timestamp * 1000).toLocaleString();
  let metaHtml = `
    <div class="field"><div class="label">Timestamp</div><div class="value">${ts}</div></div>
    <div class="field"><div class="label">Direction</div><div class="value">${msg.direction}</div></div>
    <div class="field"><div class="label">System</div><div class="value">${msg.system_type}</div></div>
    <div class="field"><div class="label">Channel</div><div class="value">${msg.channel}</div></div>
  `;
  if (msg.sn != null) metaHtml += `<div class="field"><div class="label">SN</div><div class="value">${msg.sn}</div></div>`;
  if (msg.task_id) metaHtml += `<div class="field"><div class="label">Task ID</div><div class="value">${msg.task_id}</div></div>`;
  if (msg.validation_errors) {
    metaHtml += `<div class="field" style="grid-column:span 2;background:rgba(239,68,68,0.08)">
      <div class="label">Validation</div><div class="value" style="color:var(--error)">${msg.validation_errors}</div></div>`;
  }
  document.getElementById('modal-meta').innerHTML = metaHtml;

  try {
    const parsed = JSON.parse(msg.raw_payload);
    document.getElementById('modal-payload').textContent = JSON.stringify(parsed, null, 2);
  } catch (_) {
    document.getElementById('modal-payload').textContent = msg.raw_payload;
  }
}

function closeModal(e) {
  if (!e || e.target.id === 'modal-overlay') {
    document.getElementById('modal-overlay').classList.remove('open');
  }
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── Systems View ───────────────────────────────────────────
async function refreshSystems() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    const grid = document.getElementById('systems-grid');

    const systems = ['superconducting', 'ion_trap', 'neutral_atom', 'photonic'];
    grid.innerHTML = systems.map(sys => {
      const count = data.by_system?.[sys] || 0;
      const pct = data.total_messages > 0 ? ((count / data.total_messages) * 100).toFixed(1) : 0;
      return `
        <div class="system-card ${sys}">
          <div class="name">${sys.replace('_', ' ')}</div>
          <div class="stat-row"><span>Messages</span><span class="val">${count}</span></div>
          <div class="stat-row"><span>Share</span><span class="val">${pct}%</span></div>
        </div>`;
    }).join('');

    const dist = document.getElementById('msg-distribution');
    if (data.by_type) {
      dist.innerHTML = Object.entries(data.by_type)
        .map(([type, cnt]) => `<div class="stat-row" style="display:flex;justify-content:space-between;padding:4px 0;font-size:12px">
          <span style="font-family:'JetBrains Mono',monospace">${type}</span>
          <span style="color:var(--text-primary)">${cnt}</span></div>`)
        .join('');
    }
  } catch (err) { console.error('Stats error:', err); }
}

// ── Profiler ───────────────────────────────────────────────
async function loadRecentTasks() {
  try {
    const res = await fetch('/api/tasks?limit=10');
    const data = await res.json();
    const el = document.getElementById('recent-tasks');

    if (!data.tasks?.length) {
      el.innerHTML = '<div class="empty-state"><p>No tasks captured yet</p></div>';
      return;
    }

    el.innerHTML = data.tasks.map(t => {
      const ts = new Date(t.first_seen * 1000).toLocaleTimeString();
      return `<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);cursor:pointer;font-size:12px" 
        onclick="document.getElementById('profiler-task-id').value='${t.task_id}';profileTask()">
        <span style="font-family:'JetBrains Mono',monospace;color:var(--info)">${t.task_id.substring(0,20)}...</span>
        <span style="color:${SYSTEM_COLORS[t.system_type] || '#888'}">${t.system_type}</span>
        <span style="color:var(--text-dim)">${ts}</span>
      </div>`;
    }).join('');
  } catch (err) { console.error('Tasks error:', err); }
}

async function loadPipelineStats() {
  try {
    const res = await fetch('/api/profiler/pipeline');
    const data = await res.json();
    const container = document.getElementById('pipeline-stats-container');

    if (!data || data.total_tasks === 0) {
      container.innerHTML = '<p style="color:var(--text-dim);font-size:12px">No pipeline metrics available. Run some tasks first.</p>';
      return;
    }

    let bottleneckColor = 'var(--text-dim)';
    if (data.bottleneck_recommendation.includes('COMPILATION')) bottleneckColor = '#f59e0b';
    if (data.bottleneck_recommendation.includes('SCHEDULING')) bottleneckColor = '#ef4444';
    if (data.bottleneck_recommendation.includes('EXECUTION')) bottleneckColor = '#10b981';

    container.innerHTML = `
      <div class="profiler-summary" style="margin-bottom: 20px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
        <div class="profiler-stat"><div class="label">Total Tasks</div><div class="value">${data.total_tasks}</div></div>
        <div class="profiler-stat"><div class="label">Succeeded</div><div class="value" style="color:var(--success)">${data.successful_tasks}</div></div>
        <div class="profiler-stat"><div class="label">Failed</div><div class="value" style="color:var(--error)">${data.failed_tasks}</div></div>
        <div class="profiler-stat"><div class="label">Running</div><div class="value" style="color:var(--info)">${data.running_tasks}</div></div>
      </div>

      <div style="margin-bottom: 20px;">
        <h4 style="font-size:11px;color:var(--text-dim);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">Avg Phase Latency</h4>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <div>
            <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">
              <span>Pending / Scheduling</span><span>${data.avg_pending_ms} ms</span>
            </div>
            <div style="background:var(--border);height:6px;border-radius:3px;overflow:hidden;">
              <div style="background:var(--info);height:100%;width:${Math.min(100, (data.avg_pending_ms / (data.avg_turnaround_ms || 1)) * 100)}%;"></div>
            </div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">
              <span>Compilation</span><span>${data.avg_compile_ms} ms</span>
            </div>
            <div style="background:var(--border);height:6px;border-radius:3px;overflow:hidden;">
              <div style="background:#f59e0b;height:100%;width:${Math.min(100, (data.avg_compile_ms / (data.avg_turnaround_ms || 1)) * 100)}%;"></div>
            </div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">
              <span>Execution</span><span>${data.avg_execution_ms} ms</span>
            </div>
            <div style="background:var(--border);height:6px;border-radius:3px;overflow:hidden;">
              <div style="background:#10b981;height:100%;width:${Math.min(100, (data.avg_execution_ms / (data.avg_turnaround_ms || 1)) * 100)}%;"></div>
            </div>
          </div>
        </div>
      </div>

      <div style="display:flex;gap:16px;font-size:11px;border-top:1px solid var(--border);padding-top:12px;">
        <div><span style="color:var(--text-dim)">SLA Violations:</span> 
          <span style="color:${data.pending_sla_violations > 0 ? 'var(--error)' : 'var(--success)'};font-weight:600;">
            ${data.pending_sla_violations} Pending
          </span>,
          <span style="color:${data.compile_sla_violations > 0 ? 'var(--error)' : 'var(--success)'};font-weight:600;">
            ${data.compile_sla_violations} Compile
          </span>
        </div>
        <div style="margin-left:auto;"><span style="color:var(--text-dim)">Bottleneck Recommendation:</span> 
          <span style="color:${bottleneckColor};font-weight:600;">${data.bottleneck_recommendation}</span>
        </div>
      </div>
    `;
  } catch (err) { console.error('Pipeline stats error:', err); }
}

async function profileTask() {
  const taskId = document.getElementById('profiler-task-id').value.trim();
  if (!taskId) return;

  try {
    const res = await fetch(`/api/profiler/task/${taskId}`);
    const data = await res.json();

    if (data.error) {
      document.getElementById('profiler-results').innerHTML = `
        <div class="empty-state"><div class="icon">🔍</div><h3>${data.error}</h3></div>`;
      return;
    }

    let html = `
      <div class="profiler-summary">
        <div class="profiler-stat"><div class="label">System</div><div class="value" style="color:${SYSTEM_COLORS[data.system_type]}">${data.system_type}</div></div>
        <div class="profiler-stat"><div class="label">Duration</div><div class="value">${data.total_duration_ms}ms</div></div>
        <div class="profiler-stat"><div class="label">Events</div><div class="value">${data.event_count}</div></div>
      </div>
      <div class="card"><div class="card-header"><h3>Timeline — ${taskId.substring(0,16)}...</h3></div>
      <div class="card-body"><div class="timeline">`;

    data.events.forEach(ev => {
      const cls = ev.channel === 'pub' ? 'pub' : (ev.is_valid ? '' : 'error');
      let detail = '';
      if (ev.task_status != null) detail = `Status → ${ev.task_status}`;
      if (ev.err_code != null && ev.err_code !== 0) detail += ` (ErrCode: ${ev.err_code})`;

      html += `
        <div class="timeline-event ${cls}">
          <span class="time">+${ev.relative_ms}ms</span>
          <span class="type">${ev.msg_type || '???'}</span>
          <span class="dir ${DIR_CLASS[ev.direction] || ''}" style="font-size:11px">${DIR_LABELS[ev.direction] || ev.direction}</span>
          <span class="detail">${detail}</span>
        </div>`;
    });

    html += '</div></div></div>';
    document.getElementById('profiler-results').innerHTML = html;
  } catch (err) { console.error('Profiler error:', err); }
}

// ── Validation View ────────────────────────────────────────
function refreshValidation() {
  const tbody = document.getElementById('validation-tbody');
  const empty = document.getElementById('validation-empty');
  const countEl = document.getElementById('validation-count');

  if (!validationIssues.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    countEl.textContent = '0 issues';
    countEl.className = 'badge success';
    return;
  }

  empty.style.display = 'none';
  countEl.textContent = `${validationIssues.length} issues`;
  countEl.className = 'badge error';

  tbody.innerHTML = validationIssues.slice(-100).reverse().map(msg => {
    const ts = new Date(msg.timestamp * 1000).toLocaleTimeString('en-GB', { hour12: false });
    const severity = msg.validation_errors?.includes('❌') ? 'error' : 'warning';
    return `<tr>
      <td>${ts}</td>
      <td style="color:${SYSTEM_COLORS[msg.system_type] || '#888'}">${msg.system_type}</td>
      <td>${msg.direction}</td>
      <td>${msg.msg_type || '???'}</td>
      <td><span class="badge ${severity}">${severity}</span></td>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis">${msg.validation_errors || ''}</td>
    </tr>`;
  }).join('');
}

// ── Utilities ──────────────────────────────────────────────
function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── Init ───────────────────────────────────────────────────
connectWS();
setInterval(refreshSystems, 10000);
