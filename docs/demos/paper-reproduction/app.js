const stages = [...document.querySelectorAll('.story-stage')];
const steps = [...document.querySelectorAll('.step')];
const trackFill = document.getElementById('trackFill');
const currentStageLabel = document.getElementById('currentStageLabel');

const chartData = {
  length: [
    [50, .078510], [100, .117461], [150, .141069], [200, .152887],
    [250, .159100], [300, .162019], [350, .163108], [400, .162928], [450, .162688]
  ],
  loading: [[0, .162019], [10, .163122], [20, .165009], [50, .169114], [75, .174462], [100, .170191], [150, .111233]]
};

const figures = {
  fig3: {
    title: 'Length dependence of B1+, 10 g SAR, and SAR efficiency',
    eyebrow: 'GEOMETRY STUDY · SOURCE FIGURE 3',
    description: 'Accepted-power-normalized B1+ depth profiles, longitudinal 10 g SAR distributions, and the B1+/√SAR metric reproduce the reported transition toward a broad geometry plateau.',
    reproduction: 'assets/Fig3_reproduction.png',
    comparison: 'assets/Fig3_paper_comparison.png',
    alt: 'Figure 3 length-sweep reproduction'
  },
  fig4: {
    title: 'Series-reactance dependence of B1+, 10 g SAR, and SAR efficiency',
    eyebrow: 'REACTIVE-LOADING STUDY · SOURCE FIGURE 4',
    description: 'The favorable 75–100 nH region agrees with the publication, whereas the 150 nH B1+/√SAR degradation has the same direction but a substantially larger magnitude.',
    reproduction: 'assets/Fig4_reproduction.png',
    comparison: 'assets/Fig4_paper_comparison.png',
    alt: 'Figure 4 reactive-loading reproduction'
  }
};

let activeFigure = 'fig3';
let showingComparison = false;

function setActiveStage(index) {
  steps.forEach((step, i) => {
    step.classList.toggle('active', i === index);
    step.classList.toggle('completed', i < index);
  });
  trackFill.style.transform = `scaleX(${index / (steps.length - 1)})`;
  currentStageLabel.textContent = stages[index].dataset.label;
}

let scrollFramePending = false;
function syncStageToScroll() {
  const marker = document.getElementById('progressShell').offsetHeight + window.innerHeight * .32;
  let activeIndex = 0;
  stages.forEach((stage, index) => {
    if (stage.getBoundingClientRect().top <= marker) activeIndex = index;
  });
  setActiveStage(activeIndex);
  scrollFramePending = false;
}
window.addEventListener('scroll', () => {
  if (scrollFramePending) return;
  scrollFramePending = true;
  requestAnimationFrame(syncStageToScroll);
}, { passive: true });

stages.forEach(stage => {
  const button = stage.querySelector('.reveal-button');
  button.addEventListener('click', () => {
    const revealed = stage.classList.toggle('revealed');
    button.setAttribute('aria-expanded', String(revealed));
    const stageIndex = Number(stage.dataset.stage);
    if (revealed && stageIndex < stages.length - 1) {
      steps[stageIndex].classList.add('completed');
    }
  });
});
syncStageToScroll();

steps.forEach(step => step.addEventListener('click', () => {
  document.getElementById(step.dataset.target).scrollIntoView({ behavior: 'smooth', block: 'start' });
}));

