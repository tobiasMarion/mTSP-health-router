document.addEventListener('input', (event) => {
  const input = event.target;
  const filter = input.dataset?.filter;
  if (!filter) return;
  const query = input.value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  document.querySelectorAll(`[data-${filter}]`).forEach((item) => {
    const value = item.getAttribute(`data-${filter}`).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    item.hidden = !value.includes(query);
  });
});

let collapsedBeforePrint = [];
window.addEventListener('beforeprint', () => {
  collapsedBeforePrint = [...document.querySelectorAll('details.route-day:not([open])')];
  collapsedBeforePrint.forEach(item => { item.open = true; });
});
window.addEventListener('afterprint', () => {
  collapsedBeforePrint.forEach(item => { item.open = false; });
  collapsedBeforePrint = [];
});
