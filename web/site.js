(() => {
  const escapeHtml = (value) => String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  function injectExtraStyles() {
    if (document.querySelector('link[href="/landing-extra.css"]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/landing-extra.css';
    document.head.appendChild(link);
  }

  const text = (selector, value) => {
    const node = document.querySelector(selector);
    if (node && value !== undefined && value !== null && String(value).trim()) {
      node.textContent = value;
    }
  };

  const setMetric = (name, value, suffix = '+') => {
    const node = document.querySelector(`[data-metric="${name}"]`);
    if (!node || value === undefined || value === null) return;
    const number = Number(value);
    node.textContent = Number.isFinite(number)
      ? `${number.toLocaleString('ru-RU')}${suffix}`
      : String(value);
  };

  const renderTextBlock = (selector, value) => {
    const node = document.querySelector(selector);
    if (!node || !value) return;
    const parts = String(value).split(/\n{2,}/).map((part) => part.trim()).filter(Boolean);
    node.innerHTML = parts.map((part) => `<p>${escapeHtml(part)}</p>`).join('');
  };

  const initials = (name) => String(name || 'AC')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();

  function renderLogo(settings) {
    const logos = document.querySelectorAll('[data-site-logo]');
    if (!logos.length) return;

    const logoUrl = settings.logo_file_url || settings.logo_url;
    if (logoUrl) {
      logos.forEach((logo) => {
        logo.classList.add('has-image');
        logo.innerHTML = `<img src="${escapeHtml(logoUrl)}" alt="${escapeHtml(settings.company_name || 'Akyl Cheshmesi')}">`;
      });
      return;
    }

    const staticLogo = new Image();
    staticLogo.onload = () => {
      logos.forEach((logo) => {
        logo.classList.add('has-image');
        logo.innerHTML = '<img src="/assets/akyl-logo.png" alt="Akyl Cheshmesi">';
      });
    };
    staticLogo.src = '/assets/akyl-logo.png';
  }

  function renderTeam(team) {
    const root = document.querySelector('[data-team-list]');
    if (!root) return;

    if (!team.length) {
      root.innerHTML = '<div class="team-empty">Команда будет отображаться после заполнения раздела в админке.</div>';
      return;
    }

    root.innerHTML = team.slice(0, 8).map((member) => {
      const photo = member.photo_url
        ? `<img src="${escapeHtml(member.photo_url)}" alt="${escapeHtml(member.full_name)}">`
        : escapeHtml(initials(member.full_name));
      return `<article class="team-card reveal visible">
        <div class="team-photo">${photo}</div>
        <h4>${escapeHtml(member.full_name)}</h4>
        <div class="role">${escapeHtml(member.role || member.team_label || '')}</div>
        <p>${escapeHtml(member.bio || member.team_label || '')}</p>
      </article>`;
    }).join('');
  }

  async function loadWebsiteContent() {
    const root = document.documentElement;
    if (!root.hasAttribute('data-dynamic-site')) return;

    try {
      const response = await fetch('/api/website/content/');
      if (!response.ok) return;
      const data = await response.json();
      const settings = data.settings || {};
      const team = Array.isArray(data.team) ? data.team : [];
      const metrics = data.metrics || {};

      text('[data-site-company]', settings.company_name || 'Akyl Cheshmesi');
      text('[data-site-director]', settings.director_name ? `Гендиректор: ${settings.director_name}` : '');
      text('[data-site-hero-title]', settings.hero_title);
      text('[data-site-hero-subtitle]', settings.hero_subtitle);
      text('[data-site-about]', settings.about_company);
      text('[data-site-translations]', settings.translation_company_text);
      text('[data-site-students-life]', settings.students_life_text);
      text('[data-site-security]', settings.security_text);
      renderTextBlock('[data-privacy-policy]', settings.privacy_policy);
      renderTextBlock('[data-terms-of-use]', settings.terms_of_use);
      renderLogo(settings);

      setMetric('countries', metrics.countries);
      setMetric('happy_clients', metrics.happy_clients);
      setMetric('translated_documents', metrics.translated_documents);
      setMetric('registered_users', metrics.registered_users, '');

      const googlePlay = document.querySelector('[data-google-play-link]');
      if (googlePlay && settings.google_play_url) googlePlay.href = settings.google_play_url;
      const testflight = document.querySelector('[data-testflight-link]');
      if (testflight && settings.testflight_url) testflight.href = settings.testflight_url;

      renderTeam(team);
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

  function initReveal() {
    const items = document.querySelectorAll('.reveal');
    if (!items.length) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add('visible');
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    items.forEach((item) => observer.observe(item));
  }

  injectExtraStyles();
  loadWebsiteContent();
  loadReleases();
  bindSupportForm();
  initReveal();
})();
