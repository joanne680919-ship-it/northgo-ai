(function () {
  const header = document.querySelector(".site-header");
  const toggle = document.querySelector(".nav-toggle");
  if (toggle && header) {
    toggle.addEventListener("click", function () {
      const open = header.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    document.getElementById("site-nav").addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        header.classList.remove("nav-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.querySelectorAll(".menu-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      const menu = button.parentElement;
      const open = menu.classList.toggle("open");
      button.setAttribute("aria-expanded", String(open));
    });
  });

  const form = document.querySelector("[data-enquiry]");
  if (form) {
    const params = new URLSearchParams(location.search);
    const service = params.get("service");
    if (service && form.elements.service) {
      const option = [...form.elements.service.options].some(function (item) { return item.value === service; });
      if (option) form.elements.service.value = service;
    }
    const office = form.elements.office;
    const mail = document.getElementById("office-mail");
    function selectedEmail() {
      const choice = office.options[office.selectedIndex];
      return choice.getAttribute("data-email") || "info.tpe@northgo.com";
    }
    function showMail() {
      if (mail) mail.textContent = selectedEmail();
    }
    if (office) {
      office.addEventListener("change", showMail);
      showMail();
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      let valid = true;
      form.querySelectorAll("[required]").forEach(function (field) {
        const error = field.parentElement.querySelector(".field-error");
        const empty = !String(field.value || "").trim();
        field.setAttribute("aria-invalid", String(empty));
        if (error) error.hidden = !empty;
        if (empty) valid = false;
      });
      const status = document.getElementById("form-status");
      if (!valid) {
        if (status) status.textContent = form.getAttribute("data-invalid");
        return;
      }
      const email = selectedEmail();
      const lines = [];
      ["name", "company", "email", "phone", "country", "service", "origin", "destination", "cargo", "message"].forEach(function (key) {
        const field = form.elements[key];
        if (!field) return;
        const label = field.getAttribute("data-label") || key;
        lines.push(label + ": " + String(field.value || "").trim());
      });
      const subject = form.getAttribute("data-subject") + " — " + form.elements.service.value;
      window.location.href = "mailto:" + email + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(lines.join("\n"));
      if (status) status.textContent = form.getAttribute("data-sent").replace("{email}", email);
    });
  }

  const dataEl = document.getElementById("office-data");
  const mapEl = document.getElementById("map");
  if (!dataEl || !mapEl || typeof L === "undefined") return;
  const offices = JSON.parse(dataEl.textContent);
  const boundsByRegion = {
    east: [[8.6, 103.5], [38.2, 143.8]],
    taiwan: [[22.2, 119.85], [25.45, 122.05]],
    japan: [[33.85, 134.7], [36.35, 140.6]],
    sea: [[10.15, 105.85], [11.45, 107.6]],
    na: [[33.6, -118.75], [34.5, -117.6]]
  };
  function pacificLng(lng) { return lng < 0 ? lng + 360 : lng; }
  const map = L.map(mapEl, { worldCopyJump: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);
  const markers = new Map();
  offices.forEach(function (office) {
    const icon = L.divIcon({
      className: "",
      html: '<div class="pin' + (office.hq ? " hq" : "") + '"></div>',
      iconSize: [0, 0]
    });
    const marker = L.marker([office.lat, office.lng], { icon: icon, title: office.name }).addTo(map);
    const fax = office.fax ? "<br>Fax " + office.fax : "";
    marker.bindPopup(
      '<div class="popup"><h2>' + office.name + "</h2><p>" + office.address + "<br>" + office.addressEn +
      '</p><p><a href="tel:' + office.phone.replace(/[^\d+]/g, "") + '">' + office.phone + "</a>" + fax +
      '<br><a href="mailto:' + office.email + '">' + office.email + "</a></p></div>"
    );
    markers.set(office.id, marker);
  });
  const insetEl = document.getElementById("inset");
  const inset = L.map(insetEl, { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(inset);
  offices.filter(function (office) { return office.region === "taiwan"; }).forEach(function (office) {
    const icon = L.divIcon({ className: "", html: '<div class="pin' + (office.hq ? " hq" : "") + '"></div>', iconSize: [0, 0] });
    L.marker([office.lat, office.lng], { icon: icon, keyboard: false })
      .bindTooltip(office.short, { permanent: true, direction: office.id === "txg" ? "left" : "right", offset: [office.id === "txg" ? -8 : 8, 0] })
      .addTo(inset);
  });
  function placeMarkers(region) {
    offices.forEach(function (office) {
      const lng = region === "world" ? pacificLng(office.lng) : office.lng;
      markers.get(office.id).setLatLng([office.lat, lng]);
    });
  }
  function fit(bounds, cap) {
    const box = L.latLngBounds(bounds);
    const apply = function () {
      let zoom = Math.floor(map.getBoundsZoom(box, false, L.point(24, 24)));
      if (cap) zoom = Math.min(cap, zoom);
      map.stop();
      map.setView(box.getCenter(), Math.max(zoom, 1), { animate: false });
    };
    if (!map._loaded) {
      map.setView(box.getCenter(), 2);
      requestAnimationFrame(apply);
    } else apply();
  }
  let selectToken = 0;
  function showRegion(id) {
    document.querySelectorAll("[data-region]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.getAttribute("data-region") === id));
    });
    insetEl.hidden = !(id === "world" || id === "east");
    placeMarkers(id);
    if (id === "world") fit(offices.map(function (office) { return [office.lat, pacificLng(office.lng)]; }), 3);
    else fit(boundsByRegion[id]);
    if (!inset._loaded) inset.setView([23.7, 120.9], 6);
    else inset.fitBounds([[22.2, 119.85], [25.45, 122.05]], { padding: [18, 18], animate: false });
  }
  function selectOffice(id) {
    const office = offices.find(function (item) { return item.id === id; });
    const marker = markers.get(id);
    const zoom = office.region === "taiwan" || office.region === "japan" ? 12 : 13;
    const token = ++selectToken;
    const dest = marker.getLatLng();
    map.stop();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      map.setView(dest, zoom, { animate: false });
      marker.openPopup();
      return;
    }
    map.once("moveend", function () { if (token === selectToken) marker.openPopup(); });
    map.flyTo(dest, zoom, { duration: 0.8 });
  }
  document.querySelectorAll("[data-region]").forEach(function (button) {
    button.addEventListener("click", function () { showRegion(button.getAttribute("data-region")); });
  });
  document.querySelectorAll("[data-office]").forEach(function (button) {
    button.addEventListener("click", function () { selectOffice(button.getAttribute("data-office")); });
  });
  showRegion("world");
})();
