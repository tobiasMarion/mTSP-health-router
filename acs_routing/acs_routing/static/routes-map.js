(() => {
  const plan = JSON.parse(document.querySelector('#plan-data').textContent);
  const map = L.map('routes-map');
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
  const layer = L.layerGroup().addTo(map), families = new Map(plan.families.map(f => [f.id, f]));
  const center = [plan.families.reduce((n, f) => n + f.lat, 0) / plan.families.length, plan.families.reduce((n, f) => n + f.lon, 0) / plan.families.length];
  const colors = ['#002776', '#006e29', '#a12a42', '#775000', '#67439d', '#007d89'];
  function draw() {
    layer.clearLayers();
    const agent = document.querySelector('#map-agent').value, day = document.querySelector('#map-day').value;
    let bounds = [center];
    L.marker(center).bindPopup('Ponto de partida aproximado').addTo(layer);
    plan.routes.filter(r => (!agent || r.agent === Number(agent)) && (!day || r.day === Number(day)) && r.sequence.length > 2).forEach(route => {
      const points = [center];
      route.sequence.slice(1, -1).forEach((id, index) => {
        const family = families.get(id); if (!family) return;
        const point = [family.lat, family.lon]; points.push(point); bounds.push(point);
        const label = document.createElement('span'); label.textContent = `${index + 1}. ${family.name} · ${family.address}`;
        L.circleMarker(point, {radius: 7, color: colors[(route.agent - 1) % colors.length], fillOpacity: 0.9}).bindPopup(label).addTo(layer);
      });
      points.push(center); L.polyline(points, {color: colors[(route.agent - 1) % colors.length], weight: 4, opacity: 0.8}).addTo(layer);
    });
    if (bounds.length > 1) map.fitBounds(bounds, {padding: [30, 30], maxZoom: 16}); else map.setView(center, 13);
  }
  document.querySelector('#map-agent').addEventListener('change', draw);
  document.querySelector('#map-day').addEventListener('change', draw);
  draw();
})();
