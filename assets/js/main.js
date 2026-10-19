/* Progressive enhancement only: ordinary anchor links work without this file. */
(() => {
  const links = [...document.querySelectorAll('.sidebar nav a[href^="#"]')];
  const sections = links.map((link) => document.querySelector(link.hash));
  const header = document.querySelector('.sidebar');
  if (!header || sections.some((section) => !section)) return;

  let scheduled = false;
  const updateNavigation = () => {
    const headerOffset = window.matchMedia('(max-width: 1100px)').matches
      ? header.getBoundingClientRect().height
      : 0;
    const threshold = headerOffset + Math.min(window.innerHeight * 0.25, 180);
    let current = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= threshold) current = section;
    }
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4) {
      // Short final sections can share the same maximum scroll position.
      // Keep the clicked destination active when its start is still visible.
      const destination = sections.find((section) => {
        const top = section.getBoundingClientRect().top;
        return `#${section.id}` === window.location.hash && top >= headerOffset && top < window.innerHeight;
      });
      current = destination || sections[sections.length - 1];
    }
    for (const link of links) {
      if (link.hash === `#${current.id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
    scheduled = false;
  };
  const scheduleUpdate = () => {
    if (!scheduled) {
      scheduled = true;
      window.requestAnimationFrame(updateNavigation);
    }
  };
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', scheduleUpdate);
  window.addEventListener('hashchange', scheduleUpdate);
  updateNavigation();
})();
