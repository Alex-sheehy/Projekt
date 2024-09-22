import pandas as pd
import osmnx as ox
import re
import matplotlib.pylab as plt
import copy


def ladda_data(file_path):
    """
    Load Excel data and return a dictionary of dataframes.
    """
    # Load the Excel file from the given file path
    excel_data = pd.ExcelFile(file_path)
    
    # Parse the sheets into separate dataframes
    data = {
        'brukare': excel_data.parse('Individer, brukare', header=1),
        'medarbetare': excel_data.parse('Medarbetare', header=2)
    }

    return data

def rensa_brukar_data(brukare_df):
    """
    Rensar data på brukarna till endast rader där individ namn finns och ändrar så att
    det är "TRUE" eller "FALSE" på ja och nej datan
    """
    # Rename 'Unnamed: 0' to 'Individ' for brukare_df
    brukare_df.rename(columns={'Unnamed: 0': 'Individ'}, inplace=True)
   
    # Remove brukare with missing or invalid 'Individ' or 'Adress'
    brukare_df = brukare_df.dropna(subset=['Individ']).copy()
    
    # Fill missing values in other columns with placeholder '-'
    brukare_df.fillna('-', inplace=True)
    
    # Convert relevant columns to boolean
    brukare_df['Kräver körkort'] = brukare_df['Kräver körkort'].apply(lambda x: x == 'Ja')
    brukare_df['Röker'] = brukare_df['Röker'].apply(lambda x: x == 'Ja')
    brukare_df['Har hund'] = brukare_df['Har hund'].apply(lambda x: x == 'Ja')
    brukare_df['Har katt'] = brukare_df['Har katt'].apply(lambda x: x == 'Ja')
    brukare_df['Kräver >18'] = brukare_df['Kräver >18'].apply(lambda x: x == 'Ja')

    return brukare_df

def rensa_medarb_data(medarbetare_df):
    """
    Rensar medarbetar datan så att ja och nej blir istället "TRUE" eller "FALSE"
    """
    # Rename 'Unnamed: 0' to 'Medarbetare' for medarbetare_df
    medarbetare_df.rename(columns={'Unnamed: 0': 'Medarbetare'}, inplace=True)

    # Fill missing values in other columns with placeholder '-'
    medarbetare_df.fillna('-', inplace=True)
    
    columns_medarbetare = list(medarbetare_df)

    for column in columns_medarbetare[1:]:
        medarbetare_df[column] = medarbetare_df[column].apply(lambda x: x == 'Ja')

    return medarbetare_df

def skapa_brukare_dict(brukare_df,tider,regex_filters):
    """
    Skapar en dict med data om brukarna i det givna tidsfönstret
    """
    index = 0
    brukare_dict = {}
    for tid in tider:
        regex_filter = regex_filters[index]
        tidsfönster_brukare_dict = {}
        #Tar ut individers krav under detta tidsfönster
        läkemedel = brukare_df[brukare_df["Behöver läkemedel"].str.contains(regex_filter, na=False)]
        insulin = brukare_df[brukare_df["Behöver insulin"].str.contains(regex_filter, na=False)]
        stomi = brukare_df[brukare_df["Har stomi"].str.contains(regex_filter, na=False)]
        dubbelbemanning_df = brukare_df[brukare_df[tid].str.contains(r'\*', na=False)]
        
        #Tar ut de individer som ska ha besök i detta tidsfönster
        individer = brukare_df[brukare_df[tid].apply(
            lambda x: isinstance(x, int) or 
            (isinstance(x, str) and bool(re.fullmatch(r"\d+\*\d+", x))))]

        for index, row in individer.iterrows():
            individ = row["Individ"]

            if läkemedel["Individ"].str.contains(individ, regex = False).any() == True:
                behöver_läkemedel = True
            else:
                behöver_läkemedel = False
        
            if insulin["Individ"].str.contains(individ, regex = False).any() == True:
                behöver_insulin = True
            else:
                behöver_insulin = False

            if stomi["Individ"].str.contains(individ, regex = False).any() == True:
                har_stomi = True
            else:
                har_stomi = False
            
            if dubbelbemanning_df["Individ"].str.contains(individ, regex = False).any() == True:
                dubbelbemanning = True
                dubbel_tid = row[tid].split('*')
                riktig_tid = dubbel_tid[0]
                #Skapar en dict som har en dict i sig för alla individer i detta tidsfönster
                tidsfönster_brukare_dict[individ] = {
                    "Tid": riktig_tid,
                    "Dubbelbemanning": dubbelbemanning,
                    "Behöver läkemedel": behöver_läkemedel,
                    "Kräver körkort": row["Kräver körkort"],
                    "Behöver insulin": behöver_insulin,
                    "Har stomi": har_stomi,
                    "Har hund": row["Har hund"],
                    "Har katt": row["Har katt"],
                    "Kräver>18": row["Kräver >18"],
                    "Kräver man": False,
                    "Kräver kvinna": False,
                    "Dusch": False,
                    "Aktivering": False
                }
            else:
                dubbelbemanning = False
                #Skapar en dict som har en dict i sig för alla individer i detta tidsfönster
                tidsfönster_brukare_dict[individ] = {
                    "Tid": row[tid],
                    "Dubbelbemanning": dubbelbemanning,
                    "Behöver läkemedel": behöver_läkemedel,
                    "Kräver körkort": row["Kräver körkort"],
                    "Behöver insulin": behöver_insulin,
                    "Har stomi": har_stomi,
                    "Har hund": row["Har hund"],
                    "Har katt": row["Har katt"],
                    "Kräver>18": row["Kräver >18"],
                    "Kräver man": False,
                    "Kräver kvinna": False,
                    "Dusch": False,
                    "Aktivering": False
                }
        
        brukare_dict[tid] = tidsfönster_brukare_dict
        index =+ 1

    return brukare_dict

