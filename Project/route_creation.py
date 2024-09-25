import re
from copy import deepcopy
from utils import check_visits

def skapa_brukare_dict(brukare_df, tider, regex_filters):
    """
    Create a dictionary of brukare for each time window.
    """
    brukare_dict = {}
    for index, tid in enumerate(tider):
        regex_filter = regex_filters[index]
        tidsfönster_brukare_dict = {}
        läkemedel = brukare_df[brukare_df["Behöver läkemedel"].str.contains(regex_filter, na=False)]
        insulin = brukare_df[brukare_df["Behöver insulin"].str.contains(regex_filter, na=False)]
        stomi = brukare_df[brukare_df["Har stomi"].str.contains(regex_filter, na=False)]
        dubbelbemanning_df = brukare_df[brukare_df[tid].str.contains(r'\*', na=False)]
        individer = brukare_df[brukare_df[tid].apply(
            lambda x: isinstance(x, int) or (isinstance(x, str) and bool(re.fullmatch(r"\d+\*\d+", x))))]

        for idx, row in individer.iterrows():
            individ = row["Individ"]
            behov_dict = {
                "Behöver läkemedel": läkemedel["Individ"].str.contains(individ, regex=False).any(),
                "Behöver insulin": insulin["Individ"].str.contains(individ, regex=False).any(),
                "Har stomi": stomi["Individ"].str.contains(individ, regex=False).any(),
                "Dubbelbemanning": dubbelbemanning_df["Individ"].str.contains(individ, regex=False).any()
            }
            dubbel_tid = row[tid].split('*') if behov_dict["Dubbelbemanning"] else [row[tid]]
            tidsfönster_brukare_dict[individ] = {
                "Tid": dubbel_tid[0],
                **behov_dict,
                "Kräver körkort": row["Kräver körkort"],
                "Har hund": row["Har hund"],
                "Har katt": row["Har katt"],
                "Kräver>18": row["Kräver >18"],
                "Kräver man": False,
                "Kräver kvinna": False,
                "Dusch": False,
                "Aktivering": False
            }
        brukare_dict[tid] = tidsfönster_brukare_dict
    return brukare_dict

def skapa_medarbetare_dict(medarbetare_df, tider, regex_filters):
    """
    Create a dictionary of medarbetare for each time window.
    """
    medarbetare_dict = {}
    for index, tid in enumerate(tider):
        tidsfönster_medarbetare_dict = {}
        for idx, row in medarbetare_df.iterrows():
            medarbetare = row["Medarbetare"]
            tidsfönster_medarbetare_dict[medarbetare] = {
                "Tål hund": row["Tål hund"],
                "Tål katt": row["Tål katt"],
                "Man": row["Man"],
                "Kvinna": row["Kvinna"],
                "Körkort": row["Körkort"],
                "Läkemedelsdelegering": row["Läkemedelsdelegering"],
                "Insulindelegering": row["Insulindelegering"],
                "Stomidelegering": row["Stomidelegering"],        
                "18 år el mer": row["18 år el mer"]
            }
        medarbetare_dict[tid] = tidsfönster_medarbetare_dict
    return medarbetare_dict

def skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex):
    """
    Create a dictionary representing the whole day with special conditions.
    """
    dag_dict = {}
    tid_regex = r'\b\d{2}\b'
    dusch_behov_df = brukare_df[brukare_df["Dusch"].str.contains(regex, na=False)]
    for index, row in dusch_behov_df.iterrows():
        dusch_tid = int(re.search(tid_regex, row["Dusch"]).group() if re.search(tid_regex, row["Dusch"]) else 30)
        krav_på_man = "vid dusch" in row["Kräver man"]
        krav_på_kvinna = "vid dusch" in row["Kräver kvinna"]
        try:
            brukare_dag_dict["Förmiddag"][row["Individ"]].update({
                "Tid": int(brukare_dag_dict["Förmiddag"][row["Individ"]]["Tid"]) + dusch_tid,
                "Kräver man": krav_på_man,
                "Kräver kvinna": krav_på_kvinna,
                "Dusch": True
            })
        except KeyError:
            brukare_dag_dict["Förmiddag"][row["Individ"]] = {
                "Tid": dusch_tid,
                "Dubbelbemanning": False,
                "Behöver läkemedel": False,
                "Kräver körkort": row["Kräver körkort"],
                "Behöver insulin": False,
                "Har stomi": False,
                "Har hund": row["Har hund"],
                "Har katt": row["Har katt"],
                "Kräver>18": row["Kräver >18"],
                "Kräver man": krav_på_man,
                "Kräver kvinna": krav_på_kvinna,
                "Dusch": True,
                "Aktivering": False
            }

    aktiverings_behov_df = brukare_df[brukare_df["Aktivering"].str.contains(regex, na=False)]
    for index, row in aktiverings_behov_df.iterrows():
        aktiverings_tid = int(re.search(tid_regex, row["Aktivering"]).group() if re.search(tid_regex, row["Aktivering"]) else 30)
        try:
            brukare_dag_dict["Eftermiddag"][row["Individ"]].update({
                "Tid": int(brukare_dag_dict["Eftermiddag"][row["Individ"]]["Tid"]) + aktiverings_tid,
                "Aktivering": True
            })
        except KeyError:
            brukare_dag_dict["Eftermiddag"][row["Individ"]] = {
                "Tid": aktiverings_tid,
                "Dubbelbemanning": False,
                "Behöver läkemedel": False,
                "Kräver körkort": row["Kräver körkort"],
                "Behöver insulin": False,
                "Har stomi": False,
                "Har hund": row["Har hund"],
                "Har katt": row["Har katt"],
                "Kräver>18": row["Kräver >18"],
                "Kräver man": False,
                "Kräver kvinna": False,
                "Dusch": False,
                "Aktivering": True
            }

    dag_dict = {
        "Brukare": brukare_dag_dict,
        "Medarbetare": medarbetare_dag_dict
    }
    return dag_dict

def create_weekly_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict):
    """
    Creates a dictionary for each weekday with the corresponding brukare and medarbetare.
    :param brukare_df: DataFrame of brukare data
    :param medarbetare_df: DataFrame of medarbetare data
    :param brukare_dag_dict: Dictionary of brukare per time period
    :param medarbetare_dag_dict: Dictionary of medarbetare per time period
    :return: Dictionary containing day-specific data
    """
    regex_dag_mönster = [r'\b[mM]ån', r'\b[tT]is', r'\b[oO]ns', r'\b[tT]or', r'\b[fF]re']
    days_dict = {
        "Måndag": skapa_dag_dict(brukare_df, medarbetare_df, deepcopy(brukare_dag_dict), deepcopy(medarbetare_dag_dict), regex_dag_mönster[0]),
        "Tisdag": skapa_dag_dict(brukare_df, medarbetare_df, deepcopy(brukare_dag_dict), deepcopy(medarbetare_dag_dict), regex_dag_mönster[1]),
        "Onsdag": skapa_dag_dict(brukare_df, medarbetare_df, deepcopy(brukare_dag_dict), deepcopy(medarbetare_dag_dict), regex_dag_mönster[2]),
        "Torsdag": skapa_dag_dict(brukare_df, medarbetare_df, deepcopy(brukare_dag_dict), deepcopy(medarbetare_dag_dict), regex_dag_mönster[3]),
        "Fredag": skapa_dag_dict(brukare_df, medarbetare_df, deepcopy(brukare_dag_dict), deepcopy(medarbetare_dag_dict), regex_dag_mönster[4]),
    }
    return days_dict