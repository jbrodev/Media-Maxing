(function () {
  "use strict";

  // Local-only sidebar reordering. Users can drag the nav dropdown sections
  // (Daily Workflow, Setup, Advanced Tools) to reorder them, and drag the
  // links inside each section to reorder those. The chosen order is persisted
  // locally so it survives reloads. Nothing here touches app data or network.
  const STORAGE_KEY = "local-social-ai-manager.navOrder";

  function slug(text) {
    return String(text || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function loadOrder() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === "object") {
        return {
          groups: Array.isArray(parsed.groups) ? parsed.groups : [],
          links: parsed.links && typeof parsed.links === "object" ? parsed.links : {},
        };
      }
    } catch (err) {
      /* corrupt or unavailable storage falls back to default order */
    }
    return { groups: [], links: {} };
  }

  function saveOrder(order) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(order));
    } catch (err) {
      /* local-only convenience; ignore quota/availability errors */
    }
  }

  function groupId(details) {
    const summary = details.querySelector("summary");
    return slug(summary ? summary.textContent : "");
  }

  function linkId(link) {
    return link.getAttribute("href") || slug(link.textContent);
  }

  function groups(navList) {
    return Array.from(navList.querySelectorAll(":scope > .nav-group"));
  }

  function links(container) {
    return Array.from(container.querySelectorAll(":scope > .nav-link"));
  }

  // Re-stack DOM to match a previously saved order. Unknown/new ids are left
  // in their existing position so future menu additions still appear.
  function applyOrder(navList, order) {
    if (order.groups.length) {
      const byId = new Map(groups(navList).map((g) => [groupId(g), g]));
      order.groups.forEach((id) => {
        const g = byId.get(id);
        if (g) navList.appendChild(g);
      });
    }
    groups(navList).forEach((g) => {
      const container = g.querySelector(".nav-group-links");
      const saved = order.links[groupId(g)];
      if (!container || !Array.isArray(saved) || !saved.length) return;
      const byHref = new Map(links(container).map((l) => [linkId(l), l]));
      saved.forEach((id) => {
        const l = byHref.get(id);
        if (l) container.appendChild(l);
      });
    });
  }

  function captureOrder(navList) {
    const order = { groups: [], links: {} };
    groups(navList).forEach((g) => {
      const gid = groupId(g);
      const container = g.querySelector(".nav-group-links");
      order.groups.push(gid);
      order.links[gid] = container ? links(container).map(linkId) : [];
    });
    return order;
  }

  function addGrip(el) {
    if (!el || el.querySelector(":scope > .nav-grip")) return;
    const grip = document.createElement("span");
    grip.className = "nav-grip";
    grip.setAttribute("aria-hidden", "true");
    grip.title = "Drag to reorder";
    grip.textContent = "⠿"; // braille dots grip glyph
    el.insertBefore(grip, el.firstChild);
  }

  // Returns the sibling the dragged item should be placed before, or null to
  // append at the end, based on the pointer's vertical position.
  function dragAfter(container, itemSelector, y, dragging) {
    let closest = { offset: Number.NEGATIVE_INFINITY, element: null };
    container.querySelectorAll(":scope > " + itemSelector).forEach((child) => {
      if (child === dragging) return;
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        closest = { offset, element: child };
      }
    });
    return closest.element;
  }

  function makeSortable(container, itemSelector, onChange) {
    let dragging = null;

    container.addEventListener("dragstart", (event) => {
      const item = event.target.closest(itemSelector);
      if (!item || item.parentElement !== container) return;
      dragging = item;
      item.classList.add("nav-dragging");
      event.dataTransfer.effectAllowed = "move";
      try {
        // Firefox requires payload data for a drag to initiate.
        event.dataTransfer.setData("text/plain", "");
      } catch (err) {
        /* some browsers disallow setData here; drag still works */
      }
      // Prevent a link drag from also starting a parent-section drag.
      event.stopPropagation();
    });

    container.addEventListener("dragover", (event) => {
      if (!dragging) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      const after = dragAfter(container, itemSelector, event.clientY, dragging);
      if (after == null) {
        container.appendChild(dragging);
      } else if (after !== dragging) {
        container.insertBefore(dragging, after);
      }
    });

    container.addEventListener("drop", (event) => {
      if (!dragging) return;
      event.preventDefault();
      event.stopPropagation();
      onChange();
    });

    container.addEventListener("dragend", () => {
      if (dragging) dragging.classList.remove("nav-dragging");
      dragging = null;
    });
  }

  function init() {
    const navList = document.querySelector(".nav-list");
    if (!navList) return;

    applyOrder(navList, loadOrder());

    // Keep the primary Control Center link pinned; don't let it be dragged.
    const primary = navList.querySelector(":scope > .nav-link");
    if (primary) primary.setAttribute("draggable", "false");

    const save = () => saveOrder(captureOrder(navList));

    groups(navList).forEach((group) => {
      group.setAttribute("draggable", "true");
      addGrip(group.querySelector("summary"));

      const container = group.querySelector(".nav-group-links");
      if (container) {
        links(container).forEach((link) => {
          link.setAttribute("draggable", "true");
          addGrip(link);
        });
        makeSortable(container, ".nav-link", save);
      }
    });

    makeSortable(navList, ".nav-group", save);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
