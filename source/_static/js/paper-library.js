/* Progressive enhancement: every download remains visible without JavaScript. */
(() => {
  const library = document.querySelector('.paper-library');
  const toolbar = document.querySelector('.paper-toolbar');
  if (!library || !toolbar) return;
  const cards = [...library.querySelectorAll('.paper-card')];
  const input = toolbar.querySelector('input');
  const buttons = [...toolbar.querySelectorAll('button[data-range]')];
  const status = document.querySelector('#paper-count');
  const empty = document.querySelector('#paper-empty');
  let range = 'all';
  function filter() {
    const query = input.value.normalize('NFKC').trim().replace(/年$/, '').trim();
    let count = 0;
    cards.forEach(card => {
      const year = card.querySelector('.paper-year').textContent.trim();
      const recent = Number(year) >= 2020;
      const visible = year.includes(query) && (range === 'all' || (range === 'recent' ? recent : !recent));
      card.hidden = !visible;
      if (visible) count++;
    });
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.range === range)));
    status.textContent = `显示 ${count} 份试卷`;
    empty.hidden = count !== 0;
  }
  input.addEventListener('input', filter);
  buttons.forEach(button => button.addEventListener('click', () => {
    range = button.dataset.range;
    filter();
  }));
  toolbar.hidden = false;
  filter();
})();
