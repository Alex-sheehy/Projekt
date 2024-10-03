import pandas as pd

SHIFT_PENALTIES = {
    'license': 100,
    'smoker': 10,
    'dog': 20,
    'cat': 20,
    '>18': 50,
    'man': 70,
    'woman': 70,
    'medication': 80,
    'insulin': 80,
    'stoma': 80,
    'double_staffing': 90,
    'shower': 60,
    'activation': 40
}

def assign_shifts(schedule, medarbetare_df, brukare_dag_dict):
    """
    Assign shifts to medarbetare based on the schedule, availability, and constraints.
    """
    final_schedule = {day: {'Första skift': [], 'Andra skift': []} for day in schedule}

    for day, day_schedule in schedule.items():
        brukare_list = [(brukare, details) for brukare, details in day_schedule.items() if details]

        # Sort brukare by penalties based on constraints
        brukare_sorted = sorted(
            brukare_list,
            key=lambda item: sum(SHIFT_PENALTIES.get(constraint.strip(), 0) 
                                 for constraint in (item[1]['Constraints'].split(',') if isinstance(item[1]['Constraints'], str) else [])),
            reverse=True
        )

        for brukare, details in brukare_sorted:
            # Check if the first shift is full
            if len(final_schedule[day]['Första skift']) < 9:
                final_schedule[day]['Första skift'].append(brukare)
            # Assign to the second shift if the first is full
            elif len(final_schedule[day]['Andra skift']) < 5:
                final_schedule[day]['Andra skift'].append(brukare)
            else:
                # All shifts are full; additional assignments are skipped
                print(f"Could not assign {brukare} on {day}, shifts are full.")

    return final_schedule
