(function () {
  const apiBase = "/api";
  const accessKey = "akyl_access";
  const refreshKey = "akyl_refresh";
  const themeKey = "akyl_theme";

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    });
  }

  function getAccess() {
    return localStorage.getItem(accessKey);
  }

  let refreshPromise = null;

  async function refreshAccessToken() {
    const refresh = localStorage.getItem(refreshKey);
    if (!refresh) return false;
    if (!refreshPromise) {
      refreshPromise = fetch(`${apiBase}/auth/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      }).then(async (response) => {
        if (!response.ok) return false;
        const data = await response.json();
        if (!data.access) return false;
        localStorage.setItem(accessKey, data.access);
        if (data.refresh) localStorage.setItem(refreshKey, data.refresh);
        return true;
      }).catch(() => false).finally(() => {
        refreshPromise = null;
      });
    }
    return refreshPromise;
  }

  async function api(path, options = {}, canRetry = true) {
    const headers = { ...(options.headers || {}) };
    const token = getAccess();

    if (token) headers.Authorization = `Bearer ${token}`;
    if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";

    const response = await fetch(`${apiBase}${path}`, { ...options, headers });

    if (response.status === 401 && canRetry && await refreshAccessToken()) {
      return api(path, options, false);
    }

    if (response.status === 401) {
      localStorage.removeItem(accessKey);
      localStorage.removeItem(refreshKey);
      window.location.href = "/login/";
      return null;
    }

    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (error) {
      data = { detail: text || response.statusText || "Request failed" };
    }

    if (!response.ok) {
      const message = data && (data.detail || data.message || firstApiError(data) || JSON.stringify(data));
      throw new Error(message || "Request failed");
    }

    return data;
  }

  function firstApiError(data) {
    if (!data || typeof data !== "object") return "";
    for (const value of Object.values(data)) {
      if (Array.isArray(value) && value.length) return String(value[0]);
      if (typeof value === "string") return value;
    }
    return "";
  }

  function initAuth() {
    const form = document.getElementById("loginForm");
    if (!form) return;

    if (getAccess()) window.location.href = "/messenger/";

    const message = document.getElementById("loginMessage");
    const submitButton = form.querySelector('button[type="submit"]');
    const loginTab = document.getElementById("loginTab");
    const registerTab = document.getElementById("registerTab");
    const registerEmailForm = document.getElementById("registerEmailForm");
    const registerCodeForm = document.getElementById("registerCodeForm");
    const registerProfileForm = document.getElementById("registerProfileForm");
    const authTitle = document.getElementById("authTitle");
    const authDescription = document.getElementById("authDescription");
    const registration = { email: "", verificationToken: "" };

    function setAuthMode(mode) {
      const isLogin = mode === "login";
      loginTab?.classList.toggle("active", isLogin);
      registerTab?.classList.toggle("active", !isLogin);
      loginTab?.setAttribute("aria-selected", String(isLogin));
      registerTab?.setAttribute("aria-selected", String(!isLogin));
      form.hidden = !isLogin;
      form.classList.toggle("active", isLogin);
      registerEmailForm.hidden = isLogin;
      registerEmailForm.classList.toggle("active", !isLogin);
      registerCodeForm.hidden = true;
      registerCodeForm.classList.remove("active");
      registerProfileForm.hidden = true;
      registerProfileForm.classList.remove("active");
      authTitle.textContent = isLogin ? "Добро пожаловать" : "Создать аккаунт";
      authDescription.textContent = isLogin
        ? "Войдите с email или username от мобильного приложения."
        : "Регистрация займёт три коротких шага.";
    }

    function showRegisterStep(step) {
      [registerEmailForm, registerCodeForm, registerProfileForm].forEach((item, index) => {
        const active = index + 1 === step;
        item.hidden = !active;
        item.classList.toggle("active", active);
      });
    }

    loginTab?.addEventListener("click", () => setAuthMode("login"));
    registerTab?.addEventListener("click", () => setAuthMode("register"));
    document.getElementById("registerBackToEmail")?.addEventListener("click", () => showRegisterStep(1));

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      message.textContent = "Входим...";
      if (submitButton) submitButton.disabled = true;

      const identifier = document.getElementById("email").value.trim();
      const payload = {
        email: identifier,
        identifier,
        password: document.getElementById("password").value,
      };

      try {
        const data = await api("/auth/login/", {
          method: "POST",
          body: JSON.stringify(payload),
        });

        localStorage.setItem(accessKey, data.tokens.access);
        localStorage.setItem(refreshKey, data.tokens.refresh);
        window.location.href = "/messenger/";
      } catch (error) {
        message.textContent = error.message || "Не удалось войти";
      } finally {
        if (submitButton) submitButton.disabled = false;
      }
    });

    registerEmailForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("registerEmailMessage");
      const button = registerEmailForm.querySelector('button[type="submit"]');
      registration.email = document.getElementById("registerEmail").value.trim().toLowerCase();
      status.textContent = "Отправляем код…";
      button.disabled = true;
      try {
        await api("/auth/register/", { method: "POST", body: JSON.stringify({ email: registration.email }) });
        document.getElementById("registerCodeHint").textContent = `Код отправлен на ${registration.email}`;
        status.textContent = "";
        showRegisterStep(2);
        document.getElementById("registerCode").focus();
      } catch (error) {
        status.textContent = error.message || "Не удалось отправить код";
      } finally {
        button.disabled = false;
      }
    });

    registerCodeForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("registerCodeMessage");
      const button = registerCodeForm.querySelector('button[type="submit"]');
      status.textContent = "Проверяем код…";
      button.disabled = true;
      try {
        const data = await api("/auth/verify-email/", {
          method: "POST",
          body: JSON.stringify({ email: registration.email, code: document.getElementById("registerCode").value.trim() }),
        });
        registration.verificationToken = data.verification_token;
        status.textContent = "";
        showRegisterStep(3);
        document.getElementById("registerUsername").focus();
      } catch (error) {
        status.textContent = error.message || "Неверный или просроченный код";
      } finally {
        button.disabled = false;
      }
    });

    registerProfileForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("registerProfileMessage");
      const button = registerProfileForm.querySelector('button[type="submit"]');
      const password = document.getElementById("registerPassword").value;
      const passwordConfirm = document.getElementById("registerPasswordConfirm").value;
      status.textContent = "Создаём аккаунт…";
      button.disabled = true;
      try {
        const data = await api("/auth/set-password/", {
          method: "POST",
          body: JSON.stringify({
            verification_token: registration.verificationToken,
            username: document.getElementById("registerUsername").value.trim(),
            first_name: document.getElementById("registerFirstName").value.trim(),
            last_name: document.getElementById("registerLastName").value.trim(),
            password,
            password_confirm: passwordConfirm,
          }),
        });
        localStorage.setItem(accessKey, data.tokens.access);
        localStorage.setItem(refreshKey, data.tokens.refresh);
        window.location.href = "/messenger/";
      } catch (error) {
        status.textContent = error.message || "Не удалось завершить регистрацию";
      } finally {
        button.disabled = false;
      }
    });
  }

  function initMessenger() {
    const app = document.querySelector(".messenger-app");
    if (!app) return;

    if (!getAccess()) {
      window.location.href = "/login/";
      return;
    }

    const state = {
      me: null,
      chats: [],
      contacts: [],
      searchUsers: [],
      stories: [],
      activeChat: null,
      activeTab: "chats",
      socket: null,
      storyTimer: null,
      storyFile: null,
      renderedMessageUuids: new Set(),
      currentCall: null,
      peerConnection: null,
      localStream: null,
      remoteStream: null,
      pendingOffer: null,
      pendingIce: [],
      callDurationTimer: null,
      callStartedAt: null,
      iceServers: null,
      socketReconnectTimer: null,
      socketReconnectAttempts: 0,
      cache: null,
      webPushSubscribed: false,
      chatRefreshTimer: null,
      lastChatRefreshAt: 0,
    };

    const $ = (id) => document.getElementById(id);

    const elements = {
      sidebar: $("chatSidebar"),
      rightPanel: $("rightPanel"),
      list: $("chatList"),
      stories: $("storiesStrip"),
      feedView: $("feedView"),
      feedList: $("feedList"),
      feedBackButton: $("feedBackButton"),
      search: $("chatSearch"),
      tabs: Array.from(document.querySelectorAll(".tab[data-tab]")),
      emptyState: $("emptyState"),
      chatView: $("chatView"),
      messages: $("messages"),
      title: $("activeChatTitle"),
      status: $("activeChatStatus"),
      avatar: $("activeAvatar"),
      messageForm: $("messageForm"),
      messageInput: $("messageInput"),
      fileInput: $("fileInput"),
      attachButton: $("attachButton"),
      audioCallButton: $("audioCallButton"),
      videoCallButton: $("videoCallButton"),
      menuToggle: $("menuToggle"),
      drawer: $("drawer"),
      drawerOverlay: $("drawerOverlay"),
      drawerClose: $("drawerClose"),
      logoutButton: $("logoutButton"),
      themeToggle: $("themeToggle"),
      currentThemeLabel: $("currentThemeLabel"),
      drawerAvatar: $("drawerAvatar"),
      drawerName: $("drawerName"),
      drawerPhone: $("drawerPhone"),
      drawerUsername: $("drawerUsername"),
      addStoryButton: $("addStoryButton"),
      addStoryModal: $("addStoryModal"),
      addStoryModalClose: $("addStoryModalClose"),
      cancelStoryButton: $("cancelStoryButton"),
      publishStoryButton: $("publishStoryButton"),
      storyFileInput: $("storyFileInput"),
      imageUploadArea: $("imageUploadArea"),
      imagePreview: $("imagePreview"),
      videoPreview: $("videoPreview"),
      removeImageButton: $("removeImageButton"),
      storyTextInput: $("storyTextInput"),
      storyViewer: $("storyViewer"),
      storyViewerAvatar: $("storyViewerAvatar"),
      storyViewerName: $("storyViewerName"),
      storyViewerTime: $("storyViewerTime"),
      storyViewerText: $("storyViewerText"),
      storyViewerImage: $("storyViewerImage"),
      storyViewerVideo: $("storyViewerVideo"),
      storyViewerClose: $("storyViewerClose"),
      storyProgressFill: $("storyProgressFill"),
      callModal: $("callModal"),
      callModalTitle: $("callModalTitle"),
      callModalSubtitle: $("callModalSubtitle"),
      callModalAvatar: $("callModalAvatar"),
      callModalClose: $("callModalClose"),
      callAcceptButton: $("callAcceptButton"),
      callDeclineButton: $("callDeclineButton"),
      callHangupButton: $("callHangupButton"),
      callMuteButton: $("callMuteButton"),
      callCameraButton: $("callCameraButton"),
      callDuration: $("callDuration"),
      localVideo: $("localVideo"),
      remoteVideo: $("remoteVideo"),
      toast: $("toast"),
      backToChats: $("backToChats"),
      notificationButton: $("notificationButton"),
      notificationDot: $("notificationDot"),
      newChatButton: $("newChatButton"),
      profileButton: $("profileButton"),
      profileModal: $("profileModal"),
      profileForm: $("profileForm"),
      profileModalClose: $("profileModalClose"),
      profileCancelButton: $("profileCancelButton"),
      profileAvatar: $("profileAvatar"),
      profileAvatarPreview: $("profileAvatarPreview"),
      profileFirstName: $("profileFirstName"),
      profileLastName: $("profileLastName"),
      profileBio: $("profileBio"),
    };

    let toastTimeout = null;
    let contactSearchTimeout = null;

    initTheme();
    bindEvents();
    bootstrap().catch((error) => {
      elements.messages.innerHTML = `<div class="empty-state"><div class="empty-state-box">${escapeHtml(error.message)}</div></div>`;
      showToast(error.message);
    });

    function bindEvents() {
      elements.logoutButton?.addEventListener("click", logout);
      elements.menuToggle?.addEventListener("click", openDrawer);
      elements.drawerClose?.addEventListener("click", closeDrawer);
      elements.drawerOverlay?.addEventListener("click", closeDrawer);
      elements.backToChats?.addEventListener("click", () => {
        elements.sidebar.classList.remove("hidden-mobile");
        elements.rightPanel.classList.remove("mobile-open");
      });
      elements.feedBackButton?.addEventListener("click", () => {
        elements.sidebar.classList.remove("hidden-mobile");
        elements.rightPanel.classList.remove("mobile-open");
      });

      elements.themeToggle?.addEventListener("click", toggleTheme);
      elements.notificationButton?.addEventListener("click", enableBrowserNotifications);
      elements.newChatButton?.addEventListener("click", openUserSearch);
      elements.profileButton?.addEventListener("click", openProfileModal);
      elements.profileModalClose?.addEventListener("click", closeProfileModal);
      elements.profileCancelButton?.addEventListener("click", closeProfileModal);
      elements.profileForm?.addEventListener("submit", saveProfile);
      elements.profileAvatar?.addEventListener("change", previewProfileAvatar);
      elements.profileModal?.addEventListener("click", (event) => {
        if (event.target === elements.profileModal) closeProfileModal();
      });
      document.querySelectorAll(".drawer-item[data-action]").forEach((item) => {
        item.addEventListener("click", (event) => {
          const action = item.dataset.action;
          if (action === "theme") {
            toggleTheme();
          }
          closeDrawer();
        });
      });

      elements.tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
          state.activeTab = tab.dataset.tab || "chats";
          elements.tabs.forEach((item) => item.classList.toggle("active", item === tab));
          updateSearchPlaceholder();
          renderList();
        });
      });

      elements.search?.addEventListener("input", () => {
        if (state.activeTab === "contacts") scheduleUserSearch();
        renderList();
      });

      elements.messageInput?.addEventListener("input", autoResizeMessageInput);
      elements.messageInput?.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
        event.preventDefault();
        elements.messageForm?.requestSubmit();
      });
      elements.messageForm?.addEventListener("submit", sendTextMessage);
      elements.attachButton?.addEventListener("click", () => elements.fileInput.click());
      elements.fileInput?.addEventListener("change", sendPickedFile);
      elements.audioCallButton?.addEventListener("click", () => createCall("audio"));
      elements.videoCallButton?.addEventListener("click", () => createCall("video"));
      elements.callAcceptButton?.addEventListener("click", acceptIncomingCall);
      elements.callDeclineButton?.addEventListener("click", declineIncomingCall);
      elements.callHangupButton?.addEventListener("click", endCurrentCall);
      elements.callMuteButton?.addEventListener("click", toggleCallAudio);
      elements.callCameraButton?.addEventListener("click", toggleCallVideo);
      elements.callModalClose?.addEventListener("click", requestCallClose);
      elements.callModal?.addEventListener("click", (event) => {
        if (event.target === elements.callModal) requestCallClose();
      });

      elements.addStoryButton?.addEventListener("click", openAddStoryModal);
      elements.addStoryModalClose?.addEventListener("click", closeAddStoryModal);
      elements.cancelStoryButton?.addEventListener("click", closeAddStoryModal);
      elements.addStoryModal?.addEventListener("click", (event) => {
        if (event.target === elements.addStoryModal) closeAddStoryModal();
      });
      elements.imageUploadArea?.addEventListener("click", (event) => {
        if (event.target === elements.removeImageButton || elements.removeImageButton.contains(event.target)) return;
        elements.storyFileInput.click();
      });
      elements.imageUploadArea?.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          elements.storyFileInput.click();
        }
      });
      elements.storyFileInput?.addEventListener("change", previewStoryFile);
      elements.removeImageButton?.addEventListener("click", (event) => {
        event.stopPropagation();
        clearStoryFile();
      });
      elements.publishStoryButton?.addEventListener("click", publishStory);
      elements.storyViewerClose?.addEventListener("click", closeStoryViewer);
      elements.storyViewer?.addEventListener("click", (event) => {
        if (event.target === elements.storyViewer) closeStoryViewer();
      });
    }

    async function bootstrap() {
      state.me = await api("/users/me/");
      state.cache = window.AkylStore?.scope(state.me.uuid) || null;
      renderMe();
      await hydrateCache();
      void loadIceServers();
      await Promise.allSettled([loadStories(), loadContacts(), loadChats()]);
      connectSocket();
      void refreshBrowserNotificationState();
      const requestedChat = new URLSearchParams(window.location.search).get("chat");
      if (requestedChat && state.chats.some((chat) => String(chat.uuid) === requestedChat)) {
        await openChat(requestedChat);
      }
    }

    async function hydrateCache() {
      if (!state.cache) return;
      const [chats, contacts, stories] = await Promise.all([
        state.cache.get("chats"),
        state.cache.get("contacts"),
        state.cache.get("stories"),
      ]);
      if (Array.isArray(chats)) {
        state.chats = chats;
        renderList();
      }
      if (Array.isArray(contacts)) state.contacts = contacts;
      if (Array.isArray(stories)) {
        state.stories = stories;
        renderStories();
      }
    }

    async function logout() {
      try {
        if ("serviceWorker" in navigator && "PushManager" in window) {
          const registration = await navigator.serviceWorker.ready;
          const subscription = await registration.pushManager.getSubscription();
          if (subscription) {
            await api("/web-push/subscriptions/", {
              method: "DELETE",
              body: JSON.stringify({ endpoint: subscription.endpoint }),
            });
            await subscription.unsubscribe();
          }
        }
        await api("/auth/logout/", {
          method: "POST",
          body: JSON.stringify({ refresh: localStorage.getItem(refreshKey) || "" }),
        });
      } catch (error) {
        console.warn("logout cleanup error", error);
      } finally {
        localStorage.removeItem(accessKey);
        localStorage.removeItem(refreshKey);
        window.location.href = "/login/";
      }
    }

    function initTheme() {
      const savedTheme = localStorage.getItem(themeKey);
      setTheme(savedTheme || "dark");
    }

    function setTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem(themeKey, theme);
      if (elements.currentThemeLabel) elements.currentThemeLabel.textContent = theme === "light" ? "Светлая" : "Тёмная";
    }

    function toggleTheme() {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      setTheme(next);
      showToast(next === "light" ? "Включен дневной режим" : "Включен ночной режим");
    }

    function openDrawer() {
      elements.drawer.classList.add("active");
      elements.drawerOverlay.classList.add("active");
    }

    function closeDrawer() {
      elements.drawer.classList.remove("active");
      elements.drawerOverlay.classList.remove("active");
    }

    function renderMe() {
      const name = displayUserName(state.me);
      elements.drawerAvatar.innerHTML = avatarContent(state.me, name);
      elements.drawerName.textContent = name;
      elements.drawerPhone.textContent = state.me?.phone || state.me?.phone_number || state.me?.email || "—";
      elements.drawerUsername.textContent = state.me?.username ? `@${state.me.username}` : "@user";
    }

    function openProfileModal() {
      closeDrawer();
      elements.profileFirstName.value = state.me?.first_name || "";
      elements.profileLastName.value = state.me?.last_name || "";
      elements.profileBio.value = state.me?.bio || "";
      elements.profileAvatar.value = "";
      elements.profileAvatarPreview.innerHTML = avatarContent(state.me, displayUserName(state.me));
      elements.profileModal.classList.add("active");
    }

    function closeProfileModal() {
      elements.profileModal?.classList.remove("active");
      elements.profileAvatar.value = "";
    }

    function previewProfileAvatar(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      elements.profileAvatarPreview.innerHTML = `<img src="${escapeAttr(URL.createObjectURL(file))}" alt="">`;
    }

    async function saveProfile(event) {
      event.preventDefault();
      const submitButton = elements.profileForm.querySelector('button[type="submit"]');
      const formData = new FormData();
      formData.append("first_name", elements.profileFirstName.value.trim());
      formData.append("last_name", elements.profileLastName.value.trim());
      formData.append("bio", elements.profileBio.value.trim());
      if (elements.profileAvatar.files?.[0]) formData.append("avatar", elements.profileAvatar.files[0]);
      submitButton.disabled = true;
      try {
        state.me = await api("/users/me/", { method: "PATCH", body: formData });
        renderMe();
        closeProfileModal();
        showToast("Профиль обновлён");
      } catch (error) {
        showToast(error.message || "Не удалось обновить профиль");
      } finally {
        submitButton.disabled = false;
      }
    }

    function browserDeviceId() {
      const key = "akyl_web_device_id";
      let value = localStorage.getItem(key);
      if (!value) {
        value = crypto.randomUUID();
        localStorage.setItem(key, value);
      }
      return value;
    }

    function applicationServerKey(value) {
      const padding = "=".repeat((4 - value.length % 4) % 4);
      const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
      const raw = atob(base64);
      return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
    }

    async function refreshBrowserNotificationState() {
      if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
        elements.notificationButton.hidden = true;
        return;
      }
      try {
        const registration = await navigator.serviceWorker.ready;
        state.webPushSubscribed = Boolean(await registration.pushManager.getSubscription());
      } catch (error) {
        state.webPushSubscribed = false;
      }
      elements.notificationButton.classList.toggle("active", state.webPushSubscribed);
      elements.notificationDot.classList.toggle("active", state.webPushSubscribed);
      elements.notificationButton.title = state.webPushSubscribed ? "Уведомления включены" : "Включить уведомления";
    }

    async function enableBrowserNotifications() {
      if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
        showToast("Этот браузер не поддерживает push-уведомления");
        return;
      }
      try {
        const config = await api("/web-push/config/");
        if (!config?.enabled || !config.public_key) throw new Error("Web Push пока не настроен на сервере");
        const permission = await Notification.requestPermission();
        if (permission !== "granted") throw new Error("Разрешите уведомления в настройках браузера");
        const registration = await navigator.serviceWorker.ready;
        let subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
          subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: applicationServerKey(config.public_key),
          });
        }
        const payload = subscription.toJSON();
        await api("/web-push/subscriptions/", {
          method: "POST",
          body: JSON.stringify({ ...payload, device_id: browserDeviceId() }),
        });
        state.webPushSubscribed = true;
        await refreshBrowserNotificationState();
        showToast("Уведомления включены");
      } catch (error) {
        showToast(error.message || "Не удалось включить уведомления");
      }
    }

    async function loadChats() {
      if (!state.chats.length) elements.list.innerHTML = `<div class="loading-state"><div class="loading-pulse"></div><div>Загружаем чаты...</div></div>`;
      const data = await api("/chats/");
      state.chats = normalizePage(data);
      state.lastChatRefreshAt = Date.now();
      void state.cache?.set("chats", state.chats);
      renderList();
    }

    async function loadContacts() {
      try {
        const data = await api("/users/contacts/");
        state.contacts = normalizePage(data).map((item) => item.user || item).filter(Boolean);
        void state.cache?.set("contacts", state.contacts);
      } catch (error) {
        console.warn("contacts load error", error);
        state.contacts = [];
      }
    }

    async function loadStories() {
      try {
        const data = await api("/stories/");
        state.stories = normalizePage(data);
        void state.cache?.set("stories", state.stories);
      } catch (error) {
        console.warn("stories load error", error);
        state.stories = [];
      }
      renderStories();
      if (state.activeTab === "feed") renderFeed();
    }

    function scheduleUserSearch() {
      clearTimeout(contactSearchTimeout);
      const query = elements.search.value.trim();
      if (query.length < 2) {
        state.searchUsers = [];
        renderList();
        return;
      }
      contactSearchTimeout = setTimeout(async () => {
        try {
          const data = await api(`/users/search/?q=${encodeURIComponent(query)}`);
          state.searchUsers = Array.isArray(data) ? data : normalizePage(data);
        } catch (error) {
          state.searchUsers = [];
        }
        if (state.activeTab === "contacts") renderList();
      }, 260);
    }

    function renderList() {
      const feedActive = state.activeTab === "feed";
      elements.feedView?.classList.toggle("active", feedActive);
      if (feedActive) {
        elements.emptyState.style.display = "none";
        elements.chatView.classList.remove("active");
        elements.sidebar.classList.add("hidden-mobile");
        elements.rightPanel.classList.add("mobile-open");
        renderFeed();
      } else {
        if (state.activeChat) elements.chatView.classList.add("active");
        else elements.emptyState.style.display = "grid";
        if (state.activeTab === "contacts") renderContacts();
        else renderChats();
      }
    }

    function updateSearchPlaceholder() {
      if (!elements.search) return;
      elements.search.placeholder = state.activeTab === "contacts"
        ? "Найти пользователя"
        : state.activeTab === "chats" ? "Поиск по чатам" : "Поиск";
    }

    function openUserSearch() {
      state.activeTab = "contacts";
      state.searchUsers = [];
      elements.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === "contacts"));
      elements.search.value = "";
      updateSearchPlaceholder();
      renderList();
      elements.search.focus();
    }

    function renderFeed() {
      if (!elements.feedList) return;
      const stories = [...state.stories].sort(
        (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
      );
      if (!stories.length) {
        elements.feedList.innerHTML = emptyListHtml(
          "fa-newspaper",
          "В ленте пока тихо",
          "Опубликуйте первую историю"
        );
        return;
      }

      elements.feedList.innerHTML = stories.map((story) => {
        const author = getStoryAuthor(story);
        const name = story.is_own ? "Моя история" : displayUserName(author || story);
        const mediaUrl = story.media?.file_url || story.file_url || "";
        const isVideo = story.media_type === "video" || String(story.media?.content_type || "").startsWith("video/");
        const media = mediaUrl
          ? isVideo
            ? `<video class="feed-card-media" src="${escapeAttr(mediaUrl)}" muted playsinline preload="metadata"></video>`
            : `<img class="feed-card-media" src="${escapeAttr(mediaUrl)}" alt="">`
          : "";
        return `<button class="feed-card" type="button" data-feed-story="${escapeAttr(story.uuid)}">
          <header><div class="story-viewer-avatar">${avatarContent(author, name)}</div><div><strong>${escapeHtml(name)}</strong><span>${escapeHtml(relativeTime(story.created_at))}</span></div></header>
          ${media}
          ${story.caption ? `<p>${escapeHtml(story.caption)}</p>` : ""}
        </button>`;
      }).join("");

      elements.feedList.querySelectorAll("[data-feed-story]").forEach((button) => {
        button.addEventListener("click", () => {
          const story = state.stories.find((item) => item.uuid === button.dataset.feedStory);
          if (story) openStoryViewer(story);
        });
      });
    }

    function renderChats() {
      const query = elements.search.value.trim().toLowerCase();
      const chats = state.chats.filter((chat) => {
        const title = chatTitle(chat).toLowerCase();
        const preview = messagePreview(chat).toLowerCase();
        const peer = chat.peer_user || {};
        const username = String(peer.username || "").toLowerCase();
        const phone = String(peer.phone || peer.phone_number || "").toLowerCase();
        return !query || title.includes(query) || preview.includes(query) || username.includes(query) || phone.includes(query);
      }).sort(sortChats);

      if (!chats.length) {
        elements.list.innerHTML = emptyListHtml("fa-magnifying-glass", "Ничего не найдено", "Попробуйте изменить запрос");
        return;
      }

      elements.list.innerHTML = chats.map((chat) => {
        const title = chatTitle(chat);
        const active = state.activeChat && state.activeChat.uuid === chat.uuid ? " active" : "";
        const unread = Number(chat.unread_count || 0);
        const pinned = chat.is_pinned ? `<i class="fa-solid fa-thumbtack chat-item-pin"></i>` : "";
        const badge = unread > 0 ? `<div class="unread-badge">${unread > 99 ? "99+" : unread}</div>` : "";
        const time = formatChatTime(chat.last_message_at || chat.updated_at || chat.created_at);
        return `<button class="chat-item${active}" data-chat="${escapeAttr(chat.uuid)}" type="button">
          <div class="chat-item-avatar">${avatarContent(chat.peer_user, title)}</div>
          <div class="chat-item-content">
            <div class="chat-item-top">
              <div class="chat-item-name">${escapeHtml(title)}</div>
              <div class="chat-item-time">${escapeHtml(time)}</div>
            </div>
            <div class="chat-item-bottom">
              <div class="chat-item-preview"><span>${escapeHtml(messagePreview(chat))}</span></div>
              ${pinned}${badge}
            </div>
          </div>
        </button>`;
      }).join("");

      elements.list.querySelectorAll("[data-chat]").forEach((button) => {
        button.addEventListener("click", () => openChat(button.dataset.chat));
      });
    }

    function renderContacts() {
      const query = elements.search.value.trim().toLowerCase();
      const base = query.length >= 2 ? state.searchUsers : state.contacts;
      const contacts = base.filter((user) => {
        const name = displayUserName(user).toLowerCase();
        const username = String(user.username || "").toLowerCase();
        const phone = String(user.phone || user.phone_number || "").toLowerCase();
        const email = String(user.email || "").toLowerCase();
        return !query || name.includes(query) || username.includes(query) || phone.includes(query) || email.includes(query);
      });

      if (!contacts.length) {
        elements.list.innerHTML = emptyListHtml("fa-user-slash", "Контакты не найдены", "Введите номер телефона или @никнейм");
        return;
      }

      const online = contacts.filter((item) => Boolean(item.is_online || item.online));
      const offline = contacts.filter((item) => !Boolean(item.is_online || item.online));

      const renderGroup = (label, items) => {
        if (!items.length) return "";
        return `<div class="section-label">${label} — ${items.length}</div>${items.map(renderContactItem).join("")}`;
      };

      elements.list.innerHTML = renderGroup("В сети", online) + renderGroup(online.length ? "Не в сети" : "Контакты", offline);

      elements.list.querySelectorAll("[data-user]").forEach((button) => {
        button.addEventListener("click", () => startDirectChat(button.dataset.user));
      });
    }

    function renderContactItem(user) {
      const name = displayUserName(user);
      const username = user.username ? `@${user.username}` : user.email || "@user";
      const phone = user.phone || user.phone_number || "";
      const online = user.is_online || user.online;

      return `<button class="contact-item" data-user="${escapeAttr(user.uuid)}" type="button">
        <div class="contact-item-avatar ${online ? "online" : ""}">${avatarContent(user, name)}</div>
        <div class="contact-item-content">
          <div class="contact-item-name">${escapeHtml(name)}</div>
          <div class="contact-item-username">${escapeHtml(username)}</div>
          <div class="contact-item-phone">${escapeHtml(phone || "Нажмите, чтобы начать чат")}</div>
        </div>
        <span class="contact-item-action"><i class="fa-solid fa-message"></i></span>
      </button>`;
    }

    async function startDirectChat(userUuid) {
      if (!userUuid) return;
      try {
        let chat;
        try {
          chat = await api("/chats/", {
            method: "POST",
            body: JSON.stringify({ type: "private", peer_uuid: userUuid }),
          });
        } catch (error) {
          chat = await api("/chats/direct/", {
            method: "POST",
            body: JSON.stringify({ peer_uuid: userUuid }),
          });
        }
        await loadChats();
        state.activeTab = "chats";
        elements.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === "chats"));
        openChat(chat.uuid);
      } catch (error) {
        showToast(error.message || "Не удалось создать чат");
      }
    }

    async function openChat(chatUuid) {
      const chat = state.chats.find((item) => item.uuid === chatUuid);
      if (!chat) return;

      state.activeChat = chat;
      elements.feedView?.classList.remove("active");
      state.renderedMessageUuids.clear();
      elements.title.textContent = chatTitle(chat);
      elements.status.textContent = chat.type === "group" ? `${chat.members_count || 0} участников` : "был(а) недавно";
      elements.avatar.innerHTML = avatarContent(chat.peer_user, chatTitle(chat));
      elements.emptyState.style.display = "none";
      elements.chatView.classList.add("active");
      elements.sidebar.classList.add("hidden-mobile");
      elements.rightPanel.classList.add("mobile-open");
      renderChats();

      if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: chat.uuid }));
      }

      const cachedRows = await state.cache?.get(`messages:${chat.uuid}`);
      if (Array.isArray(cachedRows) && cachedRows.length) renderMessageList(cachedRows);
      else elements.messages.innerHTML = `<div class="messages-loading"><span></span><span></span><span></span></div>`;

      try {
        const data = await api(`/chats/${chat.uuid}/messages/`);
        const rows = mergeMessages(cachedRows || [], normalizePage(data).slice().reverse());
        renderMessageList(rows);
        void state.cache?.set(`messages:${chat.uuid}`, rows.slice(-200));
        chat.unread_count = 0;
        void state.cache?.set("chats", state.chats);
        void api(`/chats/${chat.uuid}/read/`, { method: "POST", body: JSON.stringify({}) }).catch(() => {});
      } catch (error) {
        if (!cachedRows?.length) {
          elements.messages.innerHTML = emptyListHtml("", "Нет соединения", "Показывать пока нечего");
          showToast(error.message || "Не удалось загрузить сообщения");
        }
      }
    }

    function mergeMessages(...lists) {
      const byId = new Map();
      lists.flat().filter(Boolean).forEach((message) => {
        const key = message.client_uuid || message.uuid;
        if (key) byId.set(String(key), { ...(byId.get(String(key)) || {}), ...message });
      });
      return Array.from(byId.values()).sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    }

    function renderMessageList(rows) {
      state.renderedMessageUuids.clear();
      elements.messages.innerHTML = "";
      rows.forEach(appendMessage);
      elements.messages.scrollTop = elements.messages.scrollHeight;
    }

    async function cacheMessage(message) {
      const chatUuid = String(message.chat_uuid || message.chat || state.activeChat?.uuid || "");
      if (!chatUuid || !state.cache) return;
      const rows = await state.cache.get(`messages:${chatUuid}`) || [];
      await state.cache.set(`messages:${chatUuid}`, mergeMessages(rows, [message]).slice(-200));
    }

    function appendMessage(message) {
      if (!state.activeChat) return;
      const messageChatUuid = message.chat_uuid || message.chat || state.activeChat.uuid;
      if (String(messageChatUuid) !== String(state.activeChat.uuid)) return;
      if (message.uuid && state.renderedMessageUuids.has(message.uuid)) return;
      if (message.uuid) state.renderedMessageUuids.add(message.uuid);

      const own = message.is_own_message || (message.sender && state.me && message.sender.uuid === state.me.uuid);
      const node = document.createElement("article");
      node.className = `message ${own ? "own" : ""}${message.pending ? " pending" : ""}`;
      node.dataset.messageUuid = message.uuid || message.client_uuid || "";
      const sender = message.sender ? displayUserName(message.sender) : "";
      const attachments = (message.attachments || []).map(renderAttachment).join("");
      node.innerHTML = `${sender && !own ? `<small>${escapeHtml(sender)}</small>` : ""}<p>${escapeHtml(message.text || labelForType(message.message_type)).replace(/\n/g, "<br>")}</p>${attachments}<time>${formatTime(message.created_at)}</time>`;
      elements.messages.appendChild(node);
      elements.messages.scrollTop = elements.messages.scrollHeight;
      if (!message.pending) void cacheMessage(message);
    }

    function renderAttachment(media) {
      const url = media.file_url || media.url || "";
      if (!url) return "";
      const name = escapeHtml(media.original_name || "Файл");
      if (media.media_kind === "image" || String(media.content_type || "").startsWith("image/")) {
        return `<img class="message-media" src="${escapeAttr(url)}" alt="${name}">`;
      }
      if (media.media_kind === "audio" || String(media.content_type || "").startsWith("audio/")) {
        return `<audio controls src="${escapeAttr(url)}"></audio>`;
      }
      if (media.media_kind === "video" || String(media.content_type || "").startsWith("video/")) {
        return `<span class="video-note-shell"><video controls playsinline src="${escapeAttr(url)}" poster="${escapeAttr(media.thumbnail_url || "")}"></video></span>`;
      }
      return `<a class="file-chip" href="${escapeAttr(url)}" target="_blank" rel="noopener">${name}</a>`;
    }

    async function sendTextMessage(event) {
      event.preventDefault();
      if (!state.activeChat) return;
      const text = elements.messageInput.value.trim();
      if (!text) return;

      const clientUuid = crypto.randomUUID();
      const optimistic = {
        uuid: clientUuid,
        client_uuid: clientUuid,
        chat_uuid: state.activeChat.uuid,
        sender: state.me,
        is_own_message: true,
        message_type: "text",
        text,
        created_at: new Date().toISOString(),
        pending: true,
      };
      elements.messageInput.value = "";
      autoResizeMessageInput();
      appendMessage(optimistic);

      try {
        const data = await api(`/chats/${state.activeChat.uuid}/messages/`, {
          method: "POST",
          body: JSON.stringify({
            message_type: "text",
            text,
            client_uuid: clientUuid,
          }),
        });
        const pendingNode = elements.messages.querySelector(`[data-message-uuid="${CSS.escape(clientUuid)}"]`);
        pendingNode?.remove();
        state.renderedMessageUuids.delete(clientUuid);
        appendMessage(data);
        state.activeChat.last_message = { preview: text, text };
        state.activeChat.last_message_at = new Date().toISOString();
        void state.cache?.set("chats", state.chats);
        renderChats();
      } catch (error) {
        const pendingNode = elements.messages.querySelector(`[data-message-uuid="${CSS.escape(clientUuid)}"]`);
        pendingNode?.classList.add("failed");
        pendingNode?.classList.remove("pending");
        elements.messageInput.value = text;
        showToast(error.message || "Не удалось отправить сообщение");
      }
    }

    async function sendPickedFile(event) {
      const file = event.target.files[0];
      if (!file || !state.activeChat) return;

      try {
        const media = await uploadMedia(file);
        const type = media.media_kind === "image" ? "image" : media.media_kind === "video" ? "video" : media.media_kind === "audio" ? "audio" : "file";
        const message = await api(`/chats/${state.activeChat.uuid}/messages/`, {
          method: "POST",
          body: JSON.stringify({
            message_type: type,
            attachment_uuids: [media.uuid],
            client_uuid: crypto.randomUUID(),
          }),
        });
        appendMessage(message);
        state.activeChat.last_message = { preview: labelForType(type) };
        state.activeChat.last_message_at = new Date().toISOString();
        void state.cache?.set("chats", state.chats);
        renderChats();
      } catch (error) {
        showToast(error.message || "Не удалось отправить файл");
      } finally {
        event.target.value = "";
      }
    }

    async function uploadMedia(file) {
      const formData = new FormData();
      formData.append("file", file);

      const localResponse = await fetch(`${apiBase}/media/upload-local/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getAccess()}` },
        body: formData,
      });

      const localText = await localResponse.text();
      const localData = localText ? JSON.parse(localText) : null;
      if (localResponse.ok) return localData;
      if (!localData || localData.storage !== "s3") {
        throw new Error((localData && localData.detail) || "Media upload failed");
      }

      const presign = await api("/media/presign/", {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || "application/octet-stream",
          size: file.size,
        }),
      });

      const upload = presign.upload;
      const putResponse = await fetch(upload.url, {
        method: upload.method || "PUT",
        headers: upload.headers || { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });

      if (!putResponse.ok) throw new Error("S3 upload failed");

      return api("/media/complete/", {
        method: "POST",
        body: JSON.stringify({ media_uuid: presign.media.uuid }),
      });
    }

    function autoResizeMessageInput() {
      const input = elements.messageInput;
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
    }

    async function createCall(callType) {
      if (!state.activeChat) {
        showToast("Сначала выберите чат");
        return;
      }
      if (!state.activeChat.peer_user?.uuid) {
        showToast("Web-звонок сейчас доступен в личных чатах");
        return;
      }
      if (!navigator.mediaDevices?.getUserMedia || !window.RTCPeerConnection) {
        showToast("Этот браузер не поддерживает аудио- и видеозвонки");
        return;
      }

      const title = callType === "audio" ? "Аудиозвонок" : "Видеозвонок";
      showCallModal(title, "Запрашиваем доступ к устройствам…", initials(chatTitle(state.activeChat)));
      setCallButtons("outgoing", callType);

      let createdCall = null;
      try {
        const [localStream] = await Promise.all([requestCallMedia(callType), loadIceServers()]);
        const call = await api(`/chats/${state.activeChat.uuid}/calls/`, {
          method: "POST",
          body: JSON.stringify({
            call_type: callType,
            metadata: { source: "web", device_platform: "web", device_name: navigator.userAgent.slice(0, 120) },
          }),
        });
        createdCall = call;
        state.currentCall = {
          uuid: call.uuid,
          chatUuid: call.chat_uuid || state.activeChat.uuid,
          callType,
          roomKey: call.room_key || "",
          targetUserUuid: state.activeChat.peer_user.uuid,
          isCaller: true,
          accepted: false,
        };
        state.localStream = localStream;
        await createPeerConnection();
        const offer = await state.peerConnection.createOffer();
        await state.peerConnection.setLocalDescription(offer);
        await sendCallSignal("call:offer", { description: state.peerConnection.localDescription });
        elements.callModalSubtitle.textContent = `Звоним: ${chatTitle(state.activeChat)}`;
      } catch (error) {
        elements.callModalSubtitle.textContent = error.message || "Не удалось создать звонок";
        if (createdCall?.uuid) {
          void api(`/calls/${createdCall.uuid}/cancel/`, { method: "POST", body: JSON.stringify({}) }).catch(() => {});
        }
        stopCallMedia();
        state.currentCall = null;
      }
    }

    async function requestCallMedia(callType) {
      try {
        return await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
          video: callType === "video" ? { width: { ideal: 1280 }, height: { ideal: 720 } } : false,
        });
      } catch (error) {
        throw new Error(callType === "video" ? "Разрешите доступ к камере и микрофону" : "Разрешите доступ к микрофону");
      }
    }

    async function loadIceServers() {
      if (state.iceServers) return state.iceServers;
      try {
        const config = await api("/calls/ice-config/");
        if (Array.isArray(config?.ice_servers) && config.ice_servers.length) {
          state.iceServers = config.ice_servers;
          return state.iceServers;
        }
      } catch (error) {
        console.warn("ICE configuration unavailable", error);
      }
      state.iceServers = [{ urls: ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"] }];
      return state.iceServers;
    }

    async function createPeerConnection() {
      state.peerConnection?.close();
      const connection = new RTCPeerConnection({
        iceServers: await loadIceServers(),
      });
      state.peerConnection = connection;
      state.remoteStream = new MediaStream();
      elements.remoteVideo.srcObject = state.remoteStream;
      elements.localVideo.srcObject = state.localStream;
      setCallVideoMode(state.currentCall?.callType === "video");

      state.localStream?.getTracks().forEach((track) => connection.addTrack(track, state.localStream));
      connection.addEventListener("track", (event) => {
        event.streams[0]?.getTracks().forEach((track) => {
          if (!state.remoteStream.getTracks().some((item) => item.id === track.id)) state.remoteStream.addTrack(track);
        });
        elements.remoteVideo.closest(".call-media")?.classList.add("remote-ready");
        elements.callModalSubtitle.textContent = "Соединение установлено";
        startCallTimer();
      });
      connection.addEventListener("icecandidate", (event) => {
        if (event.candidate) void sendCallSignal("call:ice-candidate", { candidate: event.candidate.toJSON() });
      });
      connection.addEventListener("connectionstatechange", () => {
        if (connection.connectionState === "connected") {
          elements.callModalSubtitle.textContent = "Соединение установлено";
          startCallTimer();
        } else if (["failed", "disconnected"].includes(connection.connectionState)) {
          elements.callModalSubtitle.textContent = "Соединение прервано";
        }
      });
    }

    async function sendCallSignal(signalType, payload) {
      if (!state.currentCall?.uuid) return;
      await api(`/calls/${state.currentCall.uuid}/signals/`, {
        method: "POST",
        body: JSON.stringify({
          signal_type: signalType,
          payload,
          target_user_uuid: state.currentCall.targetUserUuid || undefined,
        }),
      });
    }

    async function acceptIncomingCall() {
      const call = state.currentCall;
      if (!call || call.isCaller) return;
      elements.callModalSubtitle.textContent = "Подключаем устройства…";
      try {
        [state.localStream] = await Promise.all([requestCallMedia(call.callType), loadIceServers()]);
        await createPeerConnection();
        await api(`/calls/${call.uuid}/accept/`, {
          method: "POST",
          body: JSON.stringify({ device_platform: "web", device_name: navigator.userAgent.slice(0, 120) }),
        });
        call.accepted = true;
        setCallButtons("active", call.callType);
        elements.callModalSubtitle.textContent = "Устанавливаем соединение…";
        if (state.pendingOffer) {
          const offer = state.pendingOffer;
          state.pendingOffer = null;
          await answerRemoteOffer(offer);
        }
      } catch (error) {
        elements.callModalSubtitle.textContent = error.message || "Не удалось принять звонок";
      }
    }

    async function answerRemoteOffer(description) {
      if (!state.peerConnection) await createPeerConnection();
      await state.peerConnection.setRemoteDescription(new RTCSessionDescription(description));
      await flushPendingIce();
      const answer = await state.peerConnection.createAnswer();
      await state.peerConnection.setLocalDescription(answer);
      await sendCallSignal("call:answer", { description: state.peerConnection.localDescription });
    }

    async function applyRemoteAnswer(description) {
      if (!state.peerConnection || state.peerConnection.currentRemoteDescription) return;
      await state.peerConnection.setRemoteDescription(new RTCSessionDescription(description));
      await flushPendingIce();
      if (state.currentCall) state.currentCall.accepted = true;
      setCallButtons("active", state.currentCall?.callType || "audio");
      startCallTimer();
    }

    async function addRemoteIce(candidate) {
      if (!candidate) return;
      if (!state.peerConnection?.remoteDescription) {
        state.pendingIce.push(candidate);
        return;
      }
      await state.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
    }

    async function flushPendingIce() {
      if (!state.peerConnection?.remoteDescription) return;
      const candidates = state.pendingIce.splice(0);
      for (const candidate of candidates) await state.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
    }

    async function declineIncomingCall() {
      if (!state.currentCall) return;
      try {
        await api(`/calls/${state.currentCall.uuid}/decline/`, { method: "POST", body: JSON.stringify({}) });
      } catch (error) {
        showToast(error.message || "Не удалось отклонить звонок");
      }
      cleanupCall();
    }

    async function endCurrentCall() {
      const call = state.currentCall;
      if (!call) return;
      const action = call.isCaller && !call.accepted ? "cancel" : "end";
      try {
        await api(`/calls/${call.uuid}/${action}/`, { method: "POST", body: JSON.stringify({}) });
      } catch (error) {
        showToast(error.message || "Не удалось завершить звонок");
      }
      cleanupCall();
    }

    function requestCallClose() {
      if (!state.currentCall) {
        closeCallModal();
        return;
      }
      if (!state.currentCall.isCaller && !state.currentCall.accepted) void declineIncomingCall();
      else void endCurrentCall();
    }

    function toggleCallAudio() {
      const track = state.localStream?.getAudioTracks()[0];
      if (!track) return;
      track.enabled = !track.enabled;
      elements.callMuteButton.classList.toggle("is-off", !track.enabled);
    }

    function toggleCallVideo() {
      const track = state.localStream?.getVideoTracks()[0];
      if (!track) return;
      track.enabled = !track.enabled;
      elements.callCameraButton.classList.toggle("is-off", !track.enabled);
    }

    function setCallButtons(mode, callType) {
      elements.callAcceptButton.hidden = mode !== "incoming";
      elements.callDeclineButton.hidden = mode !== "incoming";
      elements.callHangupButton.hidden = mode === "incoming";
      elements.callMuteButton.hidden = mode === "incoming";
      elements.callCameraButton.hidden = mode === "incoming" || callType !== "video";
      elements.callMuteButton.classList.remove("is-off");
      elements.callCameraButton.classList.remove("is-off");
    }

    function setCallVideoMode(enabled) {
      elements.localVideo.closest(".call-media")?.classList.toggle("video-active", Boolean(enabled));
    }

    function startCallTimer() {
      if (state.callStartedAt) return;
      state.callStartedAt = Date.now();
      clearInterval(state.callDurationTimer);
      const update = () => {
        const total = Math.floor((Date.now() - state.callStartedAt) / 1000);
        const minutes = String(Math.floor(total / 60)).padStart(2, "0");
        const seconds = String(total % 60).padStart(2, "0");
        elements.callDuration.textContent = `${minutes}:${seconds}`;
      };
      update();
      state.callDurationTimer = setInterval(update, 1000);
    }

    function stopCallMedia() {
      state.localStream?.getTracks().forEach((track) => track.stop());
      state.remoteStream?.getTracks().forEach((track) => track.stop());
      state.localStream = null;
      state.remoteStream = null;
      elements.localVideo.srcObject = null;
      elements.remoteVideo.srcObject = null;
      elements.remoteVideo.closest(".call-media")?.classList.remove("remote-ready");
      setCallVideoMode(false);
    }

    function cleanupCall(message) {
      state.peerConnection?.close();
      state.peerConnection = null;
      stopCallMedia();
      clearInterval(state.callDurationTimer);
      state.callDurationTimer = null;
      state.callStartedAt = null;
      state.pendingOffer = null;
      state.pendingIce = [];
      state.currentCall = null;
      elements.callDuration.textContent = "";
      closeCallModal();
      if (message) showToast(message);
    }

    function renderStories() {
      const stories = buildStoryPreviews(state.stories);
      elements.stories.innerHTML = [renderMyStoryButton(), ...stories.map(renderStoryButton)].join("");

      const my = elements.stories.querySelector("[data-story-add]");
      my?.addEventListener("click", openAddStoryModal);

      elements.stories.querySelectorAll("[data-story]").forEach((button) => {
        button.addEventListener("click", () => {
          const story = state.stories.find((item) => item.uuid === button.dataset.story);
          if (story) openStoryViewer(story);
        });
      });
    }

    function buildStoryPreviews(stories) {
      const byAuthor = new Map();
      [...stories].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)).forEach((story) => {
        const author = getStoryAuthor(story);
        const key = author?.uuid || story.uuid;
        if (!byAuthor.has(key)) byAuthor.set(key, story);
      });
      return Array.from(byAuthor.values()).slice(0, 20);
    }

    function renderMyStoryButton() {
      return `<button class="story-item" data-story-add type="button">
        <div class="story-avatar-wrapper">
          <div class="story-avatar"><i class="fa-solid fa-user"></i></div>
          <div class="add-story-badge"><i class="fa-solid fa-plus"></i></div>
        </div>
        <div class="story-name my-story">Моя история</div>
      </button>`;
    }

    function renderStoryButton(story) {
      const author = getStoryAuthor(story);
      const name = story.is_own ? "Моя история" : displayUserName(author || story);
      const image = author?.avatar || story.media?.thumbnail_url || story.media?.file_url || story.file_url || "";
      const viewed = story.viewed_by_me ? " viewed" : " has-story";
      const avatar = image ? `<img src="${escapeAttr(image)}" alt="">` : escapeHtml(initials(name));
      return `<button class="story-item" data-story="${escapeAttr(story.uuid)}" type="button">
        <div class="story-avatar-wrapper${viewed}">
          <div class="story-avatar">${avatar}</div>
        </div>
        <div class="story-name ${story.is_own ? "my-story" : ""}">${escapeHtml(name)}</div>
      </button>`;
    }

    function openAddStoryModal() {
      elements.addStoryModal.classList.add("active");
      elements.storyTextInput.focus();
    }

    function closeAddStoryModal() {
      elements.addStoryModal.classList.remove("active");
      elements.storyTextInput.value = "";
      clearStoryFile();
    }

    function previewStoryFile(event) {
      const file = event.target.files[0];
      if (!file) return;
      state.storyFile = file;
      const url = URL.createObjectURL(file);
      elements.imageUploadArea.classList.add("has-image");

      if (file.type.startsWith("video/")) {
        elements.imagePreview.style.display = "none";
        elements.videoPreview.src = url;
        elements.videoPreview.style.display = "block";
      } else {
        elements.videoPreview.style.display = "none";
        elements.videoPreview.removeAttribute("src");
        elements.imagePreview.src = url;
        elements.imagePreview.style.display = "block";
      }
    }

    function clearStoryFile() {
      state.storyFile = null;
      elements.storyFileInput.value = "";
      elements.imageUploadArea.classList.remove("has-image");
      elements.imagePreview.removeAttribute("src");
      elements.videoPreview.removeAttribute("src");
      elements.imagePreview.style.display = "none";
      elements.videoPreview.style.display = "none";
    }

    async function publishStory() {
      const text = elements.storyTextInput.value.trim();
      if (!state.storyFile && !text) {
        showToast("Добавьте фото, видео или текст");
        return;
      }

      elements.publishStoryButton.disabled = true;
      elements.publishStoryButton.style.opacity = "0.65";

      try {
        if (state.storyFile) {
          const media = await uploadMedia(state.storyFile);
          const isVideo = state.storyFile.type.startsWith("video/") || media.media_kind === "video";
          await api("/stories/", {
            method: "POST",
            body: JSON.stringify({
              media_type: isVideo ? "video" : "image",
              media_uuid: media.uuid,
              caption: text || undefined,
            }),
          });
        } else {
          await api("/stories/", {
            method: "POST",
            body: JSON.stringify({
              media_type: "text",
              caption: text,
              background: "#10b981",
            }),
          });
        }

        closeAddStoryModal();
        await loadStories();
        showToast("История опубликована!");
      } catch (error) {
        showToast(error.message || "Не удалось опубликовать историю");
      } finally {
        elements.publishStoryButton.disabled = false;
        elements.publishStoryButton.style.opacity = "1";
      }
    }

    async function openStoryViewer(story) {
      const author = getStoryAuthor(story);
      const name = story.is_own ? "Моя история" : displayUserName(author || story);
      const authorImage = author?.avatar || author?.photo_url || "";
      const image = story.media?.file_url || story.file_url || "";
      const isVideo = story.media_type === "video" || String(story.media?.content_type || "").startsWith("video/");

      elements.storyViewerAvatar.innerHTML = authorImage ? `<img src="${escapeAttr(authorImage)}" alt="">` : escapeHtml(initials(name));
      elements.storyViewerName.textContent = name;
      elements.storyViewerTime.textContent = relativeTime(story.created_at);
      elements.storyViewerText.textContent = story.caption || "История";
      elements.storyViewerText.style.display = story.media_type === "text" || story.caption ? "block" : "none";
      elements.storyViewerImage.style.display = "none";
      elements.storyViewerVideo.style.display = "none";
      elements.storyViewerVideo.pause();
      elements.storyViewerVideo.removeAttribute("src");

      if (image && isVideo) {
        elements.storyViewerVideo.src = image;
        elements.storyViewerVideo.style.display = "block";
      } else if (image) {
        elements.storyViewerImage.src = image;
        elements.storyViewerImage.style.display = "block";
      }

      elements.storyViewer.classList.add("active");
      story.viewed_by_me = true;
      renderStories();
      runStoryProgress();

      try {
        await api(`/stories/${story.uuid}/viewers/`, { method: "POST", body: JSON.stringify({}) });
      } catch (error) {
        console.warn("mark story viewed error", error);
      }
    }

    function runStoryProgress() {
      clearInterval(state.storyTimer);
      elements.storyProgressFill.style.width = "0%";
      let progress = 0;
      state.storyTimer = setInterval(() => {
        progress += 2;
        elements.storyProgressFill.style.width = `${progress}%`;
        if (progress >= 100) closeStoryViewer();
      }, 100);
    }

    function closeStoryViewer() {
      clearInterval(state.storyTimer);
      elements.storyViewer.classList.remove("active");
      elements.storyViewerVideo.pause();
    }

    function scheduleSocketReconnect() {
      clearTimeout(state.socketReconnectTimer);
      const exponent = Math.min(state.socketReconnectAttempts, 5);
      const delay = Math.min(1000 * (2 ** exponent), 30000) + Math.floor(Math.random() * 400);
      state.socketReconnectAttempts += 1;
      state.socketReconnectTimer = setTimeout(connectSocket, delay);
    }

    function scheduleChatsRefresh() {
      if (state.chatRefreshTimer) return;
      const wait = Math.max(500, 5000 - (Date.now() - state.lastChatRefreshAt));
      state.chatRefreshTimer = setTimeout(() => {
        state.chatRefreshTimer = null;
        void loadChats().catch((error) => console.warn("chat refresh error", error));
      }, wait);
    }

    function updateChatFromMessage(message) {
      const chatUuid = String(message.chat_uuid || message.chat || "");
      const chat = state.chats.find((item) => String(item.uuid) === chatUuid);
      if (!chat) {
        scheduleChatsRefresh();
        return;
      }
      chat.last_message = message;
      chat.last_message_at = message.created_at || new Date().toISOString();
      const own = message.is_own_message || String(message.sender?.uuid || message.sender_uuid || "") === String(state.me?.uuid || "");
      if (!own && String(state.activeChat?.uuid || "") !== chatUuid) {
        chat.unread_count = Number(chat.unread_count || 0) + 1;
      }
      void state.cache?.set("chats", state.chats);
      renderChats();
    }

    async function notifyRealtime(title, body, data) {
      if (!("Notification" in window) || document.visibilityState === "visible" || Notification.permission !== "granted" || state.webPushSubscribed) return;
      try {
        const registration = await navigator.serviceWorker.ready;
        await registration.showNotification(title, {
          body,
          icon: "/assets/akyl_logo.png",
          tag: `${data.type}:${data.call_uuid || data.message_uuid || data.chat_uuid || "new"}`,
          requireInteraction: data.type === "call",
          data: { ...data, url: data.chat_uuid ? `/messenger/?chat=${data.chat_uuid}` : "/messenger/" },
        });
      } catch (error) {
        console.warn("notification error", error);
      }
    }

    function connectSocket() {
      clearTimeout(state.socketReconnectTimer);
      if (!getAccess() || !navigator.onLine) {
        scheduleSocketReconnect();
        return;
      }
      if (state.socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(state.socket.readyState)) return;

      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${protocol}://${window.location.host}/ws?token=${encodeURIComponent(getAccess())}`);
      state.socket = socket;

      socket.addEventListener("open", () => {
        state.socketReconnectAttempts = 0;
        state.chats.forEach((chat) => {
          socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: chat.uuid }));
        });
      });

      socket.addEventListener("close", () => {
        if (state.socket === socket) state.socket = null;
        scheduleSocketReconnect();
      });

      socket.addEventListener("error", () => socket.close());

      socket.addEventListener("message", (event) => {
        try {
          const payload = JSON.parse(event.data);
          const message = payload?.payload?.message;
          if ((payload.type === "message:new" || payload.type === "message_persisted" || payload.type === "chat_message") && message) {
            appendMessage(message);
            void cacheMessage(message);
            updateChatFromMessage(message);
            const own = String(message.sender?.uuid || payload.payload?.sender_uuid || "") === String(state.me?.uuid || "");
            if (!own) {
              const senderName = displayUserName(message.sender);
              void notifyRealtime(senderName, message.text || labelForType(message.message_type), {
                type: "message",
                chat_uuid: message.chat_uuid || payload.payload?.chat_uuid,
                message_uuid: message.uuid,
              });
            }
          }
          void handleCallSocketEvent(payload);
        } catch (error) {
          console.warn("websocket event error", error);
        }
      });
    }

    window.addEventListener("online", () => {
      state.socketReconnectAttempts = 0;
      connectSocket();
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") connectSocket();
    });

    async function handleCallSocketEvent(envelope) {
      const type = String(envelope?.type || "").toLowerCase();
      const payload = envelope?.payload || {};
      const callUuid = payload.call_uuid || payload.uuid;
      if (!callUuid || !type.startsWith("call") && !["incoming_call", "missed_call"].includes(type)) return;
      if (payload.target_user_uuid && String(payload.target_user_uuid) !== String(state.me?.uuid)) return;
      if (payload.sender_uuid && String(payload.sender_uuid) === String(state.me?.uuid)) return;

      const inviteTypes = new Set(["call:invite", "call_invite", "incoming_call", "call:incoming"]);
      const offerTypes = new Set(["call:offer", "call_offer"]);
      const answerTypes = new Set(["call:answer", "call_answer"]);
      const iceTypes = new Set(["call:ice-candidate", "call_ice", "call:ice_candidate"]);
      const finalTypes = new Set([
        "call:decline",
        "call_decline",
        "call:end",
        "call_end",
        "call:cancel",
        "call_cancel",
        "call:missed",
        "call_missed",
        "call:auto-end",
        "missed_call",
      ]);

      if (inviteTypes.has(type)) {
        if (String(payload.initiated_by_uuid || payload.caller_uuid) === String(state.me?.uuid)) return;
        showIncomingCall(payload);
        void notifyRealtime(
          payload.caller_name || payload.initiated_by_username || "Входящий звонок",
          payload.call_type === "video" ? "Видеозвонок" : "Аудиозвонок",
          { type: "call", ...payload }
        );
        return;
      }

      if (!state.currentCall || String(state.currentCall.uuid) !== String(callUuid)) return;

      if (offerTypes.has(type)) {
        const description = callDescription(payload, "offer");
        if (!description) return;
        if (!state.currentCall.accepted) state.pendingOffer = description;
        else await answerRemoteOffer(description);
      } else if (answerTypes.has(type)) {
        const description = callDescription(payload, "answer");
        if (description) await applyRemoteAnswer(description);
      } else if (iceTypes.has(type)) {
        const candidate = payload.candidate || payload.ice_candidate;
        if (candidate) await addRemoteIce(candidate);
      } else if (type === "call:accept" || type === "call_accept") {
        state.currentCall.accepted = true;
        elements.callModalSubtitle.textContent = "Собеседник принял звонок";
        setCallButtons("active", state.currentCall.callType);
      } else if (finalTypes.has(type)) {
        const message = type.includes("missed") ? "Пропущенный звонок" : type.includes("decline") ? "Звонок отклонён" : "Звонок завершён";
        cleanupCall(message);
      }
    }

    function showIncomingCall(payload) {
      if (state.currentCall && String(state.currentCall.uuid) !== String(payload.call_uuid)) return;
      const chat = state.chats.find((item) => String(item.uuid) === String(payload.chat_uuid));
      const callerName = payload.caller_name || payload.initiated_by_username || chatTitle(chat || {});
      state.currentCall = {
        uuid: payload.call_uuid,
        chatUuid: payload.chat_uuid,
        callType: payload.call_type || "audio",
        roomKey: payload.room_key || "",
        targetUserUuid: payload.initiated_by_uuid || payload.caller_uuid || "",
        isCaller: false,
        accepted: false,
      };
      showCallModal(
        state.currentCall.callType === "video" ? "Входящий видеозвонок" : "Входящий аудиозвонок",
        callerName,
        initials(callerName)
      );
      setCallButtons("incoming", state.currentCall.callType);
    }

    function callDescription(payload, fallbackType) {
      if (payload.description && payload.description.sdp) return payload.description;
      if (payload.sdp && typeof payload.sdp === "object") return payload.sdp;
      if (typeof payload.sdp === "string") return { type: payload.sdp_type || fallbackType, sdp: payload.sdp };
      return null;
    }

    function showCallModal(title, subtitle, letter) {
      elements.callModalTitle.textContent = title;
      elements.callModalSubtitle.textContent = subtitle;
      elements.callModalAvatar.textContent = letter || initials(chatTitle(state.activeChat || {}));
      elements.callModal.classList.add("active");
    }

    function closeCallModal() {
      elements.callModal.classList.remove("active");
    }

    function showToast(message) {
      clearTimeout(toastTimeout);
      elements.toast.textContent = message;
      elements.toast.classList.add("show");
      toastTimeout = setTimeout(() => elements.toast.classList.remove("show"), 2600);
    }

    function emptyListHtml(icon, title, subtitle) {
      return `<div class="not-found-state"><i class="fa-solid ${icon}"></i><strong>${escapeHtml(title)}</strong><div>${escapeHtml(subtitle)}</div></div>`;
    }
  }

  function normalizePage(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    return [];
  }

  function initials(value) {
    const clean = String(value || "A").trim();
    const parts = clean.split(/\s+/).filter(Boolean);
    if (parts.length > 1) return parts.slice(0, 2).map((item) => item[0]).join("").toUpperCase();
    return clean.slice(0, 1).toUpperCase() || "A";
  }

  function displayUserName(user) {
    if (!user) return "Akyl";
    return user.full_name || [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username || user.email || "Akyl";
  }

  function chatTitle(chat) {
    return chat.display_title || chat.title || displayUserName(chat.peer_user) || "Без названия";
  }

  function messagePreview(chat) {
    const value = chat.last_message;
    if (!value) return "Нет сообщений";
    if (typeof value === "string") return value || "Сообщение";
    return value.preview || value.text || labelForType(value.message_type) || "Сообщение";
  }

  function avatarContent(user, fallbackName) {
    const url = user?.avatar || user?.photo_url || "";
    if (url) return `<img src="${escapeAttr(url)}" alt="">`;
    return escapeHtml(initials(fallbackName || displayUserName(user)));
  }

  function getStoryAuthor(story) {
    return story.author || story.user || null;
  }

  function sortChats(a, b) {
    const pinA = Boolean(a.is_pinned);
    const pinB = Boolean(b.is_pinned);
    if (pinA !== pinB) return pinA ? -1 : 1;
    const timeA = new Date(a.last_message_at || a.updated_at || a.created_at || 0).getTime();
    const timeB = new Date(b.last_message_at || b.updated_at || b.created_at || 0).getTime();
    return timeB - timeA;
  }

  function formatTime(value) {
    if (!value) return "";
    return new Date(value).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  }

  function formatChatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const day = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    const diff = Math.floor((start - day) / 86400000);
    if (diff <= 0) return formatTime(value);
    if (diff === 1) return "Вчера";
    if (diff < 7) return ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"][date.getDay()];
    return date.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
  }

  function relativeTime(value) {
    if (!value) return "сейчас";
    const diff = Date.now() - new Date(value).getTime();
    const minutes = Math.max(0, Math.floor(diff / 60000));
    if (minutes < 1) return "только что";
    if (minutes < 60) return `${minutes} мин назад`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ч назад`;
    return "вчера";
  }

  function labelForType(type) {
    return {
      image: "Фото",
      video: "Видео",
      audio: "Голосовое сообщение",
      video_note: "Видеокружок",
      file: "Файл",
      sticker: "Стикер",
    }[type] || "Сообщение";
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, "&#96;");
  }

  initAuth();
  initMessenger();
})();
