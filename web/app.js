(function () {
  const apiBase = "/api";
  const accessKey = "akyl_access";
  const refreshKey = "akyl_refresh";
  const themeKey = "akyl_theme";

  function getAccess() {
    return localStorage.getItem(accessKey);
  }

  async function api(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    const token = getAccess();

    if (token) headers.Authorization = `Bearer ${token}`;
    if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";

    const response = await fetch(`${apiBase}${path}`, { ...options, headers });

    if (response.status === 401) {
      localStorage.removeItem(accessKey);
      localStorage.removeItem(refreshKey);
      window.location.href = "/login/";
      return null;
    }

    const text = await response.text();
    const data = text ? JSON.parse(text) : null;

    if (!response.ok) {
<<<<<<< HEAD
      const detail = data && (data.detail || data.error || JSON.stringify(data));
      throw new Error(detail || "Request failed");
=======
      const message = data && (data.detail || data.message || JSON.stringify(data));
      throw new Error(message || "Request failed");
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
    }

    return data;
  }

  function initLogin() {
    const form = document.getElementById("loginForm");
    if (!form) return;

    if (getAccess()) window.location.href = "/messenger/";

    const message = document.getElementById("loginMessage");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      message.textContent = "Входим...";
<<<<<<< HEAD
=======

      const payload = {
        email: document.getElementById("email").value.trim(),
        password: document.getElementById("password").value,
      };

>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      try {
        const data = await api("/auth/login/", {
          method: "POST",
          body: JSON.stringify({
            email: document.getElementById("email").value.trim(),
            password: document.getElementById("password").value,
          }),
        });

        localStorage.setItem(accessKey, data.tokens.access);
        localStorage.setItem(refreshKey, data.tokens.refresh);
        window.location.href = "/messenger/";
      } catch (error) {
        message.textContent = error.message;
      }
    });
  }

