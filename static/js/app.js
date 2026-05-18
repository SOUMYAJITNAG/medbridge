/* ═══════════════════════════════════════════════════════════════════
   MedBridge Ukraine — Frontend JS (Alpine.js components + utils)
   ═══════════════════════════════════════════════════════════════════ */

/* ── Navbar scroll effect ────────────────────────────────────────── */
window.addEventListener('scroll', () => {
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  }
});

/* ── Mobile menu toggle ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.querySelector('.mobile-menu-btn');
  const links = document.querySelector('.nav-links');
  if (btn && links) {
    btn.addEventListener('click', () => links.classList.toggle('open'));
  }

  // Fade-in on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(el => { if (el.isIntersecting) el.target.classList.add('visible'); });
  }, { threshold: 0.15 });
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

  // Hero particles
  initParticles();
});

/* ── Hero canvas particles ───────────────────────────────────────── */
function initParticles() {
  const container = document.querySelector('.hero-particles');
  if (!container) return;
  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:0.35';
  container.appendChild(canvas);
  const ctx = canvas.getContext('2d');

  const resize = () => {
    canvas.width = container.offsetWidth;
    canvas.height = container.offsetHeight;
  };
  resize();
  window.addEventListener('resize', resize);

  const DOTS = 60;
  const dots = Array.from({ length: DOTS }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    vx: (Math.random() - 0.5) * 0.3,
    vy: (Math.random() - 0.5) * 0.3,
    r: Math.random() * 1.5 + 0.5,
    alpha: Math.random() * 0.5 + 0.1,
  }));

  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    dots.forEach(d => {
      d.x += d.vx; d.y += d.vy;
      if (d.x < 0 || d.x > canvas.width) d.vx *= -1;
      if (d.y < 0 || d.y > canvas.height) d.vy *= -1;
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(26,115,232,${d.alpha})`;
      ctx.fill();
    });
    // draw connections
    dots.forEach((a, i) => {
      dots.slice(i + 1).forEach(b => {
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 100) {
          ctx.beginPath();
          ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(0,87,183,${0.15 * (1 - dist / 100)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      });
    });
    requestAnimationFrame(animate);
  };
  animate();
}

/* ═══════════════════════════════════════════════════════════════════
   UPLOAD PAGE — Alpine.js component
   ═══════════════════════════════════════════════════════════════════ */
function uploadApp() {
  return {
    step: 1,
    files: [],
    patientInfo: {
      full_name: '',
      dob: '',
      gender: '',
      blood_type: '',
      primary_language: 'Ukrainian',
      secondary_language: 'English',
      origin_city: '',
      current_location: '',
      contact_info: '',
      special_notes: '',
    },
    uploading: false,
    uploadError: null,
    uploadSuccess: false,
    runId: null,

    get totalFiles() { return this.files.length; },
    get canProceedStep1() { return this.patientInfo.full_name.trim().length > 1; },
    get canSubmit() { return this.files.length > 0; },

    goStep(n) {
      if (n === 2 && !this.canProceedStep1) return;
      this.step = n;
    },

    handleDrop(e) {
      e.preventDefault();
      const dropped = Array.from(e.dataTransfer.files);
      this.addFiles(dropped);
    },
    handleDragOver(e) { e.preventDefault(); },
    handleFileInput(e) { this.addFiles(Array.from(e.target.files)); },
    triggerFileInput() { document.getElementById('file-input').click(); },

    addFiles(fileList) {
      const allowed = ['image/jpeg','image/png','image/jpg','image/webp','image/heic',
                       'audio/mpeg','audio/mp4','audio/wav','audio/ogg','audio/webm',
                       'application/pdf','text/plain'];
      fileList.forEach(f => {
        if (!allowed.includes(f.type) && !f.type.startsWith('image/') && !f.type.startsWith('audio/')) return;
        if (this.files.find(x => x.file.name === f.name && x.file.size === f.size)) return;
        this.files.push({
          file: f,
          id: Math.random().toString(36).slice(2),
          category: this.guessCat(f),
          preview: f.type.startsWith('image/') ? URL.createObjectURL(f) : null,
        });
      });
    },

    guessCat(f) {
      if (f.type.startsWith('audio/')) return 'voice_note';
      const name = f.name.toLowerCase();
      if (name.includes('prescript') || name.includes('rx')) return 'prescription';
      if (name.includes('lab') || name.includes('result')) return 'lab_result';
      if (name.includes('discharge') || name.includes('hospital')) return 'hospital_record';
      if (name.includes('xray') || name.includes('scan') || name.includes('mri')) return 'scan';
      return 'medical_document';
    },

    removeFile(id) {
      const f = this.files.find(x => x.id === id);
      if (f && f.preview) URL.revokeObjectURL(f.preview);
      this.files = this.files.filter(x => x.id !== id);
    },

    fileIcon(f) {
      if (f.file.type.startsWith('image/')) return 'img';
      if (f.file.type.startsWith('audio/')) return 'audio';
      if (f.file.type === 'application/pdf') return 'pdf';
      return 'text';
    },

    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    },

    async submit() {
      if (!this.canSubmit || this.uploading) return;
      this.uploading = true;
      this.uploadError = null;

      try {
        const fd = new FormData();
        // patient info
        Object.entries(this.patientInfo).forEach(([k, v]) => fd.append(k, v || ''));

        // files
        this.files.forEach(f => {
          fd.append('files', f.file);
          fd.append('categories', f.category);
        });

        const resp = await fetch('/api/upload', { method: 'POST', body: fd });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: 'Upload failed' }));
          throw new Error(err.detail || 'Upload failed');
        }
        const data = await resp.json();
        this.runId = data.run_id;
        this.uploadSuccess = true;

        // Redirect to pipeline page after brief pause
        setTimeout(() => {
          window.location.href = `/pipeline/${this.runId}`;
        }, 1500);
      } catch (e) {
        this.uploadError = e.message;
      } finally {
        this.uploading = false;
      }
    },
  };
}

/* ═══════════════════════════════════════════════════════════════════
   PIPELINE PAGE — Alpine.js component
   ═══════════════════════════════════════════════════════════════════ */
function pipelineApp(runId) {
  return {
    runId,
    status: 'initializing',
    progress: 0,
    currentAgent: null,
    events: [],
    agentStates: {},
    error: null,
    es: null,
    autoScroll: true,
    passportReady: false,

    agentDefs: [
      { key: 'MultimodalUnderstandingAgent', num: '01', name: 'Multimodal Understanding', desc: 'Processes images, documents & voice using Gemma 4 vision', color: '#1A73E8' },
      { key: 'MedicalStructuringAgent', num: '02', name: 'Medical Structuring', desc: 'Extracts medications, conditions, allergies & vaccinations', color: '#8B5CF6' },
      { key: 'TimelineReconstructionAgent', num: '03', name: 'Timeline Reconstruction', desc: 'Builds chronological treatment history from evidence', color: '#06B6D4' },
      { key: 'RiskUncertaintyAgent', num: '04', name: 'Risk & Uncertainty', desc: 'Flags critical risks, confidence gaps, missing data', color: '#F59E0B' },
      { key: 'HumanVerificationAgent', num: '05', name: 'Verification Prep', desc: 'Generates doctor review checklist for each claim', color: '#10B981' },
      { key: 'SummaryGenerationAgent', num: '06', name: 'Passport Generation', desc: 'Creates multilingual Emergency Medical Passport', color: '#EF4444' },
    ],

    get progressLabel() {
      if (this.status === 'initializing') return 'Initializing agents…';
      if (this.status === 'running') return `Processing: ${this.currentAgent || '…'}`;
      if (this.status === 'completed') return 'Pipeline complete!';
      if (this.status === 'failed') return 'Pipeline failed';
      return 'Waiting…';
    },

    agentState(key) {
      return this.agentStates[key] || { status: 'pending', tool: null, output: null };
    },

    init() {
      // Initialize all agent states
      this.agentDefs.forEach(a => {
        this.agentStates[a.key] = { status: 'pending', tool: null, output: null };
      });

      // Start pipeline
      this.startPipeline();
    },

    async startPipeline() {
      try {
        const resp = await fetch(`/api/pipeline/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ run_id: this.runId }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: 'Failed to start pipeline' }));
          throw new Error(err.detail || 'Failed to start pipeline');
        }
        const data = await resp.json();
        // Now connect SSE
        this.connectSSE(data.run_id || this.runId);
      } catch (e) {
        this.error = e.message;
        this.status = 'failed';
      }
    },

    connectSSE(runId) {
      this.status = 'running';
      this.es = new EventSource(`/api/pipeline/${runId}/stream`);

      this.es.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          this.handleEvent(event);
        } catch { /* ignore parse errors */ }
      };

      this.es.onerror = () => {
        if (this.status !== 'completed') {
          this.es.close();
          // Try status poll fallback
          this.pollStatus(runId);
        }
      };
    },

    handleEvent(event) {
      const ts = new Date().toLocaleTimeString('en', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      this.events.push({ ...event, ts });

      // Keep events bounded
      if (this.events.length > 200) this.events = this.events.slice(-200);

      const type = event.type || '';
      const agent = event.agent || '';

      if (type === 'pipeline_start') {
        this.status = 'running'; this.progress = 2;
      }
      else if (type === 'agent_start') {
        this.currentAgent = agent;
        if (this.agentStates[agent]) {
          this.agentStates[agent] = { ...this.agentStates[agent], status: 'running' };
        }
        // Update progress
        const idx = this.agentDefs.findIndex(a => a.key === agent);
        if (idx >= 0) this.progress = Math.round((idx / this.agentDefs.length) * 80) + 10;
      }
      else if (type === 'tool_call') {
        if (this.agentStates[agent]) {
          this.agentStates[agent] = { ...this.agentStates[agent], tool: event.tool || event.function || 'tool' };
        }
      }
      else if (type === 'tool_result') {
        if (this.agentStates[agent]) {
          this.agentStates[agent] = { ...this.agentStates[agent], tool: null };
        }
      }
      else if (type === 'agent_done') {
        if (this.agentStates[agent]) {
          this.agentStates[agent] = { ...this.agentStates[agent], status: 'done', tool: null, output: event.summary || null };
        }
      }
      else if (type === 'pipeline_done' || type === 'pipeline_complete') {
        this.status = 'completed';
        this.progress = 100;
        this.currentAgent = null;
        this.passportReady = true;
        if (this.es) this.es.close();
      }
      else if (type === 'pipeline_error' || type === 'error') {
        this.error = event.message || event.error || 'Unknown error';
        this.status = 'failed';
        if (this.es) this.es.close();
      }

      // Auto-scroll events
      if (this.autoScroll) {
        this.$nextTick(() => {
          const feed = document.querySelector('.events-feed');
          if (feed) feed.scrollTop = feed.scrollHeight;
        });
      }
    },

    async pollStatus(runId) {
      let attempts = 0;
      const poll = async () => {
        if (this.status === 'completed' || this.status === 'failed' || attempts > 120) return;
        attempts++;
        try {
          const resp = await fetch(`/api/pipeline/${runId}/status`);
          if (resp.ok) {
            const data = await resp.json();
            this.progress = data.progress || this.progress;
            if (data.status === 'completed') {
              this.status = 'completed'; this.progress = 100; this.passportReady = true;
              return;
            }
            if (data.status === 'failed') {
              this.status = 'failed'; this.error = data.error || 'Pipeline failed';
              return;
            }
          }
        } catch { /* ignore */ }
        setTimeout(poll, 3000);
      };
      await poll();
    },

    goToPassport() { window.location.href = `/passport/${this.runId}`; },

    formatEventMessage(e) {
      if (e.type === 'tool_call') return `→ ${e.tool || e.function || 'tool'}(${e.args ? JSON.stringify(e.args).slice(0, 60) : ''})`;
      if (e.type === 'tool_result') return `← result: ${String(e.result || '').slice(0, 80)}`;
      if (e.type === 'agent_text') return e.text ? String(e.text).slice(0, 100) : '';
      if (e.type === 'agent_done') return e.summary || 'Agent completed';
      if (e.type === 'pipeline_start') return 'MedBridge pipeline started';
      if (e.type === 'pipeline_done') return 'Pipeline complete — passport ready';
      if (e.type === 'pipeline_error') return `ERROR: ${e.message || e.error || ''}`;
      return e.message || JSON.stringify(e).slice(0, 80);
    },

    destroy() { if (this.es) this.es.close(); },
  };
}

