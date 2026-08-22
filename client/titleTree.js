function createNode(name, path) {
  return {
    name,
    path,
    fullTitle: null,
    isNote: false,
    children: [],
    childMap: new Map(),
  };
}

function compareNodes(a, b) {
  return a.name.localeCompare(b.name) || a.path.localeCompare(b.path);
}

function finalizeNode(node) {
  node.children = [...node.childMap.values()]
    .sort(compareNodes)
    .map(finalizeNode);
  delete node.childMap;
  return node;
}

export function buildTitleTree(titles) {
  const roots = new Map();

  for (const title of new Set(titles)) {
    if (typeof title !== "string" || !title) {
      continue;
    }

    const titleParts = title.split(".");
    // Keep unusual existing filenames accessible instead of rendering an
    // empty level for titles such as "project..design".
    const parts = titleParts.some((part) => !part) ? [title] : titleParts;
    let siblings = roots;
    const pathParts = [];
    let noteNode = null;

    for (const part of parts) {
      pathParts.push(part);
      const path = pathParts.join(".");
      if (!siblings.has(part)) {
        siblings.set(part, createNode(part, path));
      }
      noteNode = siblings.get(part);
      siblings = noteNode.childMap;
    }

    noteNode.isNote = true;
    noteNode.fullTitle = title;
  }

  return [...roots.values()].sort(compareNodes).map(finalizeNode);
}