<<<<<<< HEAD
  function initCabinet() {
    const app = document.querySelector(".cabinet-app");
=======
  function initMessenger() {
    const app = document.querySelector(".messenger-app");
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
    if (!app) return;

    if (!getAccess()) {
      window.location.href = "/login/";
      return;
    }

    const state = {
      me: null,
      chats: [],
      contacts: [],
<<<<<<< HEAD
      media: [],
      bots: [],
      stories: [],
      activeChat: null,
      section: "dashboard",
      chatFilter: "all",
=======
      searchUsers: [],
      stories: [],
      activeChat: null,
      activeTab: "chats",
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      socket: null,
      storyTimer: null,
      storyFile: null,
      renderedMessageUuids: new Set(),
    };

<<<<<<< HEAD
    const drawer = document.getElementById("cabinetDrawer");
    const sidebar = document.getElementById("chatSidebar");
    const content = document.getElementById("cabinetContent");
    const messages = document.getElementById("messages");
    const composer = document.getElementById("messageForm");
    const chatList = document.getElementById("chatList");
    const title = document.getElementById("activeChatTitle");
    const status = document.getElementById("activeChatStatus");
    const avatar = document.getElementById("activeAvatar");
    const connectionState = document.getElementById("connectionState");

    applyTheme(localStorage.getItem(themeKey) || "dark");

    document.getElementById("menuToggle").addEventListener("click", () => {
      drawer.classList.toggle("open");
    });

    document.getElementById("themeToggle").addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(next);
    });

    document.getElementById("logoutButton").addEventListener("click", async () => {
      const refresh = localStorage.getItem(refreshKey);
      try {
        if (refresh) {
          await api("/auth/logout/", { method: "POST", body: JSON.stringify({ refresh }) });
        }
      } catch (error) {
        console.warn(error);
      }
=======
    const $ = (id) => document.getElementById(id);

    const elements = {
      sidebar: $("chatSidebar"),
      rightPanel: $("rightPanel"),
      list: $("chatList"),
      stories: $("storiesStrip"),
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
      voiceButton: $("voiceButton"),
      videoNoteButton: $("videoNoteButton"),
      audioCallButton: $("audioCallButton"),
      videoCallButton: $("videoCallButton"),
      menuToggle: $("menuToggle"),
      drawer: $("drawer"),
      drawerOverlay: $("drawerOverlay"),
      drawerClose: $("drawerClose"),
      logoutButton: $("logoutButton"),
      themeToggle: $("themeToggle"),
      currentThemeLabel: $("currentThemeLabel"),
      notificationsToggle: $("notificationsToggle"),
      scaleSlider: $("scaleSlider"),
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
      toast: $("toast"),
      backToChats: $("backToChats"),
      emojiButton: $("emojiButton"),
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

      elements.themeToggle?.addEventListener("click", toggleTheme);
      elements.notificationsToggle?.addEventListener("click", (event) => {
        event.stopPropagation();
        elements.notificationsToggle.classList.toggle("active");
        showToast(elements.notificationsToggle.classList.contains("active") ? "Уведомления включены" : "Уведомления выключены");
      });
      elements.scaleSlider?.addEventListener("input", () => {
        document.documentElement.style.fontSize = `${Number(elements.scaleSlider.value)}%`;
      });

      document.querySelectorAll(".drawer-item[data-action], .drawer-premium[data-action]").forEach((item) => {
        item.addEventListener("click", (event) => {
          if (event.target.classList.contains("toggle-switch")) return;
          const action = item.dataset.action;
          if (action === "theme") {
            toggleTheme();
          } else if (action === "premium") {
            showToast("Akyl Premium — скоро!");
          } else {
            const labels = {
              account: "Мой аккаунт",
              notifications: "Уведомления и звуки",
              privacy: "Конфиденциальность",
              chats: "Настройки чатов",
              folders: "Папки с чатами",
              language: "Язык: Русский",
            };
            showToast(labels[action] || "Открыто");
          }
          closeDrawer();
        });
      });

      elements.tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
          state.activeTab = tab.dataset.tab || "chats";
          elements.tabs.forEach((item) => item.classList.toggle("active", item === tab));
          renderList();
        });
      });

      elements.search?.addEventListener("input", () => {
        if (state.activeTab === "contacts") scheduleUserSearch();
        renderList();
      });

      elements.messageInput?.addEventListener("input", autoResizeMessageInput);
      elements.messageForm?.addEventListener("submit", sendTextMessage);
      elements.attachButton?.addEventListener("click", () => elements.fileInput.click());
      elements.fileInput?.addEventListener("change", sendPickedFile);
      elements.voiceButton?.addEventListener("click", () => showCallModal("Голосовое сообщение", "Запись аудио пока подключается на клиенте", ""));
      elements.videoNoteButton?.addEventListener("click", () => showToast("Видеокружок подключается на клиенте"));
      elements.emojiButton?.addEventListener("click", () => showToast("Панель эмодзи — скоро"));
      elements.audioCallButton?.addEventListener("click", () => createCall("audio"));
      elements.videoCallButton?.addEventListener("click", () => createCall("video"));
      elements.callModalClose?.addEventListener("click", closeCallModal);
      elements.callModal?.addEventListener("click", (event) => {
        if (event.target === elements.callModal) closeCallModal();
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
      renderMe();
      await Promise.allSettled([loadStories(), loadContacts(), loadChats()]);
      connectSocket();
    }

    function logout() {
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      localStorage.removeItem(accessKey);
      localStorage.removeItem(refreshKey);
      window.location.href = "/login/";
    }

    function initTheme() {
      const savedTheme = localStorage.getItem(themeKey);
      const preferred = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
      setTheme(savedTheme || preferred);
    }

<<<<<<< HEAD
    document.getElementById("newChatButton").addEventListener("click", () => {
      setSection("users");
    });

    document.getElementById("chatSearch").addEventListener("input", renderChats);

    document.querySelectorAll(".drawer-link").forEach((button) => {
      button.addEventListener("click", () => {
        setSection(button.dataset.section);
        drawer.classList.remove("open");
      });
    });

    document.querySelectorAll(".tab").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item === button));
        state.chatFilter = button.dataset.filter;
        renderChats();
      });
    });

    composer.addEventListener("submit", async (event) => {
=======
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

    async function loadChats() {
      elements.list.innerHTML = `<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i><div>Загружаем чаты...</div></div>`;
      const data = await api("/chats/");
      state.chats = normalizePage(data);
      renderList();
    }

    async function loadContacts() {
      try {
        const data = await api("/users/contacts/");
        state.contacts = normalizePage(data).map((item) => item.user || item).filter(Boolean);
      } catch (error) {
        console.warn("contacts load error", error);
        state.contacts = [];
      }
    }

    async function loadStories() {
      try {
        const data = await api("/stories/");
        state.stories = normalizePage(data);
      } catch (error) {
        console.warn("stories load error", error);
        state.stories = [];
      }
      renderStories();
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
      if (state.activeTab === "contacts") renderContacts();
      else renderChats();
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
      state.renderedMessageUuids.clear();
      elements.title.textContent = chatTitle(chat);
      elements.status.textContent = chat.type === "group" ? `${chat.members_count || 0} участников` : "был(а) недавно";
      elements.avatar.innerHTML = avatarContent(chat.peer_user, chatTitle(chat));
      elements.emptyState.style.display = "none";
      elements.chatView.classList.add("active");
      elements.sidebar.classList.add("hidden-mobile");
      elements.rightPanel.classList.add("mobile-open");
      renderChats();

      try {
        const data = await api(`/chats/${chat.uuid}/messages/`);
        elements.messages.innerHTML = "";
        const rows = normalizePage(data).slice().reverse();
        rows.forEach(appendMessage);
        if (state.socket && state.socket.readyState === WebSocket.OPEN) {
          state.socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: chat.uuid }));
        }
      } catch (error) {
        showToast(error.message || "Не удалось загрузить сообщения");
      }
    }

    function appendMessage(message) {
      if (!state.activeChat) return;
      const messageChatUuid = message.chat_uuid || message.chat || state.activeChat.uuid;
      if (String(messageChatUuid) !== String(state.activeChat.uuid)) return;
      if (message.uuid && state.renderedMessageUuids.has(message.uuid)) return;
      if (message.uuid) state.renderedMessageUuids.add(message.uuid);

      const own = message.is_own_message || (message.sender && state.me && message.sender.uuid === state.me.uuid);
      const node = document.createElement("article");
      node.className = `message ${own ? "own" : ""}`;
      const sender = message.sender ? displayUserName(message.sender) : "";
      const attachments = (message.attachments || []).map(renderAttachment).join("");
      node.innerHTML = `${sender && !own ? `<small>${escapeHtml(sender)}</small>` : ""}<p>${escapeHtml(message.text || labelForType(message.message_type)).replace(/\n/g, "<br>")}</p>${attachments}<time>${formatTime(message.created_at)}</time>`;
      elements.messages.appendChild(node);
      elements.messages.scrollTop = elements.messages.scrollHeight;
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
        return `<video controls src="${escapeAttr(url)}" poster="${escapeAttr(media.thumbnail_url || "")}"></video>`;
      }
      return `<a class="file-chip" href="${escapeAttr(url)}" target="_blank" rel="noopener">${name}</a>`;
    }

    async function sendTextMessage(event) {
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      event.preventDefault();
      if (!state.activeChat) return;
      const text = elements.messageInput.value.trim();
      if (!text) return;

      elements.messageInput.value = "";
      autoResizeMessageInput();

      try {
        const data = await api(`/chats/${state.activeChat.uuid}/messages/`, {
          method: "POST",
          body: JSON.stringify({
            message_type: "text",
            text,
            client_uuid: crypto.randomUUID(),
          }),
        });
        appendMessage(data);
<<<<<<< HEAD
        await loadChats();
=======
        state.activeChat.last_message = { preview: text, text };
        state.activeChat.last_message_at = new Date().toISOString();
        renderChats();
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      } catch (error) {
        elements.messageInput.value = text;
        showToast(error.message || "Не удалось отправить сообщение");
      }
    }

    async function sendPickedFile(event) {
      const file = event.target.files[0];
      if (!file || !state.activeChat) return;
<<<<<<< HEAD
      const sendAsVideoNote = event.target.dataset.videoNote === "1";
=======

>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      try {
        const media = await uploadMedia(file);
        const messageType = sendAsVideoNote
          ? "video_note"
          : media.media_kind === "image"
          ? "image"
          : media.media_kind === "video"
            ? "video"
            : media.media_kind === "audio"
              ? "audio"
              : "file";
        const message = await api(`/chats/${state.activeChat.uuid}/messages/`, {
          method: "POST",
          body: JSON.stringify({
            message_type: messageType,
            attachment_uuids: [media.uuid],
            client_uuid: crypto.randomUUID(),
          }),
        });
        appendMessage(message);
<<<<<<< HEAD
        await Promise.all([loadChats(), loadMedia()]);
=======
        state.activeChat.last_message = { preview: labelForType(type) };
        state.activeChat.last_message_at = new Date().toISOString();
        renderChats();
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      } catch (error) {
        showToast(error.message || "Не удалось отправить файл");
      } finally {
        event.target.value = "";
      }
<<<<<<< HEAD
    });

    document.getElementById("voiceButton").addEventListener("click", () => {
      document.getElementById("fileInput").accept = "audio/*";
      document.getElementById("fileInput").click();
    });

    document.getElementById("videoNoteButton").addEventListener("click", () => {
      document.getElementById("fileInput").accept = "video/*";
      document.getElementById("fileInput").dataset.videoNote = "1";
      document.getElementById("fileInput").click();
    });

    document.getElementById("audioCallButton").addEventListener("click", () => createCall("audio"));
    document.getElementById("videoCallButton").addEventListener("click", () => createCall("video"));

    async function bootstrap() {
      state.me = await api("/users/me/");
      hydrateProfile();
      await Promise.all([loadChats(), loadStories(), loadContacts(), loadMedia(), loadBots()]);
      setSection("dashboard");
      connectSocket();
=======
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
    }

    function hydrateProfile() {
      const name = displayUser(state.me);
      document.getElementById("drawerAvatar").textContent = initials(name);
      document.getElementById("drawerName").textContent = name;
      document.getElementById("drawerEmail").textContent = state.me.email || state.me.username || "";
    }

    async function loadChats() {
      const data = await api("/chats/");
      state.chats = data && (data.results || data) || [];
      renderChats();
      renderActiveSection();
    }

    async function loadStories() {
      try {
        const data = await api("/stories/");
        state.stories = data.results || [];
      } catch (error) {
        state.stories = [];
      }
      renderStories();
    }

    async function loadContacts() {
      try {
        const data = await api("/users/contacts/");
        state.contacts = data.results || [];
      } catch (error) {
        state.contacts = [];
      }
    }

    async function loadMedia() {
      try {
        const data = await api("/media/my/");
        state.media = data.results || [];
      } catch (error) {
        state.media = [];
      }
    }

    async function loadBots() {
      try {
        const data = await api("/bots/");
        state.bots = data.results || [];
      } catch (error) {
        state.bots = [];
      }
    }

    function renderStories() {
      const strip = document.getElementById("storiesStrip");
      if (!state.stories.length) {
        strip.innerHTML = `<div class="story-empty">Stories</div>`;
        return;
      }
      strip.innerHTML = state.stories.slice(0, 12).map((story) => {
        const name = story.author && displayUser(story.author);
        return `<button class="story-item" type="button" title="${escapeAttr(name || "story")}">
          <span class="story-avatar-wrapper"><span class="avatar">${initials(name)}</span></span>
          <small>${escapeHtml(shortText(name || "Story", 12))}</small>
        </button>`;
      }).join("");
    }

    function renderChats() {
      const query = document.getElementById("chatSearch").value.trim().toLowerCase();
      const chats = state.chats.filter((chat) => {
        const titleText = (chat.display_title || chat.title || "").toLowerCase();
        const typeOk = state.chatFilter === "all"
          || (state.chatFilter === "private" && chat.type === "private")
          || (state.chatFilter === "groups" && chat.type === "group");
        return typeOk && titleText.includes(query);
      });

      if (!chats.length) {
        chatList.innerHTML = `<div class="chat-list-empty">Нет чатов</div>`;
        return;
      }

      chatList.innerHTML = chats.map((chat) => {
        const active = state.activeChat && state.activeChat.uuid === chat.uuid ? " active" : "";
        const preview = chat.last_message ? chat.last_message.preview : "Нет сообщений";
        const unread = chat.unread_count ? `<span class="badge">${chat.unread_count}</span>` : "";
        return `<button class="chat-item${active}" data-chat="${chat.uuid}" type="button">
          <span class="avatar">${initials(chat.display_title || chat.title)}</span>
          <span class="chat-meta">
            <strong>${escapeHtml(chat.display_title || chat.title || "Chat")}</strong>
            <small>${escapeHtml(preview)}</small>
          </span>
          <span class="chat-side">
            <time>${formatTime(chat.last_message_at)}</time>
            ${unread}
          </span>
        </button>`;
      }).join("");

      chatList.querySelectorAll("[data-chat]").forEach((button) => {
        button.addEventListener("click", () => openChat(button.dataset.chat));
      });
    }

    function setSection(section) {
      state.section = section || "dashboard";
      state.activeChat = null;
      app.dataset.section = state.section;
      messages.classList.add("is-hidden");
      composer.classList.add("is-hidden");
      content.classList.remove("is-hidden");
      document.querySelectorAll(".drawer-link").forEach((button) => {
        button.classList.toggle("active", button.dataset.section === state.section);
      });
      title.textContent = sectionTitle(state.section);
      status.textContent = sectionSubtitle(state.section);
      avatar.textContent = initials(sectionTitle(state.section));
      renderChats();
      renderActiveSection();
    }

    function renderActiveSection() {
      if (!content || content.classList.contains("is-hidden")) return;
      const section = state.section;
      if (section === "dashboard") return renderDashboard();
      if (section === "users") return renderUsers();
      if (section === "chats") return renderChatSection("all");
      if (section === "private") return renderChatSection("private");
      if (section === "groups") return renderChatSection("group");
      if (section === "media") return renderMedia();
      if (section === "bots") return renderBots();
      if (section === "settings") return renderSettings();
      if (section === "profile") return renderProfile();
      renderDashboard();
    }

    function renderDashboard() {
      const privateCount = state.chats.filter((chat) => chat.type === "private").length;
      const groupCount = state.chats.filter((chat) => chat.type === "group").length;
      const unread = state.chats.reduce((sum, chat) => sum + Number(chat.unread_count || 0), 0);
      content.innerHTML = `<div class="section-grid">
        ${statCard("Чаты", state.chats.length, "Активные диалоги")}
        ${statCard("Группы", groupCount, "Групповые комнаты")}
        ${statCard("Unread", unread, "Новые сообщения")}
        ${statCard("Медиа", state.media.length, "Файлы на сервере")}
      </div>
      <div class="content-columns">
        <section class="panel-block">
          <div class="panel-title"><strong>Последние чаты</strong><span>${privateCount} private</span></div>
          ${renderMiniChatList(state.chats.slice(0, 6))}
        </section>
        <section class="panel-block">
          <div class="panel-title"><strong>Боты</strong><span>${state.bots.length}</span></div>
          ${renderBotRows(state.bots.slice(0, 5))}
        </section>
      </div>`;
    }

    function renderUsers() {
      content.innerHTML = `<section class="panel-block full">
        <div class="panel-title"><strong>Пользователи</strong><span>${state.contacts.length}</span></div>
        ${state.contacts.length ? `<div class="data-table">
          ${state.contacts.map((item) => {
            const user = item.contact_user || item.user || item;
            return `<button class="data-row" type="button" data-user="${escapeAttr(user.uuid || "")}">
              <span class="avatar">${initials(displayUser(user))}</span>
              <span><strong>${escapeHtml(displayUser(user))}</strong><small>${escapeHtml(user.email || user.phone_number || "")}</small></span>
              <em>${escapeHtml(item.source || "contact")}</em>
            </button>`;
          }).join("")}
        </div>` : emptyPanel("Контакты появятся после переписки.")}
      </section>`;
    }

    function renderChatSection(kind) {
      const chats = kind === "all" ? state.chats : state.chats.filter((chat) => chat.type === kind);
      content.innerHTML = `<section class="panel-block full">
        <div class="panel-title"><strong>${escapeHtml(sectionTitle(state.section))}</strong><span>${chats.length}</span></div>
        ${renderMiniChatList(chats)}
      </section>`;
      content.querySelectorAll("[data-open-chat]").forEach((button) => {
        button.addEventListener("click", () => openChat(button.dataset.openChat));
      });
    }

    function renderMedia() {
      content.innerHTML = `<section class="panel-block full">
        <div class="panel-title"><strong>Медиа и файлы</strong><span>${state.media.length}</span></div>
        ${state.media.length ? `<div class="media-grid">
          ${state.media.map((media) => `<a class="media-card" href="${escapeAttr(media.file_url || "#")}" target="_blank" rel="noopener">
            ${media.thumbnail_url ? `<img src="${escapeAttr(media.thumbnail_url)}" alt="">` : `<span>${escapeHtml(media.media_kind || "file")}</span>`}
            <strong>${escapeHtml(shortText(media.original_name || "media", 28))}</strong>
            <small>${escapeHtml(formatBytes(media.size || 0))}</small>
          </a>`).join("")}
        </div>` : emptyPanel("Загруженные файлы появятся здесь.")}
      </section>`;
    }

    function renderBots() {
      content.innerHTML = `<section class="panel-block full">
        <div class="panel-title"><strong>Боты</strong><span>${state.bots.length}</span></div>
        <form class="inline-form" id="botCreateForm">
          <input name="username" placeholder="username_bot" maxlength="32">
          <input name="title" placeholder="Название бота" maxlength="120">
          <button class="mini-button" type="submit">Создать</button>
        </form>
        <div id="botCreateResult" class="form-message"></div>
        ${renderBotRows(state.bots)}
      </section>`;

      const form = document.getElementById("botCreateForm");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const result = document.getElementById("botCreateResult");
        const formData = new FormData(form);
        try {
          const bot = await api("/bots/", {
            method: "POST",
            body: JSON.stringify({
              username: String(formData.get("username") || "").trim(),
              title: String(formData.get("title") || "").trim(),
              scopes: ["send_message"],
            }),
          });
          result.textContent = `Token: ${bot.token}`;
          await loadBots();
        } catch (error) {
          result.textContent = error.message;
        }
      });
    }

    function renderSettings() {
      content.innerHTML = `<div class="content-columns">
        <section class="panel-block">
          <div class="panel-title"><strong>Настройки</strong><span>web</span></div>
          <div class="settings-list">
            <button class="settings-row" type="button" id="settingsThemeToggle"><span>Тема</span><strong>${document.documentElement.dataset.theme}</strong></button>
            <div class="settings-row"><span>Push tokens</span><strong>mobile</strong></div>
            <div class="settings-row"><span>Media storage</span><strong>local</strong></div>
          </div>
        </section>
        <section class="panel-block">
          <div class="panel-title"><strong>Realtime</strong><span>${connectionState.textContent}</span></div>
          <div class="settings-list">
            <div class="settings-row"><span>WebSocket</span><strong>${connectionState.textContent}</strong></div>
            <div class="settings-row"><span>Calls</span><strong>WebRTC signaling</strong></div>
          </div>
        </section>
      </div>`;
      document.getElementById("settingsThemeToggle").addEventListener("click", () => {
        document.getElementById("themeToggle").click();
        renderSettings();
      });
    }

    function renderProfile() {
      content.innerHTML = `<section class="panel-block full profile-panel">
        <div class="avatar avatar-xl">${initials(displayUser(state.me))}</div>
        <div>
          <h2>${escapeHtml(displayUser(state.me))}</h2>
          <p>${escapeHtml(state.me.email || "")}</p>
          <div class="profile-meta">
            <span>UUID</span><strong>${escapeHtml(state.me.uuid || "")}</strong>
            <span>Username</span><strong>${escapeHtml(state.me.username || "")}</strong>
            <span>Status</span><strong>${state.me.show_online_status ? "online visible" : "hidden"}</strong>
          </div>
        </div>
      </section>`;
    }

    function renderMiniChatList(chats) {
      if (!chats.length) return emptyPanel("Список пуст.");
      return `<div class="data-table">${chats.map((chat) => `<button class="data-row" type="button" data-open-chat="${chat.uuid}">
        <span class="avatar">${initials(chat.display_title || chat.title)}</span>
        <span><strong>${escapeHtml(chat.display_title || chat.title || "Chat")}</strong><small>${escapeHtml(chat.last_message ? chat.last_message.preview : "Нет сообщений")}</small></span>
        <em>${chat.type === "group" ? `${chat.members_count || 0} users` : "private"}</em>
      </button>`).join("")}</div>`;
    }

    function renderBotRows(bots) {
      if (!bots.length) return emptyPanel("Ботов пока нет.");
      return `<div class="data-table">${bots.map((bot) => `<div class="data-row">
        <span class="avatar">${initials(bot.title || bot.username)}</span>
        <span><strong>${escapeHtml(bot.title || "Bot")}</strong><small>@${escapeHtml(bot.username || bot.code || "")}</small></span>
        <em>${bot.is_active ? "active" : "disabled"}</em>
      </div>`).join("")}</div>`;
    }

    async function openChat(chatUuid) {
      const chat = state.chats.find((item) => item.uuid === chatUuid);
      if (!chat) return;
      state.activeChat = chat;
      content.classList.add("is-hidden");
      messages.classList.remove("is-hidden");
      composer.classList.remove("is-hidden");
      title.textContent = chat.display_title || chat.title || "Chat";
      status.textContent = chat.type === "group" ? `${chat.members_count || 0} участников` : "online/last seen";
      avatar.textContent = initials(chat.display_title || chat.title);
      sidebar.classList.add("hidden-mobile");
      renderChats();

      const data = await api(`/chats/${chat.uuid}/messages/`);
      messages.innerHTML = "";
      const rows = (data.results || []).slice().reverse();
      rows.forEach(appendMessage);
      if (!rows.length) {
        messages.innerHTML = `<div class="empty-state"><h1>${escapeHtml(title.textContent)}</h1><p>Нет сообщений.</p></div>`;
      }
      if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: chat.uuid }));
      }
    }

    function appendMessage(message) {
      if (!state.activeChat || String(message.chat_uuid || state.activeChat.uuid) !== String(state.activeChat.uuid)) {
        return;
      }
      messages.querySelector(".empty-state")?.remove();
      const own = message.is_own_message || (message.sender && state.me && message.sender.uuid === state.me.uuid);
      const node = document.createElement("article");
      node.className = `message ${own ? "own" : ""}`;
      const sender = message.sender ? displayUser(message.sender) : "";
      const attachments = (message.attachments || []).map(renderAttachment).join("");
      node.innerHTML = `<small>${escapeHtml(sender)}</small><p>${escapeHtml(message.text || labelForType(message.message_type))}</p>${attachments}<time>${formatTime(message.created_at)}</time>`;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    function renderAttachment(media) {
      const url = media.file_url || "";
      if (media.media_kind === "image") return `<img class="message-media" src="${escapeAttr(url)}" alt="${escapeAttr(media.original_name)}">`;
      if (media.media_kind === "audio") return `<audio controls src="${escapeAttr(url)}"></audio>`;
      if (media.media_kind === "video") return `<video controls src="${escapeAttr(url)}" poster="${escapeAttr(media.thumbnail_url || "")}"></video>`;
      return `<a class="file-chip" href="${escapeAttr(url)}" target="_blank" rel="noopener">${escapeHtml(media.original_name || "File")}</a>`;
    }

    async function uploadMedia(file) {
      const fileInput = document.getElementById("fileInput");
      const formData = new FormData();
      formData.append("file", file);
      if (fileInput.dataset.videoNote === "1") {
        formData.append("duration_seconds", "60");
      }

      try {
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
      } finally {
        fileInput.accept = "";
        delete fileInput.dataset.videoNote;
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
<<<<<<< HEAD
=======

>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      if (!putResponse.ok) throw new Error("S3 upload failed");

      return api("/media/complete/", {
        method: "POST",
        body: JSON.stringify({ media_uuid: presign.media.uuid }),
      });
    }

<<<<<<< HEAD
=======
    function autoResizeMessageInput() {
      const input = elements.messageInput;
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
    }

>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
    async function createCall(callType) {
      if (!state.activeChat) {
        showToast("Сначала выберите чат");
        return;
      }

      const title = callType === "audio" ? "Аудиозвонок" : "Видеозвонок";
      showCallModal(title, "Установка защищенного соединения...", initials(chatTitle(state.activeChat)));

      try {
        const call = await api(`/chats/${state.activeChat.uuid}/calls/`, {
          method: "POST",
          body: JSON.stringify({ call_type: callType, metadata: { source: "web" } }),
        });
<<<<<<< HEAD
        status.textContent = `${callType === "audio" ? "Audio" : "Video"} call: ${call.status}`;
=======
        elements.callModalSubtitle.textContent = call.room_key ? `Комната: ${call.room_key}` : "Звонок создан";
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
      } catch (error) {
        elements.callModalSubtitle.textContent = error.message || "Не удалось создать звонок";
      }
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

    function connectSocket() {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      state.socket = new WebSocket(`${protocol}://${window.location.host}/ws?token=${encodeURIComponent(getAccess())}`);

      state.socket.addEventListener("open", () => {
        if (state.activeChat) state.socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: state.activeChat.uuid }));
      });

      state.socket.addEventListener("close", () => {
        setTimeout(connectSocket, 3000);
      });

      state.socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        const message = payload?.payload?.message;
        if ((payload.type === "message:new" || payload.type === "message_persisted" || payload.type === "chat_message") && message) {
          appendMessage(message);
          void loadChats();
        }
      });
    }

