import test from "node:test";
import assert from "node:assert/strict";
import { questions } from "./questions.js";
import { normalizeSelection, isExactMatch, gradeQuiz } from "./grading.js";

test("quiz has balanced categories and complete questions", () => {
  assert.equal(questions.length, 30);
  const counts = Object.values(Object.groupBy(questions, q => q.category));
  assert.deepEqual(counts.map(x => x.length), [4, 4, 5, 5, 4, 4, 4]);
  for (const q of questions) { assert.ok(q.correct.length > 1); assert.ok(q.explanation); assert.match(q.source.url, /^curriculum\//); }
});
test("selection normalization removes duplicates and sorts", () => assert.deepEqual(normalizeSelection([3, 1, 3, 0]), [0, 1, 3]));
test("exact match rejects missing and extra answers", () => { assert.equal(isExactMatch([0, 2], [2, 0]), true); assert.equal(isExactMatch([0], [0, 2]), false); assert.equal(isExactMatch([0, 4], [0, 2]), false); });
test("complete answer key earns 100 percent", () => { const answers = Object.fromEntries(questions.map(q => [q.id, q.correct])); const result = gradeQuiz(questions, answers); assert.equal(result.percent, 100); assert.equal(result.correct, 30); });
test("unanswered quiz earns zero", () => { const result = gradeQuiz(questions, {}); assert.equal(result.percent, 0); assert.equal(result.correct, 0); });
