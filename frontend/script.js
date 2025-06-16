const backendURL = "https://summarizer-backend-7my0.onrender.com"; // Local backend
//const backendURL = "http://127.0.0.1:5000"; // Flask local backend

document.getElementById("fetchBtn").addEventListener("click", async () => {
  const topic = document.getElementById("topicInput").value.trim();
  const summaryDiv = document.getElementById("summaryOutput");
  const finalDiv = document.getElementById("finalSummary");

  summaryDiv.innerHTML = "";
  finalDiv.innerHTML = "";

  if (!topic) {
    alert("Please enter a topic.");
    return;
  }

  summaryDiv.innerHTML = `<p>Fetching and summarizing top articles for "${topic}"...</p>`;

  try {
    const res = await fetch(`${backendURL}/summarize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic })
    });

    const data = await res.json();

    summaryDiv.innerHTML = `<h3>📰 Article Summaries:</h3>`;

    data.article_summaries.forEach((item, i) => {
      const p = document.createElement("div");
      p.innerHTML = `<p><strong>${i + 1}. <a href="${item.link}" target="_blank">${item.title}</a></strong></p>
        <p>📝 ${item.summary}</p>`;
      summaryDiv.appendChild(p);
    });

    finalDiv.innerHTML = `<h3>🧠 Consolidated Summary:</h3><p>${data.consolidated_summary}</p>`;

    document.getElementById("downloadBtn").style.display = "inline-block";
    document.getElementById("emailBtn").style.display = "inline-block";

  } catch (err) {
    console.error("Error:", err);
    summaryDiv.innerHTML = `<p style="color: red;">Error: Unable to fetch summary. Please try again.</p>`;
  }
});

function getAllSummaryText() {
  const out = [...document.querySelectorAll("#summaryOutput p, #finalSummary p")];
  return out.map(p => p.innerText).join("\n\n");
}

document.getElementById("downloadBtn").addEventListener("click", () => {
  const text = getAllSummaryText();
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "summary.txt";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

document.getElementById("emailBtn").addEventListener("click", () => {
  const body = encodeURIComponent(getAllSummaryText());
  const subject = encodeURIComponent("Topic Summary");
  const gmailLink = `https://mail.google.com/mail/?view=cm&fs=1&to=&su=${subject}&body=${body}`;
  window.open(gmailLink, "_blank");
});
