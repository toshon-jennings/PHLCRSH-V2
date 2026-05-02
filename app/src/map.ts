import maplibregl from 'maplibre-gl';
import {
  activateChip,
  findChip,
  renderChipList,
  renderStoryContent,
  type StoryChip,
} from './chips';
import {
  loadBlockGroupFeatures,
  loadBlockGroupPeerComparison,
  loadSegmentFeatures,
  type SegmentProperties,
} from './mapQueries';
import {
  BLOCK_GROUP_LAYER_GROUP,
  INTERACTION_LAYER_GROUP,
  LEGENDS,
  SEGMENT_LAYER_GROUP,
  addMapSourcesAndLayers,
  clearGradeOutliers,
  setGradeOutlierVisibility,
  type LayerGroup,
} from './mapLayers';

function segmentPopupHTML(p: Partial<SegmentProperties>) {
  const row = (label: string, value: string) =>
    `<div class="seg-row"><span>${label}</span><strong>${value}</strong></div>`;
  const canopy = p.canopy_pct != null ? `${(p.canopy_pct * 100).toFixed(0)}%` : '—';
  const width = p.cartway_width_ft != null ? `${(+p.cartway_width_ft).toFixed(0)} ft` : '—';
  const grade = p.grade_range_smooth != null ? `${(p.grade_range_smooth * 100).toFixed(1)}%` : '—';
  const speed = p.maxspeed_final != null ? `${(+p.maxspeed_final).toFixed(0)} mph` : '—';
  return `<div class="seg-popup">
    ${row('Crashes', String(p.crash_count ?? '—'))}
    ${row('Canopy', canopy)}
    ${row('Grade', grade)}
    ${row('Speed', speed)}
    ${row('Width', width)}
  </div>`;
}

