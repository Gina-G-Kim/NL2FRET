#!/usr/bin/env python3
"""Self test of the rule layer (no model, no docker): golden FRETish for fixed template sentences with fixed slot values.
Run:  python3 -I tools/selftest.py   (from the bench folder). Prints SELFTEST_OK or the failing case. The golden outputs are the bench author's expectation of what the
rules do (structure); whether the official parser accepts them is checked by tools/rule_probe.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fretlint as L  # noqa: E402
import tpl_rules as T  # noqa: E402

CASES = [
    ("EARS", "WHEN the start button is pressed, the controller shall open the inlet valve within 5 seconds.",
     {"c1": "start_button_pressed", "r": "open_inlet_valve"}, "when start_button_pressed controller shall within 5 seconds satisfy open_inlet_valve"),
    ("EARS", "IF the sensor reports a fault, THEN the controller shall raise an alarm.", {"c1": "sensor_fault", "r": "alarm"}, "if sensor_fault controller shall satisfy alarm"),
    ("EARS", "WHILE the system is in standby the controller shall refuse new jobs.", {"s1": {"mode": "standby"}, "r": "refuse_new_jobs"},
     "in standby mode controller shall always satisfy refuse_new_jobs"),
    ("EARS", "WHILE the pump runs, the controller shall keep the pressure below 5 bar.", {"s1": {"expr": "pump_running"}, "r": "pressure < 5"},
     "while pump_running controller shall always satisfy pressure < 5"),
    ("EARS", "The pump shall keep the pressure below 5 bar.", {"r": "pressure < 5"}, "pump shall always satisfy pressure < 5"),
    ("EARS", "WHEN the door is opened, the alarm shall sound immediately.", {"c1": "door_open", "r": "sounding"}, "when door_open alarm shall immediately satisfy sounding"),
    ("EARS", "WHEN the door is opened, the alarm shall not sound.", {"c1": "door_open", "r": "sounding"}, "when door_open alarm shall never satisfy sounding"),
    ("MASTeR", "AS SOON AS the cover has been opened, the controller SHALL stop the motor.", {"c1": "cover_open", "r": "motor_stopped"}, "when cover_open controller shall satisfy motor_stopped"),
    ("MASTeR", "IF the supply voltage is below 10 V, the controller SHALL switch to battery operation.", {"c1": "supply_voltage < 10", "r": "battery_operation"},
     "if supply_voltage < 10 controller shall satisfy battery_operation"),
    ("MASTeR", "AS LONG AS the system is in the state maintenance, the controller SHALL ignore remote commands.", {"s1": {"mode": "maintenance"}, "r": "remote_commands_ignored"},
     "in maintenance mode controller shall always satisfy remote_commands_ignored"),
    ("MASTeR", "The system SHALL PROVIDE the operator WITH THE ABILITY TO reset the counter.", {"r": "operator_can_reset_counter"}, "system shall always satisfy operator_can_reset_counter"),
    ("Adv-EARS", "WHILE in a standby state if the battery is low the unit shall perform a shutdown.", {"s1": {"mode": "standby"}, "c1": "battery_low", "r": "shutdown"},
     "in standby mode if battery_low unit shall satisfy shutdown"),
    ("Adv-EARS", "IF the fuel is low THEN the display of the fuel gauge shall show a warning.", {"c1": "fuel_low", "r": "warning_shown"},
     "if fuel_low display_fuel_gauge shall satisfy warning_shown"),
    ("Boilerplate", "While in standby mode, the unit shall have a power consumption of at most 2 W.", {"s1": {"mode": "standby"}, "r": "power_consumption <= 2"},
     "in standby mode unit shall always satisfy power_consumption <= 2"),
    ("Boilerplate", "Unless the override is active, the controller shall close the valve.", {"c1": "override_active", "r": "valve_closed"}, "if !override_active controller shall satisfy valve_closed"),
    ("Boilerplate", "The machine shall produce a hot drink every 10 seconds.", None, ("rule_no_mapping", "every")),
    ("Boilerplate", "The controller shall open the valve within 3 ms.", {"r": "valve_open"}, "controller shall within 3 milliseconds satisfy valve_open"),
    ("SPIDER", "Globally, it is always the case that if (door_open) holds, then (alarm) holds after at most 5 secs.", {"p": "door_open", "s": "alarm"},
     "when door_open system shall within 5 seconds satisfy alarm"),
    ("SPIDER", "After (takeoff) until (landed), it is always the case that (gear_up) holds.", {"q": "takeoff", "r": "landed", "p": "gear_up"}, "after takeoff system shall until landed satisfy gear_up"),
    ("SPIDER", "Globally, it is never the case that (a & b) holds.", {"p": "a & b"}, "system shall never satisfy a & b"),
    ("SPIDER", "Globally, it is always the case that if (p1) holds, then (s1) eventually holds and is succeeded by (t1).", None, ("rule_no_mapping", "chain")),
]


def run():
    for tpl, sent, slots, want in CASES:
        p = T.parse_template(tpl, sent)
        assert p["ok"], (tpl, sent, p)
        req = T.slot_requests(p)
        if slots is None:
            slots = {k: "x" for k in req}
        lint = T.lint_slots(req, slots)
        a = T.assemble(p, lint)
        if isinstance(want, tuple):
            assert not a["ok"] and (a["code"], a["detail"]) == want, (tpl, sent, a)
        else:
            assert a["ok"] and a["fretish"] == want, (tpl, sent, a, want)
    # lint
    assert L.fix_expr("abs(he) <= 35")[0] == "absReal(he) <= 35"
    assert L.fix_expr("x ≤ 3")[0] == "x <= 3"
    assert any(v.startswith("E-WORD") for v in L.fix_expr("a and b")[2])
    assert any(v.startswith("E-UNITINEXPR") for v in L.fix_expr("v < 10 V")[2])
    assert L.normalize_fretish("c shall within 5 ms satisfy abs(x) <= 3")[0] == "c shall within 5 milliseconds satisfy absReal(x) <= 3"
    assert L.normalize_fretish("c shall within 5 seconds satisfy x")[1] == []
    assert L.classify_error("These reserved letter combinations cannot be used: abs.")[0] == "expr_reserved_abs_max"
    assert L.classify_error("Trailing unparsed input: 'x'")[1] == "structural"
    print("SELFTEST_OK", len(CASES), "rule cases")


if __name__ == "__main__":
    run()
