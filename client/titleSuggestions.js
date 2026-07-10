function isSubsequence(candidate, query) {
  const candidateChars = [...candidate];
  const queryChars = [...query];
  let queryIndex = 0;

  for (const char of candidateChars) {
    if (char === queryChars[queryIndex]) {
      queryIndex += 1;
      if (queryIndex === queryChars.length) {
        return true;
      }
    }
  }

  return false;
}

function fuzzyScore(candidate, query) {
  if (!query) {
    return 0;
  }

  const candidateLower = candidate.toLocaleLowerCase();
  const queryLower = query.toLocaleLowerCase();

  if (candidateLower === queryLower) {
    return 0;
  }
  if (candidateLower.startsWith(queryLower)) {
    return 1;
  }
  if (isSubsequence(candidateLower, queryLower)) {
    return 2;
  }
  if (candidateLower.includes(queryLower)) {
    return 3;
  }

  return null;
}

export function getTitleSuggestions(input, titles, limit = 8) {
  const title = input || "";
  const parts = title.split(".");
  const currentSegment = parts.at(-1);
  const prefixParts = parts.slice(0, -1);

  if (prefixParts.some((part) => part === "")) {
    return [];
  }

  const candidates = new Set();
  for (const existingTitle of titles) {
    const titleParts = existingTitle.split(".");
    if (titleParts.length <= prefixParts.length) {
      continue;
    }

    const prefixMatches = prefixParts.every((part, index) => {
      return titleParts[index] === part;
    });
    if (!prefixMatches) {
      continue;
    }

    const candidate = titleParts[prefixParts.length];
    if (candidate) {
      candidates.add(candidate);
    }
  }

  return [...candidates]
    .map((segment) => {
      const score = fuzzyScore(segment, currentSegment);
      return {
        segment,
        completion: [...prefixParts, segment].join("."),
        score,
      };
    })
    .filter((suggestion) => suggestion.score !== null)
    .sort((a, b) => a.score - b.score || a.segment.localeCompare(b.segment))
    .slice(0, limit);
}
