import re

def kan_besoka(medarbetare, brukare):
    """
    Checks if a medarbetare can visit a brukare based on specific conditions.
    """
    # Check for driving license requirement
    if brukare['Kräver körkort'] and not medarbetare['Körkort']:
        return False

    # Check for pet compatibility
    if brukare['Har hund'] and not medarbetare['Tål hund']:
        return False
    if brukare['Har katt'] and not medarbetare['Tål katt']:
        return False

    # Check for gender requirements
    if brukare['Kräver man'] and not medarbetare['Man']:
        return False
    if brukare['Kräver kvinna'] and not medarbetare['Kvinna']:
        return False

    # Check if the medarbetare is at least 18 years old if required
    if brukare['Kräver>18'] and not medarbetare['18 år el mer']:
        return False

    # Check for medical delegation requirements
    if brukare['Behöver läkemedel'] and not medarbetare['Läkemedelsdelegering']:
        return False
    if brukare['Behöver insulin'] and not medarbetare['Insulindelegering']:
        return False
    if brukare['Har stomi'] and not medarbetare['Stomidelegering']:
        return False

    return True  # Medarbetare can visit brukare if none of the conditions fail

def check_visits(medarbetare_dict, brukare_dict):
    """
    Checks which medarbetare can visit which brukare based on the defined constraints.
    """
    visit_compatibility = {}
    for time_period, brukare_list in brukare_dict.items():
        visit_compatibility[time_period] = {}
        sorted_brukare = sorted(brukare_list.items(), key=lambda x: int(re.search(r'\d+', x[0]).group()))
        for brukare_name, brukare in sorted_brukare:
            compatible_medarbetare = []
            for medarbetare_name, medarbetare in medarbetare_dict[time_period].items():
                if kan_besoka(medarbetare, brukare):
                    compatible_medarbetare.append(medarbetare_name)
            visit_compatibility[time_period][brukare_name] = compatible_medarbetare

    return visit_compatibility
