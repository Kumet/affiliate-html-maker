function initApp() {
  const sourceTextareas = document.querySelectorAll("[data-input-source]");
  const interactiveButtons = document.querySelectorAll("[data-requires-text]");
  const tabs = document.querySelectorAll("[data-tab-target]");
  const tabPanels = document.querySelectorAll("[data-tab-panel]");
  const previewStatus = document.querySelector("[data-preview-status]");
  const chatgptPrompt = document.getElementById("chatgpt_prompt");
  const chatgptPromptTemplate = document.getElementById("chatgpt_prompt_template");
  const chatgptExpectedProductCount = document.getElementById("chatgpt_expected_product_count");
  const chatgptProductManifest = document.getElementById("chatgpt_product_manifest_json");
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
    const originalImageUrlField = document.createElement("input");
    const originalImageUrlSource = document.getElementById("image_url_source");

    form.method = "post";
    form.action = "/download";
    form.style.display = "none";

    field.name = "source_text";
    field.value = sourceTextarea.value;
    parseModeField.type = "hidden";
    parseModeField.name = "parse_mode";
    parseModeField.value = parseMode || "product";
    originalImageUrlField.type = "hidden";
    originalImageUrlField.name = "original_image_url";
    if (originalImageUrlSource instanceof HTMLInputElement) {
      originalImageUrlField.value = originalImageUrlSource.value;
    }

    form.appendChild(field);
    form.appendChild(parseModeField);
    form.appendChild(originalImageUrlField);
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
  }

  async function submitRawDownload(textareaId, endpoint) {
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

    const formData = new FormData();
    formData.append("source_text", sourceTextarea.value);
    const response = await fetch(endpoint, { method: "POST", body: formData });
    if (!response.ok) {
      setPreviewStatus("ChatGPT用PDFの生成に失敗しました", "error");
      return;
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const fileNameMatch = disposition.match(/filename="([^"]+)"/);
    const fileName = fileNameMatch ? fileNameMatch[1] : "chatgpt_bundle.pdf";
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrl);

    const expectedProducts = response.headers.get("X-Expected-Products") || "";
    const manifestBase64 = response.headers.get("X-Product-Manifest") || "";
    let manifestJson = "[]";
    if (manifestBase64) {
      const binary = atob(manifestBase64);
      const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
      manifestJson = new TextDecoder("utf-8").decode(bytes);
    }

    if (
      chatgptPrompt instanceof HTMLTextAreaElement
      && chatgptPromptTemplate instanceof HTMLTextAreaElement
    ) {
      chatgptPrompt.disabled = false;
      chatgptPrompt.value = `${chatgptPromptTemplate.value}\n\n追加条件:\n- このPDFの想定商品数は ${expectedProducts} 件です\n- products 配列には必ず ${expectedProducts} 件分の JSON を返す\n- 情報が欠けていても item_index を維持して商品を削除しない`;
    }
    if (chatgptExpectedProductCount instanceof HTMLInputElement) {
      chatgptExpectedProductCount.value = expectedProducts;
    }
    if (chatgptProductManifest instanceof HTMLInputElement) {
      chatgptProductManifest.value = manifestJson;
    }

    document.querySelectorAll("[data-copy-button]").forEach((button) => {
      button.removeAttribute("disabled");
    });
    setPreviewStatus("ChatGPT用PDFを生成しました", "success");
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
  const imageUrlSource = document.getElementById("image_url_source");
  const originalImageUrlField = document.getElementById("chatgpt_original_image_url");
  if (imageUrlSource instanceof HTMLInputElement && originalImageUrlField instanceof HTMLInputElement) {
    const syncOriginalImageUrl = () => {
      originalImageUrlField.value = imageUrlSource.value;
    };
    imageUrlSource.addEventListener("input", syncOriginalImageUrl);
    syncOriginalImageUrl();
  }
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

  document.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.hasAttribute("data-download-image-button")) {
      return;
    }

    event.preventDefault();
    await submitRawDownload(
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
