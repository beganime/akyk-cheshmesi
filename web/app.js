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
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (error) {
      data = { detail: text || response.statusText || "Request failed" };
    }

    if (!response.ok) {
      const message = data && (data.detail || data.message || JSON.stringify(data));
      throw new Error(message || "Request failed");
    }

    return data;
  }

  function initLogin() {
    const form = document.getElementById("loginForm");
    if (!form) return;

    if (getAccess()) window.location.href = "/messenger/";

    const message = document.getElementById("loginMessage");
    const submitButton = form.querySelector('button[type="submit"]');

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
      renderMe();
      await Promise.allSettled([loadStories(), loadContacts(), loadChats()]);
      connectSocket();
    }

    function logout() {
      localStorage.removeItem(accessKey);
      localStorage.removeItem(refreshKey);
      window.location.href = "/login/";
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
        state.activeChat.last_message = { preview: text, text };
        state.activeChat.last_message_at = new Date().toISOString();
        renderChats();
      } catch (error) {
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
        const localStream = await requestCallMedia(callType);
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

    async function createPeerConnection() {
      state.peerConnection?.close();
      const connection = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
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
        state.localStream = await requestCallMedia(call.callType);
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

    function connectSocket() {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      state.socket = new WebSocket(`${protocol}://${window.location.host}/ws?token=${encodeURIComponent(getAccess())}`);

      state.socket.addEventListener("open", () => {
        state.chats.forEach((chat) => {
          state.socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: chat.uuid }));
        });
      });

      state.socket.addEventListener("close", () => {
        setTimeout(connectSocket, 3000);
      });

      state.socket.addEventListener("message", (event) => {
        try {
          const payload = JSON.parse(event.data);
          const message = payload?.payload?.message;
          if ((payload.type === "message:new" || payload.type === "message_persisted" || payload.type === "chat_message") && message) {
            appendMessage(message);
            void loadChats();
          }
          void handleCallSocketEvent(payload);
        } catch (error) {
          console.warn("websocket event error", error);
        }
      });
    }

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

  initLogin();
  initMessenger();
})();
