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
      const detail = data && (data.detail || data.error || JSON.stringify(data));
      throw new Error(detail || "Request failed");
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

  function initCabinet() {
    const app = document.querySelector(".cabinet-app");
    if (!app) return;
    if (!getAccess()) {
      window.location.href = "/login/";
      return;
    }

    const state = {
      me: null,
      chats: [],
      contacts: [],
      media: [],
      bots: [],
      stories: [],
      activeChat: null,
      section: "dashboard",
      chatFilter: "all",
      socket: null,
    };

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
      localStorage.removeItem(accessKey);
      localStorage.removeItem(refreshKey);
      window.location.href = "/login/";
    });

    document.getElementById("backToChats").addEventListener("click", () => {
      sidebar.classList.remove("hidden-mobile");
    });

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
      event.preventDefault();
      if (!state.activeChat) return;
      const input = document.getElementById("messageInput");
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
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
        await loadChats();
      } catch (error) {
        input.value = text;
        alert(error.message);
      }
    });

    document.getElementById("attachButton").addEventListener("click", () => {
      document.getElementById("fileInput").click();
    });

    document.getElementById("fileInput").addEventListener("change", async (event) => {
      const file = event.target.files[0];
      if (!file || !state.activeChat) return;
      const sendAsVideoNote = event.target.dataset.videoNote === "1";
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
        await Promise.all([loadChats(), loadMedia()]);
      } catch (error) {
        alert(error.message);
      } finally {
        event.target.value = "";
      }
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
      if (!putResponse.ok) throw new Error("S3 upload failed");

      return api("/media/complete/", {
        method: "POST",
        body: JSON.stringify({ media_uuid: presign.media.uuid }),
      });
    }

    async function createCall(callType) {
      if (!state.activeChat) return;
      try {
        const call = await api(`/chats/${state.activeChat.uuid}/calls/`, {
          method: "POST",
          body: JSON.stringify({ call_type: callType, metadata: { source: "web" } }),
        });
        status.textContent = `${callType === "audio" ? "Audio" : "Video"} call: ${call.status}`;
      } catch (error) {
        alert(error.message);
      }
    }

    function connectSocket() {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      state.socket = new WebSocket(`${protocol}://${window.location.host}/ws?token=${encodeURIComponent(getAccess())}`);
      state.socket.addEventListener("open", () => {
        connectionState.textContent = "online";
        if (state.activeChat) state.socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: state.activeChat.uuid }));
      });
      state.socket.addEventListener("close", () => {
        connectionState.textContent = "offline";
        setTimeout(connectSocket, 3000);
      });
      state.socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === "message:new" && payload.payload && payload.payload.message) {
          appendMessage(payload.payload.message);
        }
        if (payload.type === "message_persisted" && payload.payload && payload.payload.message) {
          appendMessage(payload.payload.message);
        }
      });
    }

    function applyTheme(theme) {
      document.documentElement.dataset.theme = theme;
      localStorage.setItem(themeKey, theme);
      const toggle = document.getElementById("themeToggle");
      if (toggle) toggle.textContent = theme === "dark" ? "Светлая тема" : "Тёмная тема";
    }

    bootstrap().catch((error) => {
      content.innerHTML = `<div class="empty-state"><h1>Ошибка</h1><p>${escapeHtml(error.message)}</p></div>`;
    });
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