function renderLineChart(targetId, values, options = {}) {
  const target = document.getElementById(targetId);
  const color = options.color || '#7187a5';
  const gradientId = `areaGradient-${targetId}`;
  const width = 560;
  const height = 250;
  const pad = { left: 47, right: 16, top: 18, bottom: 35 };
  const xs = values.map(d => d[0]);
  const ys = values.map(d => d[1]);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = options.yMin ?? Math.min(...ys) * .92;
  const yMax = options.yMax ?? Math.max(...ys) * 1.06;
  const x = value => pad.left + ((value - xMin) / (xMax - xMin)) * (width - pad.left - pad.right);
  const y = value => height - pad.bottom - ((value - yMin) / (yMax - yMin)) * (height - pad.top - pad.bottom);
  const points = values.map(d => `${x(d[0]).toFixed(1)},${y(d[1]).toFixed(1)}`).join(' ');
  const areaPoints = `${x(values[0][0])},${height - pad.bottom} ${points} ${x(values.at(-1)[0])},${height - pad.bottom}`;
  const yTicks = [yMin, (yMin + yMax) / 2, yMax];
  const labelEvery = options.labelEvery || 1;
  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" style="--chart-color:${color}">
      <defs><linearGradient id="${gradientId}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".22"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
      ${yTicks.map(t => `<line class="gridline" x1="${pad.left}" x2="${width-pad.right}" y1="${y(t)}" y2="${y(t)}"/><text class="axis-label" x="${pad.left-8}" y="${y(t)+3}" text-anchor="end">${t.toFixed(3)}</text>`).join('')}
      <polygon class="plot-area" points="${areaPoints}" style="fill:url(#${gradientId})"/>
      <polyline class="plot-line" points="${points}"/>
      ${values.map((d, i) => `<circle class="point ${options.alertIndex === i ? 'alert' : ''}" style="transition-delay:${.35 + i*.07}s" cx="${x(d[0])}" cy="${y(d[1])}" r="5"/>`).join('')}
      ${values.map((d, i) => i % labelEvery === 0 ? `<text class="axis-label" x="${x(d[0])}" y="${height-12}" text-anchor="middle">${d[0]}</text>` : '').join('')}
      <text class="axis-label" x="${width-pad.right}" y="${height-1}" text-anchor="end">${options.xUnit || ''}</text>
    </svg>`;
}

renderLineChart('lengthChart', chartData.length, { yMin: .07, yMax: .17, xUnit: 'length / mm', color: '#708eae' });
renderLineChart('loadingChart', chartData.loading, { yMin: .10, yMax: .18, xUnit: 'inductance / nH', alertIndex: 6, color: '#9a849b' });

const caseDots = document.getElementById('caseDots');
caseDots.innerHTML = Array.from({ length: 24 }, (_, i) => `<i style="animation-delay:${i * .035}s"></i>`).join('');

function updateFigure() {
  const figure = figures[activeFigure];
  const image = document.getElementById('mainFigure');
  image.style.opacity = '0';
  setTimeout(() => {
    image.src = showingComparison ? figure.comparison : figure.reproduction;
    image.alt = `${figure.alt}${showingComparison ? ' with paper comparison' : ''}`;
    image.style.opacity = '1';
  }, 180);
  document.getElementById('figureTitle').textContent = figure.title;
  document.getElementById('figureEyebrow').textContent = showingComparison ? `${figure.eyebrow} · PAPER COMPARISON` : figure.eyebrow;
  document.getElementById('figureDescription').textContent = figure.description;
  document.getElementById('compareBtn').textContent = showingComparison ? 'Return to reproduction only ↙' : 'Show paper comparison ↗';
}

document.querySelectorAll('.figure-tab').forEach(tab => tab.addEventListener('click', () => {
  document.querySelectorAll('.figure-tab').forEach(item => item.classList.toggle('active', item === tab));
  activeFigure = tab.dataset.figure;
  showingComparison = false;
  updateFigure();
}));

document.getElementById('compareBtn').addEventListener('click', () => {
  showingComparison = !showingComparison;
  updateFigure();
});

const lightbox = document.getElementById('lightbox');
document.getElementById('figureImageButton').addEventListener('click', () => {
  const source = document.getElementById('mainFigure');
  const image = document.getElementById('lightboxImage');
  image.src = source.src;
  image.alt = source.alt;
  lightbox.showModal();
});
document.querySelectorAll('.zoomable').forEach(button => button.addEventListener('click', () => {
  const source = button.querySelector('img');
  const image = document.getElementById('lightboxImage');
  image.src = source.src;
  image.alt = source.alt;
  lightbox.showModal();
}));
document.getElementById('closeLightbox').addEventListener('click', () => lightbox.close());
lightbox.addEventListener('click', event => { if (event.target === lightbox) lightbox.close(); });

document.getElementById('resetBtn').addEventListener('click', () => {
  stages.forEach(stage => {
    stage.classList.remove('revealed');
    stage.querySelector('.reveal-button').setAttribute('aria-expanded', 'false');
  });
  showingComparison = false;
  activeFigure = 'fig3';
  document.querySelectorAll('.figure-tab').forEach((tab, i) => tab.classList.toggle('active', i === 0));
  updateFigure();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

document.getElementById('fullscreenBtn').addEventListener('click', async () => {
  if (!document.fullscreenElement) await document.documentElement.requestFullscreen?.();
  else await document.exitFullscreen?.();
});

document.addEventListener('keydown', event => {
  if (event.key.toLowerCase() === 'r') document.getElementById('resetBtn').click();
  if (event.key.toLowerCase() === 'f') document.getElementById('fullscreenBtn').click();
  if (event.key === 'Escape' && lightbox.open) lightbox.close();
});

// Optional deterministic deep-link used for review and recording setup:
// index.html?stage=3&reveal=1 opens the fourth stage with its evidence visible.
const previewParams = new URLSearchParams(location.search);
const hashPreviewId = location.hash.endsWith('-reveal') ? location.hash.slice(1, -7) : '';
const hashPreviewStage = stages.findIndex(stage => stage.id === hashPreviewId);
const previewStage = hashPreviewStage >= 0 ? hashPreviewStage : Number(previewParams.get('stage'));
if (Number.isInteger(previewStage) && stages[previewStage]) {
  if (hashPreviewStage >= 0 || previewParams.get('reveal') === '1') {
    stages[previewStage].classList.add('revealed');
    stages[previewStage].querySelector('.reveal-button').setAttribute('aria-expanded', 'true');
  }
  setTimeout(() => stages[previewStage].scrollIntoView({ block: 'start' }), 120);
}
