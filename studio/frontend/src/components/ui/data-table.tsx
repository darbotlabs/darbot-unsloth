// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

import {
  type RowData,
  type SortingState,
  flexRender,
  useTable,
} from "@tanstack/react-table";
import { useState } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  type DataTableColumnDef,
  dataTableFeatures,
} from "./data-table-model";

interface DataTableProps<TData extends RowData> {
  columns: DataTableColumnDef<TData>[];
  data: TData[];
  className?: string;
  onRowClick?: (row: TData, rowIndex: number, rowId: string) => void;
  getRowClassName?: (
    row: TData,
    rowIndex: number,
    rowId: string,
  ) => string | undefined;
}

export function DataTable<TData extends RowData>({
  columns,
  data,
  className,
  onRowClick,
  getRowClassName,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useTable({
    features: dataTableFeatures,
    data,
    columns,
    onSortingChange: setSorting,
    state: { sorting },
  });

  return (
    <div className={cn("w-full", className)}>
      <Table>
        <TableHeader className="sticky top-0 z-10">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow
              key={headerGroup.id}
              className="bg-muted/60 hover:bg-muted/60 border-b border-border/60"
            >
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className="border-r border-border/40 last:border-r-0 h-11 px-4 text-xs"
                  style={{
                    width:
                      header.getSize() !== 150 ? header.getSize() : undefined,
                  }}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row, idx) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() ? "selected" : undefined}
                className={cn(
                  "transition-colors border-b border-border/30",
                  idx % 2 === 0
                    ? "bg-background"
                    : "bg-muted/20",
                  "hover:bg-primary/[0.03]",
                  getRowClassName?.(row.original, idx, row.id),
                )}
                onClick={() => onRowClick?.(row.original, idx, row.id)}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className="border-r border-border/20 last:border-r-0 text-ui-13 py-3 px-4 align-top whitespace-normal"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell
                colSpan={columns.length}
                className="h-32 text-center text-muted-foreground text-sm"
              >
                No results.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
