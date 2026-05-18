/* ═══════════════════════════════════════════════════════════════════
   MedBridge Ukraine — Upload Page Alpine.js component
   API flow: POST /api/upload/patient → POST /api/upload/files/{id}
             → POST /api/pipeline/run/{id} → redirect /pipeline/{run_id}
   ═══════════════════════════════════════════════════════════════════ */
function uploadApp() {
  return {
    step: 1,
    patient: {
      name: '',
      language: 'uk',
      language_other: '',
      age: '',
      notes: '',
    },
    files: [],           // raw File objects
    fileCategories: [],  // parallel array of category strings
    dragOver: false,
    loading: false,
    loadingMessage: '',
    error: null,

    /* ── Lifecycle ──────────────────────────────────────────────── */
    init() { /* no-op — Alpine calls this automatically */ },

    /* ── Navigation ─────────────────────────────────────────────── */
    nextStep() {
      if (this.step === 1) {
        if (!this.patient.name.trim()) return;
        if (this.patient.language === 'custom' && !this.patient.language_other.trim()) {
          this.error = 'Please specify the patient\u2019s language.';
          return;
        }
        this.error = null;
      }
      this.step = Math.min(3, this.step + 1);
    },

    /* ── File handling ───────────────────────────────────────────── */
    handleDrop(e) {
      this.dragOver = false;
      this.addFiles(Array.from(e.dataTransfer.files));
    },

    handleFileSelect(e) {
      this.addFiles(Array.from(e.target.files));
      // Reset input so the same file can be re-added after removal
      e.target.value = '';
    },

    addFiles(list) {
      const allowed = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
        'image/webp', 'image/bmp', 'image/heic', 'image/heif',
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg',
        'audio/mp4', 'audio/webm', 'audio/aac',
        'application/pdf', 'text/plain',
      ];
      list.forEach(f => {
        // Allow any image/* or audio/* regardless of exact subtype
        if (!allowed.includes(f.type) &&
            !f.type.startsWith('image/') &&
            !f.type.startsWith('audio/')) return;
        // Skip duplicates
        if (this.files.find(x => x.name === f.name && x.size === f.size)) return;
        this.files.push(f);
        this.fileCategories.push(this.guessCategory(f));
      });
      this.$nextTick(() => { if (typeof feather !== 'undefined') feather.replace(); });
    },

    guessCategory(f) {
      if (f.type.startsWith('audio/')) return 'voice_note';
      const n = f.name.toLowerCase();
      if (n.includes('prescript') || n.includes('_rx') || n.includes('-rx')) return 'prescription';
      if (n.includes('discharge') || n.includes('hospital')) return 'other';
      if (n.includes('lab') || n.includes('blood') || n.includes('result')) return 'lab_report';
      if (n.includes('vac') || n.includes('vaccine') || n.includes('immun')) return 'vaccination';
      if (n.includes('strip') || n.includes('medicine') || n.includes('tablet')) return 'medicine_strip';
      return 'other';
    },

    removeFile(idx) {
      this.files.splice(idx, 1);
      this.fileCategories.splice(idx, 1);
    },

    /* ── Display helpers ─────────────────────────────────────────── */
    getFileIcon(type) {
      if (!type) return 'file';
      if (type.startsWith('image/')) return 'image';
      if (type.startsWith('audio/')) return 'mic';
      if (type === 'application/pdf') return 'file-text';
      return 'file';
    },

    getFileIconClass(type) {
      if (!type) return 'icon-other';
      if (type.startsWith('image/')) return 'icon-image';
      if (type.startsWith('audio/')) return 'icon-audio';
      if (type === 'application/pdf') return 'icon-pdf';
      return 'icon-other';
    },

    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1_048_576) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / 1_048_576).toFixed(1) + ' MB';
    },

    /* ── Pipeline launch ─────────────────────────────────────────── */
    async launchPipeline() {
      if (this.loading) return;
      this.loading = true;
      this.error = null;

      try {
        // ── 1. Create patient record ────────────────────────────
        this.loadingMessage = 'Creating patient record…';
        const patientResp = await fetch('/api/upload/patient', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: this.patient.name.trim(),
            language: this.patient.language || 'uk',
            language_other: this.patient.language === 'custom'
              ? (this.patient.language_other || '').trim() || null
              : null,
            age: this.patient.age ? parseInt(this.patient.age, 10) : null,
            additional_notes: this.patient.notes || null,
          }),
        });
        if (!patientResp.ok) {
          const err = await patientResp.json().catch(() => ({ detail: 'Failed to create patient' }));
          throw new Error(err.detail || 'Failed to create patient');
        }
        const patientData = await patientResp.json();
        const patientId = patientData.id;

        // ── 2. Upload evidence files ────────────────────────────
        this.loadingMessage = `Uploading ${this.files.length} file(s)…`;
        const fd = new FormData();
        this.files.forEach(f => fd.append('files', f));
        fd.append('categories', this.fileCategories.join(','));

        const uploadResp = await fetch(`/api/upload/files/${patientId}`, {
          method: 'POST',
          body: fd,
        });
        if (!uploadResp.ok) {
          const err = await uploadResp.json().catch(() => ({ detail: 'File upload failed' }));
          throw new Error(err.detail || 'File upload failed');
        }

        // ── 3. Start AI pipeline ────────────────────────────────
        this.loadingMessage = 'Starting AI analysis pipeline…';
        const pipelineResp = await fetch(`/api/pipeline/run/${patientId}`, {
          method: 'POST',
        });
        if (!pipelineResp.ok) {
          const err = await pipelineResp.json().catch(() => ({ detail: 'Failed to start pipeline' }));
          throw new Error(err.detail || 'Failed to start pipeline');
        }
        const pipelineData = await pipelineResp.json();
        const runId = pipelineData.run_id;

        // ── 4. Redirect to pipeline monitoring page ─────────────
        this.loadingMessage = 'Launching pipeline view…';
        window.location.href = `/pipeline/${runId}`;

      } catch (e) {
        this.error = e.message;
        this.loading = false;
      }
    },
  };
}
