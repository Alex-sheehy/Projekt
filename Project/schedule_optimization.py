import pandas as pd

def get_visit_duration(brukare_row, time_window):
    """
    Determines visit duration based on brukare needs and time window.
    """
    base_duration = brukare_row[time_window]
    total_duration = 0
    required_medarbetare = 1

    if '*' in str(base_duration):
        duration, multiplier = map(int, base_duration.split('*'))
        total_duration = duration * multiplier
        required_medarbetare = multiplier
    elif '+' in str(base_duration):
        durations = list(map(int, base_duration.split('+')))
        total_duration = max(durations)
        required_medarbetare = 2
    else:
        total_duration = int(base_duration)

    extra_time = 0
    if brukare_row['Dusch']:
        extra_time += 30
    if brukare_row['Aktivering']:
        extra_time += 20

    return total_duration + extra_time, required_medarbetare

def optimize_schedule(brukare_df, medarbetare_df, distance_matrix, brukare_dag_dict):
    """
    Optimizes the schedule for medarbetare based on brukare needs and constraints.
    """
    schedule = {day: {medarbetare: [] for medarbetare in medarbetare_df['Medarbetare']} for day in brukare_dag_dict.keys()}

    for day, brukare_for_day in brukare_dag_dict.items():
        for time_window, brukare_list in brukare_for_day.items():
            for brukare, details in brukare_list.items():
                brukare_row = brukare_df.loc[brukare_df['Individ'] == brukare]

                if not brukare_row.empty:
                    visit_duration, required_medarbetare = get_visit_duration(brukare_row.iloc[0], time_window)
                    available_medarbetare = find_available_medarbetare(schedule[day], medarbetare_df, brukare, time_window, required_medarbetare)

                    if len(available_medarbetare) >= required_medarbetare:
                        assign_visit(schedule[day], available_medarbetare[:required_medarbetare], brukare, visit_duration, time_window)

    return schedule

def find_available_medarbetare(day_schedule, medarbetare_df, brukare, time_window, required_medarbetare):
    """
    Finds available medarbetare who can fulfill the visit requirements.
    """
    available_medarbetare = []

    for medarbetare, visits in day_schedule.items():
        # Check if medarbetare is already booked during the requested time window
        if not any(visit['time_window'] == time_window for visit in visits):
            # Check other requirements if necessary (e.g., skills, gender requirements)
            medarbetare_row = medarbetare_df.loc[medarbetare_df['Medarbetare'] == medarbetare].iloc[0]
            if can_fulfill_requirements(medarbetare_row, brukare):
                available_medarbetare.append(medarbetare)

    return available_medarbetare

def assign_visit(day_schedule, medarbetare_list, brukare, visit_duration, time_window):
    """
    Assigns a visit to the specified medarbetare in the day schedule.
    """
    for medarbetare in medarbetare_list:
        day_schedule[medarbetare].append({
            'brukare': brukare,
            'duration': visit_duration,
            'time_window': time_window
        })

def can_fulfill_requirements(medarbetare_row, brukare):
    """
    Checks if a medarbetare can fulfill the visit requirements of a brukare.
    """
    # Add checks for skills, certifications, preferences, etc.
    # For example, return True if medarbetare has the required skills to meet brukare's needs
    return True  # Placeholder logic; assume medarbetare can fulfill all requirements for now

