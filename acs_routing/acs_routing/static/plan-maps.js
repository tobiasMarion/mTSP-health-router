(() => {
  const printButton = document.querySelector('#print-plans');
  const printStatus = document.querySelector('#print-status');
  if (typeof L === 'undefined') {
    document.querySelectorAll('.map-status').forEach(item => { item.textContent = 'Não foi possível carregar o mapa. Verifique sua conexão.'; });
    printButton.addEventListener('click', () => window.print());
    return;
  }
  const plan = JSON.parse(document.querySelector('#plan-data').textContent);
  const osrm = document.querySelector('#map-config').dataset.osrmUrl.replace(/\/$/, '');
  const families = new Map(plan.families.map(f => [f.id, f]));
  const center = [plan.families.reduce((n, f) => n + f.lat, 0) / plan.families.length,
                  plan.families.reduce((n, f) => n + f.lon, 0) / plan.families.length];
  const colors = ['#002776', '#006e29', '#b32b35', '#956000', '#713ea1'];
  const cache = new Map(), maps = new Map();
  const routePoints = route => [center, ...route.sequence.slice(1, -1).map(id => {
    const f = families.get(id); return [f.lat, f.lon];
  }), center];
  function geometry(route) {
    const key = `${route.agent}-${route.day}`;
    if (!cache.has(key)) {
      const points = routePoints(route);
      const coords = points.map(([lat, lon]) => `${lon},${lat}`).join(';');
      const url = `${osrm}/route/v1/driving/${coords}?overview=full&geometries=geojson&steps=false`;
      cache.set(key, fetch(url, {signal: AbortSignal.timeout(10000)}).then(response => {
        if (!response.ok) throw new Error('OSRM indisponível'); return response.json();
      }).then(data => {
        if (data.code !== 'Ok' || !data.routes?.[0]?.geometry?.coordinates?.length) throw new Error('Rota indisponível');
        return {points: data.routes[0].geometry.coordinates.map(([lon, lat]) => [lat, lon]), approximate: false};
      }).catch(() => ({points, approximate: true})));
    }
    return cache.get(key);
  }
  function render(element, routes) {
    if (maps.has(element)) return maps.get(element).ready;
    const map = L.map(element, {scrollWheelZoom: false});
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    const tileReady = new Promise(resolve => { tiles.once('load', resolve); setTimeout(resolve, 6000); });
    const bounds = [center];
    L.circleMarker(center, {radius: 7, color: '#111', fillColor: '#fff', fillOpacity: 1}).bindPopup('Ponto de partida aproximado').addTo(map);
    routes.forEach(route => route.sequence.slice(1, -1).forEach((id, index) => {
      const f = families.get(id), point = [f.lat, f.lon]; bounds.push(point);
      const label = document.createElement('span'); label.textContent = `${index + 1}. ${f.name} · ${f.address}`;
      L.circleMarker(point, {radius: 6, color: colors[(route.day - 1) % colors.length], fillOpacity: 0.9}).bindPopup(label).addTo(map);
    }));
    map.fitBounds(bounds, {padding: [25, 25], maxZoom: 16});
    const status = element.nextElementSibling;
    status.textContent = 'Carregando trajetos pelas ruas...';
    const ready = Promise.all(routes.map(geometry)).then(results => {
      results.forEach((result, index) => L.polyline(result.points, {color: colors[(routes[index].day - 1) % colors.length], weight: 4, opacity: 0.8, dashArray: result.approximate ? '6 6' : null}).addTo(map));
      status.textContent = results.some(result => result.approximate) ? 'Alguns trajetos estão em linha reta: serviço de ruas indisponível.' : 'Trajetos pelas ruas obtidos via OSRM; tempos do planejamento são aproximados.';
    });
    maps.set(element, {map, ready: Promise.all([ready, tileReady])});
    return maps.get(element).ready;
  }
  const nonempty = plan.routes.filter(route => route.sequence.length > 2);
  render(document.querySelector('#weekly-plan-map'), nonempty);
  document.querySelectorAll('.daily-map').forEach(element => {
    const details = element.closest('details');
    details.addEventListener('toggle', () => {
      if (!details.open) return;
      const route = nonempty.find(r => r.agent === Number(element.dataset.agent) && r.day === Number(element.dataset.day));
      if (route) { render(element, [route]); requestAnimationFrame(() => { const item = maps.get(element); item.map.invalidateSize(); item.map.fitBounds(routePoints(route), {padding: [25, 25], maxZoom: 16}); }); }
    });
  });
  let openedForPrint = [];
  printButton.addEventListener('click', async () => {
    printButton.disabled = true; printStatus.textContent = 'Preparando mapas para impressão...';
    openedForPrint = [...document.querySelectorAll('details.route-day:not([open])')];
    openedForPrint.forEach(item => { item.open = true; });
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const pending = [maps.get(document.querySelector('#weekly-plan-map')).ready];
    document.querySelectorAll('.daily-map').forEach(element => {
      const route = nonempty.find(r => r.agent === Number(element.dataset.agent) && r.day === Number(element.dataset.day));
      if (route) { pending.push(render(element, [route])); const item = maps.get(element); item.map.invalidateSize(); item.map.fitBounds(routePoints(route), {padding: [25, 25], maxZoom: 16}); }
    });
    await Promise.all(pending);
    printStatus.textContent = ''; printButton.disabled = false; window.print();
  });
  window.addEventListener('afterprint', () => { openedForPrint.forEach(item => { item.open = false; }); openedForPrint = []; });
})();