/* ═══════════════════════════════════════════════════════════════════
   PASSPORT PAGE — Alpine.js component
   ═══════════════════════════════════════════════════════════════════ */
function passportApp(runId) {
  return {
    runId,
    passport: null,
    loading: true,
    error: null,
    activeLang: null,
    qrUrl: null,

    async init() {
      await this.loadPassport();
    },

    async loadPassport() {
      this.loading = true;
      this.error = null;
      try {
        const resp = await fetch(`/api/passport/${this.runId}`);
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: 'Failed to load passport' }));
          throw new Error(err.detail || 'Failed to load passport');
        }
        this.passport = await resp.json();
        // Set default language
        const langs = Object.keys(this.passport.multilingual_summary || {});
        if (langs.length > 0) this.activeLang = langs[0];
        // Load QR
        this.qrUrl = `/api/export/${this.runId}/qr`;
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },

    get confidenceClass() {
      const c = parseFloat(this.passport?.confidence_score || 0);
      if (c >= 75) return 'conf-high';
      if (c >= 50) return 'conf-medium';
      if (c > 0) return 'conf-low';
      return 'conf-unknown';
    },

    get confidenceLabel() {
      const c = parseFloat(this.passport?.confidence_score || 0);
      if (c >= 75) return 'HIGH';
      if (c >= 50) return 'MEDIUM';
      if (c > 0) return 'LOW';
      return 'N/A';
    },

    get riskFlagCount() {
      return (this.passport?.risk_flags || []).length;
    },

    get criticalAllergies() {
      return (this.passport?.allergies || []).filter(a =>
        a.severity === 'critical' || a.severity === 'high'
      );
    },

    allergyClass(a) {
      const s = (a.severity || '').toLowerCase();
      if (s === 'critical' || s === 'high') return 'critical';
      return '';
    },

    medicationConfClass(pct) {
      if (pct >= 75) return 'high';
      if (pct >= 50) return 'medium';
      return 'low';
    },

    tlDotClass(type) {
      const t = (type || '').toLowerCase();
      if (t.includes('hospital')) return 'hospitalization';
      if (t.includes('med') || t.includes('prescription')) return 'medication_start';
      if (t.includes('surg')) return 'surgery';
      return '';
    },

    async downloadPDF() {
      window.open(`/api/export/${this.runId}/pdf`, '_blank');
    },

    getLangName(code) {
      const names = { uk: 'Ukrainian', en: 'English', de: 'German', pl: 'Polish', cs: 'Czech', fr: 'French', ro: 'Romanian' };
      return names[code] || code.toUpperCase();
    },

    riskFlagClass(flag) {
      const s = (flag.severity || flag.level || '').toLowerCase();
      if (s === 'critical') return 'critical';
      if (s === 'high') return 'high';
      if (s === 'low') return 'low';
      return '';
    },
  };
}

