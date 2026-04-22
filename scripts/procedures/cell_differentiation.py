def _culture_info_to_r(rows):
    def r_vec(items):
        quoted = [f'"{x}"' for x in items]
        return "c(" + ", ".join(quoted) + ")"

    ids      = [r["culture_id"] for r in rows]
    passages = [str(r["passage"]) if r["passage"] is not None else "" for r in rows]

    return (
        f"culture_info_df <- data.frame(\n"
        f"  `Culture ID` = {r_vec(ids)},\n"
        f"  `Passage`    = {r_vec(passages)},\n"
        f"  check.names  = FALSE\n"
        f")"
    )


def extra_files(args, db, exp_dir, subject_ids):
    return []


def extra_replacements(args, db, subject_ids):
    if not subject_ids:
        return {"CULTURE_INFO_R": ""}

    placeholders = ",".join("?" * len(subject_ids))
    rows = db.execute(
        f"SELECT culture_id, passage FROM cell_cultures WHERE culture_id IN ({placeholders})",
        subject_ids,
    ).fetchall()
    order = {sid: i for i, sid in enumerate(subject_ids)}
    rows = sorted(rows, key=lambda r: order.get(r["culture_id"], 999))

    return {"CULTURE_INFO_R": _culture_info_to_r(rows)}
