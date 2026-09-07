// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { useTable } from "@tanstack/react-table";
import { dataTableFeatures } from "../src/components/ui/data-table-model.ts";

test("table features preserve numeric sorting and instance-bound cell values", () => {
  function Probe() {
    const table = useTable({
      features: dataTableFeatures,
      data: [{ score: 10 }, { score: 2 }, { score: 30 }],
      columns: [{ accessorKey: "score" }],
    });
    table.setSorting([{ id: "score", desc: false }]);
    assert.deepEqual(
      table.getRowModel().rows.map((row) => row.getValue("score")),
      [2, 10, 30],
    );
    const cell = table.getRowModel().rows[0].getVisibleCells()[0];
    assert.equal(cell.getContext().cell.getValue(), 2);
    table.setSorting([{ id: "score", desc: true }]);
    assert.deepEqual(
      table.getRowModel().rows.map((row) => row.getValue("score")),
      [30, 10, 2],
    );
    return null;
  }
  renderToStaticMarkup(createElement(Probe));
});

test("table features retain sizing, visibility, and selected-row state", () => {
  function Probe() {
    const table = useTable({
      features: dataTableFeatures,
      data: [{ name: "sample", score: 2 }],
      columns: [
        { accessorKey: "name", size: 220 },
        { accessorKey: "score" },
      ],
    });
    assert.deepEqual(
      table.getHeaderGroups()[0].headers.map((header) => header.getSize()),
      [220, 150],
    );
    table.setColumnVisibility({ score: false });
    const row = table.getRowModel().rows[0];
    assert.deepEqual(row.getVisibleCells().map((cell) => cell.column.id), ["name"]);
    assert.equal(row.getIsSelected(), false);
    row.toggleSelected(true);
    assert.equal(row.getIsSelected(), true);
    return null;
  }
  renderToStaticMarkup(createElement(Probe));
});
