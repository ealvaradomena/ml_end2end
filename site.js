(() => {
  'use strict';

  const progress = document.querySelector('.reading-progress span');
  const toggle = document.querySelector('.mobile-toc-toggle');
  const toc = document.getElementById('contents');
  const links = [...document.querySelectorAll('.toc-link')];
  const mobileQuery = window.matchMedia('(max-width: 780px)');

  function updateProgress() {
    if (!progress) return;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const percent = max > 0 ? Math.min(100, Math.max(0, window.scrollY / max * 100)) : 0;
    progress.style.width = `${percent}%`;
  }

  function closeContents({ restoreFocus = false } = {}) {
    if (!toc || !toggle) return;
    const wasOpen = toc.classList.contains('open');
    toc.classList.remove('open');
    document.body.classList.remove('contents-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open notebook contents');
    if (restoreFocus && wasOpen) toggle.focus();
  }

  toggle?.addEventListener('click', () => {
    if (!toc) return;
    const open = toc.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close notebook contents' : 'Open notebook contents');
    document.body.classList.toggle('contents-open', open && mobileQuery.matches);
    if (open) toc.querySelector('.toc-link')?.focus();
  });

  links.forEach(link => link.addEventListener('click', () => closeContents()));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toc?.classList.contains('open')) closeContents({ restoreFocus: true });
  });
  document.addEventListener('pointerdown', event => {
    if (mobileQuery.matches && toc?.classList.contains('open') &&
        !toc.contains(event.target) && !toggle?.contains(event.target)) closeContents();
  });
  mobileQuery.addEventListener?.('change', () => closeContents());

  // Keep the highlighted chapter comfortably inside the TOC's own scrollport.
  // Do not move the document, and give manual TOC scrolling temporary priority.
  let manualTocUntil = 0;
  let automaticTocScroll = false;
  const tocScrollport = toc?.querySelector('.toc-scroll');
  const manualTocEvent = () => {
    if (!automaticTocScroll) manualTocUntil = performance.now() + 2600;
  };
  tocScrollport?.addEventListener('wheel', manualTocEvent, { passive: true });
  tocScrollport?.addEventListener('touchstart', manualTocEvent, { passive: true });
  tocScrollport?.addEventListener('pointerdown', manualTocEvent, { passive: true });

  function revealActiveTocLink(link) {
    if (!tocScrollport || !link || mobileQuery.matches || performance.now() < manualTocUntil) return;
    const viewport = tocScrollport.getBoundingClientRect();
    const entry = link.getBoundingClientRect();
    const inset = Math.min(64, Math.max(20, viewport.height * .12));
    let delta = 0;
    if (entry.top < viewport.top + inset) delta = entry.top - viewport.top - inset;
    else if (entry.bottom > viewport.bottom - inset) delta = entry.bottom - viewport.bottom + inset;
    if (Math.abs(delta) < 1) return;
    automaticTocScroll = true;
    tocScrollport.scrollTop += delta;
    window.requestAnimationFrame(() => { automaticTocScroll = false; });
  }

  function updateActiveLink(id) {
    let activeLink = null;
    for (const link of links) {
      const active = decodeURIComponent(link.hash.slice(1)) === id;
      link.classList.toggle('active', active);
      if (active) activeLink = link;
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
    revealActiveTocLink(activeLink);
  }

  const headings = links.map(link => document.getElementById(decodeURIComponent(link.hash.slice(1)))).filter(Boolean);
  const headerOffset = () => (document.querySelector('.site-header')?.getBoundingClientRect().height || 64) + 28;
  let ticking = false;
  let activeId = '';

  function refreshReadingState() {
    ticking = false;
    updateProgress();
    if (!headings.length) return;
    const offset = headerOffset();
    let current = headings[0];
    for (const heading of headings) {
      if (heading.getBoundingClientRect().top <= offset) current = heading;
      else break;
    }
    if (activeId !== current.id) {
      activeId = current.id;
      updateActiveLink(activeId);
    }
  }
  function scheduleRefresh() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(refreshReadingState);
  }
  // Observe the chapters, with a scroll fallback for very long chapters and anchor jumps
  if ('IntersectionObserver' in window && headings.length) {
    const observer = new IntersectionObserver(scheduleRefresh, {rootMargin: '-85px 0px -70% 0px'});
    headings.forEach(heading => observer.observe(heading));
  }
  links.forEach(link => link.addEventListener('click', () => {
    activeId = decodeURIComponent(link.hash.slice(1));
    updateActiveLink(activeId);
    window.setTimeout(scheduleRefresh, 180);
  }));
  window.addEventListener('hashchange', scheduleRefresh);

  // Copy the exact source string stored by the generator, not the highlighted markup.
  // Clipboard fallback uses a temporary selectable textarea for insecure contexts.
  const copyStatus = document.createElement('span');
  copyStatus.className = 'copy-status';
  copyStatus.setAttribute('role', 'status');
  copyStatus.setAttribute('aria-live', 'polite');
  document.body.appendChild(copyStatus);
  let resetTimer;
  function selectCode(pre) {
    const range = document.createRange();
    range.selectNodeContents(pre);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }
  function legacyCopy(value) {
    const field = document.createElement('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
    document.body.appendChild(field);
    field.focus();
    field.select();
    let copied = false;
    try { copied = document.execCommand('copy'); }
    finally { field.remove(); }
    return copied;
  }
  for (const button of document.querySelectorAll('.copy-code')) {
    button.addEventListener('click', async () => {
      const pre = button.closest('.code-toolbar')?.nextElementSibling?.querySelector('pre');
      if (!pre) return;
      const encoded = button.getAttribute('data-source');
      let value = pre.textContent;
      if (encoded !== null && button.dataset.jsonEncoded === 'true') {
        try { value = JSON.parse('"' + encoded + '"'); }
        catch { value = pre.textContent; }
      }
      let copied = false;
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(value);
          copied = true;
        }
      } catch { /* Try the legacy clipboard path below */ }
      if (!copied) copied = legacyCopy(value);
      if (!copied) selectCode(pre);
      const label = copied ? 'Copied!' : 'Code selected';
      button.textContent = label;
      copyStatus.textContent = copied ? 'Python code copied to clipboard.' : 'Code selected. Press Control+C or Command+C to copy.';
      clearTimeout(resetTimer);
      resetTimer = window.setTimeout(() => { button.textContent = 'Copy code'; }, 2200);
    });
  }

  window.addEventListener('scroll', scheduleRefresh, { passive: true });
  window.addEventListener('resize', scheduleRefresh);
  scheduleRefresh();
})();
