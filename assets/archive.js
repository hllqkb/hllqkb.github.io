(() => {
  const search = document.querySelector('#article-search');
  if (!search) return;
  const rows = [...document.querySelectorAll('.article-row')];
  const groups = [...document.querySelectorAll('.year-group')];
  search.addEventListener('input', () => {
    const query = search.value.trim().toLocaleLowerCase();
    let count = 0;
    rows.forEach((row) => {
      row.hidden = !row.dataset.search.toLocaleLowerCase().includes(query);
      if (!row.hidden) count += 1;
    });
    groups.forEach((group) => {
      group.hidden = !group.querySelector('.essay-row:not([hidden])');
    });
    document.querySelector('#search-status').textContent = query ? `${count} 篇文章` : `全部 ${rows.length} 篇`;
    document.querySelector('#empty-results').hidden = count !== 0;
  });
})();
