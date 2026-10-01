import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCollapsedColumns } from "./useCollapsedColumns";

const KEY = "board.collapsed";

describe("useCollapsedColumns", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("starts with every column expanded and remembers what is folded", () => {
    const { result } = renderHook(() => useCollapsedColumns());
    expect(result.current.isCollapsed("rejected")).toBe(false);

    act(() => result.current.toggle("rejected"));
    expect(result.current.isCollapsed("rejected")).toBe(true);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual(["rejected"]);

    // Otra página (otro montaje) lo lee del navegador.
    const { result: again } = renderHook(() => useCollapsedColumns());
    expect(again.current.isCollapsed("rejected")).toBe(true);

    act(() => again.current.toggle("rejected"));
    expect(again.current.isCollapsed("rejected")).toBe(false);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual([]);
  });

  it.each([["not json"], ['{"rejected":true}']])(
    "ignores a stored value that is not a list (%s)",
    (stored) => {
      localStorage.setItem(KEY, stored);
      const { result } = renderHook(() => useCollapsedColumns());
      expect(result.current.isCollapsed("rejected")).toBe(false);
    },
  );

  it("still folds for this page when the browser storage fails", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const { result } = renderHook(() => useCollapsedColumns());

    act(() => result.current.toggle("accepted"));
    expect(result.current.isCollapsed("accepted")).toBe(true);
  });
});
