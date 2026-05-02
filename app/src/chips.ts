import type maplibregl from 'maplibre-gl';
import { GRADE_OUTLIER_THRESHOLD, setGradeOutlierThreshold } from './mapLayers';
import { countGradeOutliers } from './mapQueries';

export type StoryChip = {
  id: string;
  title: string;
  hook: string;
  toggleIds: string[];
  camera: maplibregl.FlyToOptions;
  stat: string;
  writeup: string;
  extras?: 'grade-outlier-slider';
};

export const CHIPS: StoryChip[] = [
  {
    id: 'canopy-width',
    title: 'Canopy on Narrow Streets',
    hook: 'Tree cover reduces crashes — but mostly on narrow residential roads.',
    toggleIds: ['toggle-canopy-width'],
    camera: { center: [-75.198, 39.957], zoom: 14.5 },
    stat: 'Narrow residential streets with moderate canopy show ~15–25% fewer crashes than equivalent streets with no canopy.',
    writeup: 'Wide arterial roads are built for speed, and it seems no amount of canopy coverage makes a difference. On narrow residential streets, canopy coverage is a meaningful predictor of safety. Streets that are wide <em>and</em> treeless show the highest crash concentrations.',
  },
  {
    id: 'grade-speed',
    title: 'Grade × Speed',
    hook: 'Steep hills prevent crashes on less-frenetic streets.',
    toggleIds: ['toggle-grade-speed'],
    camera: { center: [-75.221, 40.025], zoom: 14, pitch: 30, bearing: -20 },
    stat: 'On 25 mph streets, 10% grade is associated with ~65% fewer crashes. On 45+ mph arterials, the relationship reverses — grade becomes a hazard.',
    writeup: 'On slow residential streets, it follows that hills are self-calming with drivers naturally breaking on steep grades. But on faster arterials, grade amplifies risk. Possibilities: overall vision and traffic context reduces, stopping distances increase, reaction time compressed. Generally, the consequences of a mistake are more severe. The same slope that makes a Manayunk side street relatively safe makes a fast connector road more dangerous.',
  },
  {
    id: 'method-check',
    title: 'The grade of salt',
    hook: 'The grade calculation is not robust on bridges, ramps, and very short segments.',
    toggleIds: ['toggle-grade'],
    camera: { center: [-75.178, 40.008], zoom: 13.5 },
    stat: 'Some segments show grades above 15% — physically implausible for a drivable city road. Most are measurement artifacts.',
    writeup: 'I calculated grade from LiDAR elevation data and noticed a small but significant number of outliers with impossible grades. Eye-checks revealed these are onramps, bridges, and overpasses. My initial attempts at sampling more points, and introducing smoothing, were not successful in limiting these errors. Use the slider to explore the threshold and see where the calculation goes wrong.',
    extras: 'grade-outlier-slider',
  },
];

export function findChip(id: string | null): StoryChip | undefined {
  return id ? CHIPS.find((chip) => chip.id === id) : undefined;
}

export type SetSidebarMode = (mode: 'idle' | 'pinned' | 'story', payload?: StoryChip) => void;

export function activateChip(chip: StoryChip, map: maplibregl.Map, setSidebarMode: SetSidebarMode) {
  document.querySelectorAll<HTMLInputElement>('#layer-panel input[type=checkbox]').forEach((input) => {
    const should = chip.toggleIds.includes(input.id);
    if (input.checked !== should) {
      input.checked = should;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  map.flyTo({ ...chip.camera, essential: true });
  setSidebarMode('story', chip);
  document.querySelectorAll('.chip').forEach((el) =>
    el.classList.toggle('active', el.getAttribute('data-chip-id') === chip.id)
  );
}

export function renderStoryContent(chip: StoryChip, map: maplibregl.Map) {
  const el = document.getElementById('story-content')!;
  const sliderHtml = chip.extras === 'grade-outlier-slider' ? `
    <div class="outlier-slider-wrap">
      <div class="outlier-slider-label">
        <span>Outlier threshold</span>
        <strong id="slider-val">15%</strong>
      </div>
      <input type="range" class="outlier-slider" id="outlier-threshold-slider"
             min="5" max="30" value="15" step="1">
      <div class="outlier-count" id="outlier-count">Counting…</div>
    </div>` : '';
  el.innerHTML = `
    <div class="story-label">Finding</div>
    <div class="story-title">${chip.title}</div>
    <div class="story-stat">${chip.stat}</div>
    <div class="story-writeup">${chip.writeup}</div>
    ${sliderHtml}`;

  if (chip.extras === 'grade-outlier-slider') {
    const checkbox = document.getElementById('toggle-grade-outliers') as HTMLInputElement | null;
    if (checkbox && !checkbox.checked) {
      checkbox.checked = true;
      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    }
    setupOutlierSlider(map);
  }
}

export function renderChipList(onActivate: (chip: StoryChip) => void) {
  const listEl = document.getElementById('chip-list')!;
  listEl.innerHTML = CHIPS.map((chip) => `
    <button class="chip" data-chip-id="${chip.id}">
      <div class="chip-title">${chip.title}</div>
      <div class="chip-hook">${chip.hook}</div>
    </button>`).join('');
  listEl.querySelectorAll<HTMLButtonElement>('.chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      const chip = findChip(btn.dataset.chipId ?? null);
      if (chip) onActivate(chip);
    });
  });
}

function setupOutlierSlider(map: maplibregl.Map) {
  const slider = document.getElementById('outlier-threshold-slider') as HTMLInputElement | null;
  const valLabel = document.getElementById('slider-val') as HTMLElement | null;
  const countEl = document.getElementById('outlier-count') as HTMLElement | null;
  if (!slider || !valLabel || !countEl) return;

  const valueEl = valLabel;
  const outputEl = countEl;
  let timer: ReturnType<typeof setTimeout> | undefined;
  async function apply(threshold: number) {
    valueEl.textContent = `${threshold}%`;
    const t = threshold / 100;
    setGradeOutlierThreshold(map, t);
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const n = await countGradeOutliers(t);
        outputEl.textContent = `${n.toLocaleString()} segments flagged at ≥${threshold}% grade`;
      } catch {
        outputEl.textContent = '';
      }
    }, 150);
  }
  slider.addEventListener('input', () => apply(Number(slider.value)));
  apply(GRADE_OUTLIER_THRESHOLD * 100);
}
