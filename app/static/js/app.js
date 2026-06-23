function initApp() {
  const sourceTextareas = document.querySelectorAll("[data-input-source]");
  const interactiveButtons = document.querySelectorAll("[data-requires-text]");
  const tabs = document.querySelectorAll("[data-tab-target]");
  const tabPanels = document.querySelectorAll("[data-tab-panel]");
  const previewStatus = document.querySelector("[data-preview-status]");
  let activeRequestCount = 0;

  function syncActionState() {
    interactiveButtons.forEach((button) => {
      const textareaId = button.getAttribute("data-source-textarea");
      const textarea = textareaId ? document.getElementById(textareaId) : null;
      const hasText = Boolean(
        (textarea instanceof HTMLTextAreaElement || textarea instanceof HTMLInputElement)
        && textarea.value.trim()
      );
      button.disabled = !hasText;
    });
  }

  function setPreviewStatus(message, state = "idle") {
    if (!(previewStatus instanceof HTMLElement)) {
      return;
    }

    previewStatus.textContent = message;
    previewStatus.classList.remove("is-loading", "is-success", "is-error");

    if (state === "loading") {
      previewStatus.classList.add("is-loading");
    } else if (state === "success") {
      previewStatus.classList.add("is-success");
    } else if (state === "error") {
      previewStatus.classList.add("is-error");
    }
  }

  function activateTab(targetId) {
    tabs.forEach((tab) => {
      const isActive = tab.getAttribute("data-tab-target") === targetId;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });

    tabPanels.forEach((panel) => {
      const isActive = panel.id === targetId;
      panel.classList.toggle("is-active", isActive);
      panel.hidden = !isActive;
    });
  }

  function submitDownload(textareaId, parseMode) {
    const sourceTextarea = textareaId ? document.getElementById(textareaId) : null;
    if (
      !(
        sourceTextarea instanceof HTMLTextAreaElement
        || sourceTextarea instanceof HTMLInputElement
      )
      || !sourceTextarea.value.trim()
    ) {
      return;
    }

    const form = document.createElement("form");
    const field = document.createElement("textarea");
    const parseModeField = document.createElement("input");

    form.method = "post";
    form.action = "/download";
    form.style.display = "none";

    field.name = "source_text";
    field.value = sourceTextarea.value;
    parseModeField.type = "hidden";
    parseModeField.name = "parse_mode";
    parseModeField.value = parseMode || "product";

    form.appendChild(field);
    form.appendChild(parseModeField);
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
  }

  function submitRawDownload(textareaId, endpoint) {
    const sourceTextarea = textareaId ? document.getElementById(textareaId) : null;
    if (
      !(
        sourceTextarea instanceof HTMLTextAreaElement
        || sourceTextarea instanceof HTMLInputElement
      )
      || !sourceTextarea.value.trim()
    ) {
      return;
    }

    const form = document.createElement("form");
    const field = document.createElement("textarea");

    form.method = "post";
    form.action = endpoint;
    form.style.display = "none";

    field.name = "source_text";
    field.value = sourceTextarea.value;
    form.appendChild(field);
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
  }

  async function copyTextFromTarget(targetId) {
    const source = targetId ? document.getElementById(targetId) : null;
    if (!(source instanceof HTMLTextAreaElement || source instanceof HTMLInputElement)) {
      return false;
    }

    source.focus();
    source.select();

    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(source.value);
      return true;
    }

    return document.execCommand("copy");
  }

  sourceTextareas.forEach((textarea) => {
    textarea.addEventListener("input", syncActionState);
  });
  syncActionState();

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab-target");
      if (!targetId) {
        return;
      }

      activateTab(targetId);
    });
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.hasAttribute("data-download-button")) {
      return;
    }

    event.preventDefault();
    submitDownload(
      target.getAttribute("data-source-textarea"),
      target.getAttribute("data-parse-mode")
    );
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.hasAttribute("data-download-image-button")) {
      return;
    }

    event.preventDefault();
    submitRawDownload(
      target.getAttribute("data-source-textarea"),
      target.getAttribute("data-download-endpoint") || "/download-chatgpt-image"
    );
  });

  document.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.hasAttribute("data-copy-button")) {
      return;
    }

    event.preventDefault();
    const originalText = target.textContent || "";
    const copied = await copyTextFromTarget(target.getAttribute("data-copy-target"));
    target.textContent = copied ? "コピーしました" : "コピー失敗";
    window.setTimeout(() => {
      target.textContent = originalText;
    }, 1600);
  });

  document.body.addEventListener("htmx:beforeRequest", (event) => {
    const target = event.detail.target;
    if (!(target instanceof HTMLElement) || target.id !== "preview-panel") {
      return;
    }

    activeRequestCount += 1;
    setPreviewStatus("プレビューを生成中です", "loading");
  });

  document.body.addEventListener("htmx:afterRequest", (event) => {
    const target = event.detail.target;
    if (!(target instanceof HTMLElement) || target.id !== "preview-panel") {
      return;
    }

    activeRequestCount = Math.max(0, activeRequestCount - 1);
    if (activeRequestCount > 0) {
      return;
    }

    if (event.detail.successful) {
      setPreviewStatus("プレビューを更新しました", "success");
      return;
    }

    setPreviewStatus("プレビューの生成に失敗しました", "error");
  });

  document.body.addEventListener("htmx:responseError", (event) => {
    const target = event.detail.target;
    if (!(target instanceof HTMLElement) || target.id !== "preview-panel") {
      return;
    }

    activeRequestCount = 0;
    setPreviewStatus("プレビューの生成に失敗しました", "error");
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp, { once: true });
} else {
  initApp();
}
