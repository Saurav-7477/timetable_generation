from ortools.sat.python import cp_model

# ==== SETUP ====

# Weekdays and periods
days = range(5)       # Monday to Friday
periods = range(4)    # 4 periods/day
timeslots = [(d, p) for d in days for p in periods]

# Classes/divisions
classes = ['6A', '6B']

# Subjects and assigned teachers
subjects = ['English', 'Math', 'Science', 'Marathi', 'History']
teachers = {
    'English': 'Ms. Khan',
    'Math': 'Mr. Patel',
    'Science': 'Ms. Rani',
    'Marathi': 'Mr. Patil',
    'History': 'Ms. Pooja'
}

# Sessions needed per subject per class per week
subject_periods_per_class = {subj: 3 for subj in subjects}

# ==== MODEL ====

model = cp_model.CpModel()

# subject_vars[(class, subject, day, period)] = BoolVar
subject_vars = {}
for cls in classes:
    for subj in subjects:
        for day, period in timeslots:
            subject_vars[(cls, subj, day, period)] = model.NewBoolVar(f'{cls}_{subj}_{day}_{period}')

# ==== CONSTRAINTS ====

# 1. Each subject must appear exactly 3 times per week per class
for cls in classes:
    for subj in subjects:
        model.Add(sum(subject_vars[(cls, subj, d, p)] for d, p in timeslots) == subject_periods_per_class[subj])

# 2. A class can have at most one subject per timeslot
for cls in classes:
    for d, p in timeslots:
        model.Add(sum(subject_vars[(cls, subj, d, p)] for subj in subjects) <= 1)

# 3. A teacher cannot be assigned to more than one class in the same timeslot
for subj, teacher in teachers.items():
    for d, p in timeslots:
        model.Add(sum(subject_vars[(cls, subj, d, p)] for cls in classes) <= 1)

# ==== SOLVER ====

solver = cp_model.CpSolver()
status = solver.Solve(model)

# ==== OUTPUT ====

if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
    for cls in classes:
        print(f'\n📘 Timetable for {cls}')
        for d in days:
            row = []
            for p in periods:
                found = False
                for subj in subjects:
                    if solver.Value(subject_vars[(cls, subj, d, p)]):
                        row.append(subj[:3])  # Show first 3 letters of subject
                        found = True
                        break
                if not found:
                    row.append('---')
            print(f'Day {d + 1}: {row}')
else:
    print("❌ No feasible timetable found.")
