document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("ask_form");
  const messageInput = document.getElementById("user_message");
  const resultDiv = document.getElementById("result");

  // Create buttons dynamically or ensure your HTML has these:
  const previewBtn = document.getElementById("preview_btn");
  const sendBtn = document.getElementById("send_btn");

  // Helper: Display JSON result nicely
  function displayResult(data, isError = false) {
    resultDiv.innerHTML = "";
    if (isError) {
      const p = document.createElement("p");
      p.style.color = "red";
      p.textContent = data.error || "An error occurred.";
      resultDiv.appendChild(p);
    } else {
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(data, null, 2);
      resultDiv.appendChild(pre);
    }
  }

  // Track last payload for Send
  let lastPayload = null;

  // Preview handler
  previewBtn.addEventListener("click", async () => {
    const text = messageInput.value.trim();
    if (!text) return alert("Please enter a message to preview.");

    previewBtn.disabled = true;
    sendBtn.disabled = true;
    displayResult({ loading: "Generating preview..." });

    try {
      const response = await fetch("/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await response.json();
      if (!response.ok) {
        displayResult(data, true);
        lastPayload = null;
      } else {
        displayResult(data, false);
        lastPayload = { message: text }; // Cache payload for send
      }
    } catch (err) {
      displayResult({ error: err.message }, true);
      lastPayload = null;
    } finally {
      previewBtn.disabled = false;
      sendBtn.disabled = false;
    }
  });

  // Send handler
  sendBtn.addEventListener("click", async () => {
    if (!lastPayload) {
      return alert("Please preview your message before sending.");
    }

    previewBtn.disabled = true;
    sendBtn.disabled = true;
    displayResult({ loading: "Sending..." });

    try {
      const response = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastPayload),
      });
      const data = await response.json();

      if (!response.ok) {
        displayResult(data, true);
      } else {
        displayResult(data);
        // Optionally clear input or lastPayload after sending
        // messageInput.value = "";
        // lastPayload = null;
      }
    } catch (err) {
      displayResult({ error: err.message }, true);
    } finally {
      previewBtn.disabled = false;
      sendBtn.disabled = false;
    }
  });

  // Optional: You can bind form submit to preview or disable form submit
  form.addEventListener("submit", (e) => e.preventDefault());
});
