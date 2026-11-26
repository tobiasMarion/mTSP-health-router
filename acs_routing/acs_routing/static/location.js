(() => {
  const container = document.querySelector('.location-picker');
  const status = document.querySelector('#geocode-status');
  if (!container || typeof L === 'undefined') return;
  const map = L.map('location-map').setView([-30.04, -51.16], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
  let marker;
  function select(lat, lon) {
    document.querySelector('#family-lat').value = Number(lat).toFixed(7);
    document.querySelector('#family-lon').value = Number(lon).toFixed(7);
    if (marker) marker.setLatLng([lat, lon]); else marker = L.marker([lat, lon], {icon: L.divIcon({className: 'location-pin', html: '<span></span>', iconSize: [28, 36], iconAnchor: [14, 34]})}).addTo(map);
    map.setView([lat, lon], 17);
    map.invalidateSize();
    status.textContent = 'Local selecionado. Confira a posição no mapa.';
  }
  map.on('click', event => select(event.latlng.lat, event.latlng.lng));
  const address = document.querySelector('#family-address');
  let lookupVersion = 0, lastLookup = 0;
  address.addEventListener('input', () => { lookupVersion++; document.querySelector('#geocode-results').replaceChildren(); document.querySelector('#family-lat').value = ''; document.querySelector('#family-lon').value = ''; if (marker) { marker.remove(); marker = null; } });
  document.querySelector('#geocode-button').addEventListener('click', async () => {
    if (!address.value.trim()) { status.textContent = 'Informe o endereço antes de buscar.'; return; }
    if (Date.now() - lastLookup < 1100) { status.textContent = 'Aguarde um instante antes de buscar novamente.'; return; }
    lastLookup = Date.now(); const version = ++lookupVersion;
    const url = new URL(container.dataset.geocoderUrl, window.location.href);
    url.search = new URLSearchParams({q: `${address.value}, Porto Alegre, RS, Brasil`, format: 'jsonv2', limit: '5'});
    status.textContent = 'Buscando endereço...';
    const results = document.querySelector('#geocode-results'); results.replaceChildren();
    try {
      const response = await fetch(url); if (!response.ok) throw new Error('Busca indisponível');
      const items = await response.json();
      if (version !== lookupVersion) return;
      if (items.length) select(Number(items[0].lat), Number(items[0].lon));
      status.textContent = items.length ? `Primeiro resultado selecionado: ${items[0].display_name}. Confira o ponto ou escolha outro resultado.` : 'Nenhum resultado encontrado. Selecione o ponto no mapa.';
      items.forEach(item => { const button = document.createElement('button'); button.type = 'button'; button.className = 'geocode-result'; button.textContent = item.display_name; button.addEventListener('click', () => { select(Number(item.lat), Number(item.lon)); results.replaceChildren(); }); results.append(button); });
    } catch (_) { if (version === lookupVersion) status.textContent = 'Não foi possível consultar o serviço. Selecione o ponto no mapa ou informe as coordenadas.'; }
  });
  container.closest('form').addEventListener('submit', event => {
    if (!document.querySelector('#family-lat').value || !document.querySelector('#family-lon').value) {
      event.preventDefault(); status.textContent = 'Busque o endereço ou selecione a localização no mapa antes de adicionar.';
      document.querySelector('#geocode-button').focus();
    }
  });
})();
