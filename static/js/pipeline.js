/* ═══════════════════════════════════════════════════════════════════
   MedBridge Ukraine — Pipeline Page Alpine.js component
   Connects to SSE stream at /api/pipeline/{run_id}/stream and renders
   live agent-card progress.
   ═══════════════════════════════════════════════════════════════════ */
function pipelineApp(runId) {
  return {
    runId,
    overallStatus: 'running',  // 'running' | 'done' | 'error'
    errorMessage: '',
    events: [],
    es: null,

    /* ── Agent definitions (steps 1-7 from graph.py _AGENT_META) ── */
    agents: [
      {
        step: 1, key: 'MultimodalAnalysis',
        label: 'Multimodal Analysis',
        description: 'Processing images, audio & documents with Gemma 4',
        icon: 'eye', color: '#1A73E8',
        status: 'pending', currentTool: null, outputPreview: null,
      },
      {
        step: 2, key: 'MedicalStructuring',
        label: 'Medical Structuring',
        description: 'Extracting medications, conditions, allergies & vaccinations',
        icon: 'package', color: '#8B5CF6',
        status: 'pending', currentTool: null, outputPreview: null,
      },
      {
        step: 3, key: 'TimelineReconstruction',
        label: 'Timeline Reconstruction',
        description: 'Building chronological medical history from evidence',
        icon: 'clock', color: '#06B6D4',
        status: 'pending', currentTool: null, outputPreview: null,
      },
      {
        step: 4, key: 'RiskAnalysis',
        label: 'Risk & Uncertainty',
        description: 'Flagging critical risks and confidence gaps',
        icon: 'alert-triangle', color: '#F59E0B',
        status: 'pending', currentTool: null, outputPreview: null,
      },
      {
        step: 5, key: 'VerificationPrep',
        label: 'Verification Prep',
        description: 'Generating clinician review checklist for each claim',
        icon: 'clipboard', color: '#10B981',
        status: 'pending', currentTool: null, outputPreview: null,
      },
      {
        step: 6, key: 'HumanApproval',
        label: 'Approval Gate',
        description: 'Checking verification requirements and human approval status',
        icon: 'user-check', color: '#6B7280',
        status: 'pending', currentTool: null, outputPreview: null,
      },
      {
        step: 7, key: 'PassportGeneration',
        label: 'Passport Generation',
        description: 'Creating multilingual Emergency Medical Passport',
        icon: 'file-text', color: '#EF4444',
        status: 'pending', currentTool: null, outputPreview: null,
      },
    ],

    /* ── Computed ────────────────────────────────────────────────── */
    get completedSteps() {
      return this.agents.filter(a => a.status === 'done').length;
    },

    progressPct() {
      const done = this.agents.filter(a => a.status === 'done').length;
      const running = this.agents.filter(a => a.status === 'running').length;
      return Math.min(100, Math.round((done + running * 0.5) / this.agents.length * 100));
    },

    statusLabel() {
      if (this.overallStatus === 'done') return 'Pipeline Complete!';
      if (this.overallStatus === 'error') return 'Pipeline Failed';
      return 'Processing…';
    },

    statusIcon() {
      if (this.overallStatus === 'done') return 'check-circle';
      if (this.overallStatus === 'error') return 'alert-circle';
      return 'activity';
    },

    /* ── Lifecycle ───────────────────────────────────────────────── */
    async init() {
      // Check if pipeline already finished before connecting SSE
      try {
        const resp = await fetch(`/api/pipeline/${this.runId}/status`);
        if (resp.ok) {
          const data = await resp.json();
          if (data.status === 'completed') {
            this.overallStatus = 'done';
            this.agents = this.agents.map(a => ({ ...a, status: 'done' }));
            this.$nextTick(() => { if (typeof feather !== 'undefined') feather.replace(); });
            return;
          }
          if (data.status === 'failed') {
            this.overallStatus = 'error';
            this.errorMessage = data.error || 'Pipeline failed';
            this.$nextTick(() => { if (typeof feather !== 'undefined') feather.replace(); });
            return;
          }
        }
      } catch { /* fall through to SSE */ }

      this.connectSSE();
    },

    destroy() {
      if (this.es) this.es.close();
    },

    /* ── SSE connection ──────────────────────────────────────────── */
    connectSSE() {
      this.es = new EventSource(`/api/pipeline/${this.runId}/stream`);

      this.es.onmessage = (e) => {
        try {
          this.handleEvent(JSON.parse(e.data));
        } catch { /* ignore malformed events */ }
      };

      this.es.onerror = () => {
        if (this.overallStatus === 'running') {
          this.es.close();
          this.pollStatus();
        }
      };
    },

    /* ── Event handler ───────────────────────────────────────────── */
    handleEvent(event) {
      const time = new Date().toLocaleTimeString('en', {
        hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
      });

      if (event.type !== 'heartbeat') {
        this.events.push({ ...event, time });
        if (this.events.length > 200) this.events = this.events.slice(-200);
      }

      const step = event.step;
      const agentIdx = this.agents.findIndex(a => a.step === step);

      if (event.type === 'agent_start' && agentIdx >= 0) {
        // Make reactive by replacing the whole object
        this.agents[agentIdx] = { ...this.agents[agentIdx], status: 'running' };

      } else if (event.type === 'agent_done' && agentIdx >= 0) {
        this.agents[agentIdx] = {
          ...this.agents[agentIdx],
          status: 'done',
          currentTool: null,
          outputPreview: event.summary || null,
        };

      } else if (event.type === 'pipeline_done' || event.type === 'pipeline_complete') {
        this.overallStatus = 'done';
        if (this.es) this.es.close();

      } else if (event.type === 'pipeline_error') {
        this.overallStatus = 'error';
        this.errorMessage = event.error || event.message || 'Unknown error';
        if (this.es) this.es.close();
      }

      // Re-render feather icons after DOM updates
      this.$nextTick(() => {
        if (typeof feather !== 'undefined') {
          try { feather.replace(); } catch { /* ignore icon re-render errors */ }
        }
      });
    },

    /* ── Polling fallback ────────────────────────────────────────── */
    async pollStatus() {
      let attempts = 0;
      const poll = async () => {
        if (this.overallStatus !== 'running' || attempts > 60) return;
        attempts++;
        try {
          const resp = await fetch(`/api/pipeline/${this.runId}/status`);
          if (resp.ok) {
            const data = await resp.json();
            if (data.status === 'completed') {
              this.overallStatus = 'done';
              this.agents = this.agents.map(a => ({ ...a, status: 'done' }));
              this.$nextTick(() => { if (typeof feather !== 'undefined') feather.replace(); });
              return;
            }
            if (data.status === 'failed') {
              this.overallStatus = 'error';
              this.errorMessage = data.error || 'Pipeline failed';
              this.$nextTick(() => { if (typeof feather !== 'undefined') feather.replace(); });
              return;
            }
          }
        } catch { /* ignore transient errors */ }
        setTimeout(poll, 3000);
      };
      await poll();
    },

    /* ── UI helpers ──────────────────────────────────────────────── */
    clearEvents() {
      this.events = [];
    },

    formatEventMessage(evt) {
      const t = evt.type || '';
      if (t === 'agent_start') return `▶ Starting: ${evt.agent_label || evt.agent || ''}`;
      if (t === 'agent_done') return `✓ Done: ${evt.summary || evt.agent_label || evt.agent || ''}`;
      if (t === 'pipeline_done' || t === 'pipeline_complete') return '🎉 Pipeline complete — passport ready!';
      if (t === 'pipeline_error') return `✗ Error: ${evt.error || evt.message || ''}`;
      if (t === 'heartbeat') return '· heartbeat';
      return evt.message || evt.description || JSON.stringify(evt).slice(0, 80);
    },
  };
}