<<<<<<< HEAD
    function applyTheme(theme) {
      document.documentElement.dataset.theme = theme;
      localStorage.setItem(themeKey, theme);
      const toggle = document.getElementById("themeToggle");
      if (toggle) toggle.textContent = theme === "dark" ? "Светлая тема" : "Тёмная тема";
    }

    bootstrap().catch((error) => {
      content.innerHTML = `<div class="empty-state"><h1>Ошибка</h1><p>${escapeHtml(error.message)}</p></div>`;
    });
=======
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
>>>>>>> d91a3b0b2ceacecc762eb4290b1fd95049711286
  }

  function statCard(label, value, helper) {
    return `<section class="stat-card"><small>${escapeHtml(helper)}</small><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></section>`;
  }

  function emptyPanel(text) {
    return `<div class="empty-panel">${escapeHtml(text)}</div>`;
  }

  function sectionTitle(section) {
    return {
      dashboard: "Dashboard",
      users: "Пользователи",
      chats: "Все чаты",
      private: "Личные чаты",
      groups: "Групповые чаты",
      media: "Медиа и файлы",
      bots: "Боты",
      settings: "Настройки",
      profile: "Профиль",
    }[section] || "Dashboard";
  }

  function sectionSubtitle(section) {
    return {
      dashboard: "Обзор мессенджера",
      users: "Контакты и пользователи",
      chats: "Активные диалоги",
      private: "Диалоги один на один",
      groups: "Команды и группы",
      media: "Локальное хранилище",
      bots: "Telegram-like bot API",
      settings: "Web cabinet",
      profile: "Текущий аккаунт",
    }[section] || "";
  }

  function displayUser(user) {
    if (!user) return "Akyl";
    return [user.first_name, user.last_name].filter(Boolean).join(" ").trim()
      || user.full_name
      || user.username
      || user.email
      || "Akyl";
  }

  function initials(value) {
    return String(value || "A").trim().slice(0, 1).toUpperCase();
  }

  function shortText(value, length) {
    const text = String(value || "");
    return text.length > length ? `${text.slice(0, length - 3)}...` : text;
  }

  function formatTime(value) {
    if (!value) return "";
    return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function formatBytes(value) {
    const size = Number(value || 0);
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
  }

  function labelForType(type) {
    return {
      image: "Photo",
      video: "Video",
      audio: "Audio message",
      video_note: "Video note",
      file: "File",
      sticker: "Sticker",
    }[type] || "";
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  initLogin();
  initCabinet();
})();