export async function initMap(container: string) {
  const map = new maplibregl.Map({
    container,
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center: [-75.1652, 39.9526],
    zoom: 11,
  });

  await map.once('load');

  const [segmentFeatures, blockGroupFeatures] = await Promise.all([
    loadSegmentFeatures(),
    loadBlockGroupFeatures(),
  ]);
  addMapSourcesAndLayers(map, segmentFeatures, blockGroupFeatures);

  let hoveredId: number | string | null = null;
  let pinnedSegId: number | string | null = null;
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });

  map.on('mousemove', 'segments-hit', (e) => {
    if (!e.features?.length) return;
    map.getCanvas().style.cursor = 'pointer';

    const id = e.features[0].id as number | string;
    if (hoveredId !== null && hoveredId !== id) {
      map.setFeatureState({ source: 'segments', id: hoveredId }, { hover: false });
    }
    hoveredId = id;
    map.setFeatureState({ source: 'segments', id }, { hover: true });

    if (id === pinnedSegId) {
      popup.remove();
      return;
    }
    const p = e.features[0].properties as Partial<SegmentProperties>;
    popup.setLngLat(e.lngLat).setHTML(segmentPopupHTML(p)).addTo(map);
  });

  map.on('mouseleave', 'segments-hit', () => {
    map.getCanvas().style.cursor = '';
    if (hoveredId !== null) {
      map.setFeatureState({ source: 'segments', id: hoveredId }, { hover: false });
      hoveredId = null;
    }
    popup.remove();
  });

  const legendColorClass = (color: string) => `legend-color-${color.replace('#', '').toLowerCase()}`;

  function renderLegend(container: HTMLElement, layerId: string | null) {
    if (!layerId || !LEGENDS[layerId]) {
      container.innerHTML = '';
      container.classList.remove('visible');
      return;
    }
    const legend = LEGENDS[layerId];
    let body = '';
    if (legend.kind === 'steps') {
      body = `
        <div class="legend-steps">
          ${legend.stops.map((s) => `<div class="${legendColorClass(s.color)}"></div>`).join('')}
        </div>
        <div class="legend-labels">
          ${legend.stops.map((s) => `<span>${s.label}</span>`).join('')}
        </div>`;
    } else {
      const [tl, tr, bl, br] = legend.cells;
      body = `
        <div class="biv-legend">
          <span class="biv-y-hi">${legend.yHi}</span>
          <div class="biv-row">
            <div class="${legendColorClass(tl)}"></div><div class="${legendColorClass(tr)}"></div>
          </div>
          <span class="biv-y-lo">${legend.yLo}</span>
          <div class="biv-row">
            <div class="${legendColorClass(bl)}"></div><div class="${legendColorClass(br)}"></div>
          </div>
          <span class="biv-y-axis">${legend.yLabel}</span>
          <div class="biv-x-axis">
            <span>${legend.xLo}</span>
            <span class="biv-x-name">${legend.xLabel}</span>
            <span>${legend.xHi}</span>
          </div>
        </div>`;
    }
    const extras = layerId === 'grade' ? `
      <label class="outlier-check">
        <input type="checkbox" id="toggle-grade-outliers">
        <span>Highlight outliers &gt;15%</span>
      </label>` : '';
    container.innerHTML = body + extras;
    container.classList.add('visible');
  }

  function setupGroup(group: LayerGroup, onDeactivate?: Partial<Record<string, () => void>>) {
    const setVisible = (layerId: string, visible: boolean) =>
      map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');

    group.forEach(({ toggleId, layerId, legendId }) => {
      const el = document.getElementById(toggleId) as HTMLInputElement | null;
      const legendEl = document.getElementById(legendId)!;
      if (el && !el.checked) {
        setVisible(layerId, false);
      } else if (el?.checked) {
        renderLegend(legendEl, layerId);
      }
    });

    group.forEach(({ toggleId, layerId, legendId }) => {
      const legendEl = document.getElementById(legendId)!;
      document.getElementById(toggleId)?.addEventListener('change', (e) => {
        const checked = (e.target as HTMLInputElement).checked;
        if (checked) {
          group.forEach((item) => {
            if (item.toggleId !== toggleId) {
              setVisible(item.layerId, false);
              onDeactivate?.[item.layerId]?.();
              const other = document.getElementById(item.toggleId) as HTMLInputElement | null;
              if (other) other.checked = false;
              renderLegend(document.getElementById(item.legendId)!, null);
            }
          });
          setVisible(layerId, true);
          renderLegend(legendEl, layerId);
        } else {
          setVisible(layerId, false);
          onDeactivate?.[layerId]?.();
          renderLegend(legendEl, null);
        }
      });
    });
  }

  setupGroup(SEGMENT_LAYER_GROUP, { grade: () => clearGradeOutliers(map) });

  document.getElementById('legend-grade')!.addEventListener('change', (e) => {
    const target = e.target as HTMLInputElement;
    if (target.id === 'toggle-grade-outliers') {
      setGradeOutlierVisibility(map, target.checked);
    }
  });

  setupGroup(INTERACTION_LAYER_GROUP);
  setupGroup(BLOCK_GROUP_LAYER_GROUP);

  function setupCollapsiblePanels() {
    const resizeMapAfterPanelMotion = () => {
      requestAnimationFrame(() => map.resize());
      window.setTimeout(() => map.resize(), 240);
    };

    const setupPanelToggle = (
      panelId: string,
      toggleId: string,
      expandedIcon: string,
      collapsedIcon: string,
      labels: { expand: string; collapse: string },
      onChange?: () => void,
    ) => {
      const panel = document.getElementById(panelId);
      const toggle = document.getElementById(toggleId) as HTMLButtonElement | null;
      const icon = toggle?.querySelector<HTMLElement>('.panel-collapse-icon');
      if (!panel || !toggle) return;

      const sync = () => {
        const expanded = !panel.classList.contains('is-collapsed');
        toggle.setAttribute('aria-expanded', String(expanded));
        toggle.setAttribute('aria-label', expanded ? labels.collapse : labels.expand);
        if (icon) icon.textContent = expanded ? expandedIcon : collapsedIcon;
      };

      toggle.addEventListener('click', () => {
        panel.classList.toggle('is-collapsed');
        sync();
        onChange?.();
      });
      sync();
    };

    setupPanelToggle(
      'sidebar',
      'sidebar-toggle',
      '‹',
      '›',
      { expand: 'Expand sidebar', collapse: 'Collapse sidebar' },
      resizeMapAfterPanelMotion,
    );

    setupPanelToggle(
      'layer-panel',
      'layer-panel-toggle',
      '›',
      '‹',
      { expand: 'Expand layers panel', collapse: 'Collapse layers panel' },
    );

    document.querySelectorAll<HTMLButtonElement>('.panel-section-toggle').forEach((toggle) => {
      const section = toggle.closest('.panel-section') as HTMLElement | null;
      if (!section) return;
      const label = toggle.querySelector('span:not(.section-toggle-icon)')?.textContent?.trim() || 'section';

      const sync = () => {
        const expanded = !section.classList.contains('is-collapsed');
        toggle.setAttribute('aria-expanded', String(expanded));
        toggle.setAttribute('aria-label', `${expanded ? 'Collapse' : 'Expand'} ${label}`);
      };

      toggle.addEventListener('click', () => {
        section.classList.toggle('is-collapsed');
        sync();
      });
      sync();
    });
  }

  let activeChipId: string | null = null;

  function setSidebarMode(mode: 'idle' | 'pinned' | 'story', payload?: StoryChip) {
    const sidebar = document.getElementById('sidebar')!;
    const hasChip = mode === 'story' ? true : !!activeChipId;
    const collapsedClass = sidebar.classList.contains('is-collapsed') ? ' is-collapsed' : '';
    sidebar.className = `mode-${mode}${hasChip ? ' has-active-chip' : ''}${collapsedClass}`;
    if (mode === 'story' && payload) {
      activeChipId = payload.id;
      sidebar.className = `mode-story has-active-chip${collapsedClass}`;
      renderStoryContent(payload, map);
    }
  }

  function unpin() {
    if (pinnedSegId !== null) {
      map.setFeatureState({ source: 'segments', id: pinnedSegId }, { pinned: false });
      pinnedSegId = null;
    }
    const chip = findChip(activeChipId);
    if (chip) {
      setSidebarMode('story', chip);
    } else {
      setSidebarMode('idle');
    }
  }

  document.getElementById('sidebar-back-story')!.addEventListener('click', unpin);

  document.getElementById('sidebar-back-idle')!.addEventListener('click', () => {
    activeChipId = null;
    document.querySelectorAll('.chip').forEach((el) => el.classList.remove('active'));
    setSidebarMode('idle');
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') unpin();
  });

  map.on('click', (e) => {
    const hit = map.queryRenderedFeatures(e.point, { layers: ['segments-hit'] });
    if (!hit.length && pinnedSegId !== null) unpin();
  });

  map.on('click', 'segments-hit', (e) => {
    if (!e.features?.length) return;
    const id = e.features[0].id as number | string;
    const props = e.features[0].properties as unknown as SegmentProperties;
    if (pinnedSegId !== null && pinnedSegId !== id) {
      map.setFeatureState({ source: 'segments', id: pinnedSegId }, { pinned: false });
    }
    pinnedSegId = id;
    map.setFeatureState({ source: 'segments', id }, { pinned: true });
    setSidebarMode('pinned');
    renderPinnedStats(props);
    runPeerQuery(props);
  });

  function renderPinnedStats(p: SegmentProperties) {
    const content = document.getElementById('pinned-content')!;
    const streetName = [p.st_name, p.st_type].filter(Boolean).join(' ') || 'Unknown segment';
    const fmt = (v: any, suffix: string, dec = 0) =>
      v != null && !isNaN(+v) ? `${(+v).toFixed(dec)}${suffix}` : '—';

    const delta = (p.cartway_width_ft != null && p.state_total_width_ft != null)
      ? +p.cartway_width_ft - +p.state_total_width_ft : null;
    const deltaStr = delta != null
      ? `${delta >= 0 ? '+' : ''}${delta.toFixed(1)} ft vs state` : null;
    const deltaCls = delta != null && Math.abs(delta) > 3 ? (delta > 0 ? ' warn' : ' good') : '';

    const rows: [string, string, string][] = [
      ['Crashes', fmt(p.crash_count, ''), ''],
      ['Canopy', fmt(p.canopy_pct != null ? p.canopy_pct * 100 : null, '%'), ''],
      ['Grade', fmt(p.grade_range_smooth != null ? p.grade_range_smooth * 100 : null, '%', 1), ''],
      ['Speed', fmt(p.maxspeed_final, ' mph'), ''],
      ['Width (calc.)', fmt(p.cartway_width_ft, ' ft'), ''],
    ];
    if (deltaStr) rows.push([
      'Width (state)',
      `${fmt(p.state_total_width_ft, ' ft')} <small class="stat-note">${deltaStr}</small>`,
      deltaCls,
    ]);
    if (p.state_lane_cnt != null) rows.push(['State lanes', String(p.state_lane_cnt), '']);
    if (p.state_divisor_type && p.state_divisor_type !== 'null') {
      rows.push(['Divider', p.state_divisor_type, '']);
    }

    content.innerHTML = `
      <div class="pinned-street">
        <div class="pinned-street-name">${streetName}</div>
      </div>
      ${rows.map(([label, val, cls]) =>
        `<div class="stat-row${cls}"><span>${label}</span><strong>${val}</strong></div>`
      ).join('')}
      <div class="peer-comparison" id="peer-comparison">
        <h4>Loading block-group context…</h4>
      </div>`;
  }

  async function runPeerQuery(p: SegmentProperties) {
    const peerEl = document.getElementById('peer-comparison');
    if (!peerEl) return;

    try {
      const comparison = await loadBlockGroupPeerComparison(p);
      if (!comparison) {
        peerEl.innerHTML = '<h4>No block group data for this segment.</h4>';
        return;
      }

      const pctile = comparison.crashPctile != null ? Math.round(comparison.crashPctile * 100) : null;
      const medCrash = comparison.bgMedianCrash != null ? comparison.bgMedianCrash.toFixed(0) : '—';
      const medCanopy = comparison.bgMedianCanopy != null
        ? `${(comparison.bgMedianCanopy * 100).toFixed(0)}%`
        : '—';

      peerEl.innerHTML = `
        <h4>Block group (${comparison.peerN} segments)</h4>
        <div class="stat-row">
          <span>Crashes — block-group median</span>
          <strong>${medCrash}${pctile != null ? ` <small class="stat-note">(this: ${pctile}th pctile)</small>` : ''}</strong>
        </div>
        <div class="stat-row">
          <span>Canopy — block-group median</span>
          <strong>${medCanopy}</strong>
        </div>
        <details class="sql-details">
          <summary>View DuckDB query</summary>
          <pre>${comparison.sql}</pre>
        </details>`;
    } catch (err) {
      peerEl.innerHTML = '<h4>Query failed.</h4>';
      console.error(err);
    }
  }

  renderChipList((chip) => activateChip(chip, map, setSidebarMode));
  setupCollapsiblePanels();

  return map;
}
