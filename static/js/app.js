(function () {
  "use strict";

  /* ---------------- Sidebar (mobile) ---------------- */
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("show");
  }

  document.querySelectorAll("[data-toggle-sidebar]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (!sidebar) return;
      sidebar.classList.toggle("open");
      if (backdrop) backdrop.classList.toggle("show");
    });
  });

  if (backdrop) backdrop.addEventListener("click", closeSidebar);

  /* ---------------- Helper format angka ---------------- */
  function angka(value) {
    return new Intl.NumberFormat("id-ID").format(value);
  }

  function persen(value) {
    return new Intl.NumberFormat("id-ID", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value) + "%";
  }

  /* ---------------- Form pemeriksaan QC ---------------- */
  const unitRows = document.getElementById("unit-rows");
  if (unitRows) {
    const totalForms = document.getElementById("id_unit-TOTAL_FORMS");
    const addButton = document.getElementById("add-unit");
    const template = document.getElementById("unit-empty-template");
    const metodeField = document.getElementById("id_metode");
    const totalField = document.getElementById("id_total_production");
    const sampleField = document.getElementById("id_sample_size");
    const failField = document.getElementById("id_qty_fail");
    const sampleWrap = document.getElementById("sample-wrap");
    const summary = document.getElementById("inspection-summary");

    function visibleRows() {
      return Array.prototype.slice
        .call(unitRows.querySelectorAll(".unit-row"))
        .filter(function (row) {
          return !row.classList.contains("is-deleted");
        });
    }

    function renumber() {
      visibleRows().forEach(function (row, index) {
        const label = row.querySelector(".row-number");
        if (label) label.textContent = "Unit " + (index + 1);
        const ref = row.querySelector('input[name$="-unit_ref"]');
        if (ref && !ref.value) {
          ref.value = "UNIT-" + String(index + 1).padStart(3, "0");
        }
        const del = row.querySelector('input[name$="-DELETE"]');
        if (del) del.checked = false;
      });
    }

    function updateSummary() {
      const total = parseInt(totalField && totalField.value, 10) || 0;
      const metode = metodeField ? metodeField.value : "full";
      const sample = parseInt(sampleField && sampleField.value, 10) || 0;
      const fail = parseInt(failField && failField.value, 10) || 0;
      const inspected = metode === "sampling" ? sample : total;
      const pass = Math.max(inspected - fail, 0);
      const rate = inspected > 0 ? (fail / inspected) * 100 : 0;
      const details = visibleRows().length;

      if (sampleWrap) {
        sampleWrap.style.display = metode === "sampling" ? "" : "none";
      }

      if (summary) {
        summary.querySelector("[data-calc=inspected]").textContent = angka(inspected);
        summary.querySelector("[data-calc=pass]").textContent = angka(pass);
        summary.querySelector("[data-calc=fail]").textContent = angka(fail);
        summary.querySelector("[data-calc=rate]").textContent = persen(rate);
        summary.querySelector("[data-calc=details]").textContent = angka(details);
        summary.classList.toggle("border-danger", fail > inspected && inspected > 0);
      }
    }

    if (addButton && template && totalForms) {
      addButton.addEventListener("click", function () {
        const index = parseInt(totalForms.value, 10);
        const html = template.innerHTML.replace(/__prefix__/g, index);
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html.trim();
        const node = wrapper.firstElementChild;
        unitRows.appendChild(node);
        totalForms.value = index + 1;
        renumber();
        updateSummary();
        const firstInput = node.querySelector("input");
        if (firstInput) firstInput.focus();
      });
    }

    unitRows.addEventListener("click", function (event) {
      const removeButton = event.target.closest("[data-remove-unit]");
      if (!removeButton) return;
      event.preventDefault();
      const row = removeButton.closest(".unit-row");
      if (!row) return;
      const del = row.querySelector('input[name$="-DELETE"]');
      if (del) del.checked = true;
      row.classList.add("is-deleted");
      updateSummary();
    });

    unitRows.addEventListener("input", updateSummary);
    unitRows.addEventListener("change", updateSummary);
    if (metodeField) metodeField.addEventListener("change", updateSummary);
    if (totalField) totalField.addEventListener("input", updateSummary);
    if (sampleField) sampleField.addEventListener("input", updateSummary);
    if (failField) failField.addEventListener("input", updateSummary);

    renumber();
    updateSummary();
  }

  /* ---------------- Cetak ---------------- */
  document.querySelectorAll("[data-print]").forEach(function (button) {
    button.addEventListener("click", function () {
      window.print();
    });
  });
})();