/* ═══════════════════════════════════════════════════════════════════
   VERIFY PAGE — Alpine.js component
   ═══════════════════════════════════════════════════════════════════ */
function verifyApp(runId) {
  return {
    runId,
    checklist: null,
    passport: null,
    loading: true,
    error: null,
    submitting: false,
    submitted: false,
    verificationError: null,

    doctorInfo: {
      name: '',
      specialty: '',
      license: '',
      institution: '',
      notes: '',
    },

    itemDecisions: {},  // { [fieldName]: { status, note } }

    get totalItems() { return (this.checklist || []).reduce((s, sec) => s + (sec.items || []).length, 0); },
    get approvedCount() { return Object.values(this.itemDecisions).filter(d => d.status === 'approved').length; },
    get flaggedCount() { return Object.values(this.itemDecisions).filter(d => d.status === 'flagged').length; },
    get rejectedCount() { return Object.values(this.itemDecisions).filter(d => d.status === 'rejected').length; },
    get canSubmit() { return this.doctorInfo.name.length > 1 && this.doctorInfo.license.length > 1; },

    async init() {
      this.loading = true;
      try {
        const [clRes, ppRes] = await Promise.all([
          fetch(`/api/passport/${this.runId}/checklist`),
          fetch(`/api/passport/${this.runId}`),
        ]);
        if (clRes.ok) {
          const clData = await clRes.json();
          this.checklist = clData.sections || [];
          // Initialize decisions
          this.checklist.forEach(sec => {
            (sec.items || []).forEach(item => {
              this.itemDecisions[item.field_name] = { status: 'pending', note: '' };
            });
          });
        }
        if (ppRes.ok) this.passport = await ppRes.json();
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },

    setDecision(fieldName, status) {
      const cur = this.itemDecisions[fieldName] || {};
      this.itemDecisions[fieldName] = {
        ...cur,
        status: cur.status === status ? 'pending' : status,
      };
    },

    getDecision(fieldName) { return this.itemDecisions[fieldName] || { status: 'pending', note: '' }; },
    isActive(fieldName, status) { return this.getDecision(fieldName).status === status; },

    sectionClass(sec) {
      const p = (sec.priority || '').toLowerCase();
      if (p === 'critical') return 'priority-critical';
      if (p === 'high') return 'priority-high';
      return '';
    },

    priorityPillClass(p) {
      const v = (p || '').toLowerCase();
      if (v === 'critical') return 'critical';
      if (v === 'high') return 'high';
      if (v === 'medium') return 'medium';
      return 'low';
    },

    confidenceColor(pct) {
      if (pct >= 75) return 'var(--success)';
      if (pct >= 50) return 'var(--warning)';
      return 'var(--danger)';
    },

    itemClass(fieldName) {
      const s = this.getDecision(fieldName).status;
      if (s === 'approved') return 'approved';
      if (s === 'flagged') return 'flagged';
      if (s === 'rejected') return 'rejected';
      return '';
    },

    async submit() {
      if (!this.canSubmit || this.submitting) return;
      this.submitting = true;
      this.verificationError = null;
      try {
        const payload = {
          run_id: this.runId,
          doctor_name: this.doctorInfo.name,
          doctor_specialty: this.doctorInfo.specialty,
          doctor_license: this.doctorInfo.license,
          institution: this.doctorInfo.institution,
          overall_notes: this.doctorInfo.notes,
          decisions: this.itemDecisions,
        };
        const resp = await fetch(`/api/passport/${this.runId}/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: 'Verification failed' }));
          throw new Error(err.detail || 'Verification failed');
        }
        this.submitted = true;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } catch (e) {
        this.verificationError = e.message;
      } finally {
        this.submitting = false;
      }
    },
  };
}

/* ── Register Alpine.js components globally ──────────────────────── */
document.addEventListener('alpine:init', () => {
  Alpine.data('uploadApp', uploadApp);
});
