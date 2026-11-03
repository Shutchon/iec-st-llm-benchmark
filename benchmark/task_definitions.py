# -*- coding: utf-8 -*-
"""นิยามชุดข้อมูล IEC-ST-30 ฉบับสมบูรณ์ (แหล่งความจริงของ dataset)

องค์ประกอบ:
- GROUND_TRUTH_FIXES : แก้โค้ดอ้างอิงเดิมที่คอมไพล์ไม่ผ่าน MatIEC (T16 ใช้คำสงวน 'Step',
  T22 ใช้ 'Integral' ซึ่ง MatIEC crash, T29 ใช้ SHR กับ INT ซึ่งผิดมาตรฐาน ANY_BIT)
- IO_FIXES           : แก้ metadata I/O ที่ parser หลุด (T20 Out เป็น VAR_IN_OUT, T26 ประกาศรวมบรรทัดเดียว)
- NEW_TASKS          : โจทย์ 4 ข้อที่ขาดไป (T05 TOF, T12 DOL, T14 Conveyor Sorter, T18 Fill Station)
- TESTS              : truth table ของทั้ง 30 ข้อ

รูปแบบ step ของ tests (runner ต้องทำตามนี้):
  {"in":  {...},            # ค่า input แบบ sticky (merge กับ step ก่อนหน้า) — TIME ให้เป็น int มิลลิวินาที
   "io":  {...},            # ค่า VAR_IN_OUT แบบ sticky
   "cycles": 1,             # จำนวนรอบสแกนที่จะเดินหน้า (default 1)
   "dt_ms": 100,            # เวลาต่อรอบสแกน (default 100)
   "expect":        {...},  # ค่า output/io ที่ต้องเท่ากันเป๊ะ (BOOL/INT/BYTE/WORD/array)
   "expect_approx": {v: {"value": x, "tol": t}},   # REAL เทียบภายใน tolerance
   "expect_time":   {v: {"ms": x, "tol_ms": t}}}   # TIME เทียบเป็น ms
หมายเหตุ: แต่ละ test scenario = FB instance ใหม่ (state เริ่มศูนย์) ตรวจผลหลังรอบสแกนสุดท้ายของ step
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1) แก้ ground truth ที่คอมไพล์ไม่ผ่าน
# ─────────────────────────────────────────────────────────────────────────────
GROUND_TRUTH_FIXES = {
    # T16: 'Step' เป็นคำสงวนของ IEC 61131-3 (องค์ประกอบ SFC) → เปลี่ยนเป็น Phase
    "T16": """FUNCTION_BLOCK T16_Traffic
VAR_OUTPUT
    G : BOOL;
    Y : BOOL;
    R : BOOL;
END_VAR
VAR
    Phase : INT;
    Timer : TON;
