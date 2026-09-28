"use strict";

const form = document.querySelector("#recommendation-form");
const userInput = document.querySelector("#user-id");
const limitSelect = document.querySelector("#result-limit");
const list = document.querySelector("#recommendation-list");
const emptyState = document.querySelector("#empty-state");
const errorState = document.querySelector("#error-state");
const countLabel = document.querySelector("#result-count");
const statusLabel = document.querySelector("#request-status");
const refreshButton = form.querySelector("button[type='submit']");
const requestPulse = document.querySelector(".request-pulse");

function setBusy(isBusy, message) {
  list.setAttribute("aria-busy", String(isBusy));
  refreshButton.disabled = isBusy;
  requestPulse.classList.toggle("is-working", isBusy);
  statusLabel.textContent = message;
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function makeRecommendationCard(item, index, userId) {
  const card = makeElement("article", "recommendation-card");
  card.style.animationDelay = `${Math.min(index * 45, 225)}ms`;

  const rank = makeElement("div", "rank-marker", String(index + 1).padStart(2, "0"));
  rank.setAttribute("aria-label", `Recommendation ${index + 1}`);

  const content = makeElement("div", "course-content");
  const metadata = makeElement("div", "course-meta");
  metadata.append(
    makeElement("span", "category", item.category || "Learning"),
    makeElement("span", "meta-bullet", "·"),
    makeElement("span", "", item.difficulty || "All levels"),
  );
  content.append(
    metadata,
    makeElement("h3", "", item.title),
    makeElement("p", "course-explanation", item.explanation),
  );

  const score = makeElement("div", "course-score");
  const scoreValue = Math.max(0, Math.min(100, Math.round((item.score || 0) * 100)));
  score.append(
    makeElement("strong", "score-number", `${scoreValue}%`),
    makeElement("span", "score-label", "MATCH"),
  );
  const track = makeElement("div", "score-track");
  const fill = document.createElement("span");
  fill.style.width = `${scoreValue}%`;
  track.append(fill);
  score.append(track);

  const actions = makeElement("div", "card-actions");
  actions.append(
    makeFeedbackButton("Save for later", "bookmark", item, userId),
    makeFeedbackButton("Mark complete", "complete", item, userId),
  );
  card.append(rank, content, score, actions);
  return card;
}

function makeFeedbackButton(label, type, item, userId) {
  const button = makeElement("button", "feedback-button", label);
  button.type = "button";
  button.addEventListener("click", () => sendFeedback(button, userId, item.id, type));
  return button;
}

async function loadRecommendations() {
  const userId = Number(userInput.value);
  const limit = Number(limitSelect.value);
  if (!Number.isInteger(userId) || userId <= 0) {
    errorState.hidden = false;
    errorState.textContent = "Enter a valid learner ID to continue.";
    return;
  }

  emptyState.hidden = true;
  errorState.hidden = true;
  countLabel.textContent = "LOADING";
  list.replaceChildren(...Array.from({ length: Math.min(limit, 4) }, () => makeElement("div", "loading-card")));
  setBusy(true, "Finding a good next step");

  try {
    const response = await fetch(`/recommend/${userId}?limit=${limit}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load recommendations.");

    const recommendations = data.recommendations || [];
    list.replaceChildren(...recommendations.map((item, index) => makeRecommendationCard(item, index, userId)));
    countLabel.textContent = `${recommendations.length} ${recommendations.length === 1 ? "ITEM" : "ITEMS"}`;
    emptyState.hidden = recommendations.length !== 0;
    setBusy(false, `Updated for learner ${userId}`);
    await loadMetrics();
  } catch (error) {
    list.replaceChildren();
    countLabel.textContent = "UNAVAILABLE";
    errorState.hidden = false;
    errorState.textContent = error.message || "Unable to reach the recommendation service.";
    setBusy(false, "Could not update recommendations");
  }
}

async function sendFeedback(button, userId, contentId, type) {
  button.classList.add("is-sending");
  button.textContent = "Saving…";
  try {
    const response = await fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, content_id: contentId, type }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Feedback could not be saved.");
    statusLabel.textContent = type === "complete" ? "Progress recorded" : "Saved to your activity";
    await loadRecommendations();
  } catch (error) {
    button.classList.remove("is-sending");
    button.textContent = type === "complete" ? "Mark complete" : "Save for later";
    errorState.hidden = false;
    errorState.textContent = error.message || "Feedback could not be saved.";
  }
}

async function loadMetrics() {
  try {
    const [healthResponse, metricsResponse] = await Promise.all([
      fetch("/health"),
      fetch("/metrics"),
    ]);
    const metrics = await metricsResponse.json();
    const healthy = healthResponse.ok;

    document.querySelector("#health-label").textContent = healthy ? "Service online" : "Service unavailable";
    document.querySelector("#health-indicator").className = `health-indicator ${healthy ? "is-online" : "is-offline"}`;
    document.querySelector("#metric-requests").textContent = metrics.request_count ?? "—";
    document.querySelector("#metric-latency").textContent = Number(metrics.average_latency_ms || 0).toFixed(1);
    const hitRate = Math.round((metrics.cache_hit_rate || 0) * 100);
    document.querySelector("#metric-cache").textContent = `${hitRate}%`;
    document.querySelector("#cache-bar").style.width = `${hitRate}%`;
  } catch {
    document.querySelector("#health-label").textContent = "Service unavailable";
    document.querySelector("#health-indicator").className = "health-indicator is-offline";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const url = new URL(window.location.href);
  url.searchParams.set("user_id", userInput.value);
  history.replaceState(null, "", url);
  loadRecommendations();
});

const initialUser = new URLSearchParams(window.location.search).get("user_id");
if (initialUser && /^\d+$/.test(initialUser)) userInput.value = initialUser;
loadMetrics();
loadRecommendations();