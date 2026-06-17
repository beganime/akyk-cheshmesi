(() => {
  const escapeHtml = (value) => String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const text = (selector, value) => {
    const node = document.querySelector(selector);
    if (node && value) node.textContent = value;
  };

  const renderTextBlock = (selector, value) => {
    const node = document.querySelector(selector);
    if (!node || !value) return;
    const parts = String(value).split(/\n{2,}/).map((part) => part.trim()).filter(Boolean);
    node.innerHTML = parts.map((part) => `<p>${escapeHtml(part)}</p>`).join('');
  };

  async function loadWebsiteContent() {
    const root = document.documentElement;
    if (!root.hasAttribute('data-dynamic-site')) return;

    try {
      const response = await fetch('/api/website/content/');
      if (!response.ok) return;
      const data = await response.json();
      const settings = data.settings || {};
      const team = Array.isArray(data.team) ? data.team : [];

      text('[data-site-company]', settings.company_name);
      text('[data-site-director]', settings.director_name ? `Гендиректор: ${settings.director_name}` : '');
      text('[data-site-hero-title]', settings.hero_title);
      text('[data-site-hero-subtitle]', settings.hero_subtitle);
      text('[data-site-about]', settings.about_company);
      text('[data-site-translations]', settings.translation_company_text);
      text('[data-site-students-life]', settings.students_life_text);
      text('[data-site-security]', settings.security_text);
      renderTextBlock('[data-privacy-policy]', settings.privacy_policy);
      renderTextBlock('[data-terms-of-use]', settings.terms_of_use);

      const logo = document.querySelector('[data-site-logo]');
      const logoUrl = settings.logo_file_url || settings.logo_url;
      if (logo && logoUrl) {
        logo.innerHTML = `<img src="${escapeHtml(logoUrl)}" alt="${escapeHtml(settings.company_name || 'Akyl Cheshmesi')}" />`;
      }

      const googlePlay = document.querySelector('[data-google-play-link]');
      if (googlePlay && settings.google_play_url) googlePlay.href = settings.google_play_url;
      const testflight = document.querySelector('[data-testflight-link]');
      if (testflight && settings.testflight_url) testflight.href = settings.testflight_url;

      const teamRoot = document.querySelector('[data-team-list]');
      if (teamRoot && team.length) {
        teamRoot.innerHTML = team.slice(0, 8).map((member) => (
          `<article class="bento-card"><h3>${escapeHtml(member.full_name)}</h3><p>${escapeHtml(member.role || member.team_label || '')}</p><p>${escapeHtml(member.bio || '')}</p></article>`
        )).join('');
      }
    } catch (_) {}
  }

  async function loadReleases() {
    const root = document.querySelector('[data-release-list]');
    if (!root) return;

    try {
      const response = await fetch('/api/app-releases/');
      if (!response.ok) return;
      const data = await response.json();
      const releases = Array.isArray(data) ? data : (data.results || []);
      if (!releases.length) return;

      root.innerHTML = releases.slice(0, 4).map((item) => {
        const url = item.resolved_download_url || item.download_url || item.google_play_url || item.testflight_url || '#';
        const title = `${item.platform || 'app'} ${item.version || ''}`.trim();
        const subtitle = `${item.channel || 'testing'} · ${item.store_status || 'draft'}`;
        return `<a class="download-card" href="${escapeHtml(url)}"><strong>${escapeHtml(title)}</strong><small>${escapeHtml(subtitle)}</small></a>`;
      }).join('');
    } catch (_) {}
  }

  function bindSupportForm() {
    const form = document.querySelector('[data-support-form]');
    const status = document.querySelector('[data-form-status]');
    if (!form) return;

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (status) status.textContent = 'Отправляем заявку...';

      const payload = Object.fromEntries(new FormData(form).entries());
      try {
        const response = await fetch('/api/website/support/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.message || 'Не удалось отправить заявку');
        form.reset();
        if (status) status.textContent = data.message || 'Заявка принята.';
      } catch (error) {
        if (status) status.textContent = error.message || 'Ошибка отправки заявки';
      }
    });
  }

  loadWebsiteContent();
  loadReleases();
  bindSupportForm();
})();
