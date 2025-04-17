import pandas as pd
import random
from datetime import datetime, timedelta

# Load data from CSV files
courses = pd.read_csv('courses_subjects.csv')
teachers = pd.read_csv('teachers.csv')
classrooms = pd.read_csv('classrooms.csv')
teacher_availability = pd.read_csv('teacher_availability.csv')
teacher_preferences = pd.read_csv('teacher_preferences.csv')

# Define timetable generation function
def generate_yearly_timetable(course, year, semester, start_date, end_date, holidays=[]):
    timetable = []
    subjects = courses[(courses['Course'] == course) & (courses['Year'] == year) & (courses['Semester'] == semester)]
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    time_slots = ['9:00-10:00', '10:00-11:00', '11:00-12:00', '1:00-2:00', '2:00-3:00']

    subject_hours = {subject['Subject']: subject['Weekly_Hours'] for _, subject in subjects.iterrows()}
    start_date = datetime.strptime(start_date, '%d-%b')
    end_date = datetime.strptime(end_date, '%d-%b')

    current_date = start_date
    week_count = 1

    

    while current_date <= end_date:
        if current_date.strftime('%A') in weekdays and current_date.strftime('%d-%b') not in holidays:
            day = current_date.strftime('%A')
            
            # Ensure break from 12:00-1:00
            timetable.append({'Week': week_count, 'Date': current_date.strftime('%d-%b'), 'Day': day, 'Time': '12:00-1:00', 'Subject': 'Break', 'Teacher': '-', 'Classroom': '-'} )
            scheduled_hours = {subject: 0 for subject in subject_hours}
            used_slots = set()

            for slot in time_slots:
                available_subjects = [s for s in subject_hours if scheduled_hours[s] < subject_hours[s]]

                # Avoid consecutive long classes
                if not available_subjects:
                    available_subjects = list(subject_hours.keys())
                subject = random.choice(available_subjects)
                if timetable and timetable[-1]['Subject'] == subject:
                    available_subjects.remove(subject)
                    if available_subjects:
                        subject = random.choice(available_subjects)

                teacher_candidates = teachers[teachers['Subject'] == subject]
                teacher = None

                # Prioritize preferred teachers
                preferred_teachers = teacher_preferences[(teacher_preferences['Subject'] == subject) & (teacher_preferences['Preferred_Day'] == day) & (teacher_preferences['Preferred_Time'] == slot)]
                if not preferred_teachers.empty:
                    teacher_candidates = teacher_candidates[teacher_candidates['Teacher Name'].isin(preferred_teachers['Teacher Name'])]

                # Assign available teacher
                for _, t in teacher_candidates.iterrows():
                    if teacher_availability.loc[(teacher_availability['Teacher Name'] == t['Teacher Name']) & (teacher_availability['Day'] == day) & (teacher_availability['Time'] == slot)].empty:
                        teacher = t
                        break

                # Fallback to substitute teacher
                if teacher is None:
                    substitute_teachers = teachers[teachers['Subject'] == subject]['Teacher Name'].tolist()
                    if substitute_teachers:
                        teacher = {'Teacher Name': random.choice(substitute_teachers) + ' (Substitute)'}
                    else:
                        teacher = {'Teacher Name': 'TBD'}

                # Assign appropriate classroom
                if 'Lab' in subject:
                    classroom_candidates = classrooms[(classrooms['Type'] == 'Lab') & (classrooms['Capacity'] >= 30)]
                else:
                    classroom_candidates = classrooms[(classrooms['Type'] == subjects[subjects['Subject'] == subject].iloc[0]['Classroom_Type']) & (classrooms['Capacity'] >= 30)]

                if classroom_candidates.empty:
                    classroom_candidates = classrooms[classrooms['Capacity'] >= 30]

                classroom = classroom_candidates.sample().iloc[0]

                # Prevent subject repetition in consecutive slots
                if (day, slot) in used_slots:
                    continue

                timetable.append({
                    'Week': week_count,
                    'Date': current_date.strftime('%d-%b'),
                    'Day': day,
                    'Time': slot,
                    'Subject': subject,
                    'Teacher': teacher['Teacher Name'],
                    'Classroom': classroom['Room Number']
                })
                scheduled_hours[subject] += 1
                used_slots.add((day, slot))

        # Move to the next day
        current_date += timedelta(days=1)
        if current_date.strftime('%A') == 'Monday':
            week_count += 1

    return timetable

# Generate timetable
course = "BSc Computer"
year = 2
semester = 3
start_date = '01-Jan'
end_date = '31-Dec'
holidays = ['15-Aug', '25-Dec']

ai_timetable = generate_yearly_timetable(course, year, semester, start_date, end_date, holidays)

# Export to Excel
pd.DataFrame(ai_timetable).to_excel('Yearly_Timetable01.xlsx', index=False)

print("Yearly timetable generated and saved as 'Yearly_Timetable.xlsx'")
