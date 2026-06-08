(function () {
  const apiBase = "/api";
  const accessKey = "akyl_access";
  const refreshKey = "akyl_refresh";

  function getAccess() {
    return localStorage.getItem(accessKey);
  }

  async function api(path, options = {}) {
    const headers = options.headers || {};
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
      const message = data && (data.detail || JSON.stringify(data));
      throw new Error(message || "Request failed");
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
      const payload = {
        email: document.getElementById("email").value.trim(),
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
        message.textContent = error.message;
      }
    });
  }

  function initials(value) {
    return (value || "A").trim().slice(0, 1).toUpperCase();
  }

  function formatTime(value) {
    if (!value) return "";
    return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
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
      activeChat: null,
      socket: null,
    };

    const chatList = document.getElementById("chatList");
    const messages = document.getElementById("messages");
    const title = document.getElementById("activeChatTitle");
    const status = document.getElementById("activeChatStatus");
    const avatar = document.getElementById("activeAvatar");
    const connectionState = document.getElementById("connectionState");
    const sidebar = document.getElementById("chatSidebar");

    document.getElementById("logoutButton").addEventListener("click", () => {
      localStorage.removeItem(accessKey);
      localStorage.removeItem(refreshKey);
      window.location.href = "/login/";
    });

    document.getElementById("backToChats").addEventListener("click", () => {
      sidebar.classList.remove("hidden-mobile");
    });

    document.getElementById("chatSearch").addEventListener("input", renderChats);

    document.getElementById("messageForm").addEventListener("submit", async (event) => {
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
      } catch (error) {
        alert(error.message);
      } finally {
        event.target.value = "";
      }
    });

    document.getElementById("voiceButton").addEventListener("click", () => {
      alert("Запись аудио подключается на клиентской стороне. Backend уже принимает message_type=audio.");
    });
    document.getElementById("videoNoteButton").addEventListener("click", () => {
      alert("Видеокружок записывается клиентом и отправляется как message_type=video_note.");
    });
    document.getElementById("audioCallButton").addEventListener("click", () => createCall("audio"));
    document.getElementById("videoCallButton").addEventListener("click", () => createCall("video"));

    async function bootstrap() {
      state.me = await api("/users/me/");
      await loadStories();
      await loadChats();
      connectSocket();
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
      if (!putResponse.ok) {
        throw new Error("S3 upload failed");
      }

      return api("/media/complete/", {
        method: "POST",
        body: JSON.stringify({ media_uuid: presign.media.uuid }),
      });
    }

    async function loadStories() {
      const strip = document.getElementById("storiesStrip");
      try {
        const data = await api("/stories/");
        const stories = data.results || [];
        strip.innerHTML = stories.slice(0, 12).map((story) => {
          const name = story.author && (story.author.username || story.author.full_name || story.author.email);
          return `<button class="story-dot" title="${name || "story"}"><span>${initials(name)}</span></button>`;
        }).join("");
      } catch (error) {
        strip.innerHTML = "";
      }
    }

    async function loadChats() {
      const data = await api("/chats/");
      state.chats = data.results || data;
      renderChats();
    }

    function renderChats() {
      const query = document.getElementById("chatSearch").value.trim().toLowerCase();
      const chats = state.chats.filter((chat) => (chat.display_title || chat.title || "").toLowerCase().includes(query));
      chatList.innerHTML = chats.map((chat) => {
        const active = state.activeChat && state.activeChat.uuid === chat.uuid ? " active" : "";
        const unread = chat.unread_count ? `<span class="badge">${chat.unread_count}</span>` : "";
        const preview = chat.last_message ? chat.last_message.preview : "Нет сообщений";
        return `<button class="chat-item${active}" data-chat="${chat.uuid}">
          <span class="avatar">${initials(chat.display_title)}</span>
          <span class="chat-meta"><strong>${chat.display_title}</strong><small>${preview}</small></span>
          ${unread}
        </button>`;
      }).join("");
      chatList.querySelectorAll("[data-chat]").forEach((button) => {
        button.addEventListener("click", () => openChat(button.dataset.chat));
      });
    }

    async function openChat(chatUuid) {
      const chat = state.chats.find((item) => item.uuid === chatUuid);
      if (!chat) return;
      state.activeChat = chat;
      title.textContent = chat.display_title;
      status.textContent = chat.type === "group" ? `${chat.members_count} участников` : "online/last seen";
      avatar.textContent = initials(chat.display_title);
      sidebar.classList.add("hidden-mobile");
      renderChats();
      const data = await api(`/chats/${chat.uuid}/messages/`);
      messages.innerHTML = "";
      const rows = (data.results || []).slice().reverse();
      rows.forEach(appendMessage);
      if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify({ type: "subscribe_chat", chat_uuid: chat.uuid }));
      }
    }

    function appendMessage(message) {
      if (!state.activeChat || String(message.chat_uuid || state.activeChat.uuid) !== String(state.activeChat.uuid)) {
        return;
      }
      const own = message.is_own_message || (message.sender && state.me && message.sender.uuid === state.me.uuid);
      const node = document.createElement("article");
      node.className = `message ${own ? "own" : ""}`;
      const sender = message.sender ? (message.sender.username || message.sender.email || "") : "";
      const attachments = (message.attachments || []).map(renderAttachment).join("");
      node.innerHTML = `<small>${sender}</small><p>${escapeHtml(message.text || labelForType(message.message_type))}</p>${attachments}<time>${formatTime(message.created_at)}</time>`;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    function renderAttachment(media) {
      const url = media.file_url || "";
      if (media.media_kind === "image") return `<img class="message-media" src="${url}" alt="${escapeHtml(media.original_name)}">`;
      if (media.media_kind === "audio") return `<audio controls src="${url}"></audio>`;
      if (media.media_kind === "video") return `<video controls src="${url}" poster="${media.thumbnail_url || ""}"></video>`;
      return `<a class="file-chip" href="${url}" target="_blank" rel="noopener">${escapeHtml(media.original_name)}</a>`;
    }

    function labelForType(type) {
      return {
        image: "Photo",
        video: "Video",
        audio: "Audio message",
        video_note: "Video note",
        file: "File",
      }[type] || "";
    }

    async function createCall(callType) {
      if (!state.activeChat) return;
      try {
        const call = await api(`/chats/${state.activeChat.uuid}/calls/`, {
          method: "POST",
          body: JSON.stringify({ call_type: callType, metadata: { source: "web" } }),
        });
        alert(`${callType === "audio" ? "Аудио" : "Видео"} звонок создан. Room: ${call.room_key}`);
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

    function escapeHtml(value) {
      return String(value || "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[char]));
    }

    bootstrap().catch((error) => {
      messages.innerHTML = `<div class="empty-state"><h1>Ошибка</h1><p>${escapeHtml(error.message)}</p></div>`;
    });
  }

  initLogin();
  initMessenger();
})();