def skapa_medarbetare_dict(medarbetare_df, tider, reges_filters):
    """
    Skapar en dict med data om medarbetarna för den givna tidsfönstret 
    """
    medarbetare_dict = {}
    index = 0
    for tid in tider: 
        tidsfönster_medarbetare_dict = {}
        reges_filter = reges_filters[index]

        for index, row in medarbetare_df.iterrows():
            medarbetare = row["Medarbetare"]

            #Skapar en dict som har en dict i sig för alla medarbetare
            tidsfönster_medarbetare_dict[medarbetare] = {
                "Tål hund": row["Tål hund"],
                "Tål katt": row["Tål katt"],
                "Man": row["Man"],
                "Kvinna": row["Kvinna"],
                "Körkort": row["Körkort"],
                "Läkemedelsdelegering": row["Läkemedelsdelegering"],
                "Insulindelegering": row["Insulindelegering"],
                "Stomidelegering":row["Stomidelegering"],        
                "18 år el mer": row["18 år el mer"]
            }

        medarbetare_dict[tid] = tidsfönster_medarbetare_dict
        index =+ 1
    return medarbetare_dict


def skapa_dag_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict, regex):
    """
    Skapar en dict för hela dagen. Där även den lägger in speciella villkor
    som gäller för det specefika dagen. 
    """
    dag_dict = {}
    tid_regex = r'\b\d{2}\b'
    #Uppdaterar för dusch villkor
    dusch_behov_df = brukare_df[brukare_df["Dusch"].str.contains(regex, na=False)]
    for index, row in dusch_behov_df.iterrows():
        dusch_tid = re.search(tid_regex,row["Dusch"])
        if dusch_tid == None:
            #Om det inte finns en bestämd duschtid så sätts det till 30 min
            dusch_tid = 30
        else:
            dusch_tid = int(dusch_tid.group())
        krav_på_man = "vid dusch" in row["Kräver man"]
        krav_på_kvinna = "vid dusch" in row["Kräver kvinna"]
        try:
            besök_tid = brukare_dag_dict["Förmiddag"][row["Individ"]]["Tid"]
            uppdaterad_besök_tid = int(besök_tid) + dusch_tid
            brukare_dag_dict["Förmiddag"][row["Individ"]]["Tid"] = uppdaterad_besök_tid
            brukare_dag_dict["Förmiddag"][row["Individ"]]["Kräver man"] = krav_på_man
            brukare_dag_dict["Förmiddag"][row["Individ"]]["Kräver kvinna"] = krav_på_kvinna
            brukare_dag_dict["Förmiddag"][row["Individ"]]["Dusch"] = True
        except KeyError:
            #om burkaren inte skulle få besök på fm så sätts det in ett
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

    #Uppdaterar för aktiverings villkor
    aktiverings_behov_df = brukare_df[brukare_df["Aktivering"].str.contains(regex, na=False)]
    for index, row in aktiverings_behov_df.iterrows():
        aktiverings_tid = re.search(tid_regex,row["Aktivering"])
        if aktiverings_tid == None:
            #Om det inte finns en bestämd aktiveringstid så sätts det till 30 min
            aktiverings_tid = 30
        else:
            aktiverings_tid = int(aktiverings_tid.group())
        try:
            besök_tid = brukare_dag_dict["Eftermiddag"][row["Individ"]]["Tid"]
            uppdaterad_besök_tid = int(besök_tid) + aktiverings_tid
            brukare_dag_dict["Eftermiddag"][row["Individ"]]["Tid"] = uppdaterad_besök_tid
            brukare_dag_dict["Eftermiddag"][row["Individ"]]["Aktivering"] = True
        except KeyError:
            #om burkaren inte skulle få besök på em så sätts det in ett
            brukare_dag_dict["Eftermiddag"][row["Individ"]] = {
                "Tid": dusch_tid,
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
            "Medarbetare": medarbetare_dag_dict}
    return dag_dict


