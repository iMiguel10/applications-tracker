import { describe, expect, it } from "vitest";
import type { Board } from "../types/Board";
import { canMove, daysInStatus, moveCard } from "./board";

const card = (id: string) => ({
  id,
  position_title: `Puesto ${id}`,
  company: { id: "c", name: "Acme" },
  status_since: "2026-09-01T10:00:00Z",
});

const board: Board = {
  columns: [
    {
      status: "saved",
      total: 1,
      items: [card("a")],
      allowed_transitions: ["applied", "withdrawn"],
    },
    {
      status: "applied",
      total: 3,
      items: [card("b")],
      allowed_transitions: ["screening"],
    },
    { status: "withdrawn", total: 0, items: [], allowed_transitions: [] },
  ],
};

describe("board", () => {
  it("counts whole calendar days in the status, never negative", () => {
    expect(
      daysInStatus("2026-09-01T23:30:00", new Date(2026, 8, 2, 0, 10)),
    ).toBe(1);
    expect(daysInStatus("2026-09-01T10:00:00", new Date(2026, 8, 1, 18))).toBe(
      0,
    );
    expect(daysInStatus("2026-09-05T10:00:00", new Date(2026, 8, 1))).toBe(0);
  });

  it("only allows the column's transitions", () => {
    expect(canMove(board, "saved", "applied")).toBe(true);
    expect(canMove(board, "saved", "saved")).toBe(false);
    expect(canMove(board, "applied", "withdrawn")).toBe(false);
    expect(canMove(board, "withdrawn", "saved")).toBe(false);
  });

  it("moves the card to the top of the target column and fixes the totals", () => {
    const now = new Date("2026-10-01T12:00:00Z");
    const moved = moveCard(board, "a", "saved", "applied", now);

    expect(moved.columns[0]).toMatchObject({ total: 0, items: [] });
    expect(moved.columns[1].total).toBe(4);
    expect(moved.columns[1].items.map((item) => item.id)).toEqual(["a", "b"]);
    expect(moved.columns[1].items[0].status_since).toBe(now.toISOString());
  });

  it("leaves the board untouched for a forbidden move or an unknown card", () => {
    expect(moveCard(board, "b", "applied", "withdrawn")).toBe(board);
    expect(moveCard(board, "zzz", "saved", "applied")).toBe(board);
  });
});
