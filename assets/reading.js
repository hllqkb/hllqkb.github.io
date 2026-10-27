(() => {
  const menu = document.querySelector('.chapter-menu');
  const compact = window.matchMedia('(max-width: 800px)');
  if (menu) {
    menu.open = !compact.matches;
    compact.addEventListener('change', (event) => { menu.open = !event.matches; });
    menu.addEventListener('click', (event) => {
      if (compact.matches && event.target.closest('.toc a')) menu.open = false;
    });
  }
  document.querySelectorAll('.prose table').forEach((table) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-scroll';
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    wrapper.setAttribute('aria-label', '表格，可左右滑动查看');
    table.before(wrapper);
    wrapper.append(table);
  });
  const search = document.querySelector('#article-search');
  const category = document.querySelector('#article-category');
  if (search && category) {
    document.querySelector('[data-search-tools]').hidden = false;
    const rows = [...document.querySelectorAll('.article-row')];
    const update = () => {
      const query = search.value.trim().toLocaleLowerCase();
      let count = 0;
      rows.forEach((row) => {
        const visible = row.dataset.search.toLocaleLowerCase().includes(query)
          && (!category.value || row.dataset.category === category.value);
        row.hidden = !visible;
        if (visible) count += 1;
      });
      document.querySelector('#search-status').textContent = `${count} 篇文章`;
      document.querySelector('#empty-results').hidden = count !== 0;
    };
    search.addEventListener('input', update);
    category.addEventListener('change', update);
  }
})();
