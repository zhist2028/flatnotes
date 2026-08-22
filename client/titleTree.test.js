import assert from "node:assert/strict";
import test from "node:test";

import { buildTitleTree } from "./titleTree.js";

test("builds virtual levels and marks real notes", () => {
  const tree = buildTitleTree([
    "project.flatnotes",
    "project.flatnotes.design",
  ]);

  assert.equal(tree.length, 1);
  assert.equal(tree[0].name, "project");
  assert.equal(tree[0].isNote, false);

  const flatnotes = tree[0].children[0];
  assert.equal(flatnotes.name, "flatnotes");
  assert.equal(flatnotes.isNote, true);
  assert.equal(flatnotes.fullTitle, "project.flatnotes");
  assert.equal(flatnotes.children[0].name, "design");
  assert.equal(flatnotes.children[0].isNote, true);
});

test("allows a node to be both a note and a parent", () => {
  const tree = buildTitleTree(["project", "project.design"]);

  assert.equal(tree[0].isNote, true);
  assert.equal(tree[0].fullTitle, "project");
  assert.equal(tree[0].children[0].fullTitle, "project.design");
});

test("sorts each level and removes duplicate titles", () => {
  const tree = buildTitleTree(["zeta", "alpha.two", "alpha.one", "zeta"]);

  assert.deepEqual(
    tree.map((node) => node.name),
    ["alpha", "zeta"],
  );
  assert.deepEqual(
    tree[0].children.map((node) => node.name),
    ["one", "two"],
  );
});

test("keeps titles with empty segments accessible as a single node", () => {
  const tree = buildTitleTree(["project..design"]);

  assert.equal(tree[0].name, "project..design");
  assert.equal(tree[0].fullTitle, "project..design");
  assert.equal(tree[0].children.length, 0);
});
