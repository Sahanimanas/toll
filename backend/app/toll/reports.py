"""Report synthesizer for GET /api/report — ported 1:1 from the original
Node backend so the Report page renders identically."""


def _rnd(seed: int) -> float:
    return ((seed * 9301 + 49297) % 233280) / 233280


def _inr(n: int) -> str:
    # en-IN grouping (lakh/crore): 12,84,000
    s = str(abs(int(n)))
    if len(s) <= 3:
        grouped = s
    else:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        grouped = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + grouped


def build_report(type: str, frm: str = "", to: str = "", lane: str = "",
                 cls: str = "", shift: str = "") -> dict:
    kpis, headers, rows = [], [], []
    chart = {"type": "bar", "labels": [], "series": []}
    title, summary = type, ""

    if type == "Daily Revenue":
        title = "Daily Revenue Report"
        summary = f"{frm or '—'} to {to or '—'} · {lane or 'All Lanes'} · {shift or 'All'} shift"
        chart["labels"] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        chart["series"] = [300000 + int(_rnd(i + 1) * 200000) for i in range(7)]
        total = sum(chart["series"])
        kpis = [
            {"label": "Total Revenue", "value": "₹" + f"{total/100000:.1f}" + "L", "color": "b"},
            {"label": "Avg / Day", "value": "₹" + str(round(total / 7 / 1000)) + "K", "color": "g"},
            {"label": "Peak Day", "value": "Sun", "color": "p"},
            {"label": "Transactions", "value": "12,840", "color": "t"},
        ]
        headers = ["Date", "Lane", "Transactions", "Cash", "FASTag", "Total"]
        for i, d in enumerate(chart["labels"]):
            cash = 5000 + int(_rnd(i * 5) * 5000)
            rows.append([
                f"2025-03-{24+i}", lane or "All", 1500 + int(_rnd(i * 3) * 900),
                "₹" + str(cash), "₹" + _inr(chart["series"][i] - cash), "₹" + _inr(chart["series"][i]),
            ])

    elif type == "Weekly Traffic":
        title = "Weekly Traffic Report"
        summary = f"Last 7 days · {lane or 'All Lanes'}"
        chart["labels"] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        chart["series"] = [11000 + int(_rnd(i + 1) * 4000) for i in range(7)]
        total = sum(chart["series"])
        kpis = [
            {"label": "Total Vehicles", "value": _inr(total), "color": "g"},
            {"label": "Daily Avg", "value": _inr(round(total / 7)), "color": "b"},
            {"label": "Peak Hour", "value": "08:00", "color": "p"},
            {"label": "Off-peak", "value": "03:00", "color": "o"},
        ]
        headers = ["Day", "Cars", "LCV", "Bus", "3-Axle", "Oversized", "Total"]
        for i, d in enumerate(chart["labels"]):
            t = chart["series"][i]
            rows.append([d, round(t * .55), round(t * .20), round(t * .13),
                         round(t * .07), round(t * .05), t])

    elif type == "Violations Log":
        title = "Violations Log Report"
        summary = f"{frm or '—'} to {to or '—'}"
        chart["labels"] = ["No FASTag", "Speeding", "Wrong Lane", "Axle Violation"]
        chart["series"] = [287, 134, 89, 46]
        total = sum(chart["series"])
        kpis = [
            {"label": "Total Violations", "value": total, "color": "r"},
            {"label": "No FASTag", "value": 287, "color": "o"},
            {"label": "Speeding", "value": 134, "color": "p"},
            {"label": "Resolved", "value": "82%", "color": "g"},
        ]
        headers = ["Type", "Count", "Fines Collected", "Avg Fine", "% of Total"]
        for i, t in enumerate(chart["labels"]):
            rows.append([t, chart["series"][i], "₹" + _inr(chart["series"][i] * 500),
                         "₹500", f"{(chart['series'][i]/total)*100:.1f}%"])

    elif type == "Vehicle Class Split":
        title = "Vehicle Class Split"
        summary = f"{frm or '—'} to {to or '—'} · {lane or 'All Lanes'}"
        chart["labels"] = ["Car / Jeep", "LCV", "Bus", "3-Axle", "Oversized"]
        chart["series"] = [4880, 2950, 2050, 1410, 1550]
        total = sum(chart["series"])
        kpis = [
            {"label": "Total Vehicles", "value": _inr(total), "color": "b"},
            {"label": "Top Class", "value": "Car / Jeep", "color": "g"},
            {"label": "Highest Revenue", "value": "3-Axle", "color": "p"},
            {"label": "Avg Toll", "value": "₹192", "color": "o"},
        ]
        headers = ["Class", "Count", "% Share", "Avg Toll", "Total Revenue"]
        tolls = [85, 285, 445, 685, 985]
        for i, c in enumerate(chart["labels"]):
            rows.append([c, chart["series"][i], f"{(chart['series'][i]/total)*100:.1f}%",
                         "₹" + str(tolls[i]), "₹" + _inr(chart["series"][i] * tolls[i])])

    elif type == "FASTag Reconciliation":
        title = "FASTag Reconciliation"
        summary = f"{frm or '—'} to {to or '—'}"
        chart["labels"] = ["HDFC", "SBI", "ICICI", "AXIS", "PNB"]
        chart["series"] = [3200, 2800, 2400, 1900, 1600]
        total = sum(chart["series"])
        kpis = [
            {"label": "Total Reconciled", "value": _inr(total), "color": "g"},
            {"label": "Success Rate", "value": "96.8%", "color": "g"},
            {"label": "Pending", "value": 356, "color": "o"},
            {"label": "Failed", "value": 38, "color": "r"},
        ]
        headers = ["Acquirer Bank", "Transactions", "Amount", "Pending", "Failed", "Success %"]
        for i, b in enumerate(chart["labels"]):
            pend = 50 + int(_rnd(i * 3) * 100)
            fail = 5 + int(_rnd(i * 7) * 15)
            rows.append(["NPCI/" + b, chart["series"][i], "₹" + _inr(chart["series"][i] * 250),
                         pend, fail, f"{(chart['series'][i]-fail)/chart['series'][i]*100:.2f}%"])

    else:  # Equipment & Lane Report
        title = "Equipment & Lane Report"
        summary = f"{frm or '2025-03-24'} to {to or '2025-03-30'} · {lane or 'All Lanes'} · {shift or 'All'} shift"
        days = ["2025-03-24", "2025-03-25", "2025-03-26", "2025-03-27",
                "2025-03-28", "2025-03-29", "2025-03-30"]
        txn = [3210, 3560, 2980, 3840, 4120, 3690, 2840]
        rev = [581810, 644680, 539780, 695520, 746160, 668290, 514520]
        veh = [3380, 3720, 3140, 4020, 4310, 3880, 2980]
        vio = [42, 58, 35, 67, 72, 55, 48]
        fas = [96, 97, 95, 96, 98, 97, 96]
        spd = [54, 52, 56, 53, 51, 55, 54]
        fail = [4, 6, 3, 8, 5, 4, 7]
        chart["labels"] = [d[5:] for d in days]
        chart["series"] = rev
        kpis = [
            {"label": "Total Transactions", "value": "3,420", "delta": "8.4%", "dir": "up", "color": "k"},
            {"label": "Total Revenue", "value": "₹6.24L", "delta": "12.8%", "dir": "up", "color": "b"},
            {"label": "Violations", "value": "148", "delta": "3.2%", "dir": "up", "color": "r"},
            {"label": "Compliance Rate", "value": "95.7%", "delta": "1.2%", "dir": "up", "color": "g"},
        ]
        headers = ["DATE", "LANE", "TRANSACTIONS", "REVENUE (₹)", "VEHICLES",
                   "VIOLATIONS", "FASTAG %", "AVG SPEED", "FAILED"]
        for i, d in enumerate(days):
            rows.append([
                d,
                {"type": "lane", "value": lane or "All Lanes"},
                {"type": "bold", "value": _inr(txn[i])},
                {"type": "bold", "value": "₹" + _inr(rev[i])},
                {"type": "bold", "value": _inr(veh[i])},
                {"type": "violation", "value": vio[i]},
                {"type": "progress", "value": fas[i]},
                f"{spd[i]} km/h",
                {"type": "fail", "value": fail[i]},
            ])
        rows.append({
            "total": True,
            "cells": [
                {"type": "totlabel", "value": "TOTAL"},
                {"type": "totmuted", "value": lane or "All Lanes"},
                {"type": "totbold", "value": _inr(sum(txn))},
                {"type": "totblue", "value": "₹" + _inr(sum(rev))},
                {"type": "totbold", "value": _inr(sum(veh))},
                {"type": "totred", "value": sum(vio)},
                {"type": "totmuted", "value": "—"},
                {"type": "totmuted", "value": "—"},
                {"type": "totred", "value": sum(fail)},
            ],
        })

    return {"title": title, "summary": summary, "kpis": kpis, "chart": chart,
            "headers": headers, "rows": rows}
