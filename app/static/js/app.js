const sourceTextareas = document.querySelectorAll("[data-input-source]");
const interactiveButtons = document.querySelectorAll("[data-requires-text]");
const tabs = document.querySelectorAll("[data-tab-target]");
const tabPanels = document.querySelectorAll("[data-tab-panel]");

function syncActionState() {
  interactiveButtons.forEach((button) => {
    const textareaId = button.getAttribute("data-source-textarea");
    const textarea = textareaId ? document.getElementById(textareaId) : null;
    const hasText = Boolean(textarea instanceof HTMLTextAreaElement && textarea.value.trim());
    button.disabled = !hasText;
  });
}

sourceTextareas.forEach((textarea) => {
  textarea.addEventListener("input", syncActionState);
});
syncActionState();

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

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const targetId = tab.getAttribute("data-tab-target");
    if (!targetId) {
      return;
    }

    activateTab(targetId);
  });
});

function submitDownload(textareaId, parseMode) {
  const sourceTextarea = textareaId ? document.getElementById(textareaId) : null;
  if (!(sourceTextarea instanceof HTMLTextAreaElement) || !sourceTextarea.value.trim()) {
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
