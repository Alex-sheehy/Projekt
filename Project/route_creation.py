from copy import deepcopy

def skapa_brukare_dict(brukare_df, tider, regex_filters):
    """
    Create a dictionary of brukare for each time window.
    """
    brukare_dict = {}
    for index, tid in enumerate(tider):
        brukare_dict[tid] = {}
        regex_filter = regex_filters[index]
        brukare_filtered = brukare_df[brukare_df[tid].astype(str).str.contains(regex_filter, na=False)]
        
        for _, row in brukare_filtered.iterrows():
                        brukare_dict[tid][row["Individ"]] = {
                "Duration": row[tid],
                "Constraints": row['Constraints'],
                "Kräver körkort": row["Kräver körkort"],
                "Har hund": row["Har hund"],
                "Har katt": row["Har katt"],
                "Behöver läkemedel": row["Behöver läkemedel"],
                "Behöver insulin": row["Behöver insulin"],
                "Har stomi": row["Har stomi"],
                "Dubbelbemanning": row["Dubbelbemanning"],
                "Dusch": row["Dusch"],
                "Aktivering": row["Aktivering"]
            }
    return brukare_dict

def skapa_medarbetare_dict(medarbetare_df, tider, regex_filters):
    """
    Create a dictionary of medarbetare for each time window.
    """
    medarbetare_dict = {}
    for tid in tider:
        medarbetare_dict[tid] = {}
        for _, row in medarbetare_df.iterrows():
            medarbetare_dict[tid][row["Medarbetare"]] = {
                "Capabilities": row['Capabilities'].split(',')
            }
    return medarbetare_dict

def skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex):
    """
    Create a daily dictionary incorporating special needs like Dusch and Aktivering.
    """
    dag_dict = {
        "Brukare": deepcopy(brukare_dag_dict),
        "Medarbetare": deepcopy(medarbetare_dag_dict)
    }

    # Adjust brukare dict for special requirements like Dusch and Aktivering
    for _, row in brukare_df.iterrows():
        if row["Dusch"]:
            dag_dict["Brukare"]["Förmiddag"][row["Individ"]]["Duration"] += 30
            dag_dict["Brukare"]["Förmiddag"][row["Individ"]]["Dusch"] = True
        if row["Aktivering"]:
            dag_dict["Brukare"]["Eftermiddag"][row["Individ"]]["Duration"] += 20
            dag_dict["Brukare"]["Eftermiddag"][row["Individ"]]["Aktivering"] = True

    return dag_dict

def create_weekly_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict):
    """
    Creates a weekly schedule dictionary incorporating brukare and medarbetare data.
    """
    regex_dag_mönster = [r'\b[mM]ån', r'\b[tT]is', r'\b[oO]ns', r'\b[tT]or', r'\b[fF]re']
    days_dict = {
        "Måndag": skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex_dag_mönster[0]),
        "Tisdag": skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex_dag_mönster[1]),
        "Onsdag": skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex_dag_mönster[2]),
        "Torsdag": skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex_dag_mönster[3]),
        "Fredag": skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex_dag_mönster[4]),
    }
    return days_dict
