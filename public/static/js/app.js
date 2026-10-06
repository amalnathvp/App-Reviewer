// App Reviewer - Clean White & Blue Dashboard Logic
// Zero emojis, full PM analytics, version regression & churn tracking

document.addEventListener('DOMContentLoaded', () => {
  // State
  let currentAnalysisData = null;
  let chartInstances = {};

  // Elements
  const searchForm = document.getElementById('search-form');
  const searchInput = document.getElementById('single-app-input');
  const btnSubmit = document.getElementById('btn-submit-analyze');
  const loadingState = document.getElementById('loading-state');
  const resultsView = document.getElementById('results-view');
  const quickTryChips = document.querySelectorAll('.quick-try-chip');

  const detailsTabBtns = document.querySelectorAll('.details-tab-btn');
  const detailsTabPanes = document.querySelectorAll('.details-tab-pane');

  // Quick Try Chips
  quickTryChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const appName = chip.dataset.app;
      searchInput.value = appName;
      triggerAnalysis(appName);
    });
  });

  // Form Submit
  searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = searchInput.value.trim();
    if (!query) {
      alert('Please enter an app name or link.');
      return;
    }
    triggerAnalysis(query);
  });

  // Details Tab Switching
  detailsTabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      detailsTabBtns.forEach(b => b.classList.remove('active'));
      detailsTabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Trigger Analysis
  async function triggerAnalysis(query) {
    btnSubmit.disabled = true;
    loadingState.style.display = 'block';
    resultsView.style.display = 'none';
    loadingState.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
      const response = await fetch('/api/quick-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, review_limit: 80 })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Could not analyze application.');
      }

      const res = await response.json();
      currentAnalysisData = res.analysis;

      setTimeout(() => {
        loadingState.style.display = 'none';
        btnSubmit.disabled = false;
        renderDashboard(currentAnalysisData);
        resultsView.style.display = 'block';
        resultsView.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 400);

    } catch (err) {
      loadingState.style.display = 'none';
      btnSubmit.disabled = false;
      alert('Analysis Error: ' + err.message);
    }
  }

  // Render Full Dashboard
  function renderDashboard(data) {
    if (!data) return;

    const app = data.app_overview || {};
    const quality = data.data_quality || {};
    const sentiment = data.sentiment || {};
    const visual = data.visual_analytics || {};
    const versionAnalysis = data.version_analysis || [];
    const churnAnalysis = data.churn_analysis || {};

    // 1. App Header Banner
    document.getElementById('res-app-title').textContent = app.name || 'Mobile App';
    document.getElementById('res-app-category').textContent = `Category: ${app.category || 'Mobile App'}`;
    document.getElementById('res-app-rating').textContent = `Store Rating: ${app.rating ? app.rating + ' / 5' : 'N/A'}`;
    
    const platformsText = (quality.platforms && quality.platforms.length > 0)
      ? quality.platforms.map(p => p === 'google_play' ? 'Android (Google Play)' : 'iOS (App Store)').join(' & ')
      : 'Mobile Stores';
    document.getElementById('res-app-platforms').textContent = platformsText;
    document.getElementById('res-app-sample-size').textContent = `${quality.reviews_analyzed || 0} Reviews Analyzed`;

    // 2. KPI Summary Boxes
    document.getElementById('kpi-val-rating').textContent = app.rating ? `${app.rating}` : 'N/A';
    document.getElementById('kpi-val-analyzed').textContent = quality.reviews_analyzed || 0;
    document.getElementById('kpi-val-spam').textContent = `${quality.duplicates_removed || 0} duplicates & spam filtered`;

    const pos = sentiment.positive || 0;
    const neg = sentiment.negative || 0;
    document.getElementById('kpi-val-positive').textContent = `${pos}%`;
    document.getElementById('kpi-val-negative').textContent = `Negative: ${neg}% | Mixed: ${sentiment.mixed || 0}%`;

    const problems = data.prioritized_problems || [];
    if (problems.length > 0) {
      document.getElementById('kpi-val-top-issue').textContent = problems[0].problem;
      document.getElementById('kpi-val-top-score').textContent = `Priority Score: ${problems[0].priority_score} (Impact x Freq x Severity)`;
    } else {
      document.getElementById('kpi-val-top-issue').textContent = 'None Detected';
      document.getElementById('kpi-val-top-score').textContent = 'No critical friction';
    }

    // 3. Render Graphs & Charts (Chart.js)
    renderCharts(visual, sentiment);

    // 4. Render App Version Regression Table
    renderVersionTable(versionAnalysis);

    // 5. Render Heatmap Table
    renderHeatmap(visual.heatmap || []);

    // 6. Render Churn & Retention Risk
    renderChurnAnalysis(churnAnalysis);

    // 7. Render Top Problems with Version & Platform Breakdown
    renderProblems(problems);

    // 8. Render What Users Love
    renderPositives(data.positive_feedback || []);

    // 9. Render Mini PRD
    renderPRD(data.prd || {});

    // 10. Render Executive Summary & JSON
    document.getElementById('exec-summary-text').textContent = data.executive_summary || 'Executive summary unavailable.';
    document.getElementById('json-box-code').textContent = JSON.stringify(data, null, 2);
  }

  // Render Chart.js Visuals
  function renderCharts(visual, sentiment) {
    Object.values(chartInstances).forEach(c => c && c.destroy());
    chartInstances = {};

    // Chart 1: Timeline Chart (Line/Area)
    const timelineData = visual.timeline || { labels: ['Recent'], positive: [1], negative: [0], avg_rating: [4.5] };
    const ctxTimeline = document.getElementById('chart-timeline').getContext('2d');
    chartInstances.timeline = new Chart(ctxTimeline, {
      type: 'line',
      data: {
        labels: timelineData.labels,
        datasets: [
          {
            label: 'Positive Reviews',
            data: timelineData.positive,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          },
          {
            label: 'Negative Reviews',
            data: timelineData.negative,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { family: 'Inter', size: 12 } } }
        },
        scales: {
          x: { grid: { color: '#f1f5f9' } },
          y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } }
        }
      }
    });

    // Chart 2: Sentiment Donut
    const ctxSentiment = document.getElementById('chart-sentiment').getContext('2d');
    chartInstances.sentiment = new Chart(ctxSentiment, {
      type: 'doughnut',
      data: {
        labels: ['Positive', 'Negative', 'Mixed', 'Neutral'],
        datasets: [{
          data: [sentiment.positive || 0, sentiment.negative || 0, sentiment.mixed || 0, sentiment.neutral || 0],
          backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#94a3b8'],
          borderWidth: 3,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, font: { family: 'Inter', size: 12 } } }
        }
      }
    });

    // Chart 3: Star Ratings Bar
    const ratingsData = visual.ratings || { labels: ['5 Stars', '4 Stars', '3 Stars', '2 Stars', '1 Star'], counts: [10, 5, 2, 1, 2] };
    const ctxRatings = document.getElementById('chart-ratings').getContext('2d');
    chartInstances.ratings = new Chart(ctxRatings, {
      type: 'bar',
      data: {
        labels: ratingsData.labels,
        datasets: [{
          label: 'Count',
          data: ratingsData.counts,
          backgroundColor: ['#2563eb', '#3b82f6', '#60a5fa', '#f59e0b', '#ef4444'],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } }
        }
      }
    });

    // Chart 4: Priority Leaderboard Bar (Horizontal)
    const probData = visual.problem_chart || { labels: ['Issue 1'], scores: [20] };
    const ctxPriority = document.getElementById('chart-priority').getContext('2d');
    chartInstances.priority = new Chart(ctxPriority, {
      type: 'bar',
      data: {
        labels: probData.labels,
        datasets: [{
          label: 'Priority Score',
          data: probData.scores,
          backgroundColor: probData.scores.map(s => s >= 35 ? '#ef4444' : (s >= 20 ? '#f59e0b' : '#2563eb')),
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: function(context) {
                const idx = context.dataIndex;
                const imp = probData.impacts ? probData.impacts[idx] : 3;
                const frq = probData.frequencies ? probData.frequencies[idx] : 3;
                const sev = probData.severities ? probData.severities[idx] : 3;
                return `Impact: ${imp}/5 | Frequency: ${frq}/5 | Severity: ${sev}/5`;
              }
            }
          }
        },
        scales: {
          x: { beginAtZero: true, grid: { color: '#f1f5f9' } },
          y: { grid: { display: false } }
        }
      }
    });
  }

  // Render Version Regression Table
  function renderVersionTable(versions) {
    const tbody = document.getElementById('version-tbody');
    tbody.innerHTML = '';

    if (!versions || versions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #94a3b8; padding: 1.5rem;">No version metadata detected in reviews.</td></tr>';
      return;
    }

    versions.forEach(v => {
      const tr = document.createElement('tr');
      let statusClass = 'status-healthy';
      if (v.status === 'Regression Alert') statusClass = 'status-alert';
      else if (v.status === 'Degraded') statusClass = 'status-degraded';

      tr.innerHTML = `
        <td style="font-weight: 700; color: #0f172a;">${escapeHtml(v.version)}</td>
        <td><span class="meta-pill">${escapeHtml(v.platform)}</span></td>
        <td style="font-weight: 600;">${v.review_count}</td>
        <td style="font-weight: 700; color: ${v.average_rating < 3.0 ? '#ef4444' : '#2563eb'};">${v.average_rating}</td>
        <td style="color: ${v.negative_percentage > 35 ? '#ef4444' : '#64748b'};">${v.negative_percentage}%</td>
        <td style="font-weight: 500;">${escapeHtml(v.top_friction)}</td>
        <td><span class="status-badge ${statusClass}">${escapeHtml(v.status)}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Render Heatmap Table
  function renderHeatmap(rows) {
    const tbody = document.getElementById('heatmap-tbody');
    tbody.innerHTML = '';

    if (!rows || rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #94a3b8; padding: 1.5rem;">Insufficient data for heatmap.</td></tr>';
      return;
    }

    rows.forEach(r => {
      const tr = document.createElement('tr');
      let cellsHtml = `<td>${escapeHtml(r.theme)}</td>`;
      r.cells.forEach(val => {
        let heatClass = 'heat-0';
        if (val >= 6) heatClass = 'heat-5';
        else if (val >= 4) heatClass = 'heat-4';
        else if (val >= 3) heatClass = 'heat-3';
        else if (val >= 2) heatClass = 'heat-2';
        else if (val >= 1) heatClass = 'heat-1';

        cellsHtml += `<td class="${heatClass}">${val > 0 ? val : '-'}</td>`;
      });
      tr.innerHTML = cellsHtml;
      tbody.appendChild(tr);
    });
  }

  // Render Churn & Retention Analysis
  function renderChurnAnalysis(churn) {
    const churnLevelEl = document.getElementById('churn-level-text');
    const churnStatEl = document.getElementById('churn-stat-desc');
    const compEl = document.getElementById('competitors-list-wrapper');
    const cohortEl = document.getElementById('cohort-breakdown-wrapper');

    const level = churn.churn_risk_level || 'Low Risk';
    churnLevelEl.textContent = level;
    if (level.includes('Critical')) churnLevelEl.style.color = 'var(--rose)';
    else if (level.includes('Moderate')) churnLevelEl.style.color = 'var(--amber)';
    else churnLevelEl.style.color = 'var(--emerald)';

    churnStatEl.textContent = `${churn.churn_threat_count || 0} reviews (${churn.churn_percentage || 0}%) threaten uninstallation or account cancellation.`;

    // Competitors
    const comps = churn.competitor_mentions || {};
    const compKeys = Object.keys(comps);
    if (compKeys.length > 0) {
      compEl.innerHTML = compKeys.map(k => `<span class="competitor-pill">${escapeHtml(k)} (${comps[k]} mentions)</span>`).join(' ');
    } else {
      compEl.innerHTML = '<span style="font-size: 0.85rem; color: #94a3b8;">No competitor migrations mentioned.</span>';
    }

    // Cohorts
    const cohorts = churn.cohort_breakdown || {};
    cohortEl.innerHTML = `
      <div style="margin-bottom: 0.45rem;">
        <strong>Long-term Users:</strong> ${cohorts.long_term_users?.count || 0} mentions (${cohorts.long_term_users?.percentage || 0}%)
        <div style="font-size: 0.78rem; color: #64748b;">${escapeHtml(cohorts.long_term_users?.sentiment || '')}</div>
      </div>
      <div style="margin-bottom: 0.45rem;">
        <strong>New Onboarding Users:</strong> ${cohorts.new_users?.count || 0} mentions (${cohorts.new_users?.percentage || 0}%)
        <div style="font-size: 0.78rem; color: #64748b;">${escapeHtml(cohorts.new_users?.sentiment || '')}</div>
      </div>
      <div>
        <strong>Paying Subscribers:</strong> ${cohorts.paying_subscribers?.count || 0} mentions (${cohorts.paying_subscribers?.percentage || 0}%)
        <div style="font-size: 0.78rem; color: #64748b;">${escapeHtml(cohorts.paying_subscribers?.sentiment || '')}</div>
      </div>
    `;
  }

  // Render Top Problems with Affected Versions
  function renderProblems(problems) {
    const grid = document.getElementById('top-problems-grid');
    grid.innerHTML = '';

    if (!problems || problems.length === 0) {
      grid.innerHTML = '<div style="color: #64748b; padding: 1.5rem;">No critical friction issues found.</div>';
      return;
    }

    problems.slice(0, 4).forEach((p, idx) => {
      const card = document.createElement('div');
      const isUrgent = p.priority_score >= 25;
      card.className = `action-card ${isUrgent ? 'urgent' : 'quick-win'}`;

      const quote = (p.evidence && p.evidence.length > 0) ? p.evidence[0] : '';
      const versionsList = (p.affected_versions && p.affected_versions.length > 0)
        ? p.affected_versions.map(v => `<span class="version-chip">${escapeHtml(v)}</span>`).join(' ')
        : '<span class="version-chip">All Versions</span>';

      const platformsMap = p.platform_breakdown || {};
      const platformsStr = Object.keys(platformsMap).map(k => `${k}: ${platformsMap[k]}`).join(', ');

      card.innerHTML = `
        <div class="card-top-badges">
          <span class="action-tag ${isUrgent ? 'tag-urgent' : 'tag-quick'}">
            ${isUrgent ? 'Urgent Blocker' : 'High Priority'} • Priority Score: ${p.priority_score}
          </span>
          <span style="font-size: 0.75rem; font-weight: 700; color: ${p.churn_risk === 'High Risk' ? 'var(--rose)' : 'var(--text-muted)'};">
            ${escapeHtml(p.churn_risk || 'Low Risk')}
          </span>
        </div>

        <h5>#${idx + 1} ${escapeHtml(p.problem)}</h5>
        <p>${escapeHtml(p.description)}</p>

        <div style="margin-bottom: 0.75rem;">
          <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.3rem;">
            Affected Versions:
          </div>
          <div>${versionsList}</div>
          ${platformsStr ? `<div style="font-size: 0.75rem; color: #64748b; margin-top: 0.3rem;">Platform breakdown: ${escapeHtml(platformsStr)}</div>` : ''}
        </div>

        <div class="solution-box">
          <strong>Recommended Engineering Fix:</strong> ${escapeHtml(p.possible_root_cause)}
          <div style="font-size: 0.75rem; font-weight: 700; margin-top: 0.3rem; color: var(--blue-primary);">
            Verdict: ${escapeHtml(p.release_verdict || 'Triage for next release')}
          </div>
        </div>

        ${quote ? `<div class="evidence-quote">${escapeHtml(quote)}</div>` : ''}
      `;
      grid.appendChild(card);
    });
  }

  // Render Positive Delighters
  function renderPositives(positives) {
    const grid = document.getElementById('top-positives-grid');
    grid.innerHTML = '';

    if (!positives || positives.length === 0) {
      grid.innerHTML = '<div style="color: #64748b; padding: 1.5rem;">No specific strengths recorded.</div>';
      return;
    }

    positives.slice(0, 4).forEach(p => {
      const card = document.createElement('div');
      card.className = 'action-card positive';
      const quote = (p.evidence && p.evidence.length > 0) ? p.evidence[0] : '';

      card.innerHTML = `
        <span class="action-tag tag-positive">Key Strength (${p.mentions} mentions)</span>
        <h5 style="color: #065f46;">${escapeHtml(p.theme)}</h5>
        <p>${escapeHtml(p.sentiment_drivers)}</p>
        ${quote ? `<div class="evidence-quote" style="border-left-color: #10b981;">${escapeHtml(quote)}</div>` : ''}
      `;
      grid.appendChild(card);
    });
  }

  // Render Mini PRD
  function renderPRD(prd) {
    const view = document.getElementById('prd-details-view');
    const funcList = (prd.functional_requirements || []).map(r => `<li>${escapeHtml(r)}</li>`).join('');
    const metricsList = (prd.success_metrics || []).map(m => `<li><strong>${escapeHtml(m.metric)}</strong>: Target ${escapeHtml(m.target)} (Baseline: ${escapeHtml(m.baseline)})</li>`).join('');

    view.innerHTML = `
      <h4>${escapeHtml(prd.product_feature_name || 'Experience Stabilization Feature')}</h4>
      <p>${escapeHtml(prd.problem_statement || 'User-reported friction resolution.')}</p>

      <div class="prd-block">
        <h6>Target Audience & Need</h6>
        <p><strong>Target Users:</strong> ${escapeHtml(prd.target_users || 'Mobile app users')}</p>
        <p><strong>Core Need:</strong> ${escapeHtml(prd.user_need || 'Reliable execution without interruptions')}</p>
      </div>

      <div class="prd-block">
        <h6>Goals & Impact</h6>
        <p><strong>Product Goal:</strong> ${escapeHtml(prd.product_goal || '')}</p>
        <p><strong>Business Goal:</strong> ${escapeHtml(prd.business_goal || '')}</p>
      </div>

      <div class="prd-block">
        <h6>Functional Requirements</h6>
        <ul>${funcList}</ul>
      </div>

      <div class="prd-block">
        <h6>Success Metrics</h6>
        <ul>${metricsList}</ul>
      </div>

      <div class="prd-block">
        <h6>Suggested MVP Scope</h6>
        <p>${escapeHtml(prd.mvp_scope || 'Targeted bug fixes and client-side error telemetry.')}</p>
      </div>
    `;
  }

  // Copy & Download JSON
  document.getElementById('btn-copy-json').addEventListener('click', () => {
    if (!currentAnalysisData) return;
    navigator.clipboard.writeText(JSON.stringify(currentAnalysisData, null, 2)).then(() => {
      alert('Analysis JSON copied to clipboard.');
    });
  });

  document.getElementById('btn-download-json').addEventListener('click', () => {
    if (!currentAnalysisData) return;
    const blob = new Blob([JSON.stringify(currentAnalysisData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `app_reviewer_analysis_${(currentAnalysisData.app_overview?.name || 'app').toLowerCase().replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
