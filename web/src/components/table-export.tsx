"use client";

import { useState } from "react";

type Cell = string | number;

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function csvEscape(value: Cell) {
  const s = String(value);
  return /["\n,]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function TableExport({ headers, rows, filename }: { headers: string[]; rows: Cell[][]; filename: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const text = [headers, ...rows].map((r) => r.join("\t")).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      // clipboard permission denied or unavailable — no-op, button just won't confirm
    }
  }

  function handleCsv() {
    const csv = [headers, ...rows].map((r) => r.map(csvEscape).join(",")).join("\r\n");
    // Leading BOM so Excel opens UTF-8 correctly (several tables carry Amharic text)
    download(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }), `${filename}.csv`);
  }

  async function handleExcel() {
    const mod = await import("exceljs");
    const ExcelJS = (mod as unknown as { Workbook?: unknown }).Workbook
      ? mod
      : (mod as unknown as { default: typeof mod }).default;
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet("Sheet1");
    ws.addRow(headers);
    rows.forEach((r) => ws.addRow(r));
    ws.getRow(1).font = { bold: true };
    ws.columns.forEach((col) => {
      col.width = 20;
    });
    const buf = await wb.xlsx.writeBuffer();
    download(
      new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
      `${filename}.xlsx`
    );
  }

  async function handlePdf() {
    const [{ jsPDF }, autoTableMod] = await Promise.all([import("jspdf"), import("jspdf-autotable")]);
    const autoTable = autoTableMod.default;
    const doc = new jsPDF({ orientation: headers.length > 5 ? "landscape" : "portrait" });
    autoTable(doc, {
      head: [headers],
      body: rows.map((r) => r.map(String)),
      styles: { fontSize: 8 },
      headStyles: { fillColor: [0, 145, 71] },
    });
    doc.save(`${filename}.pdf`);
  }

  return (
    <div className="export-group" role="group" aria-label="Export table">
      <button type="button" className="export-btn" onClick={handleCopy} title="Copy table to clipboard">
        {copied ? "Copied" : "Copy"}
      </button>
      <button type="button" className="export-btn" onClick={handleCsv} title="Download as CSV">
        CSV
      </button>
      <button type="button" className="export-btn" onClick={handleExcel} title="Download as Excel">
        Excel
      </button>
      <button type="button" className="export-btn" onClick={handlePdf} title="Download as PDF">
        PDF
      </button>
    </div>
  );
}
