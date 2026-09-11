(() => {
  'use strict';

  const MAX_RENDERED = 240;
  const state = { catalog: [], query: '', pack: '', kind: '' };
  const search = document.querySelector('#search');
  const pack = document.querySelector('#pack');
  const kind = document.querySelector('#kind');
  const grid = document.querySelector('#grid');
  const count = document.querySelector('#result-count');
  const note = document.querySelector('#render-note');
  const template = document.querySelector('#card-template');

  const norm = value => (value || '').toString().toLowerCase();

  function addOptions(select, values) {
    [...new Set(values.filter(Boolean))]
      .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
      .forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.append(option);
      });
  }

  function filtered() {
    const terms = norm(state.query).trim().split(/\s+/).filter(Boolean);
    return state.catalog.filter(item => {
      if (state.pack && item.pack !== state.pack) return false;
      if (state.kind && item.kind !== state.kind) return false;
      if (!terms.length) return true;
      const haystack = norm(item.searchText || [item.name, item.pack, item.kind, item.assetPath, ...(item.tags || [])].join(' '));
      return terms.every(term => haystack.includes(term));
    });
  }

  function render() {
    const matches = filtered();
    const shown = matches.slice(0, MAX_RENDERED);
    count.textContent = `${matches.length.toLocaleString()} prefab${matches.length === 1 ? '' : 's'}`;
    note.textContent = matches.length > MAX_RENDERED ? `Showing first ${MAX_RENDERED}; refine the search to narrow results.` : '';
    grid.replaceChildren();

    const fragment = document.createDocumentFragment();
    for (const item of shown) {
      const node = template.content.cloneNode(true);
      node.querySelector('.thumb-link').href = `./${item.page}`;
      node.querySelector('.type-mark').textContent = (item.kind || 'prefab').toUpperCase();
      node.querySelector('.name').textContent = item.name;
      node.querySelector('.kind').textContent = item.kind || 'prefab';
      node.querySelector('.pack').textContent = item.pack || 'Unknown pack';
      node.querySelector('.path').textContent = item.assetPath;
      fragment.append(node);
    }
    grid.append(fragment);
  }

  search.addEventListener('input', event => { state.query = event.target.value; render(); });
  pack.addEventListener('change', event => { state.pack = event.target.value; render(); });
  kind.addEventListener('change', event => { state.kind = event.target.value; render(); });

  fetch('./catalog.json', { cache: 'no-cache' })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(data => {
      state.catalog = Array.isArray(data) ? data : (data.entries || []);
      addOptions(pack, state.catalog.map(item => item.pack));
      addOptions(kind, state.catalog.map(item => item.kind));
      render();
      search.focus({ preventScroll: true });
    })
    .catch(error => {
      count.textContent = 'Catalog unavailable';
      note.textContent = error.message;
    });
})();
