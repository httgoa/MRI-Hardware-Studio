(() => {
  const stages = [...document.querySelectorAll('.story-stage')];
  const steps = [...document.querySelectorAll('.step')];
  const label = document.getElementById('currentStageLabel');
  const fill = document.getElementById('trackFill');
  const imageDialog = document.getElementById('imageDialog');
  const buttonLabels = ['Review the simulation brief', 'Inspect the automated execution', 'Review matching and field processing', 'Reveal the result package'];

  function setStage(index) {
    const current = Math.max(0, Math.min(index, stages.length - 1));
    steps.forEach((step, i) => {
      step.classList.toggle('active', i === current);
      step.classList.toggle('done', i < current);
    });
    label.textContent = stages[current].dataset.label;
    fill.style.width = `${(current / (stages.length - 1)) * 100}%`;
  }

  function reveal(stage, scroll = false) {
    stage.classList.add('revealed');
    const button = stage.querySelector('.reveal-button');
    button.setAttribute('aria-expanded', 'true');
    button.innerHTML = 'Evidence revealed <span>✓</span>';
    if (scroll) stage.querySelector('.stage-detail').scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  stages.forEach((stage, index) => {
    stage.querySelector('.reveal-button').addEventListener('click', () => reveal(stage, true));
    new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) setStage(index);
    }, {rootMargin: '-36% 0px -48% 0px', threshold: 0}).observe(stage);
  });

  steps.forEach((step, index) => step.addEventListener('click', () => stages[index].scrollIntoView({behavior: 'smooth', block: 'start'})));

  document.querySelectorAll('.zoomable').forEach(button => button.addEventListener('click', () => {
    const source = button.querySelector('img');
    const target = imageDialog.querySelector('img');
    target.src = source.src;
    target.alt = source.alt;
    imageDialog.showModal();
  }));

  document.querySelector('[data-close-dialog]').addEventListener('click', () => imageDialog.close());
  imageDialog.addEventListener('click', event => { if (event.target === imageDialog) imageDialog.close(); });

  document.getElementById('fullscreenBtn').addEventListener('click', async () => {
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
    else await document.exitFullscreen();
  });

  document.getElementById('resetBtn').addEventListener('click', () => {
    stages.forEach((stage, index) => {
      stage.classList.remove('revealed');
      const button = stage.querySelector('.reveal-button');
      button.setAttribute('aria-expanded', 'false');
      button.innerHTML = `${buttonLabels[index]} <span>→</span>`;
    });
    history.replaceState(null, '', location.pathname);
    window.scrollTo({top: 0, behavior: 'smooth'});
  });

  document.addEventListener('keydown', event => {
    if (event.key.toLowerCase() === 'r' && !event.ctrlKey && !event.metaKey) document.getElementById('resetBtn').click();
    if (event.key.toLowerCase() === 'f' && !event.ctrlKey && !event.metaKey) document.getElementById('fullscreenBtn').click();
    if (event.key === 'Escape' && imageDialog.open) imageDialog.close();
  });

  const hashMatch = location.hash.match(/^#stage-(0[1-4])(?:-reveal)?$/);
  const params = new URLSearchParams(location.search);
  if (params.get('reveal') === 'all') stages.forEach(stage => reveal(stage));
  const queryStage = Number(params.get('stage'));
  const deepIndex = hashMatch ? Number(hashMatch[1]) - 1 : (queryStage >= 1 && queryStage <= 4 ? queryStage - 1 : null);
  if (deepIndex !== null) {
    if (location.hash.endsWith('-reveal') || params.get('reveal') === '1') reveal(stages[deepIndex]);
    requestAnimationFrame(() => window.scrollTo(0, stages[deepIndex].offsetTop - 100));
  }
  setStage(0);
})();