def load_node_map():
    # Define the place name for Skellefteå Kommun
    place_name = "Skellefteå, Västerbotten, Sweden"

    # Download the road network for driving
    G = ox.graph_from_place(place_name, network_type='drive')

    # Plot the road network of Skellefteå
    fig, ax = ox.plot_graph(G, node_size=1, edge_color='white', edge_linewidth=0.1)
    plt.show()


def main():

    data = ladda_data("Studentuppgift fiktiv planering.xlsx")
    
    #Data rensning
    brukare_df = rensa_brukar_data(data["brukare"])
    medarbetare_df = rensa_medarb_data( data["medarbetare"])

    tid = ["Morgon", "Förmiddag", "Lunch", "Eftermiddag", "Middag", "Tidig kväll", "Sen kväll"]
    regex_tid_mönster = [ r'\b[mM]org\b', r'\b[fF]m\b', r'\b[lL]unch\b',  r'\b[eE]m\b', r'\b[mM]iddag\b', 
                         r'\b[tT]idig kväll\b', r'\b[sS]en kväll\b']
    #Skapar dicts för alla olika tidsfönster som besök kan ske med data om brukare
    brukare_dag_dict = skapa_brukare_dict(brukare_df, tid, regex_tid_mönster)

    #Skapa dicts för medarebetare och dess villkor, för de olika tidsfönstrena
    #TODO: Fixa då att det faktiskt är någon skillnad på medarbetarna mellan de olika tidsfönstrena
    medarbetare_dag_dict = skapa_medarbetare_dict(medarbetare_df, tid, regex_tid_mönster)

    #Skapar dicts för alla veckodagar
    regex_dag_mönster = [r'\b[mM]ån', r'\b[tT]is', r'\b[oO]ns', r'\b[tT]or', r'\b[fF]re']
    mån_dict = skapa_dag_dict(brukare_df, medarbetare_df, copy.deepcopy(brukare_dag_dict), medarbetare_dag_dict.copy(), regex_dag_mönster[0])
    tis_dict = skapa_dag_dict(brukare_df, medarbetare_df, copy.deepcopy(brukare_dag_dict), medarbetare_dag_dict.copy(), regex_dag_mönster[1])
    ons_dict = skapa_dag_dict(brukare_df, medarbetare_df, copy.deepcopy(brukare_dag_dict), medarbetare_dag_dict.copy(), regex_dag_mönster[2])
    tor_dict = skapa_dag_dict(brukare_df, medarbetare_df, copy.deepcopy(brukare_dag_dict), medarbetare_dag_dict.copy(), regex_dag_mönster[3])
    fre_dict = skapa_dag_dict(brukare_df, medarbetare_df, copy.deepcopy(brukare_dag_dict), medarbetare_dag_dict.copy(), regex_dag_mönster[4])

    vecko_dict = {"Måndag": mån_dict,
               "Tidag": tis_dict,
               "Onsdag": ons_dict,
               "Torsdag": tor_dict,
               "Fredag": fre_dict}
    
    for key, value in mån_dict["Brukare"]["Förmiddag"].items():
        print(f"{key}: {value}")
    
    #TODO fixa så att kartan kan användas på rätt sätt
    #loadNodeMap()
    
    #print(brukare_df)
    #print(brukare_df)
    #print(medarbetare_df)

if __name__ == '__main__':
    main()