END_VAR
CASE Phase OF
    0: G := TRUE; Y := FALSE; R := FALSE; Timer(IN := TRUE, PT := T#10s);
       IF Timer.Q THEN Phase := 1; Timer(IN := FALSE); END_IF;
    1: G := FALSE; Y := TRUE; R := FALSE; Timer(IN := TRUE, PT := T#3s);
       IF Timer.Q THEN Phase := 2; Timer(IN := FALSE); END_IF;
    2: G := FALSE; Y := FALSE; R := TRUE; Timer(IN := TRUE, PT := T#13s);
       IF Timer.Q THEN Phase := 0; Timer(IN := FALSE); END_IF;
END_CASE;
END_FUNCTION_BLOCK""",
    # T22: 'Integral' และ 'Derivative' เป็นคำที่ MatIEC crash → IntAccum/Deriv
    "T22": """FUNCTION_BLOCK T22_PID
VAR_INPUT
    PV, SP, Kp, Ki, Kd : REAL;
END_VAR
VAR_OUTPUT
    Out : REAL;
END_VAR
VAR
    Error, LastError, IntAccum, Deriv : REAL;
END_VAR
    Error := SP - PV;
    IntAccum := IntAccum + Error;
    Deriv := Error - LastError;
    Out := (Kp * Error) + (Ki * IntAccum) + (Kd * Deriv);
    LastError := Error;
END_FUNCTION_BLOCK""",
    # T29: SHR/AND ต้องใช้กับ ANY_BIT ไม่ใช่ INT → แปลงเป็น WORD ก่อน
    "T29": """FUNCTION_BLOCK T29_ModbusPack
VAR_INPUT
    Val1, Val2 : INT;
END_VAR
VAR_OUTPUT
    Payload : ARRAY[0..3] OF BYTE;
END_VAR
VAR
    W1, W2 : WORD;
END_VAR
    W1 := INT_TO_WORD(Val1);
    W2 := INT_TO_WORD(Val2);
    Payload[0] := WORD_TO_BYTE(SHR(W1, 8));
    Payload[1] := WORD_TO_BYTE(W1 AND 16#00FF);
    Payload[2] := WORD_TO_BYTE(SHR(W2, 8));
    Payload[3] := WORD_TO_BYTE(W2 AND 16#00FF);
END_FUNCTION_BLOCK""",
}

# ─────────────────────────────────────────────────────────────────────────────
# 2) แก้ metadata I/O
# ─────────────────────────────────────────────────────────────────────────────
IO_FIXES = {
    # T20: Out เป็น VAR_IN_OUT ไม่ใช่ VAR_OUTPUT
    "T20": {"outputs": [], "io_vars": [{"name": "Out", "type": "REAL"}]},
    # T26: ประกาศ input รวมบรรทัดเดียว parser หลุด → ใส่ครบ 5 ตัวตามโค้ด
    "T26": {"inputs": [{"name": "X", "type": "REAL"}, {"name": "X1", "type": "REAL"},
                        {"name": "Y1", "type": "REAL"}, {"name": "X2", "type": "REAL"},
                        {"name": "Y2", "type": "REAL"}]},
}

# ─────────────────────────────────────────────────────────────────────────────
# 3) โจทย์ใหม่ 4 ข้อ
# ─────────────────────────────────────────────────────────────────────────────
NEW_TASKS = [
    {
        "id": "T05", "title": "Off-Delay Timer (TOF)", "complexity": "basic",
        "requirement": "Implement an off-delay timer: output stays TRUE while IN is TRUE and remains TRUE for PT duration after IN falls FALSE.",
        "inputs": [{"name": "IN", "type": "BOOL"}, {"name": "PT", "type": "TIME"}],
        "outputs": [{"name": "Q", "type": "BOOL"}, {"name": "ET", "type": "TIME"}],
        "io_vars": [], "locals_raw": "tof_inst : TOF",
        "ground_truth": """FUNCTION_BLOCK T05_TimerOff
VAR_INPUT
    IN : BOOL;
    PT : TIME;
END_VAR
VAR_OUTPUT
    Q : BOOL;
    ET : TIME;
END_VAR
VAR
    tof_inst : TOF;
END_VAR
    tof_inst(IN := IN, PT := PT, Q => Q, ET => ET);
END_FUNCTION_BLOCK""",
    },
    {
        "id": "T12", "title": "DOL Motor Starter with Overload Protection", "complexity": "intermediate",
        "requirement": "Direct-On-Line motor starter: latch RUN from START pushbutton, drop out on STOP or thermal OVERLOAD; OVERLOAD latches FAULT until reset by STOP.",
        "inputs": [{"name": "START", "type": "BOOL"}, {"name": "STOP", "type": "BOOL"}, {"name": "OVERLOAD", "type": "BOOL"}],
        "outputs": [{"name": "RUN", "type": "BOOL"}, {"name": "FAULT", "type": "BOOL"}],
        "io_vars": [], "locals_raw": "",
        "ground_truth": """FUNCTION_BLOCK T12_DOL
VAR_INPUT
    START : BOOL;
    STOP : BOOL;
    OVERLOAD : BOOL;
END_VAR
VAR_OUTPUT
    RUN : BOOL;
    FAULT : BOOL;
END_VAR
    IF OVERLOAD THEN
        FAULT := TRUE;
    END_IF;
    IF STOP THEN
        FAULT := FALSE;
    END_IF;
    IF (START OR RUN) AND NOT STOP AND NOT FAULT THEN
        RUN := TRUE;
    ELSE
        RUN := FALSE;
    END_IF;
END_FUNCTION_BLOCK""",
    },
    {
        "id": "T14", "title": "Conveyor Box Sorting", "complexity": "intermediate",
        "requirement": "On a running conveyor, detect boxes at a photo sensor (rising edge of PhotoIn): tall boxes (SizeHigh=TRUE) are diverted (Diverter=TRUE) and counted in CountDivert, short boxes pass (Diverter=FALSE) and increment CountPass. When the conveyor stops, retract the diverter.",
        "inputs": [{"name": "ConveyorRun", "type": "BOOL"}, {"name": "PhotoIn", "type": "BOOL"}, {"name": "SizeHigh", "type": "BOOL"}],
        "outputs": [{"name": "Diverter", "type": "BOOL"}, {"name": "CountPass", "type": "INT"}, {"name": "CountDivert", "type": "INT"}],
        "io_vars": [], "locals_raw": "last_PhotoIn : BOOL",
        "ground_truth": """FUNCTION_BLOCK T14_Sorter
VAR_INPUT
    ConveyorRun : BOOL;
    PhotoIn : BOOL;
    SizeHigh : BOOL;
END_VAR
VAR_OUTPUT
    Diverter : BOOL;
    CountPass : INT;
    CountDivert : INT;
END_VAR
VAR
    last_PhotoIn : BOOL;
END_VAR
    IF NOT ConveyorRun THEN
        Diverter := FALSE;
    ELSIF PhotoIn AND NOT last_PhotoIn THEN
        IF SizeHigh THEN
            Diverter := TRUE;
            CountDivert := CountDivert + 1;
        ELSE
            Diverter := FALSE;
            CountPass := CountPass + 1;
        END_IF;
    END_IF;
    last_PhotoIn := PhotoIn;
END_FUNCTION_BLOCK""",
    },
    {
        "id": "T18", "title": "Bottle Filling Station", "complexity": "intermediate",
        "requirement": "Semi-automatic bottle filler with 4 states: Idle (all off), Feeding (conveyor runs until BottleDetected), Filling (conveyor stops, fill valve opens until FullSignal), Discharge (conveyor runs until the bottle leaves the sensor, then back to Idle).",
        "inputs": [{"name": "Start", "type": "BOOL"}, {"name": "BottleDetected", "type": "BOOL"}, {"name": "FullSignal", "type": "BOOL"}],
        "outputs": [{"name": "Conveyor", "type": "BOOL"}, {"name": "FillValve", "type": "BOOL"}],
        "io_vars": [], "locals_raw": "State : INT",
        "ground_truth": """FUNCTION_BLOCK T18_FillStation
VAR_INPUT
    Start : BOOL;
    BottleDetected : BOOL;
    FullSignal : BOOL;
END_VAR
VAR_OUTPUT
    Conveyor : BOOL;
    FillValve : BOOL;
END_VAR
VAR
    State : INT; (* 0: Idle, 1: Feeding, 2: Filling, 3: Discharge *)
END_VAR
    CASE State OF
        0: Conveyor := FALSE; FillValve := FALSE;
           IF Start THEN State := 1; END_IF;
        1: Conveyor := TRUE; FillValve := FALSE;
           IF BottleDetected THEN State := 2; END_IF;
        2: Conveyor := FALSE; FillValve := TRUE;
           IF FullSignal THEN State := 3; END_IF;
        3: Conveyor := TRUE; FillValve := FALSE;
           IF NOT BottleDetected THEN State := 0; END_IF;
    END_CASE;
END_FUNCTION_BLOCK""",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# 4) Truth tables / functional tests ครบ 30 ข้อ
# ─────────────────────────────────────────────────────────────────────────────
def _s(in_=None, cycles=1, dt_ms=100, expect=None, approx=None, time_=None, io=None):
    s = {"cycles": cycles, "dt_ms": dt_ms}
    if in_: s["in"] = in_
    if io: s["io"] = io
    if expect is not None: s["expect"] = expect
    if approx is not None: s["expect_approx"] = approx
    if time_ is not None: s["expect_time"] = time_
    return s

TESTS = {
    "T01": [{"name": "AND gate truth table",
             "steps": [_s({"IN1": False, "IN2": False}, expect={"OUT": False}),
                       _s({"IN1": False, "IN2": True},  expect={"OUT": False}),
                       _s({"IN1": True,  "IN2": False}, expect={"OUT": False}),
                       _s({"IN1": True,  "IN2": True},  expect={"OUT": True}),
                       _s({"IN1": True,  "IN2": False}, expect={"OUT": False})]}],
    "T02": [{"name": "TON 3s on-delay",
             "steps": [_s({"IN": True, "PT": 3000}, cycles=10, expect={"Q": False}),
                       _s(cycles=21, expect={"Q": True}, time_={"ET": {"ms": 3000, "tol_ms": 150}}),
                       _s(cycles=5,  expect={"Q": True}),
                       _s({"IN": False}, expect={"Q": False})]}],
    "T03": [{"name": "SR latch set-dominant",
             "steps": [_s({"S1": True,  "R": False}, expect={"Q1": True}),
                       _s({"S1": False, "R": False}, expect={"Q1": True}),
                       _s({"S1": False, "R": True},  expect={"Q1": False}),
                       _s({"S1": False, "R": False}, expect={"Q1": False}),
                       _s({"S1": True,  "R": True},  expect={"Q1": True})]}],
    "T04": [{"name": "CTU count to PV=3 with reset",
             "steps": [_s({"CU": True, "RESET": False, "PV": 3}, expect={"CV": 1, "Q": False}),
                       _s({"CU": False}, expect={"CV": 1}),
                       _s({"CU": True},  expect={"CV": 2, "Q": False}),
                       _s({"CU": False}, expect={"CV": 2}),
                       _s({"CU": True},  expect={"CV": 3, "Q": True}),
                       _s({"RESET": True}, expect={"CV": 0, "Q": False})]}],
    "T05": [{"name": "TOF 2s off-delay",
             "steps": [_s({"IN": True, "PT": 2000}, expect={"Q": True}),
                       _s({"IN": False}, cycles=10, expect={"Q": True}),
                       _s(cycles=11, expect={"Q": False})]}],
    "T06": [{"name": "Celsius to Fahrenheit",
             "steps": [_s({"TempC": 0.0},   approx={"TempF": {"value": 32.0,  "tol": 0.001}}),
                       _s({"TempC": 100.0}, approx={"TempF": {"value": 212.0, "tol": 0.001}}),
                       _s({"TempC": -40.0}, approx={"TempF": {"value": -40.0, "tol": 0.001}})]}],
    "T07": [{"name": "500ms blink toggling",
             "steps": [_s({"ENABLE": True}, cycles=6, expect={"OUT": True}),
                       _s(cycles=7, expect={"OUT": False}),
                       _s(cycles=7, expect={"OUT": True}),
                       _s({"ENABLE": False}, cycles=3, expect={"OUT": True})]}],
    "T08": [{"name": "integer greater-than",
             "steps": [_s({"VAL1": 5, "VAL2": 3}, expect={"RESULT": True}),
                       _s({"VAL1": 3, "VAL2": 5}, expect={"RESULT": False}),
                       _s({"VAL1": 4, "VAL2": 4}, expect={"RESULT": False})]}],
    "T09": [{"name": "Schmitt trigger hysteresis (High=10, Low=5)",
             "steps": [_s({"Val": 9.0, "High": 10.0, "Low": 5.0}, expect={"Q": False}),
                       _s({"Val": 7.0},  expect={"Q": False}),
                       _s({"Val": 10.0}, expect={"Q": True}),
                       _s({"Val": 7.0},  expect={"Q": True}),
                       _s({"Val": 5.0},  expect={"Q": False}),
                       _s({"Val": 7.0},  expect={"Q": False}),
                       _s({"Val": 9.9},  expect={"Q": False})]}],
    "T10": [{"name": "absolute value",
             "steps": [_s({"InputVal": 7},  expect={"AbsVal": 7}),
                       _s({"InputVal": -9}, expect={"AbsVal": 9}),
                       _s({"InputVal": 0},  expect={"AbsVal": 0})]}],
    "T11": [{"name": "star-delta 5s transition",
             "steps": [_s({"START": True, "STOP": False}, expect={"Main": True, "Star": True, "Delta": False}),
                       _s({"START": False}, cycles=10, expect={"Main": True, "Star": True, "Delta": False}),
                       _s(cycles=41, expect={"Main": True, "Star": False, "Delta": True}),
                       _s({"STOP": True}, expect={"Main": False, "Star": False, "Delta": False})]}],
    "T12": [{"name": "DOL start/overload/reset",
             "steps": [_s({"START": True, "STOP": False, "OVERLOAD": False}, expect={"RUN": True, "FAULT": False}),
                       _s({"START": False}, expect={"RUN": True}),
                       _s({"OVERLOAD": True}, expect={"RUN": False, "FAULT": True}),
                       _s({"OVERLOAD": False}, expect={"RUN": False, "FAULT": True}),
                       _s({"START": True}, expect={"RUN": False, "FAULT": True}),
                       _s({"STOP": True}, expect={"RUN": False, "FAULT": False}),
                       _s({"STOP": False, "START": True}, expect={"RUN": True, "FAULT": False})]}],
    "T13": [{"name": "analog clamping 0..10",
             "steps": [_s({"IN": 5.0, "MinL": 0.0, "MaxL": 10.0}, approx={"OUT": {"value": 5.0, "tol": 0.001}}),
                       _s({"IN": -3.0}, approx={"OUT": {"value": 0.0, "tol": 0.001}}),
                       _s({"IN": 15.0}, approx={"OUT": {"value": 10.0, "tol": 0.001}}),
                       _s({"IN": 10.0}, approx={"OUT": {"value": 10.0, "tol": 0.001}})]}],
    "T14": [{"name": "sort tall vs short boxes",
             "steps": [_s({"ConveyorRun": True, "PhotoIn": False, "SizeHigh": False},
                          expect={"Diverter": False, "CountPass": 0, "CountDivert": 0}),
                       _s({"PhotoIn": True, "SizeHigh": True},
                          expect={"Diverter": True, "CountDivert": 1, "CountPass": 0}),
                       _s({"PhotoIn": False}, expect={"Diverter": True}),
                       _s({"PhotoIn": True, "SizeHigh": False},
                          expect={"Diverter": False, "CountPass": 1, "CountDivert": 1}),
                       _s({"PhotoIn": False}, expect={"Diverter": False}),
                       _s({"PhotoIn": True, "SizeHigh": True},
                          expect={"Diverter": True, "CountDivert": 2, "CountPass": 1}),
                       _s({"ConveyorRun": False, "PhotoIn": False}, expect={"Diverter": False})]}],
    "T15": [{"name": "lead-lag alternation",
             "steps": [_s({"Demand": True, "Swap": False}, expect={"Pump1": True,  "Pump2": False}),
                       _s({"Demand": False}, expect={"Pump1": False, "Pump2": False}),
                       _s({"Demand": True}, expect={"Pump1": True,  "Pump2": False}),
                       _s({"Swap": True, "Demand": False}, expect={"Pump1": False, "Pump2": False}),
                       _s({"Swap": False, "Demand": True}, expect={"Pump1": False, "Pump2": True}),
                       _s({"Demand": False}, expect={"Pump1": False, "Pump2": False})]}],
    "T16": [{"name": "traffic light 10s/3s/13s cycle",
             "steps": [_s(cycles=5,  expect={"G": True,  "Y": False, "R": False}),
                       _s(cycles=95, expect={"G": True,  "Y": False, "R": False}),
                       _s(cycles=5,  expect={"G": False, "Y": True,  "R": False}),
                       _s(cycles=35, expect={"G": False, "Y": False, "R": True}),
                       _s(cycles=135, expect={"G": True,  "Y": False, "R": False})]}],
    "T17": [{"name": "50ms debounce on and off",
             "steps": [_s({"RawIn": True}, cycles=6, dt_ms=10, expect={"FilteredOut": True}),
                       _s({"RawIn": False}, cycles=4, dt_ms=10, expect={"FilteredOut": True}),
                       _s(cycles=6, dt_ms=10, expect={"FilteredOut": False}),
                       _s({"RawIn": True}, cycles=2, dt_ms=10, expect={"FilteredOut": False}),
                       _s(cycles=4, dt_ms=10, expect={"FilteredOut": True})]}],
    "T18": [{"name": "fill cycle through 4 states",
             "steps": [_s({"Start": True, "BottleDetected": False, "FullSignal": False},
                          expect={"Conveyor": False, "FillValve": False}),
                       _s({"Start": False}, expect={"Conveyor": True, "FillValve": False}),
                       _s({"BottleDetected": True}, cycles=2,
                          expect={"Conveyor": False, "FillValve": True}),
                       _s({"FullSignal": True}, cycles=2,
                          expect={"Conveyor": True, "FillValve": False}),
                       _s({"FullSignal": False, "BottleDetected": False}, cycles=2,
                          expect={"Conveyor": False, "FillValve": False})]}],
    "T19": [{"name": "moving average of 3",
             "steps": [_s({"NewVal": 10.0}, approx={"Avg": {"value": 10.0/3, "tol": 0.01}}),
                       _s({"NewVal": 20.0}, approx={"Avg": {"value": 10.0,  "tol": 0.01}}),
                       _s({"NewVal": 30.0}, approx={"Avg": {"value": 20.0,  "tol": 0.01}}),
                       _s({"NewVal": 0.0},  approx={"Avg": {"value": 50.0/3, "tol": 0.01}})]}],
    "T20": [{"name": "ramp up to setpoint with clamp",
             "steps": [_s({"Setpoint": 10.0, "Rate": 3.0}, io={"Out": 0.0},
                          approx={"Out": {"value": 3.0, "tol": 0.001}}),
                       _s(approx={"Out": {"value": 6.0, "tol": 0.001}}),
                       _s(approx={"Out": {"value": 9.0, "tol": 0.001}}),
                       _s(approx={"Out": {"value": 10.0, "tol": 0.001}}),
                       _s({"Setpoint": 0.0}, approx={"Out": {"value": 7.0, "tol": 0.001}}),
                       _s(approx={"Out": {"value": 4.0, "tol": 0.001}}),
                       _s(approx={"Out": {"value": 1.0, "tol": 0.001}}),
                       _s(approx={"Out": {"value": 0.0, "tol": 0.001}})]}],
    "T21": [{"name": "batch mix cycle",
             "steps": [_s({"Start": True, "LevelFull": False, "LevelEmpty": False},
                          expect={"FillValve": False, "Motor": False, "DrainValve": False}),
                       _s({"Start": False}, expect={"FillValve": True, "Motor": False, "DrainValve": False}),
                       _s({"LevelFull": True}, cycles=2,
                          expect={"FillValve": False, "Motor": True, "DrainValve": False}),
                       _s({"LevelFull": False}, cycles=99,
                          expect={"FillValve": False, "Motor": True, "DrainValve": False}),
                       _s(cycles=2, expect={"FillValve": False, "Motor": False, "DrainValve": True}),
                       _s({"LevelEmpty": True}, cycles=2,
                          expect={"FillValve": False, "Motor": False, "DrainValve": False}),
                       _s({"LevelEmpty": False}, expect={"FillValve": False, "Motor": False, "DrainValve": False})]}],
    "T22": [
        {"name": "pure P action",
         "steps": [_s({"PV": 8.0, "SP": 10.0, "Kp": 2.0, "Ki": 0.0, "Kd": 0.0},
                      approx={"Out": {"value": 4.0, "tol": 0.001}}),
                   _s(approx={"Out": {"value": 4.0, "tol": 0.001}})]},
        {"name": "PI action accumulates",
         "steps": [_s({"PV": 9.0, "SP": 10.0, "Kp": 1.0, "Ki": 0.5, "Kd": 0.0},
                      approx={"Out": {"value": 1.5, "tol": 0.001}}),
                   _s(approx={"Out": {"value": 2.0, "tol": 0.001}}),
                   _s(approx={"Out": {"value": 2.5, "tol": 0.001}})]},
        {"name": "zero error gives zero output (P only)",
         "steps": [_s({"PV": 10.0, "SP": 10.0, "Kp": 3.0, "Ki": 0.0, "Kd": 0.0},
                      approx={"Out": {"value": 0.0, "tol": 0.001}})]}],
    "T23": [{"name": "find maximum of 10",
             "steps": [_s({"Vals": [3, -7, 15, 0, 9, 2, 8, 1, 5, 4]}, expect={"MaxVal": 15})]},
            {"name": "all equal values",
             "steps": [_s({"Vals": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2]}, expect={"MaxVal": 2})]}],
    "T24": [{"name": "alarm latch and acknowledge",
             "steps": [_s({"Fault": False, "Ack": False}, expect={"AlarmActive": False}),
                       _s({"Fault": True},  expect={"AlarmActive": True}),
                       _s({"Fault": False}, expect={"AlarmActive": True}),
                       _s({"Ack": True},    expect={"AlarmActive": False}),
                       _s({"Ack": False},   expect={"AlarmActive": False}),
                       _s({"Fault": True, "Ack": True}, expect={"AlarmActive": True})]}],
    "T25": [{"name": "XOR checksum of 4 bytes",
             "steps": [_s({"Data": [1, 2, 3, 4]},   expect={"CRC": 251}),
                       _s({"Data": [0, 0, 0, 0]},   expect={"CRC": 255}),
                       _s({"Data": [255, 255, 255, 255]}, expect={"CRC": 255})]}],
    "T26": [{"name": "midpoint interpolation",
             "steps": [_s({"X": 5.0, "X1": 0.0, "Y1": 0.0, "X2": 10.0, "Y2": 100.0},
                          approx={"Y": {"value": 50.0, "tol": 0.001}}),
                       _s({"X": 0.0},  approx={"Y": {"value": 0.0, "tol": 0.001}}),
                       _s({"X": 10.0}, approx={"Y": {"value": 100.0, "tol": 0.001}})]},
            {"name": "degenerate segment falls back to Y1",
             "steps": [_s({"X": 1.0, "X1": 2.0, "Y1": 7.0, "X2": 2.0, "Y2": 99.0},
                          approx={"Y": {"value": 7.0, "tol": 0.001}})]}],
    "T27": [{"name": "sort 5 integers ascending",
             "steps": [_s(io={"Arr": [5, 1, 4, 2, 3]}, expect={"Arr": [1, 2, 3, 4, 5]})]},
            {"name": "already sorted stays put",
             "steps": [_s(io={"Arr": [1, 2, 3, 4, 5]}, expect={"Arr": [1, 2, 3, 4, 5]})]},
            {"name": "descending input fully reversed",
             "steps": [_s(io={"Arr": [9, 7, 5, 3, 1]}, expect={"Arr": [1, 3, 5, 7, 9]})]}],
    "T28": [{"name": "3 pulses within 1s window → 3 Hz",
             "steps": [_s({"Pulse": True},  expect={"Freq": 0.0}),
                       _s({"Pulse": False}),
                       _s({"Pulse": True}),
                       _s({"Pulse": False}),
                       _s({"Pulse": True}),
                       _s({"Pulse": False}),
                       _s(cycles=5, approx={"Freq": {"value": 3.0, "tol": 0.001}})]}],
    "T29": [{"name": "pack two INTs big-endian",
             "steps": [_s({"Val1": 4660, "Val2": -21555},
                          expect={"Payload": [18, 52, 171, 205]})]},
            {"name": "zero values",
             "steps": [_s({"Val1": 0, "Val2": 258},
                          expect={"Payload": [0, 0, 1, 2]})]}],
    "T30": [{"name": "elevator direction 3 floors",
             "steps": [_s({"CallFloor": 3, "AtFloor": 2}, expect={"MotorUp": True,  "MotorDown": False}),
                       _s({"CallFloor": 1, "AtFloor": 2}, expect={"MotorUp": False, "MotorDown": True}),
                       _s({"CallFloor": 2, "AtFloor": 2}, expect={"MotorUp": False, "MotorDown": False}),
                       _s({"CallFloor": 3, "AtFloor": 3}, expect={"MotorUp": False, "MotorDown": False})]}],
}
