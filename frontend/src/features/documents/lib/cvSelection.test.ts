import { describe, expect, it } from "vitest";
import {
  defaultCvName,
  fullSelection,
  toggleItem,
  toggleSection,
  toRequest,
} from "./cvSelection";

describe("cvSelection", () => {
  it("starts with every section and nothing excluded", () => {
    expect(toRequest(fullSelection())).toEqual({
      sections: [
        "summary",
        "experience",
        "education",
        "project",
        "certification",
        "skills",
        "languages",
      ],
      excluded_ids: [],
    });
  });

  it("keeps the CV order whatever the order of the clicks", () => {
    let state = fullSelection();
    state = toggleSection(state, "summary");
    state = toggleSection(state, "skills");
    state = toggleSection(state, "summary");

    expect(toRequest(state).sections).toEqual([
      "summary",
      "experience",
      "education",
      "project",
      "certification",
      "languages",
    ]);
  });

  it("toggling an item twice puts it back", () => {
    let state = toggleItem(fullSelection(), "b");
    state = toggleItem(state, "a");
    expect(toRequest(state).excluded_ids).toEqual(["a", "b"]);

    state = toggleItem(state, "b");
    expect(toRequest(state).excluded_ids).toEqual(["a"]);
  });

  it("does not mutate the previous state", () => {
    const before = fullSelection();
    toggleItem(before, "a");
    toggleSection(before, "skills");

    expect(before.excluded.size).toBe(0);
    expect(before.sections.has("skills")).toBe(true);
  });

  it("names the CV after the design and the local day", () => {
    expect(defaultCvName("Moderno", new Date(2026, 9, 1, 23, 30))).toBe("CV Moderno 2026-10-01");
  });
});
