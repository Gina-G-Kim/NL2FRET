"""AP mismatch record (author rule 'author_subset_v1'). Recording only; this value never changes a verdict.

Reading of the authors' code (see docs/DESIGN.md, section 4): a query is comparable when vars(first argument) is a subset of vars(second argument);
the equiv and Sound queries are called as (GT, Pred), the Compl query as (Pred, GT). So N/M (author rule) per query kind is:
  equiv, sound : vars(GT) not a subset of vars(Pred)
  compl        : vars(Pred) not a subset of vars(GT)
vars are the boolean atom names after abstraction. The interpretation of the authors' code is not verified against their source (not in the
repository); nm_by_kind is therefore a record of this reading.
"""

RULE_ID = "author_subset_v1"
RULE_DESCRIPTION = (
    "Author-code reading: a query is comparable when vars(first argument) is a subset of vars(second argument); equiv and sound are called as "
    "(GT, Pred), compl as (Pred, GT). Level: abstract boolean atoms. Recorded only, never used for a verdict."
)


def ap_check(atoms_gt, atoms_pred, signal_vars_gt=None, signal_vars_pred=None):
    if atoms_gt is None or atoms_pred is None:
        return {"rule_id": RULE_ID, "level": "abstract_atoms", "vars_gt": None, "vars_pred": None, "equal": None, "gt_subset_pred": None,
                "pred_subset_gt": None, "only_gt": None, "only_pred": None, "nm_by_kind": None, "nm_pair_any": None, "nm_pair_all": None,
                "signal_vars_gt": signal_vars_gt, "signal_vars_pred": signal_vars_pred}
    g, p = set(atoms_gt), set(atoms_pred)
    gsp, psg = g <= p, p <= g
    nm = {"equiv": not gsp, "sound": not gsp, "compl": not psg}
    return {
        "rule_id": RULE_ID, "level": "abstract_atoms", "vars_gt": sorted(g), "vars_pred": sorted(p), "equal": g == p,
        "gt_subset_pred": gsp, "pred_subset_gt": psg, "only_gt": sorted(g - p), "only_pred": sorted(p - g),
        "nm_by_kind": nm, "nm_pair_any": any(nm.values()), "nm_pair_all": all(nm.values()),
        "signal_vars_gt": signal_vars_gt, "signal_vars_pred": signal_vars_pred,
    }
