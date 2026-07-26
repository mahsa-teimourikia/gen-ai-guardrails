import { questions } from "./questions.js";
import { gradeQuiz } from "./grading.js";

const key = "gen-ai-guardrails-quiz-v1";
const state = JSON.parse(localStorage.getItem(key) || "{}");
const $ = (id) => document.getElementById(id);
const save = () => localStorage.setItem(key, JSON.stringify(state));
const categories = [...new Set(questions.map((q) => q.category))];
const slug = (value) => value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

function renderCategories() {
  $("category-list").innerHTML = categories.map((c) => `<a href="#${slug(c)}"><span>${c}</span><strong>${questions.filter(q => q.category === c).length}</strong></a>`).join("");
}
function renderQuestions() {
  $("question-list").innerHTML = questions.map((q, i) => `<fieldset class="question" id="${slug(q.category)}-${i + 1}"><legend><span class="question-number">${String(i + 1).padStart(2, "0")}</span><span>${q.prompt}</span></legend><p class="hint">Select all that apply</p><div class="options">${q.options.map((option, j) => `<label class="option"><input type="checkbox" name="${q.id}" value="${j}" ${state[q.id]?.includes(j) ? "checked" : ""}><span>${option}</span></label>`).join("")}</div><div class="feedback" hidden></div></fieldset>`).join("");
  document.querySelectorAll("input[type=checkbox]").forEach(input => input.addEventListener("change", () => { state[input.name] = [...document.querySelectorAll(`input[name="${input.name}"]:checked`)].map(x => Number(x.value)); save(); updateProgress(); }));
}
function updateProgress() { const answered = questions.filter(q => (state[q.id] || []).length).length; $("answered-count").textContent = answered; $("progress-track").value = answered; }
function grade() { const result = gradeQuiz(questions, state); $("results").hidden = false; $("score-percent").textContent = `${result.percent}%`; $("score-heading").textContent = result.percent >= 80 ? "Strong guardrail instincts" : result.percent >= 60 ? "Good foundation — keep practicing" : "Review the learning path and try again"; $("score-summary").textContent = `${result.correct}/${result.total} questions fully correct. Exact-match grading rewards selecting every correct answer and no incorrect answers.`; $("topic-scores").innerHTML = result.categories.map(c => `<li><span>${c.category}</span><strong>${c.correct}/${c.total}</strong></li>`).join(""); window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); return result; }
function review() { document.querySelectorAll(".question").forEach((el, i) => { const q = questions[i]; const chosen = state[q.id] || []; const feedback = el.querySelector(".feedback"); el.classList.toggle("is-correct", chosen.length === q.correct.length && chosen.every(x => q.correct.includes(x))); feedback.hidden = false; feedback.innerHTML = `<strong>Correct: ${q.correct.map(x => q.options[x]).join(" · ")}</strong><p>${q.explanation}</p><a href="https://github.com/mahsa-teimourikia/gen-ai-guardrails/blob/main/${q.source.url}" target="_blank" rel="noreferrer">Read the source: ${q.source.label}</a>`; }); }
$("question-count").textContent = questions.length; $("progress-total").textContent = questions.length; $("progress-track").max = questions.length; $("category-count").textContent = categories.length; renderCategories(); renderQuestions(); updateProgress();
$("quiz-form").addEventListener("submit", (e) => { e.preventDefault(); grade(); }); $("review-button").addEventListener("click", review); $("retry-button").addEventListener("click", () => { $("results").hidden = true; document.querySelector(".question").scrollIntoView({ behavior: "smooth" }); }); $("reset-button").addEventListener("click", () => { Object.keys(state).forEach(k => delete state[k]); save(); renderQuestions(); updateProgress(); $("results").hidden = true; window.scrollTo({ top: 0, behavior: "smooth" }); });
