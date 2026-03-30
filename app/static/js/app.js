const sourceTextarea = document.querySelector("#source_text");
const interactiveButtons = document.querySelectorAll("[data-requires-text]");

function syncActionState() {
  const hasText = Boolean(sourceTextarea?.value.trim());
  interactiveButtons.forEach((button) => {
    button.disabled = !hasText;
  });
}

if (sourceTextarea) {
  sourceTextarea.addEventListener("input", syncActionState);
  syncActionState();
}

function submitDownload() {
  if (!sourceTextarea || !sourceTextarea.value.trim()) {
    return;
  }

  const form = document.createElement("form");
  const field = document.createElement("textarea");

  form.method = "post";
  form.action = "/download";
  form.style.display = "none";

  field.name = "source_text";
  field.value = sourceTextarea.value;

  form.appendChild(field);
  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement) || target.id !== "download-button") {
    return;
  }

  event.preventDefault();
  submitDownload();
});
